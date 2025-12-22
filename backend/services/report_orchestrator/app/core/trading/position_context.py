"""
Position Context Model

Position context data model for passing complete position information during trading decisions.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class PositionContext:
    """
    Complete Position Context

    Contains all information needed for decision making: current position, account state, risk metrics.
    """

    # ========== Basic Info ==========
    has_position: bool
    """Whether there is a position"""

    current_position: Optional[dict] = None
    """Current position details (if any)"""

    # ========== Position Details ==========
    direction: Optional[str] = None
    """Position direction: 'long' or 'short'"""

    entry_price: float = 0.0
    """Entry price"""

    current_price: float = 0.0
    """Current price"""

    size: float = 0.0
    """Position size"""

    leverage: int = 1
    """Leverage multiplier"""

    margin_used: float = 0.0
    """Margin used"""

    # ========== Profit & Loss ==========
    unrealized_pnl: float = 0.0
    """Unrealized PnL (USDT)"""

    unrealized_pnl_percent: float = 0.0
    """Unrealized PnL percentage"""

    # ========== Risk Metrics ==========
    liquidation_price: Optional[float] = None
    """Liquidation price"""

    distance_to_liquidation_percent: float = 0.0
    """Distance to liquidation (percentage)"""

    # ========== Take Profit / Stop Loss ==========
    take_profit_price: Optional[float] = None
    """Take profit price"""

    stop_loss_price: Optional[float] = None
    """Stop loss price"""

    distance_to_tp_percent: float = 0.0
    """Distance to take profit (percentage)"""

    distance_to_sl_percent: float = 0.0
    """Distance to stop loss (percentage)"""

    # ========== Account Status ==========
    available_balance: float = 0.0
    """Available balance"""

    total_equity: float = 0.0
    """Total equity"""

    used_margin: float = 0.0
    """Used margin (total)"""

    # ========== Position Limits ==========
    max_position_percent: float = 1.0
    """Max position ratio (0-1)"""

    current_position_percent: float = 0.0
    """Current position ratio (0-1)"""

    can_add_position: bool = False
    """Whether can add to position"""

    max_additional_amount: float = 0.0
    """Max additional amount in USDT"""

    # ========== Holding Duration ==========
    opened_at: Optional[datetime] = None
    """Position open time"""

    holding_duration_hours: float = 0.0
    """Holding duration (hours)"""

    # ========== Helper Methods ==========

    def to_summary(self) -> str:
        """
        Generate human-readable position summary for prompt injection.

        Used in Agent prompts to display current position/account state.
        """
        if not self.has_position:
            return """
📊 **Current Position Status**: No Position
- Available Balance: ${:.2f} USDT
- Total Equity: ${:.2f} USDT
- Status: ✅ Free to open new position
""".format(self.available_balance, self.total_equity)

        # P&L emoji
        pnl_emoji = "📈" if self.unrealized_pnl >= 0 else "📉"

        # Position status
        position_status = "✅ Can add more" if self.can_add_position else "❌ Max position reached"

        # Risk level
        if self.distance_to_liquidation_percent > 50:
            risk_level = "🟢 Safe"
        elif self.distance_to_liquidation_percent > 20:
            risk_level = "🟡 Warning"
        else:
            risk_level = "🔴 Danger"

        # Safe handling of None values
        tp_price_str = f"${self.take_profit_price:.2f}" if self.take_profit_price else "Not set"
        sl_price_str = f"${self.stop_loss_price:.2f}" if self.stop_loss_price else "Not set"
        liq_price_str = f"${self.liquidation_price:.2f}" if self.liquidation_price else "Unknown"

        return f"""
📊 **Current Position Status**: Has Position ({(self.direction or 'unknown').upper()})

### Position Details
- Direction: **{(self.direction or 'unknown').upper()}** ({self.leverage}x leverage)
- Entry Price: ${self.entry_price:.2f}
- Current Price: ${self.current_price:.2f}
- Position Size: {self.size:.6f} BTC
- Margin Used: ${self.margin_used:.2f} USDT

### Profit & Loss
- {pnl_emoji} Unrealized P&L: ${self.unrealized_pnl:.2f} USDT ({self.unrealized_pnl_percent:+.2f}%)

### Take Profit / Stop Loss
- Take Profit: {tp_price_str} (distance: {self.distance_to_tp_percent:+.2f}%)
- Stop Loss: {sl_price_str} (distance: {self.distance_to_sl_percent:+.2f}%)

### Risk Metrics
- Liquidation Price: {liq_price_str}
- Distance to Liquidation: {self.distance_to_liquidation_percent:.1f}% ({risk_level})

### Account Status
- Available Balance: ${self.available_balance:.2f} USDT
- Total Equity: ${self.total_equity:.2f} USDT
- Used Margin: ${self.used_margin:.2f} USDT

### Position Management
- Current Position: {self.current_position_percent*100:.1f}% / {self.max_position_percent*100:.1f}%
- Status: {position_status}
- Can Add: ${self.max_additional_amount:.2f} USDT

### Holding Duration
- Opened At: {self.opened_at.strftime('%Y-%m-%d %H:%M:%S') if self.opened_at else 'N/A'}
- Duration: {self.holding_duration_hours:.1f} hours
"""

    def to_dict(self) -> dict:
        """Convert to dictionary format"""
        return {
            "has_position": self.has_position,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "size": self.size,
            "leverage": self.leverage,
            "margin_used": self.margin_used,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_percent": self.unrealized_pnl_percent,
            "liquidation_price": self.liquidation_price,
            "distance_to_liquidation_percent": self.distance_to_liquidation_percent,
            "take_profit_price": self.take_profit_price,
            "stop_loss_price": self.stop_loss_price,
            "distance_to_tp_percent": self.distance_to_tp_percent,
            "distance_to_sl_percent": self.distance_to_sl_percent,
            "available_balance": self.available_balance,
            "total_equity": self.total_equity,
            "used_margin": self.used_margin,
            "max_position_percent": self.max_position_percent,
            "current_position_percent": self.current_position_percent,
            "can_add_position": self.can_add_position,
            "max_additional_amount": self.max_additional_amount,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "holding_duration_hours": self.holding_duration_hours
        }
