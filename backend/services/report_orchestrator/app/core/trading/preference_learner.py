"""
User Preference Learner

Learns user trading preferences from SEMI_AUTO confirmation/rejection patterns.
Adapts trade suggestions to match user's risk tolerance and style.

Phase 3.3 of the architecture evolution roadmap.

Learns:
- Preferred leverage range
- Risk tolerance (TP/SL ratios)
- Direction bias (long/short preference)
- Confidence threshold for action
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
import os
import json

import redis.asyncio as redis
import structlog

from .trading_config import get_infra_config

logger = structlog.get_logger(__name__)


@dataclass
class UserPreferences:
    """Learned user preferences."""
    user_id: str = "default"
    
    # Leverage preferences
    avg_accepted_leverage: float = 5.0
    min_accepted_leverage: int = 1
    max_accepted_leverage: int = 20
    
    # Direction preferences
    long_accept_rate: float = 0.5  # How often user accepts long trades
    short_accept_rate: float = 0.5
    direction_bias: str = "neutral"  # "long_bias", "short_bias", "neutral"
    
    # Risk preferences
    avg_accepted_sl: float = 3.0  # Average accepted stop-loss %
    avg_accepted_tp: float = 6.0  # Average accepted take-profit %
    risk_reward_ratio: float = 2.0
    
    # Confidence threshold
    min_accepted_confidence: int = 60  # Minimum confidence user accepts
    
    # Stats
    total_decisions: int = 0
    confirmed_count: int = 0
    rejected_count: int = 0
    modified_count: int = 0
    
    last_updated: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "leverage": {
                "average": round(self.avg_accepted_leverage, 1),
                "min": self.min_accepted_leverage,
                "max": self.max_accepted_leverage,
            },
            "direction": {
                "long_accept_rate": round(self.long_accept_rate, 2),
                "short_accept_rate": round(self.short_accept_rate, 2),
                "bias": self.direction_bias,
            },
            "risk": {
                "avg_stop_loss": round(self.avg_accepted_sl, 1),
                "avg_take_profit": round(self.avg_accepted_tp, 1),
                "risk_reward_ratio": round(self.risk_reward_ratio, 2),
            },
            "confidence": {
                "min_accepted": self.min_accepted_confidence,
            },
            "stats": {
                "total_decisions": self.total_decisions,
                "confirmed": self.confirmed_count,
                "rejected": self.rejected_count,
                "modified": self.modified_count,
                "confirm_rate": round(self.confirmed_count / max(1, self.total_decisions) * 100, 1),
            },
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


@dataclass 
class TradeDecision:
    """Record of a user trade decision."""
    trade_id: str
    user_id: str
    timestamp: datetime
    
    # Original signal
    direction: str
    leverage: int
    confidence: int
    stop_loss_percent: float
    take_profit_percent: float
    
    # Decision
    action: str  # "confirmed", "rejected", "modified", "expired"
    
    # Modifications (if any)
    modified_leverage: Optional[int] = None
    modified_sl: Optional[float] = None
    modified_tp: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "original": {
                "direction": self.direction,
                "leverage": self.leverage,
                "confidence": self.confidence,
                "stop_loss_percent": self.stop_loss_percent,
                "take_profit_percent": self.take_profit_percent,
            },
            "action": self.action,
            "modifications": {
                "leverage": self.modified_leverage,
                "stop_loss": self.modified_sl,
                "take_profit": self.modified_tp,
            } if self.action == "modified" else None,
        }


class UserPreferenceLearner:
    """
    Learns user preferences from trade decisions.
    
    Updates preferences in real-time as user confirms/rejects trades.
    """
    
    REDIS_KEY_PREFS = "user_preferences:"
    REDIS_KEY_DECISIONS = "user_decisions:"
    LEARNING_RATE = 0.1  # How fast to adapt (0-1)
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self._prefs_cache: Dict[str, UserPreferences] = {}

    async def _ensure_redis(self) -> Optional[redis.Redis]:
        """Ensure Redis connection exists."""
        if self.redis is None:
            redis_url = get_infra_config().redis_url
            try:
                self.redis = redis.from_url(redis_url, decode_responses=True)
                await self.redis.ping()
            except Exception as e:
                logger.warning("preference_learner_redis_failed", error=str(e))
                return None
        return self.redis
    
    async def get_preferences(self, user_id: str = "default") -> UserPreferences:
        """Get learned preferences for a user."""
        # Check cache
        if user_id in self._prefs_cache:
            return self._prefs_cache[user_id]
        
        try:
            redis_client = await self._ensure_redis()
            if redis_client:
                key = f"{self.REDIS_KEY_PREFS}{user_id}"
                data = await redis_client.get(key)
                if data:
                    prefs_dict = json.loads(data)
                    prefs = self._dict_to_preferences(prefs_dict, user_id)
                    self._prefs_cache[user_id] = prefs
                    return prefs
        except Exception as e:
            logger.error("get_preferences_failed", user_id=user_id, error=str(e))
        
        return UserPreferences(user_id=user_id)
    
    def _dict_to_preferences(self, d: Dict, user_id: str) -> UserPreferences:
        """Convert dict to UserPreferences."""
        return UserPreferences(
            user_id=user_id,
            avg_accepted_leverage=d.get("avg_accepted_leverage", 5.0),
            min_accepted_leverage=d.get("min_accepted_leverage", 1),
            max_accepted_leverage=d.get("max_accepted_leverage", 20),
            long_accept_rate=d.get("long_accept_rate", 0.5),
            short_accept_rate=d.get("short_accept_rate", 0.5),
            direction_bias=d.get("direction_bias", "neutral"),
            avg_accepted_sl=d.get("avg_accepted_sl", 3.0),
            avg_accepted_tp=d.get("avg_accepted_tp", 6.0),
            risk_reward_ratio=d.get("risk_reward_ratio", 2.0),
            min_accepted_confidence=d.get("min_accepted_confidence", 60),
            total_decisions=d.get("total_decisions", 0),
            confirmed_count=d.get("confirmed_count", 0),
            rejected_count=d.get("rejected_count", 0),
            modified_count=d.get("modified_count", 0),
            last_updated=datetime.fromisoformat(d["last_updated"]) if d.get("last_updated") else None,
        )
    
    async def record_decision(
        self,
        trade_id: str,
        user_id: str,
        direction: str,
        leverage: int,
        confidence: int,
        stop_loss_percent: float,
        take_profit_percent: float,
        action: str,  # "confirmed", "rejected", "modified", "expired"
        modified_leverage: Optional[int] = None,
        modified_sl: Optional[float] = None,
        modified_tp: Optional[float] = None,
    ) -> UserPreferences:
        """
        Record a user's trade decision and update preferences.
        
        Returns updated preferences.
        """
        decision = TradeDecision(
            trade_id=trade_id,
            user_id=user_id,
            timestamp=datetime.now(),
            direction=direction,
            leverage=leverage,
            confidence=confidence,
            stop_loss_percent=stop_loss_percent,
            take_profit_percent=take_profit_percent,
            action=action,
            modified_leverage=modified_leverage,
            modified_sl=modified_sl,
            modified_tp=modified_tp,
        )
        
        # Get current preferences
        prefs = await self.get_preferences(user_id)
        
        # Update preferences based on decision
        prefs = self._update_preferences(prefs, decision)
        
        # Persist
        await self._save_preferences(prefs)
        await self._save_decision(decision)
        
        logger.info(
            "user_decision_recorded",
            user_id=user_id,
            trade_id=trade_id,
            action=action,
            confirm_rate=f"{prefs.confirmed_count}/{prefs.total_decisions}"
        )
        
        return prefs
    
    def _update_preferences(
        self, 
        prefs: UserPreferences, 
        decision: TradeDecision
    ) -> UserPreferences:
        """Update preferences based on a new decision."""
        prefs.total_decisions += 1
        prefs.last_updated = datetime.now()
        
        if decision.action == "confirmed":
            prefs.confirmed_count += 1
            self._learn_from_confirmed(prefs, decision)
            
        elif decision.action == "rejected":
            prefs.rejected_count += 1
            self._learn_from_rejected(prefs, decision)
            
        elif decision.action == "modified":
            prefs.modified_count += 1
            prefs.confirmed_count += 1  # Modified still executed
            self._learn_from_modified(prefs, decision)
        
        # Update direction bias
        long_rate = prefs.long_accept_rate
        short_rate = prefs.short_accept_rate
        
        if long_rate > short_rate + 0.15:
            prefs.direction_bias = "long_bias"
        elif short_rate > long_rate + 0.15:
            prefs.direction_bias = "short_bias"
        else:
            prefs.direction_bias = "neutral"
        
        # Update risk/reward ratio
        if prefs.avg_accepted_sl > 0:
            prefs.risk_reward_ratio = prefs.avg_accepted_tp / prefs.avg_accepted_sl
        
        return prefs
    
    def _learn_from_confirmed(
        self, 
        prefs: UserPreferences, 
        decision: TradeDecision
    ):
        """Learn from a confirmed trade."""
        lr = self.LEARNING_RATE
        
        # Update leverage preference
        prefs.avg_accepted_leverage = (
            prefs.avg_accepted_leverage * (1 - lr) + 
            decision.leverage * lr
        )
        
        # Update direction accept rate
        if decision.direction.lower() in ("long", "open_long"):
            prefs.long_accept_rate = prefs.long_accept_rate * (1 - lr) + 1.0 * lr
        else:
            prefs.short_accept_rate = prefs.short_accept_rate * (1 - lr) + 1.0 * lr
        
        # Update SL/TP preferences
        prefs.avg_accepted_sl = (
            prefs.avg_accepted_sl * (1 - lr) + 
            decision.stop_loss_percent * lr
        )
        prefs.avg_accepted_tp = (
            prefs.avg_accepted_tp * (1 - lr) + 
            decision.take_profit_percent * lr
        )
        
        # Update confidence threshold (lower it slightly when user accepts)
        if decision.confidence < prefs.min_accepted_confidence:
            prefs.min_accepted_confidence = int(
                prefs.min_accepted_confidence * (1 - lr) + 
                decision.confidence * lr
            )
    
    def _learn_from_rejected(
        self, 
        prefs: UserPreferences, 
        decision: TradeDecision
    ):
        """Learn from a rejected trade."""
        lr = self.LEARNING_RATE
        
        # Update direction reject (lower accept rate)
        if decision.direction.lower() in ("long", "open_long"):
            prefs.long_accept_rate = prefs.long_accept_rate * (1 - lr) + 0.0 * lr
        else:
            prefs.short_accept_rate = prefs.short_accept_rate * (1 - lr) + 0.0 * lr
        
        # Raise confidence threshold when user rejects
        if decision.confidence < prefs.min_accepted_confidence + 10:
            prefs.min_accepted_confidence = min(90, prefs.min_accepted_confidence + 2)
    
    def _learn_from_modified(
        self, 
        prefs: UserPreferences, 
        decision: TradeDecision
    ):
        """Learn from a modified trade."""
        lr = self.LEARNING_RATE * 1.5  # Stronger learning from explicit edits
        
        # Learn from modifications
        if decision.modified_leverage:
            prefs.avg_accepted_leverage = (
                prefs.avg_accepted_leverage * (1 - lr) + 
                decision.modified_leverage * lr
            )
        
        if decision.modified_sl:
            prefs.avg_accepted_sl = (
                prefs.avg_accepted_sl * (1 - lr) + 
                decision.modified_sl * lr
            )
        
        if decision.modified_tp:
            prefs.avg_accepted_tp = (
                prefs.avg_accepted_tp * (1 - lr) + 
                decision.modified_tp * lr
            )
    
    async def _save_preferences(self, prefs: UserPreferences) -> None:
        """Save preferences to Redis."""
        try:
            redis_client = await self._ensure_redis()
            if redis_client:
                key = f"{self.REDIS_KEY_PREFS}{prefs.user_id}"
                data = {
                    "avg_accepted_leverage": prefs.avg_accepted_leverage,
                    "min_accepted_leverage": prefs.min_accepted_leverage,
                    "max_accepted_leverage": prefs.max_accepted_leverage,
                    "long_accept_rate": prefs.long_accept_rate,
                    "short_accept_rate": prefs.short_accept_rate,
                    "direction_bias": prefs.direction_bias,
                    "avg_accepted_sl": prefs.avg_accepted_sl,
                    "avg_accepted_tp": prefs.avg_accepted_tp,
                    "risk_reward_ratio": prefs.risk_reward_ratio,
                    "min_accepted_confidence": prefs.min_accepted_confidence,
                    "total_decisions": prefs.total_decisions,
                    "confirmed_count": prefs.confirmed_count,
                    "rejected_count": prefs.rejected_count,
                    "modified_count": prefs.modified_count,
                    "last_updated": prefs.last_updated.isoformat() if prefs.last_updated else None,
                }
                await redis_client.set(key, json.dumps(data))
                self._prefs_cache[prefs.user_id] = prefs
        except Exception as e:
            logger.error("save_preferences_failed", user=prefs.user_id, error=str(e))
    
    async def _save_decision(self, decision: TradeDecision) -> None:
        """Save decision to Redis list."""
        try:
            redis_client = await self._ensure_redis()
            if redis_client:
                key = f"{self.REDIS_KEY_DECISIONS}{decision.user_id}"
                await redis_client.lpush(key, json.dumps(decision.to_dict()))
                # Keep last 100 decisions
                await redis_client.ltrim(key, 0, 99)
        except Exception as e:
            logger.error("save_decision_failed", error=str(e))
    
    async def get_recent_decisions(
        self, 
        user_id: str = "default", 
        limit: int = 20
    ) -> List[Dict]:
        """Get recent decisions for a user."""
        try:
            redis_client = await self._ensure_redis()
            if redis_client:
                key = f"{self.REDIS_KEY_DECISIONS}{user_id}"
                decisions = await redis_client.lrange(key, 0, limit - 1)
                return [json.loads(d) for d in decisions]
        except Exception as e:
            logger.error("get_decisions_failed", error=str(e))
        return []
    
    def suggest_adjustments(
        self, 
        prefs: UserPreferences, 
        signal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Suggest adjustments to a signal based on user preferences.
        
        Returns suggested modifications.
        """
        suggestions = {}
        
        direction = signal.get("direction", "").lower()
        leverage = signal.get("leverage", 5)
        confidence = signal.get("confidence", 50)
        sl = signal.get("stop_loss_percent", 3)
        tp = signal.get("take_profit_percent", 6)
        
        # Suggest leverage adjustment
        if leverage > prefs.avg_accepted_leverage * 1.5:
            suggestions["leverage"] = {
                "original": leverage,
                "suggested": int(prefs.avg_accepted_leverage),
                "reason": "User typically prefers lower leverage"
            }
        elif leverage < prefs.avg_accepted_leverage * 0.5:
            suggestions["leverage"] = {
                "original": leverage,
                "suggested": int(prefs.avg_accepted_leverage),
                "reason": "User typically uses higher leverage"
            }
        
        # Suggest based on direction bias
        if prefs.direction_bias == "long_bias" and direction in ("short", "open_short"):
            suggestions["direction_warning"] = "User has long bias, may reject shorts"
        elif prefs.direction_bias == "short_bias" and direction in ("long", "open_long"):
            suggestions["direction_warning"] = "User has short bias, may reject longs"
        
        # Confidence warning
        if confidence < prefs.min_accepted_confidence:
            suggestions["confidence_warning"] = {
                "signal_confidence": confidence,
                "user_threshold": prefs.min_accepted_confidence,
                "message": "Below user's typical acceptance threshold"
            }
        
        # SL/TP suggestions
        if sl > prefs.avg_accepted_sl * 1.5:
            suggestions["stop_loss"] = {
                "original": sl,
                "suggested": round(prefs.avg_accepted_sl, 1),
                "reason": "Tighter than user's typical SL"
            }
        
        return suggestions
    
    async def reset_preferences(self, user_id: str = "default") -> UserPreferences:
        """Reset user preferences to defaults."""
        prefs = UserPreferences(user_id=user_id)
        await self._save_preferences(prefs)
        logger.info("user_preferences_reset", user_id=user_id)
        return prefs


# Singleton instance
_preference_learner: Optional[UserPreferenceLearner] = None


def get_preference_learner() -> UserPreferenceLearner:
    """Get singleton UserPreferenceLearner instance."""
    global _preference_learner
    if _preference_learner is None:
        _preference_learner = UserPreferenceLearner()
    return _preference_learner


async def get_user_preferences(user_id: str = "default") -> UserPreferences:
    """Convenience function to get user preferences."""
    return await get_preference_learner().get_preferences(user_id)
