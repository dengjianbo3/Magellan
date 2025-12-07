"""
Position Context Model

持仓上下文数据模型，用于在交易决策过程中传递完整的持仓信息。
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class PositionContext:
    """
    完整的持仓上下文
    
    包含当前持仓、账户状态、风险指标等所有决策所需信息。
    """
    
    # ========== 基础信息 ==========
    has_position: bool
    """是否有持仓"""
    
    current_position: Optional[dict] = None
    """当前持仓详情（如果有）"""
    
    # ========== 持仓详情 ==========
    direction: Optional[str] = None
    """持仓方向: 'long' or 'short'"""
    
    entry_price: float = 0.0
    """入场价格"""
    
    current_price: float = 0.0
    """当前价格"""
    
    size: float = 0.0
    """持仓数量"""
    
    leverage: int = 1
    """杠杆倍数"""
    
    margin_used: float = 0.0
    """已用保证金"""
    
    # ========== 盈亏情况 ==========
    unrealized_pnl: float = 0.0
    """未实现盈亏（USDT）"""
    
    unrealized_pnl_percent: float = 0.0
    """未实现盈亏百分比"""
    
    # ========== 风险指标 ==========
    liquidation_price: Optional[float] = None
    """强平价格"""
    
    distance_to_liquidation_percent: float = 0.0
    """距离强平的距离（百分比）"""
    
    # ========== 止盈止损 ==========
    take_profit_price: Optional[float] = None
    """止盈价格"""
    
    stop_loss_price: Optional[float] = None
    """止损价格"""
    
    distance_to_tp_percent: float = 0.0
    """距离止盈的距离（百分比）"""
    
    distance_to_sl_percent: float = 0.0
    """距离止损的距离（百分比）"""
    
    # ========== 账户状态 ==========
    available_balance: float = 0.0
    """可用余额"""
    
    total_equity: float = 0.0
    """总权益"""
    
    used_margin: float = 0.0
    """已用保证金（总计）"""
    
    # ========== 仓位限制 ==========
    max_position_percent: float = 1.0
    """最大仓位比例（0-1）"""
    
    current_position_percent: float = 0.0
    """当前仓位占比（0-1）"""
    
    can_add_position: bool = False
    """是否可以追加仓位"""
    
    max_additional_amount: float = 0.0
    """最多还能追加多少USDT"""
    
    # ========== 持仓时长 ==========
    opened_at: Optional[datetime] = None
    """开仓时间"""
    
    holding_duration_hours: float = 0.0
    """持仓时长（小时）"""
    
    # ========== 辅助方法 ==========
    
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
        """转换为字典格式"""
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
