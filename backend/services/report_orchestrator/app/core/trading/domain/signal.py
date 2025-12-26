"""
TradingSignal Domain Model

Represents the final trading decision from a meeting.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
from .vote import VoteDirection, AgentVote, VoteSummary


@dataclass
class TradingSignal:
    """
    Final trading signal from a trading meeting.
    
    Contains all information needed to execute a trade and track its origin.
    """
    # Core decision
    direction: VoteDirection
    symbol: str = "BTC-USDT-SWAP"
    
    # Position parameters
    leverage: int = 1
    amount_percent: float = 0.2  # 0.0-1.0 (portion of available margin)
    entry_price: float = 0.0
    
    # Risk management
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_percent: float = 5.0
    stop_loss_percent: float = 2.0
    
    # Confidence metrics
    confidence: int = 50  # 0-100
    consensus_strength: float = 0.0  # 0.0-1.0
    
    # Reasoning and context
    reasoning: str = ""
    leader_summary: str = ""
    
    # Vote details
    agents_consensus: Dict[str, str] = field(default_factory=dict)
    votes: List[AgentVote] = field(default_factory=list)
    
    # Metadata
    meeting_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    trigger_reason: str = "scheduled"  # "scheduled", "manual", "position_closed"
    
    def __post_init__(self):
        """
        Calculate dependent fields if not set.
        
        CRITICAL: TP/SL percentages represent MARGIN loss/gain, not price movement.
        With leverage, actual price movement = margin_percent / leverage
        
        Example: 5x leverage, 2% margin stop loss
        - Price move needed = 2% / 5 = 0.4%
        - So SL price = entry * (1 - 0.4%)
        """
        if self.entry_price > 0 and self.leverage > 0:
            # Adjust percentages for leverage
            # TP/SL percent is margin-based, convert to price-based
            price_tp_percent = self.take_profit_percent / self.leverage
            price_sl_percent = self.stop_loss_percent / self.leverage
            
            # Calculate TP price if not set
            if self.take_profit_price is None:
                if self.direction == VoteDirection.LONG:
                    self.take_profit_price = self.entry_price * (1 + price_tp_percent / 100)
                elif self.direction == VoteDirection.SHORT:
                    self.take_profit_price = self.entry_price * (1 - price_tp_percent / 100)
            
            # Calculate SL price if not set
            if self.stop_loss_price is None:
                if self.direction == VoteDirection.LONG:
                    self.stop_loss_price = self.entry_price * (1 - price_sl_percent / 100)
                elif self.direction == VoteDirection.SHORT:
                    self.stop_loss_price = self.entry_price * (1 + price_sl_percent / 100)
    
    @property
    def is_actionable(self) -> bool:
        """Check if signal requires trade action."""
        return self.direction in (
            VoteDirection.LONG, 
            VoteDirection.SHORT,
            VoteDirection.CLOSE,
            VoteDirection.ADD_LONG,
            VoteDirection.ADD_SHORT
        )
    
    @property
    def risk_reward_ratio(self) -> float:
        """Calculate risk/reward ratio."""
        if not self.take_profit_price or not self.stop_loss_price or self.entry_price == 0:
            return 0.0
        
        if self.direction == VoteDirection.LONG:
            risk = abs(self.entry_price - self.stop_loss_price)
            reward = abs(self.take_profit_price - self.entry_price)
        elif self.direction == VoteDirection.SHORT:
            risk = abs(self.stop_loss_price - self.entry_price)
            reward = abs(self.entry_price - self.take_profit_price)
        else:
            return 0.0
        
        return reward / risk if risk > 0 else 0.0
    
    @classmethod
    def from_vote_summary(
        cls,
        summary: VoteSummary,
        entry_price: float,
        symbol: str = "BTC-USDT-SWAP",
        leader_summary: str = "",
        meeting_id: str = "",
        trigger_reason: str = "scheduled"
    ) -> "TradingSignal":
        """
        Create signal from aggregated votes.
        
        Uses vote summary to determine direction, confidence, and parameters.
        """
        direction = summary.consensus_direction
        
        # Build agents consensus dict
        agents_consensus = {
            v.agent_name: v.direction.value
            for v in summary.votes
        }
        
        return cls(
            direction=direction,
            symbol=symbol,
            leverage=int(summary.avg_leverage),
            confidence=int(summary.avg_confidence),
            consensus_strength=summary.consensus_strength,
            entry_price=entry_price,
            take_profit_percent=summary.avg_take_profit_percent,
            stop_loss_percent=summary.avg_stop_loss_percent,
            leader_summary=leader_summary,
            agents_consensus=agents_consensus,
            votes=summary.votes,
            meeting_id=meeting_id,
            trigger_reason=trigger_reason
        )
    
    @classmethod
    def hold_signal(cls, reason: str = "No clear consensus") -> "TradingSignal":
        """Create a hold signal."""
        return cls(
            direction=VoteDirection.HOLD,
            reasoning=reason,
            confidence=50
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "direction": self.direction.value,
            "symbol": self.symbol,
            "leverage": self.leverage,
            "amount_percent": self.amount_percent,
            "entry_price": self.entry_price,
            "take_profit_price": self.take_profit_price,
            "stop_loss_price": self.stop_loss_price,
            "take_profit_percent": self.take_profit_percent,
            "stop_loss_percent": self.stop_loss_percent,
            "confidence": self.confidence,
            "consensus_strength": self.consensus_strength,
            "reasoning": self.reasoning,
            "leader_summary": self.leader_summary,
            "agents_consensus": self.agents_consensus,
            "risk_reward_ratio": self.risk_reward_ratio,
            "meeting_id": self.meeting_id,
            "timestamp": self.timestamp.isoformat(),
            "trigger_reason": self.trigger_reason
        }
    
    def to_summary(self) -> str:
        """Format as human-readable summary."""
        lines = [
            f"📊 Trading Signal: {self.direction.value.upper()}",
            f"Symbol: {self.symbol}",
            f"Entry: ${self.entry_price:,.2f}",
            f"Leverage: {self.leverage}x",
            f"Confidence: {self.confidence}%",
        ]
        
        if self.take_profit_price:
            lines.append(f"Take Profit: ${self.take_profit_price:,.2f} (+{self.take_profit_percent:.1f}%)")
        if self.stop_loss_price:
            lines.append(f"Stop Loss: ${self.stop_loss_price:,.2f} (-{self.stop_loss_percent:.1f}%)")
        
        lines.append(f"Risk/Reward: {self.risk_reward_ratio:.2f}")
        
        if self.agents_consensus:
            consensus_str = ", ".join(f"{k}: {v}" for k, v in self.agents_consensus.items())
            lines.append(f"Consensus: {consensus_str}")
        
        return "\n".join(lines)
