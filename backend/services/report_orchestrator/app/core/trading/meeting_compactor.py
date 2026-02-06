"""
Meeting Compactor

Compresses conversation history in long meetings to prevent context rot.
Based on Anthropic's compaction strategy and Google ADK's context management.

Key strategies:
1. Keep recent N messages intact
2. Summarize older messages into concise bullet points
3. Preserve key decisions and data points
"""

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CompactionResult:
    """Result of message compaction"""
    original_count: int
    compacted_count: int
    summary_message: Dict[str, Any]
    recent_messages: List[Dict[str, Any]]
    tokens_saved: int


class MeetingCompactor:
    """
    Compress meeting conversation history.
    
    Anthropic Compaction Strategy:
    - When messages exceed threshold, summarize older ones
    - Keep recent messages for immediate context
    - Preserve key data points and decisions
    
    Usage:
        compactor = MeetingCompactor()
        
        if await compactor.should_compact(messages):
            result = await compactor.compact(messages)
            # result.summary_message + result.recent_messages
    """
    
    COMPACT_THRESHOLD = 15  # Trigger compaction after this many messages
    KEEP_RECENT = 5  # Keep this many recent messages unchanged
    SUMMARY_MAX_TOKENS = 300  # Maximum tokens for summary
    
    def __init__(self, llm_service=None, threshold: int = None, keep_recent: int = None):
        """
        Args:
            llm_service: Optional LLM for intelligent summarization
            threshold: Custom threshold for triggering compaction
            keep_recent: Custom count of recent messages to preserve
        """
        self.llm_service = llm_service
        self.threshold = threshold or self.COMPACT_THRESHOLD
        self.keep_recent = keep_recent or self.KEEP_RECENT
        self._stats = {
            "compactions": 0,
            "messages_compressed": 0,
            "tokens_saved": 0
        }
    
    async def should_compact(self, messages: List[Dict[str, Any]]) -> bool:
        """Check if messages should be compacted"""
        return len(messages) > self.threshold
    
    async def compact(self, messages: List[Dict[str, Any]]) -> CompactionResult:
        """
        Compact message history.
        
        Args:
            messages: List of message dicts with 'role', 'content' keys
            
        Returns:
            CompactionResult with summary + recent messages
        """
        if len(messages) <= self.keep_recent:
            # Nothing to compact
            return CompactionResult(
                original_count=len(messages),
                compacted_count=len(messages),
                summary_message={},
                recent_messages=messages,
                tokens_saved=0
            )
        
        # Split into old (to summarize) and recent (to keep)
        old_messages = messages[:-self.keep_recent]
        recent_messages = messages[-self.keep_recent:]
        
        # Calculate original token count
        original_tokens = self._estimate_tokens(old_messages)
        
        # Generate summary
        summary = await self._summarize_messages(old_messages)
        
        # Calculate compressed token count
        compressed_tokens = len(summary) // 4
        tokens_saved = original_tokens - compressed_tokens
        
        # Create summary message
        summary_message = {
            "role": "system",
            "content": f"[Earlier discussion summary ({len(old_messages)} messages compressed)]:\n{summary}",
            "metadata": {
                "type": "compaction_summary",
                "original_count": len(old_messages),
                "compacted_at": datetime.now().isoformat()
            }
        }
        
        # Update stats
        self._stats["compactions"] += 1
        self._stats["messages_compressed"] += len(old_messages)
        self._stats["tokens_saved"] += tokens_saved
        
        logger.info(f"[MeetingCompactor] Compacted {len(old_messages)} messages, "
                   f"saved {tokens_saved} tokens")
        
        return CompactionResult(
            original_count=len(messages),
            compacted_count=1 + len(recent_messages),
            summary_message=summary_message,
            recent_messages=recent_messages,
            tokens_saved=tokens_saved
        )
    
    async def _summarize_messages(self, messages: List[Dict[str, Any]]) -> str:
        """
        Summarize a list of messages.
        
        Strategy:
        1. If LLM available, use it for intelligent summarization
        2. Otherwise, extract key points rule-based
        """
        if self.llm_service:
            try:
                return await self._llm_summarize(messages)
            except Exception as e:
                logger.warning(f"LLM summarization failed: {e}, using rule-based")
        
        return self._rule_based_summarize(messages)
    
    async def _llm_summarize(self, messages: List[Dict[str, Any]]) -> str:
        """Use LLM for intelligent summarization"""
        # Format messages for summarization
        content = "\n".join([
            f"[{msg.get('role', 'unknown')}]: {msg.get('content', '')[:500]}"
            for msg in messages
        ])
        
        prompt = f"""Summarize the key points from this trading meeting discussion concisely.

DISCUSSION:
{content[:4000]}

OUTPUT FORMAT (bullet points, max 200 words):
- Key market observations
- Important data points mentioned
- Decisions or recommendations made
- Open questions or concerns

SUMMARY:"""
        
        response = await self.llm_service.generate(
            prompt,
            temperature=0.3,
            max_tokens=300
        )
        
        return response.strip()
    
    def _rule_based_summarize(self, messages: List[Dict[str, Any]]) -> str:
        """Rule-based extraction of key points"""
        key_points = []
        data_points = []
        decisions = []
        
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "unknown")
            
            # Skip very short messages
            if len(content) < 20:
                continue
            
            # Extract key patterns
            content_lower = content.lower()
            
            # Data points (numbers, percentages)
            import re
            numbers = re.findall(r'\$?[\d,]+\.?\d*%?', content)
            if numbers and len(numbers) <= 3:
                data_points.extend(numbers[:2])
            
            # Decisions/recommendations
            if any(word in content_lower for word in ["recommend", "suggest", "should", "decision", "conclude"]):
                # Extract first sentence as decision
                first_sentence = content.split('.')[0][:100]
                decisions.append(f"{role}: {first_sentence}")
            
            # Key observations
            elif any(word in content_lower for word in ["bullish", "bearish", "support", "resistance", "trend"]):
                first_sentence = content.split('.')[0][:80]
                key_points.append(first_sentence)
        
        # Build summary
        parts = []
        
        if decisions:
            parts.append("Decisions: " + "; ".join(decisions[:3]))
        
        if key_points:
            parts.append("Observations: " + "; ".join(key_points[:3]))
        
        if data_points:
            parts.append(f"Data: {', '.join(set(data_points[:5]))}")
        
        if not parts:
            parts.append(f"Discussion with {len(messages)} messages")
        
        return "\n".join(parts)
    
    def _estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Estimate token count for messages"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += len(content) // 4
        return total
    
    def get_stats(self) -> Dict[str, int]:
        """Get compaction statistics"""
        return self._stats.copy()


class MessageHistoryManager:
    """
    Manage message history with automatic compaction.
    
    Integrates MeetingCompactor into a simple API for TradingMeeting.
    
    Usage:
        manager = MessageHistoryManager(llm_service)
        
        # Add messages
        manager.add_message({"role": "user", "content": "..."})
        
        # Get compacted history for context
        history = await manager.get_compacted_history()
    """
    
    def __init__(self, llm_service=None, threshold: int = 15, keep_recent: int = 5):
        self.messages: List[Dict[str, Any]] = []
        self.compactor = MeetingCompactor(llm_service, threshold, keep_recent)
        self._compaction_summary: Optional[Dict[str, Any]] = None
    
    def add_message(self, message: Dict[str, Any]):
        """Add a message to history"""
        message["timestamp"] = datetime.now().isoformat()
        self.messages.append(message)
    
    async def get_compacted_history(self) -> List[Dict[str, Any]]:
        """
        Get message history, compacting if needed.
        
        Returns list starting with summary (if compacted) + recent messages
        """
        if await self.compactor.should_compact(self.messages):
            result = await self.compactor.compact(self.messages)
            
            # Store compaction result
            self._compaction_summary = result.summary_message
            
            # Return compacted history
            history = []
            if result.summary_message:
                history.append(result.summary_message)
            history.extend(result.recent_messages)
            return history
        
        return self.messages.copy()
    
    def clear(self):
        """Clear message history"""
        self.messages = []
        self._compaction_summary = None
    
    @property
    def message_count(self) -> int:
        return len(self.messages)
    
    @property
    def needs_compaction(self) -> bool:
        return len(self.messages) > self.compactor.threshold
