"""
Trading Decision Store

Stores and retrieves trading decisions in Redis for frontend persistence.
Allows display of historical decisions after page refresh/restart.
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass
class TradingDecision:
    """
    Single trading decision record from ExecutorAgent.
    
    Stored in Redis with format: trading:decisions:<trade_id>
    """
    # Decision metadata
    trade_id: str
    timestamp: datetime
    trigger_reason: str = "scheduled"  # scheduled, manual, etc.
    
    # Decision result
    direction: str = "hold"  # hold, open_long, open_short, close_position
    confidence: int = 0
    leverage: int = 1
    reasoning: str = ""
    
    # Price info at decision time
    entry_price: float = 0.0
    tp_price: float = 0.0
    sl_price: float = 0.0
    amount_percent: float = 0.0
    
    # Context captured at decision time
    leader_summary: str = ""
    agent_votes: List[Dict[str, Any]] = field(default_factory=list)
    position_context: Dict[str, Any] = field(default_factory=dict)
    
    # Execution status
    was_executed: bool = False
    execution_error: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradingDecision':
        """Create from dictionary"""
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)
    
    def to_frontend_format(self) -> Dict[str, Any]:
        """Format for frontend display (Signal Details modal)"""
        return {
            "trade_id": self.trade_id,
            "timestamp": self.timestamp.isoformat(),
            "direction": self.direction.upper(),
            "confidence": self.confidence,
            "leverage": self.leverage,
            "reasoning": self.reasoning,
            "entry_price": self.entry_price,
            "tp_price": self.tp_price,
            "sl_price": self.sl_price,
            "leader_summary": self.leader_summary,
            "agent_votes": self.agent_votes,
            "position": self.position_context,
            "was_executed": self.was_executed,
        }


class TradingDecisionStore:
    """
    Redis store for trading decisions.
    
    Features:
    - Save decisions with automatic expiry (30 days)
    - Load recent decisions for frontend
    - Query by trade_id
    
    Key pattern: trading:decisions:<trade_id>
    List key for recent: trading:decisions:recent (LPUSH sorted list)
    """
    
    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
        self.key_prefix = "trading:decisions:"
        self.recent_list_key = "trading:decisions:recent"
        self.max_recent = 50  # Keep last 50 decisions in memory
        self.expiry_seconds = 30 * 24 * 3600  # 30 days
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            await self._redis.ping()
            logger.info("[TradingDecisionStore] Connected to Redis")
        except Exception as e:
            logger.warning(f"[TradingDecisionStore] Failed to connect to Redis: {e}")
            self._redis = None
    
    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
    
    async def save_decision(self, decision: TradingDecision) -> bool:
        """
        Save a trading decision to Redis.
        
        Returns True if saved successfully.
        """
        if not self._redis:
            await self.connect()
        
        if not self._redis:
            logger.warning("[TradingDecisionStore] Cannot save: no Redis connection")
            return False
        
        try:
            key = f"{self.key_prefix}{decision.trade_id}"
            decision_json = json.dumps(decision.to_dict(), ensure_ascii=False)
            
            # Save the decision with expiry
            await self._redis.set(key, decision_json, ex=self.expiry_seconds)
            
            # Add to recent list (for quick retrieval)
            await self._redis.lpush(self.recent_list_key, decision.trade_id)
            # Trim to keep only max_recent
            await self._redis.ltrim(self.recent_list_key, 0, self.max_recent - 1)
            
            logger.info(f"[TradingDecisionStore] Saved decision: {decision.trade_id} ({decision.direction})")
            return True
            
        except Exception as e:
            logger.error(f"[TradingDecisionStore] Error saving decision: {e}")
            return False
    
    async def get_decision(self, trade_id: str) -> Optional[TradingDecision]:
        """Get a specific decision by trade_id"""
        if not self._redis:
            await self.connect()
        
        if not self._redis:
            return None
        
        try:
            key = f"{self.key_prefix}{trade_id}"
            data = await self._redis.get(key)
            if data:
                return TradingDecision.from_dict(json.loads(data))
            return None
        except Exception as e:
            logger.error(f"[TradingDecisionStore] Error getting decision: {e}")
            return None
    
    async def get_recent_decisions(self, limit: int = 20) -> List[TradingDecision]:
        """
        Get most recent decisions (newest first).
        
        Args:
            limit: Maximum number of decisions to return
            
        Returns:
            List of TradingDecision objects
        """
        if not self._redis:
            await self.connect()
        
        if not self._redis:
            return []
        
        try:
            # Get trade_ids from recent list
            trade_ids = await self._redis.lrange(self.recent_list_key, 0, limit - 1)
            
            if not trade_ids:
                return []
            
            # Fetch each decision
            decisions = []
            for trade_id in trade_ids:
                decision = await self.get_decision(trade_id)
                if decision:
                    decisions.append(decision)
            
            return decisions
            
        except Exception as e:
            logger.error(f"[TradingDecisionStore] Error getting recent decisions: {e}")
            return []
    
    async def get_recent_decisions_for_frontend(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent decisions formatted for frontend display.
        
        Returns list of dicts ready for JSON response.
        """
        decisions = await self.get_recent_decisions(limit)
        return [d.to_frontend_format() for d in decisions]
    
    async def get_latest_decision(self) -> Optional[TradingDecision]:
        """Get the most recent decision"""
        decisions = await self.get_recent_decisions(limit=1)
        return decisions[0] if decisions else None


# Singleton instance for easy import
_decision_store: Optional[TradingDecisionStore] = None


async def get_decision_store(redis_url: str = "redis://redis:6379") -> TradingDecisionStore:
    """Get or create the decision store singleton"""
    global _decision_store
    if _decision_store is None:
        _decision_store = TradingDecisionStore(redis_url)
        await _decision_store.connect()
    return _decision_store
