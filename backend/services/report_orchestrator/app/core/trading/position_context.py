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
        生成人类可读的持仓摘要
        
        用于在Agent的prompt中展示持仓信息
        """
        if not self.has_position:
            return """
📊 **当前持仓状况**: 无持仓
- 可用余额: ${:.2f} USDT
- 总权益: ${:.2f} USDT
- 状态: ✅ 可自由开仓
""".format(self.available_balance, self.total_equity)
        
        # 计算盈亏的emoji
        pnl_emoji = "📈" if self.unrealized_pnl >= 0 else "📉"
        
        # 计算仓位状态
        position_status = "✅ 可追加" if self.can_add_position else "❌ 已满仓"
        
        # 计算风险等级
        if self.distance_to_liquidation_percent > 50:
            risk_level = "🟢 安全"
        elif self.distance_to_liquidation_percent > 20:
            risk_level = "🟡 警戒"
        else:
            risk_level = "🔴 危险"
        
        return f"""
📊 **当前持仓状况**: 有持仓 ({(self.direction or 'unknown').upper()})

### 持仓信息
- 方向: **{(self.direction or 'unknown').upper()}** ({self.leverage}x 杠杆)
- 入场价: ${self.entry_price:.2f}
- 当前价: ${self.current_price:.2f}
- 持仓量: {self.size:.6f} BTC
- 保证金: ${self.margin_used:.2f} USDT

### 盈亏情况
- {pnl_emoji} 浮动盈亏: ${self.unrealized_pnl:.2f} USDT ({self.unrealized_pnl_percent:+.2f}%)

### 止盈止损
- 止盈价: ${self.take_profit_price:.2f} (距离: {self.distance_to_tp_percent:+.2f}%)
- 止损价: ${self.stop_loss_price:.2f} (距离: {self.distance_to_sl_percent:+.2f}%)

### 风险指标
- 强平价: ${self.liquidation_price:.2f}
- 距强平: {self.distance_to_liquidation_percent:.1f}% ({risk_level})

### 账户状态
- 可用余额: ${self.available_balance:.2f} USDT
- 总权益: ${self.total_equity:.2f} USDT
- 已用保证金: ${self.used_margin:.2f} USDT

### 仓位管理
- 当前仓位: {self.current_position_percent*100:.1f}% / {self.max_position_percent*100:.1f}%
- 状态: {position_status}
- 可追加: ${self.max_additional_amount:.2f} USDT

### 持仓时长
- 开仓时间: {self.opened_at.strftime('%Y-%m-%d %H:%M:%S') if self.opened_at else 'N/A'}
- 持仓时长: {self.holding_duration_hours:.1f} 小时
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
