"""
Redis-backed memory store.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List

try:
    import redis.asyncio as redis
except Exception:  # pragma: no cover
    redis = None

from .interface import MemoryHit, MemoryStore
from .noop_store import NoopMemoryStore

logger = logging.getLogger(__name__)


class RedisMemoryStore(MemoryStore):
    """Best-effort Redis memory store with graceful fallback."""

    def __init__(
        self,
        redis_url: str | None = None,
        key_prefix: str = "atomic:memory",
        max_items_per_bucket: int = 300,
        ttl_seconds: int | None = None,
    ) -> None:
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://redis:6379")
        self.key_prefix = key_prefix
        self.max_items = max(50, int(max_items_per_bucket))
        self.ttl_seconds = int(
            ttl_seconds
            if ttl_seconds is not None
            else os.getenv("ATOMIC_MEMORY_TTL_SECONDS", str(30 * 24 * 3600))
        )
        self._client = None
        self._fallback = NoopMemoryStore(max_items_per_bucket=max_items_per_bucket)
        self._degraded = False

    async def _ensure_client(self):
        if redis is None:
            self._degraded = True
            return None
        if self._client is not None:
            return self._client
        try:
            self._client = redis.from_url(self.redis_url, decode_responses=True)
            await self._client.ping()
            self._degraded = False
            return self._client
        except Exception as e:
            logger.warning("[AtomicMemory] Redis unavailable, fallback to noop: %s", e)
            self._degraded = True
            self._client = None
            return None

    def _agent_key(self, user_id: str, agent_id: str, collection: str) -> str:
        return f"{self.key_prefix}:u:{user_id}:a:{agent_id}:{collection}"

    def _shared_key(self, user_id: str) -> str:
        return f"{self.key_prefix}:u:{user_id}:shared:evidence"

    async def add_agent_memory(
        self,
        user_id: str,
        agent_id: str,
        content: str,
        metadata: Dict[str, Any] | None = None,
        collection: str = "episodic",
    ) -> str:
        record_id = uuid.uuid4().hex
        payload = {
            "id": record_id,
            "content": (content or "").strip(),
            "metadata": dict(metadata or {}),
            "ts": time.time(),
            "collection": collection,
        }
        if not payload["content"]:
            return record_id

        client = await self._ensure_client()
        if client is None:
            await self._fallback.add_agent_memory(user_id, agent_id, content, metadata, collection)
            return record_id

        key = self._agent_key(str(user_id), str(agent_id), str(collection))
        try:
            await client.lpush(key, json.dumps(payload, ensure_ascii=False))
            await client.ltrim(key, 0, self.max_items - 1)
            if self.ttl_seconds > 0:
                await client.expire(key, self.ttl_seconds)
            return record_id
        except Exception as e:
            logger.warning("[AtomicMemory] Redis write failed, fallback to noop: %s", e)
            self._degraded = True
            await self._fallback.add_agent_memory(user_id, agent_id, content, metadata, collection)
            return record_id

    async def query_agent_memory(
        self,
        user_id: str,
        agent_id: str,
        query: str,
        top_k: int = 3,
        collection: str = "episodic",
    ) -> List[MemoryHit]:
        q = (query or "").strip().lower()
        if not q:
            return []

        client = await self._ensure_client()
        if client is None:
            return await self._fallback.query_agent_memory(user_id, agent_id, query, top_k, collection)

        key = self._agent_key(str(user_id), str(agent_id), str(collection))
        try:
            rows = await client.lrange(key, 0, min(self.max_items - 1, 200))
        except Exception as e:
            logger.warning("[AtomicMemory] Redis read failed, fallback to noop: %s", e)
            self._degraded = True
            return await self._fallback.query_agent_memory(user_id, agent_id, query, top_k, collection)

        parsed = [self._safe_parse(row) for row in (rows or [])]
        ranked = sorted(parsed, key=lambda row: self._score_text(q, row.get("content", "")), reverse=True)
        hits: List[MemoryHit] = []
        for row in ranked[: max(1, top_k)]:
            score = self._score_text(q, row.get("content", ""))
            if score <= 0:
                continue
            hits.append(
                MemoryHit(
                    content=str(row.get("content", "")),
                    score=score,
                    metadata=dict(row.get("metadata") or {}),
                    collection=str(row.get("collection", collection)),
                )
            )
        return hits

    async def add_shared_evidence(
        self,
        user_id: str,
        content: str,
        metadata: Dict[str, Any] | None = None,
    ) -> str:
        record_id = uuid.uuid4().hex
        payload = {
            "id": record_id,
            "content": (content or "").strip(),
            "metadata": dict(metadata or {}),
            "ts": time.time(),
            "collection": "shared:evidence",
        }
        if not payload["content"]:
            return record_id

        client = await self._ensure_client()
        if client is None:
            await self._fallback.add_shared_evidence(user_id, content, metadata)
            return record_id

        key = self._shared_key(str(user_id))
        try:
            await client.lpush(key, json.dumps(payload, ensure_ascii=False))
            await client.ltrim(key, 0, self.max_items - 1)
            if self.ttl_seconds > 0:
                await client.expire(key, self.ttl_seconds)
            return record_id
        except Exception as e:
            logger.warning("[AtomicMemory] Redis evidence write failed, fallback to noop: %s", e)
            self._degraded = True
            await self._fallback.add_shared_evidence(user_id, content, metadata)
            return record_id

    async def query_shared_evidence(
        self,
        user_id: str,
        query: str,
        top_k: int = 3,
    ) -> List[MemoryHit]:
        q = (query or "").strip().lower()
        if not q:
            return []

        client = await self._ensure_client()
        if client is None:
            return await self._fallback.query_shared_evidence(user_id, query, top_k)

        key = self._shared_key(str(user_id))
        try:
            rows = await client.lrange(key, 0, min(self.max_items - 1, 200))
        except Exception as e:
            logger.warning("[AtomicMemory] Redis evidence read failed, fallback to noop: %s", e)
            self._degraded = True
            return await self._fallback.query_shared_evidence(user_id, query, top_k)

        parsed = [self._safe_parse(row) for row in (rows or [])]
        ranked = sorted(parsed, key=lambda row: self._score_text(q, row.get("content", "")), reverse=True)
        hits: List[MemoryHit] = []
        for row in ranked[: max(1, top_k)]:
            score = self._score_text(q, row.get("content", ""))
            if score <= 0:
                continue
            hits.append(
                MemoryHit(
                    content=str(row.get("content", "")),
                    score=score,
                    metadata=dict(row.get("metadata") or {}),
                    collection="shared:evidence",
                )
            )
        return hits

    async def health(self) -> Dict[str, Any]:
        if await self._ensure_client() is None:
            return {
                "provider": "redis",
                "degraded": True,
                "reason": "redis_unavailable",
            }
        return {
            "provider": "redis",
            "degraded": self._degraded,
        }

    @staticmethod
    def _safe_parse(row: str) -> Dict[str, Any]:
        try:
            data = json.loads(row)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {"content": str(row or ""), "metadata": {}}

    @staticmethod
    def _score_text(query: str, content: str) -> float:
        text = (content or "").lower()
        if not text:
            return 0.0
        if query in text:
            return 1.0
        q_tokens = {t for t in query.split() if t}
        if not q_tokens:
            return 0.0
        overlap = sum(1 for tok in q_tokens if tok in text)
        return overlap / max(1, len(q_tokens))
