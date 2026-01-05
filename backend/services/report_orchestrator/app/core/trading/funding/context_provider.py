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
        leverage: int = None,
        expected_holding_hours: int = 24,
        margin: float = 100.0
    ) -> str:
        """
        Generate funding fee context for Agent prompts
        
        Args:
            symbol: Trading pair
            direction: Expected position direction
            leverage: Expected leverage (if None, uses DEFAULT_LEVERAGE env var)
            expected_holding_hours: Expected holding duration
            margin: Expected margin amount
            
        Returns:
            Formatted context string for prompt injection
        """
        # Use default leverage from config if not provided
        if leverage is None:
            leverage = self.config.default_leverage if hasattr(self.config, 'default_leverage') else 5
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
## ⚠️ Funding Rate Status (CRITICAL - MUST CONSIDER)

### Current Rate Info
- **Current Rate**: {funding_rate.rate_percent:.4f}% ({payment_status} side)
- **Next Settlement**: in {funding_rate.minutes_to_settlement} mins
- **24h Average**: {funding_rate.avg_24h * 100:.4f}%
- **Rate Trend**: {funding_rate.trend.value}
- **Extreme Rate**: {"⚠️ YES" if funding_rate.is_extreme else "NO"}

### Cost Estimation ({direction.upper()} direction, {leverage}x leverage)
| Holding Time | Est. Cost | % of Margin |
|--------------|-----------|-------------|
| 8 Hours      | ${cost_estimate.estimated_cost / (expected_holding_hours/8):.2f} | {cost_estimate.cost_percent_of_margin / (expected_holding_hours/8):.2f}% |
| 24 Hours     | ${cost_estimate.estimated_cost * (24/expected_holding_hours):.2f} | {cost_estimate.cost_percent_of_margin * (24/expected_holding_hours):.2f}% |
| {expected_holding_hours} Hours | ${cost_estimate.estimated_cost:.2f} | {cost_estimate.cost_percent_of_margin:.2f}% |

### Key Metrics
- **Break-Even Price Move**: {cost_estimate.break_even_price_move:.3f}% (Price move needed to zero out fees)
- **Recommended Max Holding**: {optimal_holding} hours
- **Trade Viability**: {viability.value}

### Entry Timing Advice
{entry_decision.reason}

### Decision Recommendations
"""
        # Add recommendations based on situation
        if is_paying and funding_rate.is_extreme:
            context += f"""
🔴 **HIGH RATE WARNING**: Current funding rate is extremely high ({funding_rate.rate_percent:.3f}%)!
- You will PAY approx ${cost_estimate.estimated_cost / (expected_holding_hours/8):.2f} every 8 hours.
- Short-term holding is recommended to avoid fee accumulation.
- Ensure expected profit covers these costs.
"""
        elif is_paying and funding_rate.rate > 0.0003:
            context += f"""
🟡 **Rate Alert**: Current funding rate is elevated ({funding_rate.rate_percent:.3f}%).
- Recommended to limit holding time within {optimal_holding} hours.
- Set wider Take Profit targets to cover fee costs.
"""
        elif not is_paying and abs(funding_rate.rate) > 0.0001:
            context += f"""
🟢 **Favorable Rate**: Current rate is favorable for {direction} position!
- You will RECEIVE approx ${abs(cost_estimate.estimated_cost):.2f} in funding fees.
- Consider extending holding time to maximize fee yield.
"""
        else:
            context += f"""
✅ **Normal Rate**: Funding rate impact is minimal.
- Fee costs are manageable; standard trading strategy applies.
"""
        
        return context
    
    def _generate_fallback_context(self) -> str:
        """Generate fallback context when API fails"""
        return """
## ⚠️ Funding Rate Status

**NOTE**: Unable to fetch real-time funding rate data.

### General Guidelines
- Perpetual contracts settle funding fees every 8 hours.
- Longs pay Shorts when rate is positive; Shorts pay Longs when negative.
- Consider cumulative funding costs for long-term positions.
- Verify current rates before making trading decisions.
"""
    
    async def get_funding_data_for_vote(
        self,
        symbol: str = "BTC-USDT-SWAP",
        direction: str = "long",
        leverage: int = None,
        expected_holding_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get funding data for Agent voting
        
        Returns structured data rather than formatted text.
        
        Args:
            symbol: Trading pair
            direction: Expected direction
            leverage: Expected leverage (if None, uses config default)
            expected_holding_hours: Expected holding time
            
        Returns:
            Dict with funding data for decision-making
        """
        # Use default leverage from config if not provided
        if leverage is None:
            leverage = self.config.default_leverage if hasattr(self.config, 'default_leverage') else 5
        
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
            'payment_status': 'Paying' if is_paying else 'Receiving',
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
