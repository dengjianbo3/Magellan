"""
Vote Domain Models

Represents agent votes and voting-related structures.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List


def _get_env_float(key: str, default: float) -> float:
    """Get float from environment variable"""
    val = os.getenv(key)
    if val:
        try:
            return float(val)
        except ValueError:
            pass
    return default


def _get_default_tp() -> float:
    """Get default take profit from env"""
    return _get_env_float("DEFAULT_TP_PERCENT", 8.0)


def _get_default_sl() -> float:
    """Get default stop loss from env"""
    return _get_env_float("DEFAULT_SL_PERCENT", 3.0)


class VoteDirection(Enum):
    """Possible vote directions."""
    LONG = "long"
    SHORT = "short"
    HOLD = "hold"
    CLOSE = "close"
    ADD_LONG = "add_long"
    ADD_SHORT = "add_short"
    
    @classmethod
    def from_string(cls, value: str) -> "VoteDirection":
        """
        Parse direction from string with normalization.
        
        Handles various input formats:
        - "long", "buy", "bullish" -> LONG
        - "short", "sell", "bearish" -> SHORT
        - "hold", "wait", "neutral" -> HOLD
        - "close", "exit" -> CLOSE
        """
        normalized = value.lower().strip()
        
        mapping = {
            # Long variants
            "long": cls.LONG,
            "buy": cls.LONG,
            "bullish": cls.LONG,
            "做多": cls.LONG,
            "开多": cls.LONG,
            "add_long": cls.ADD_LONG,
            "addlong": cls.ADD_LONG,
            
            # Short variants
            "short": cls.SHORT,
            "sell": cls.SHORT,
            "bearish": cls.SHORT,
            "做空": cls.SHORT,
            "开空": cls.SHORT,
            "add_short": cls.ADD_SHORT,
            "addshort": cls.ADD_SHORT,
            
            # Hold variants
            "hold": cls.HOLD,
            "wait": cls.HOLD,
            "neutral": cls.HOLD,
            "观望": cls.HOLD,
            "等待": cls.HOLD,
            
            # Close variants
            "close": cls.CLOSE,
            "exit": cls.CLOSE,
            "平仓": cls.CLOSE,
        }
        
        return mapping.get(normalized, cls.HOLD)
    
    @property
    def is_bullish(self) -> bool:
        """Check if direction is bullish."""
        return self in (VoteDirection.LONG, VoteDirection.ADD_LONG)
    
    @property
    def is_bearish(self) -> bool:
        """Check if direction is bearish."""
        return self in (VoteDirection.SHORT, VoteDirection.ADD_SHORT)
    
    @property
    def is_neutral(self) -> bool:
        """Check if direction is neutral."""
        return self in (VoteDirection.HOLD, VoteDirection.CLOSE)


@dataclass
class Vote:
    """
    A single vote from an agent.
    
    Contains the trading recommendation with confidence and risk parameters.
    TP/SL defaults read from DEFAULT_TP_PERCENT and DEFAULT_SL_PERCENT env vars.
    """
    direction: VoteDirection
    confidence: int  # 0-100
    leverage: int = 1  # 1-125
    take_profit_percent: float = field(default_factory=_get_default_tp)
    stop_loss_percent: float = field(default_factory=_get_default_sl)
    reasoning: str = ""
    
    def __post_init__(self):
        """Validate vote parameters."""
        # Clamp confidence to valid range
        self.confidence = max(0, min(100, self.confidence))
        
        # Clamp leverage to valid range
        self.leverage = max(1, min(125, self.leverage))
        
        # Ensure TP/SL are positive
        self.take_profit_percent = abs(self.take_profit_percent)
        self.stop_loss_percent = abs(self.stop_loss_percent)


@dataclass
class AgentVote:
    """
    Complete vote record from an agent.
    
    Extends Vote with agent identification and metadata.
    """
    agent_id: str
    agent_name: str
    vote: Vote
    raw_response: str = ""
    parse_method: str = "json"  # "json", "text_inference", "fallback"
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def direction(self) -> VoteDirection:
        return self.vote.direction
    
    @property
    def confidence(self) -> int:
        return self.vote.confidence
    
    @property
    def leverage(self) -> int:
        return self.vote.leverage
    
    @property
    def take_profit_percent(self) -> float:
        return self.vote.take_profit_percent
    
    @property
    def stop_loss_percent(self) -> float:
        return self.vote.stop_loss_percent
    
    @property
    def reasoning(self) -> str:
        return self.vote.reasoning
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "direction": self.direction.value,
            "confidence": self.confidence,
            "leverage": self.leverage,
            "take_profit_percent": self.take_profit_percent,
            "stop_loss_percent": self.stop_loss_percent,
            "reasoning": self.reasoning,
            "parse_method": self.parse_method,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class VoteSummary:
    """
    Aggregated summary of all agent votes.
    """
    votes: List[AgentVote]
    
    @property
    def total_count(self) -> int:
        return len(self.votes)
    
    @property
    def long_count(self) -> int:
        return sum(1 for v in self.votes if v.direction.is_bullish)
    
    @property
    def short_count(self) -> int:
        return sum(1 for v in self.votes if v.direction.is_bearish)
    
    @property
    def hold_count(self) -> int:
        return sum(1 for v in self.votes if v.direction == VoteDirection.HOLD)
    
    @property
    def close_count(self) -> int:
        return sum(1 for v in self.votes if v.direction == VoteDirection.CLOSE)
    
    @property
    def avg_confidence(self) -> float:
        if not self.votes:
            return 0.0
        return sum(v.confidence for v in self.votes) / len(self.votes)
    
    @property
    def avg_leverage(self) -> float:
        if not self.votes:
            return 1.0
        return sum(v.leverage for v in self.votes) / len(self.votes)
    
    @property
    def avg_take_profit_percent(self) -> float:
        if not self.votes:
            return _get_default_tp()
        return sum(v.take_profit_percent for v in self.votes) / len(self.votes)
    
    @property
    def avg_stop_loss_percent(self) -> float:
        if not self.votes:
            return _get_default_sl()
        return sum(v.stop_loss_percent for v in self.votes) / len(self.votes)
    
    @property
    def consensus_direction(self) -> VoteDirection:
        """Determine consensus direction based on vote counts."""
        if self.long_count > self.short_count and self.long_count >= 2:
            return VoteDirection.LONG
        elif self.short_count > self.long_count and self.short_count >= 2:
            return VoteDirection.SHORT
        elif self.close_count >= 2:
            return VoteDirection.CLOSE
        else:
            return VoteDirection.HOLD
    
    @property
    def consensus_strength(self) -> float:
        """Calculate consensus strength (0.0 - 1.0)."""
        if not self.votes:
            return 0.0
        max_count = max(self.long_count, self.short_count, self.hold_count)
        return max_count / len(self.votes)
    
    def to_string(self) -> str:
        """Format as human-readable summary."""
        return (
            f"Vote Summary: {self.long_count} Long / {self.short_count} Short / "
            f"{self.hold_count} Hold / {self.close_count} Close\n"
            f"Consensus: {self.consensus_direction.value} "
            f"(strength: {self.consensus_strength:.0%})\n"
            f"Avg Confidence: {self.avg_confidence:.1f}% | "
            f"Avg Leverage: {self.avg_leverage:.1f}x"
        )
