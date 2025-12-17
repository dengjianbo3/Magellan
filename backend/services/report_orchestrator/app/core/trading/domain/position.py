"""
PositionContext Domain Model

Represents the current position state for injection into agent prompts.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class PositionContext:
    """
    Current trading position state.
    
    Injected into every agent prompt to ensure position-aware decisions.
    """
    # Position status
    has_position: bool = False
    direction: str = ""  # "long" or "short"
    
    # Price information
    entry_price: float = 0.0
    current_price: float = 0.0
    
    # P&L
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0
    
    # Position size
    leverage: int = 1
    position_size_percent: float = 0.0  # Portion of account
    margin_used: float = 0.0
    
    # Risk levels
    liquidation_price: Optional[float] = None
    liquidation_distance_percent: float = 0.0
    
    # TP/SL
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    tp_distance_percent: float = 0.0
    sl_distance_percent: float = 0.0
    
    # Timing
    opened_at: Optional[datetime] = None
    holding_duration_hours: float = 0.0
    
    @property
    def is_long(self) -> bool:
        return self.direction.lower() == "long"
    
    @property
    def is_short(self) -> bool:
        return self.direction.lower() == "short"
    
    @property
    def is_profitable(self) -> bool:
        return self.unrealized_pnl > 0
    
    @property
    def is_in_danger(self) -> bool:
        """Check if position is close to liquidation (< 20%)."""
        return self.has_position and self.liquidation_distance_percent < 20
    
    def to_summary(self) -> str:
        """
        Format position context for prompt injection.
        
        This is the primary format used to inject position awareness
        into agent prompts.
        """
        lines = [
            "═══════════════════════════════════════",
            "📊 CURRENT POSITION STATUS",
            "═══════════════════════════════════════",
        ]
        
        if not self.has_position:
            lines.append("✅ No Active Position")
            lines.append(f"📍 Current Price: ${self.current_price:,.2f}")
        else:
            # Position info
            direction_emoji = "📈" if self.is_long else "📉"
            pnl_emoji = "💰" if self.is_profitable else "💸"
            pnl_sign = "+" if self.is_profitable else ""
            
            lines.extend([
                f"✅ Has Active Position: Yes",
                f"{direction_emoji} Direction: {self.direction.upper()}",
                f"💵 Entry Price: ${self.entry_price:,.2f}",
                f"📍 Current Price: ${self.current_price:,.2f}",
                f"{pnl_emoji} Unrealized P&L: {pnl_sign}${self.unrealized_pnl:,.2f} ({pnl_sign}{self.unrealized_pnl_percent:.2f}%)",
                f"⚡ Leverage: {self.leverage}x",
                f"🎚️ Position Size: {self.position_size_percent:.1f}%",
            ])
            
            # Liquidation risk
            if self.liquidation_price:
                danger_emoji = "🚨" if self.is_in_danger else "🚫"
                lines.append(
                    f"{danger_emoji} Liquidation: ${self.liquidation_price:,.2f} "
                    f"({self.liquidation_distance_percent:.1f}% away)"
                )
            
            # TP/SL
            if self.take_profit_price:
                lines.append(
                    f"🎯 Take Profit: ${self.take_profit_price:,.2f} "
                    f"({self.tp_distance_percent:+.1f}%)"
                )
            if self.stop_loss_price:
                lines.append(
                    f"🛑 Stop Loss: ${self.stop_loss_price:,.2f} "
                    f"({self.sl_distance_percent:+.1f}%)"
                )
            
            # Duration
            if self.holding_duration_hours > 0:
                hours = self.holding_duration_hours
                if hours < 1:
                    duration_str = f"{int(hours * 60)} minutes"
                elif hours < 24:
                    duration_str = f"{hours:.1f} hours"
                else:
                    duration_str = f"{hours / 24:.1f} days"
                lines.append(f"⏱️ Holding Duration: {duration_str}")
        
        lines.append("═══════════════════════════════════════")
        return "\n".join(lines)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "has_position": self.has_position,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_percent": self.unrealized_pnl_percent,
            "leverage": self.leverage,
            "position_size_percent": self.position_size_percent,
            "liquidation_price": self.liquidation_price,
            "liquidation_distance_percent": self.liquidation_distance_percent,
            "take_profit_price": self.take_profit_price,
            "stop_loss_price": self.stop_loss_price,
            "tp_distance_percent": self.tp_distance_percent,
            "sl_distance_percent": self.sl_distance_percent,
            "holding_duration_hours": self.holding_duration_hours
        }
    
    @classmethod
    def no_position(cls, current_price: float = 0.0) -> "PositionContext":
        """Create context for no active position."""
        return cls(
            has_position=False,
            current_price=current_price
        )
    
    @classmethod
    def from_position(
        cls,
        direction: str,
        entry_price: float,
        current_price: float,
        size_percent: float,
        leverage: int,
        margin: float,
        liquidation_price: Optional[float] = None,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None,
        opened_at: Optional[datetime] = None
    ) -> "PositionContext":
        """Create context from position parameters."""
        # Calculate P&L
        if direction.lower() == "long":
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_percent = ((entry_price - current_price) / entry_price) * 100
        
        pnl = margin * leverage * (pnl_percent / 100)
        
        # Calculate distances
        liq_distance = 0.0
        if liquidation_price:
            liq_distance = abs((current_price - liquidation_price) / current_price) * 100
        
        tp_distance = 0.0
        if tp_price:
            tp_distance = ((tp_price - current_price) / current_price) * 100
        
        sl_distance = 0.0
        if sl_price:
            sl_distance = ((sl_price - current_price) / current_price) * 100
        
        # Calculate duration
        duration_hours = 0.0
        if opened_at:
            duration_hours = (datetime.now() - opened_at).total_seconds() / 3600
        
        return cls(
            has_position=True,
            direction=direction,
            entry_price=entry_price,
            current_price=current_price,
            unrealized_pnl=pnl,
            unrealized_pnl_percent=pnl_percent,
            leverage=leverage,
            position_size_percent=size_percent,
            margin_used=margin,
            liquidation_price=liquidation_price,
            liquidation_distance_percent=liq_distance,
            take_profit_price=tp_price,
            stop_loss_price=sl_price,
            tp_distance_percent=tp_distance,
            sl_distance_percent=sl_distance,
            opened_at=opened_at,
            holding_duration_hours=duration_hours
        )
