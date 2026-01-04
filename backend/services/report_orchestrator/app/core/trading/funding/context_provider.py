"""
Funding Context Provider

Generates funding rate context for Agent prompt injection.
Ensures all agents are aware of funding costs when making decisions.
"""

import logging
from typing import Optional, Dict, Any

from .models import FundingRate, FundingDirection, EntryAction
from .config import get_funding_config
from .data_service import get_funding_data_service
from .calculator import get_funding_calculator
from .entry_timing import get_entry_timing_controller
from .holding_manager import get_holding_time_manager

logger = logging.getLogger(__name__)


class FundingContextProvider:
    """
    Funding Context Provider
    
    Generates context strings and data for injecting funding rate
    awareness into Agent prompts and decision-making.
    """
    
    def __init__(self):
        self.config = get_funding_config()
    
    async def generate_context(
        self,
        symbol: str = "BTC-USDT-SWAP",
        direction: str = "long",
        leverage: int = 3,
        expected_holding_hours: int = 24,
        margin: float = 100.0
    ) -> str:
        """
        Generate funding fee context for Agent prompts
        
        Args:
            symbol: Trading pair
            direction: Expected position direction
            leverage: Expected leverage
            expected_holding_hours: Expected holding duration
            margin: Expected margin amount
            
        Returns:
            Formatted context string for prompt injection
        """
        data_service = await get_funding_data_service()
        calculator = get_funding_calculator()
        timing_controller = get_entry_timing_controller()
        
        # Get current funding rate
        funding_rate = await data_service.get_current_rate(symbol)
        
        if not funding_rate:
            return self._generate_fallback_context()
        
        # Determine payment direction
        payment_dir = funding_rate.direction_for_position(direction)
        is_paying = payment_dir == FundingDirection.PAYING
        payment_status = "支付" if is_paying else "收取"
        
        # Calculate position value and costs
        position_value = margin * leverage
        cost_estimate = calculator.estimate_holding_cost(
            position_value=position_value,
            margin=margin,
            leverage=leverage,
            holding_hours=expected_holding_hours,
            current_rate=funding_rate.rate,
            avg_rate=funding_rate.avg_24h,
            direction=direction
        )
        
        # Get entry timing advice
        entry_decision = timing_controller.should_delay_entry(direction, funding_rate)
        
        # Generate viability assessment
        viability = calculator.evaluate_trade_viability(
            expected_profit_percent=5.0,  # Assume 5% target
            expected_holding_hours=expected_holding_hours,
            funding_rate=funding_rate.rate,
            leverage=leverage,
            direction=direction
        )
        
        # Calculate optimal holding time
        holding_manager = get_holding_time_manager()
        optimal_holding = holding_manager.calculate_optimal_holding(
            expected_profit_percent=5.0,
            funding_rate=funding_rate.rate,
            leverage=leverage,
            confidence=50,
            direction=direction
        )
        
        # Format context
        context = f"""
## ⚠️ 资金费率状态 (CRITICAL - 必须考虑)

### 当前费率信息
- **当前费率**: {funding_rate.rate_percent:.4f}% ({payment_status}方)
- **下次结算**: {funding_rate.minutes_to_settlement} 分钟后
- **24h平均**: {funding_rate.avg_24h * 100:.4f}%
- **费率趋势**: {funding_rate.trend.value}
- **极端费率**: {"⚠️ 是" if funding_rate.is_extreme else "否"}

### 成本评估 ({direction.upper()} 方向, {leverage}x杠杆)
| 持仓时间 | 预估成本 | 保证金占比 |
|----------|----------|------------|
| 8小时 | ${cost_estimate.estimated_cost / (expected_holding_hours/8):.2f} | {cost_estimate.cost_percent_of_margin / (expected_holding_hours/8):.2f}% |
| 24小时 | ${cost_estimate.estimated_cost * (24/expected_holding_hours):.2f} | {cost_estimate.cost_percent_of_margin * (24/expected_holding_hours):.2f}% |
| {expected_holding_hours}小时 | ${cost_estimate.estimated_cost:.2f} | {cost_estimate.cost_percent_of_margin:.2f}% |

### 关键指标
- **盈亏平衡价差**: {cost_estimate.break_even_price_move:.3f}% (价格需变动这么多才能保本)
- **建议最长持仓**: {optimal_holding} 小时
- **交易可行性**: {viability.value}

### 入场时机建议
{entry_decision.reason}

### 决策建议
"""
        # Add recommendations based on situation
        if is_paying and funding_rate.is_extreme:
            context += f"""
🔴 **高费率警告**: 当前费率极高 ({funding_rate.rate_percent:.3f}%)！
- 每8小时将支付约 ${cost_estimate.estimated_cost / (expected_holding_hours/8):.2f} 资金费
- 短期持仓可能更合适，避免费用累积
- 确保预期利润能覆盖费用成本
"""
        elif is_paying and funding_rate.rate > 0.0003:
            context += f"""
🟡 **费率提醒**: 当前费率偏高 ({funding_rate.rate_percent:.3f}%)。
- 建议控制持仓时间在 {optimal_holding} 小时内
- 设置更宽的止盈目标以覆盖费用
"""
        elif not is_paying and abs(funding_rate.rate) > 0.0001:
            context += f"""
🟢 **费率有利**: 当前费率对 {direction} 方向有利！
- 持仓期间将收取资金费约 ${abs(cost_estimate.estimated_cost):.2f}
- 可适当延长持仓时间获取更多收益
"""
        else:
            context += f"""
✅ **费率正常**: 当前费率影响较小。
- 费用成本可控，正常交易策略可行
"""
        
        return context
    
    def _generate_fallback_context(self) -> str:
        """Generate fallback context when API fails"""
        return """
## ⚠️ 资金费率状态

**注意**: 无法获取实时资金费率数据。

### 通用建议
- 永续合约每8小时结算一次资金费
- 多头在正费率时支付，空头收取
- 长期持仓需考虑累计资金费成本
- 建议在做出交易决策前核实当前费率
"""
    
    async def get_funding_data_for_vote(
        self,
        symbol: str = "BTC-USDT-SWAP",
        direction: str = "long",
        leverage: int = 3,
        expected_holding_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get funding data for Agent voting
        
        Returns structured data rather than formatted text.
        
        Args:
            symbol: Trading pair
            direction: Expected direction
            leverage: Expected leverage
            expected_holding_hours: Expected holding time
            
        Returns:
            Dict with funding data for decision-making
        """
        data_service = await get_funding_data_service()
        calculator = get_funding_calculator()
        
        funding_rate = await data_service.get_current_rate(symbol)
        
        if not funding_rate:
            return {
                'available': False,
                'error': 'Unable to fetch funding rate'
            }
        
        payment_dir = funding_rate.direction_for_position(direction)
        is_paying = payment_dir == FundingDirection.PAYING
        
        # Estimate costs for standard margin
        cost_8h = calculator.estimate_holding_cost(
            position_value=100 * leverage,
            margin=100,
            leverage=leverage,
            holding_hours=8,
            current_rate=funding_rate.rate,
            direction=direction
        )
        
        cost_24h = calculator.estimate_holding_cost(
            position_value=100 * leverage,
            margin=100,
            leverage=leverage,
            holding_hours=24,
            current_rate=funding_rate.rate,
            direction=direction
        )
        
        viability = calculator.evaluate_trade_viability(
            expected_profit_percent=5.0,
            expected_holding_hours=expected_holding_hours,
            funding_rate=funding_rate.rate,
            leverage=leverage,
            direction=direction
        )
        
        return {
            'available': True,
            'symbol': symbol,
            'current_rate': funding_rate.rate,
            'current_rate_percent': funding_rate.rate_percent,
            'avg_24h': funding_rate.avg_24h,
            'avg_24h_percent': funding_rate.avg_24h * 100,
            'trend': funding_rate.trend.value,
            'is_extreme': funding_rate.is_extreme,
            'minutes_to_settlement': funding_rate.minutes_to_settlement,
            'direction': direction,
            'is_paying': is_paying,
            'payment_status': '支付' if is_paying else '收取',
            'leverage': leverage,
            'cost_8h_percent': cost_8h.cost_percent_of_margin,
            'cost_24h_percent': cost_24h.cost_percent_of_margin,
            'break_even_move': cost_24h.break_even_price_move,
            'viability': viability.value,
            'viability_ok': viability.value != 'not_viable'
        }


# Global singleton
_provider: Optional[FundingContextProvider] = None


async def get_funding_context_provider() -> FundingContextProvider:
    """Get or create funding context provider singleton"""
    global _provider
    if _provider is None:
        _provider = FundingContextProvider()
    return _provider
