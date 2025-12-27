"""
File Memory

External memory system for storing full data outside context window.
Based on Manus AI's file system memory pattern.

Key features:
- Store full tool results with lightweight references
- On-demand retrieval when needed
- Automatic cleanup of old entries
"""

import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class MemoryReference:
    """Lightweight reference to stored data"""
    ref_id: str
    key: str
    created_at: str
    metadata: Dict[str, Any]
    size_bytes: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ref_id": self.ref_id,
            "key": self.key,
            "created_at": self.created_at,
            "metadata": self.metadata
        }


class FileMemory:
    """
    Redis-based external memory system.
    
    Mimics Manus AI's file system memory pattern:
    - Full data stored externally (Redis)
    - Lightweight references in context window
    - On-demand retrieval
    
    Usage:
        memory = FileMemory(redis_client)
        
        # Store full analysis
        ref_id = await memory.write("tech_analysis", full_analysis, {"agent": "technical"})
        
        # Get lightweight reference for context
        ref = await memory.get_reference(ref_id)
        # ref = {"ref_id": "memory:tech_analysis:abc123", "metadata": {...}}
        
        # Retrieve full data when needed
        full_data = await memory.read(ref_id)
    """
    
    PREFIX = "memory:"
    DEFAULT_TTL = 86400 * 7  # 7 days
    
    def __init__(self, redis_client=None, ttl_seconds: int = None):
        """
        Args:
            redis_client: Async Redis client
            ttl_seconds: Time-to-live for stored data
        """
        self.redis = redis_client
        self.ttl = ttl_seconds or self.DEFAULT_TTL
        self._stats = {
            "writes": 0,
            "reads": 0,
            "bytes_stored": 0
        }
    
    async def write(self, key: str, content: Any, metadata: Dict[str, Any] = None) -> str:
        """
        Write data to memory.
        
        Args:
            key: Logical key (e.g., "tech_analysis", "search_results")
            content: Data to store
            metadata: Optional metadata about the content
            
        Returns:
            Reference ID for retrieval
        """
        ref_id = f"{self.PREFIX}{key}:{uuid4().hex[:8]}"
        
        # Serialize content
        try:
            content_json = json.dumps(content, default=str, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize content: {e}")
            content_json = str(content)
        
        size_bytes = len(content_json.encode('utf-8'))
        
        # Store in Redis
        if self.redis:
            try:
                await self.redis.hset(ref_id, mapping={
                    "content": content_json,
                    "key": key,
                    "created_at": datetime.now().isoformat(),
                    "metadata": json.dumps(metadata or {}),
                    "size_bytes": str(size_bytes)
                })
                await self.redis.expire(ref_id, self.ttl)
                
                self._stats["writes"] += 1
                self._stats["bytes_stored"] += size_bytes
                
                logger.debug(f"[FileMemory] Stored {size_bytes} bytes as {ref_id}")
                
            except Exception as e:
                logger.error(f"[FileMemory] Write failed: {e}")
                return None
        else:
            # In-memory fallback for testing
            if not hasattr(self, '_memory'):
                self._memory = {}
            self._memory[ref_id] = {
                "content": content_json,
                "key": key,
                "created_at": datetime.now().isoformat(),
                "metadata": json.dumps(metadata or {}),
                "size_bytes": str(size_bytes)
            }
        
        return ref_id
    
    async def read(self, ref_id: str) -> Optional[Any]:
        """
        Read full data from memory.
        
        Args:
            ref_id: Reference ID from write()
            
        Returns:
            Original content, or None if not found
        """
        try:
            if self.redis:
                data = await self.redis.hgetall(ref_id)
            else:
                data = getattr(self, '_memory', {}).get(ref_id, {})
            
            if not data:
                logger.warning(f"[FileMemory] Not found: {ref_id}")
                return None
            
            # Handle bytes from Redis
            content = data.get("content", data.get(b"content"))
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            self._stats["reads"] += 1
            
            # Parse JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return content
                
        except Exception as e:
            logger.error(f"[FileMemory] Read failed: {e}")
            return None
    
    async def get_reference(self, ref_id: str) -> Optional[MemoryReference]:
        """
        Get lightweight reference (metadata only, no content).
        
        This is what should be included in context window.
        
        Args:
            ref_id: Reference ID
            
        Returns:
            MemoryReference with metadata
        """
        try:
            if self.redis:
                data = await self.redis.hgetall(ref_id)
            else:
                data = getattr(self, '_memory', {}).get(ref_id, {})
            
            if not data:
                return None
            
            # Handle bytes from Redis
            def decode(val):
                if isinstance(val, bytes):
                    return val.decode('utf-8')
                return val
            
            return MemoryReference(
                ref_id=ref_id,
                key=decode(data.get("key", data.get(b"key", ""))),
                created_at=decode(data.get("created_at", data.get(b"created_at", ""))),
                metadata=json.loads(decode(data.get("metadata", data.get(b"metadata", "{}")))),
                size_bytes=int(decode(data.get("size_bytes", data.get(b"size_bytes", 0))))
            )
            
        except Exception as e:
            logger.error(f"[FileMemory] Get reference failed: {e}")
            return None
    
    async def delete(self, ref_id: str) -> bool:
        """Delete stored data"""
        try:
            if self.redis:
                await self.redis.delete(ref_id)
            else:
                if hasattr(self, '_memory'):
                    self._memory.pop(ref_id, None)
            return True
        except Exception as e:
            logger.error(f"[FileMemory] Delete failed: {e}")
            return False
    
    async def list_by_key(self, key: str, limit: int = 10) -> List[MemoryReference]:
        """
        List references by key pattern.
        
        Args:
            key: Key prefix to search
            limit: Maximum number of results
            
        Returns:
            List of MemoryReference
        """
        pattern = f"{self.PREFIX}{key}:*"
        refs = []
        
        try:
            if self.redis:
                cursor = 0
                while len(refs) < limit:
                    cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                    for key in keys[:limit - len(refs)]:
                        ref = await self.get_reference(key.decode() if isinstance(key, bytes) else key)
                        if ref:
                            refs.append(ref)
                    if cursor == 0:
                        break
            else:
                for ref_id in list(getattr(self, '_memory', {}).keys())[:limit]:
                    if ref_id.startswith(f"{self.PREFIX}{key}:"):
                        ref = await self.get_reference(ref_id)
                        if ref:
                            refs.append(ref)
            
        except Exception as e:
            logger.error(f"[FileMemory] List failed: {e}")
        
        return refs
    
    async def cleanup_old(self, max_age_hours: int = 24) -> int:
        """
        Clean up entries older than max_age_hours.
        
        Returns:
            Number of entries deleted
        """
        deleted = 0
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        try:
            if self.redis:
                cursor = 0
                while True:
                    cursor, keys = await self.redis.scan(cursor, match=f"{self.PREFIX}*", count=100)
                    for key in keys:
                        ref = await self.get_reference(key.decode() if isinstance(key, bytes) else key)
                        if ref and ref.created_at:
                            try:
                                created = datetime.fromisoformat(ref.created_at)
                                if created < cutoff:
                                    await self.delete(ref.ref_id)
                                    deleted += 1
                            except ValueError:
                                pass
                    if cursor == 0:
                        break
                        
        except Exception as e:
            logger.error(f"[FileMemory] Cleanup failed: {e}")
        
        logger.info(f"[FileMemory] Cleaned up {deleted} old entries")
        return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        return self._stats.copy()


# Global instance for convenience
_file_memory: Optional[FileMemory] = None


def get_file_memory(redis_client=None) -> FileMemory:
    """Get or create global FileMemory instance"""
    global _file_memory
    if _file_memory is None:
        _file_memory = FileMemory(redis_client)
    return _file_memory
