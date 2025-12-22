"""
AccountInfo Domain Model

Represents account balance and trading capacity information.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AccountInfo:
    """
    Account balance and capacity information.
    
    Provides a snapshot of the trading account's current state.
    """
    # Balance
    total_equity: float = 0.0  # Total account value
    available_balance: float = 0.0  # Available for new positions
    used_margin: float = 0.0  # Currently used as collateral
    
    # P&L
    unrealized_pnl: float = 0.0  # Floating P&L from open positions
    realized_pnl_today: float = 0.0  # Today's realized P&L
    
    # Trading capacity
    max_avail_size: float = 0.0  # OKX-calculated max position size
    margin_ratio: float = 0.0  # Used margin / total equity
    
    # Risk metrics
    daily_loss_limit: float = 0.0  # Daily loss limit (USDT)
    daily_loss_used: float = 0.0  # How much of daily limit used
    
    # Currency
    currency: str = "USDT"
    
    @property
    def available_percent(self) -> float:
        """Percentage of equity available for trading."""
        if self.total_equity <= 0:
            return 0.0
        return (self.available_balance / self.total_equity) * 100
    
    @property
    def utilization_percent(self) -> float:
        """Percentage of equity currently utilized."""
        if self.total_equity <= 0:
            return 0.0
        return (self.used_margin / self.total_equity) * 100
    
    @property
    def daily_loss_remaining(self) -> float:
        """Remaining daily loss allowance."""
        return max(0, self.daily_loss_limit - self.daily_loss_used)
    
    @property
    def can_trade(self) -> bool:
        """Check if account can open new positions."""
        return (
            self.available_balance > 0 and 
            self.daily_loss_remaining > 0
        )
    
    def to_summary(self) -> str:
        """Format as human-readable summary."""
        lines = [
            "═══════════════════════════════════════",
            "💰 ACCOUNT STATUS",
            "═══════════════════════════════════════",
            f"Total Equity: ${self.total_equity:,.2f} {self.currency}",
            f"Available: ${self.available_balance:,.2f} ({self.available_percent:.1f}%)",
            f"Used Margin: ${self.used_margin:,.2f} ({self.utilization_percent:.1f}%)",
        ]
        
        if self.unrealized_pnl != 0:
            pnl_sign = "+" if self.unrealized_pnl > 0 else ""
            lines.append(f"Unrealized P&L: {pnl_sign}${self.unrealized_pnl:,.2f}")
        
        if self.daily_loss_limit > 0:
            lines.append(
                f"Daily Loss: ${self.daily_loss_used:,.2f} / ${self.daily_loss_limit:,.2f} limit"
            )
        
        lines.append("═══════════════════════════════════════")
        return "\n".join(lines)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "total_equity": self.total_equity,
            "available_balance": self.available_balance,
            "used_margin": self.used_margin,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl_today": self.realized_pnl_today,
            "max_avail_size": self.max_avail_size,
            "margin_ratio": self.margin_ratio,
            "daily_loss_limit": self.daily_loss_limit,
            "daily_loss_used": self.daily_loss_used,
            "currency": self.currency,
            "available_percent": self.available_percent,
            "utilization_percent": self.utilization_percent,
            "can_trade": self.can_trade
        }
    
    @classmethod
    def from_okx_response(cls, data: dict) -> "AccountInfo":
        """Create from OKX API response."""
        return cls(
            total_equity=float(data.get("totalEq", 0)),
            available_balance=float(data.get("availBal", 0)),
            used_margin=float(data.get("frozenBal", 0)),
            unrealized_pnl=float(data.get("upl", 0)),
            margin_ratio=float(data.get("mgnRatio", 0)),
            currency=data.get("ccy", "USDT")
        )
