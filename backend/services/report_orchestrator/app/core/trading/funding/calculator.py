"""
Funding Cost Calculator

Provides cost estimation and break-even analysis for funding fees.
"""

import math
import logging
from typing import Optional
from dataclasses import dataclass

from .models import (
    FundingRate, 
    HoldingCostEstimate, 
    TradeViability,
    TruePnL
)
from .config import get_funding_config

logger = logging.getLogger(__name__)


class FundingCostCalculator:
    """
    Funding Cost Calculator
    
    Provides:
    - Holding cost estimation
    - Break-even price movement calculation
    - Trade viability evaluation
    - True PnL calculation
    """
    
    def __init__(self):
        self.config = get_funding_config()
    
    def estimate_holding_cost(
        self,
        position_value: float,
        margin: float,
        leverage: int,
        holding_hours: int,
        current_rate: float,
        avg_rate: Optional[float] = None,
        direction: str = "long"
    ) -> HoldingCostEstimate:
        """
        Estimate cost of holding a position
        
        Args:
            position_value: Total position value in USDT (size × price)
            margin: Margin used for position
            leverage: Leverage multiplier
            holding_hours: Expected holding duration in hours
            current_rate: Current funding rate (e.g., 0.0003 = 0.03%)
            avg_rate: Average funding rate (for more accurate estimation)
            direction: "long" or "short"
            
        Returns:
            HoldingCostEstimate with cost analysis
        """
        # Use weighted average of current and historical rate
        if avg_rate is not None:
            assumed_rate = current_rate * 0.6 + avg_rate * 0.4
        else:
            assumed_rate = current_rate
        
        # Determine if position pays or receives funding
        # Positive rate: longs pay, shorts receive
        # Negative rate: shorts pay, longs receive
        is_paying = (direction == "long" and assumed_rate > 0) or \
                   (direction == "short" and assumed_rate < 0)
        
        # Number of settlement periods
        settlement_count = math.ceil(holding_hours / 8)
        
        # Cost per settlement = position_value × rate
        cost_per_settlement = abs(position_value * assumed_rate)
        
        # Total expected cost
        expected_cost = cost_per_settlement * settlement_count
        
        # If receiving, cost is negative (income)
        if not is_paying:
            expected_cost = -expected_cost  # Negative = receiving money
        
        # Min/max estimates (assuming rate could change by 50%)
        rate_variance = 0.5
        if is_paying:
            min_cost = expected_cost * (1 - rate_variance)  # Rate drops
            max_cost = expected_cost * (1 + rate_variance)  # Rate increases
        else:
            min_cost = expected_cost * (1 + rate_variance)  # Less income
            max_cost = expected_cost * (1 - rate_variance)  # More income
        
        # Cost as percentage of margin
        cost_percent = (abs(expected_cost) / margin * 100) if margin > 0 else 0
        
        # Break-even price movement
        break_even = self.calculate_break_even_move(
            holding_hours=holding_hours,
            funding_rate=assumed_rate,
            leverage=leverage,
            trading_fee=self.config.default_trading_fee,
            direction=direction
        )
        
        result = HoldingCostEstimate(
            holding_hours=holding_hours,
            settlement_count=settlement_count,
            estimated_cost=expected_cost,
            min_cost=min_cost,
            max_cost=max_cost,
            cost_percent_of_margin=cost_percent,
            break_even_price_move=break_even,
            assumed_rate=assumed_rate,
            leverage=leverage,
            position_value=position_value
        )
        
        logger.debug(
            f"[FundingCalc] Hold {holding_hours}h: "
            f"cost=${expected_cost:.2f} ({cost_percent:.2f}% margin), "
            f"break_even={break_even:.3f}%"
        )
        
        return result
    
    def calculate_break_even_move(
        self,
        holding_hours: int,
        funding_rate: float,
        leverage: int,
        trading_fee: float = 0.001,
        direction: str = "long"
    ) -> float:
        """
        Calculate minimum price movement needed to break even
        
        Formula:
        - settlements = holding_hours / 8
        - funding_cost_rate = |rate| × settlements × leverage (if paying)
        - total_cost_rate = funding_cost_rate + trading_fee × 2
        - break_even_move = total_cost_rate × 100 / leverage
        
        Args:
            holding_hours: Expected holding duration
            funding_rate: Funding rate (e.g., 0.0003)
            leverage: Leverage multiplier
            trading_fee: Trading fee rate (e.g., 0.001 for 0.1%)
            direction: Position direction
            
        Returns:
            Break-even price movement as percentage
        """
        # Determine if paying
        is_paying = (direction == "long" and funding_rate > 0) or \
                   (direction == "short" and funding_rate < 0)
        
        settlement_count = math.ceil(holding_hours / 8)
        
        # Funding cost impact on margin
        if is_paying:
            funding_cost_rate = abs(funding_rate) * settlement_count * leverage
        else:
            # If receiving, funding reduces break-even requirement
            funding_cost_rate = -abs(funding_rate) * settlement_count * leverage
        
        # Trading fees (open + close)
        total_fee_rate = trading_fee * 2 * leverage
        
        # Total cost as rate
        total_cost_rate = funding_cost_rate + total_fee_rate
        
        # Convert to price movement percentage
        # With leverage, price_move = cost_rate / leverage × 100
        break_even_move = total_cost_rate / leverage * 100
        
        return max(0, break_even_move)  # Can't be negative
    
    def evaluate_trade_viability(
        self,
        expected_profit_percent: float,
        expected_holding_hours: int,
        funding_rate: float,
        leverage: int,
        direction: str = "long"
    ) -> TradeViability:
        """
        Evaluate if a trade is viable considering funding costs
        
        This replaces the "extreme rate ban" - instead of banning trades
        at high rates, we evaluate if expected profit can cover costs.
        
        Args:
            expected_profit_percent: Expected profit as % of margin
            expected_holding_hours: Expected holding duration
            funding_rate: Current funding rate
            leverage: Leverage multiplier
            direction: Position direction
            
        Returns:
            TradeViability enum
        """
        # Calculate break-even requirement
        break_even = self.calculate_break_even_move(
            holding_hours=expected_holding_hours,
            funding_rate=funding_rate,
            leverage=leverage,
            direction=direction
        )
        
        # Compare expected profit to break-even
        profit_ratio = expected_profit_percent / break_even if break_even > 0 else float('inf')
        
        if profit_ratio >= self.config.profit_buffer_multiplier:
            # Expected profit well exceeds costs
            logger.info(
                f"[FundingCalc] Trade VIABLE: profit {expected_profit_percent:.2f}% >> "
                f"break_even {break_even:.2f}% (ratio {profit_ratio:.1f}x)"
            )
            return TradeViability.VIABLE
        elif profit_ratio >= 1.0:
            # Profit barely covers costs
            logger.warning(
                f"[FundingCalc] Trade MARGINAL: profit {expected_profit_percent:.2f}% ~ "
                f"break_even {break_even:.2f}% (ratio {profit_ratio:.1f}x)"
            )
            return TradeViability.MARGINAL
        else:
            # Costs exceed expected profit
            logger.warning(
                f"[FundingCalc] Trade NOT_VIABLE: profit {expected_profit_percent:.2f}% < "
                f"break_even {break_even:.2f}% (ratio {profit_ratio:.1f}x)"
            )
            return TradeViability.NOT_VIABLE
    
    def calculate_true_pnl(
        self,
        price_pnl: float,
        accumulated_funding: float,
        trading_fees: float,
        margin: float,
        funding_count: int = 0,
        avg_funding_rate: float = 0.0
    ) -> TruePnL:
        """
        Calculate true PnL including all costs
        
        Args:
            price_pnl: PnL from price movement
            accumulated_funding: Total funding paid (negative) or received (positive)
            trading_fees: Total trading fees paid
            margin: Position margin for percentage calculations
            funding_count: Number of funding settlements
            avg_funding_rate: Average funding rate during holding
            
        Returns:
            TruePnL object with complete analysis
        """
        return TruePnL(
            price_pnl=price_pnl,
            price_pnl_percent=0,  # Will be calculated in __post_init__
            funding_pnl=accumulated_funding,
            funding_count=funding_count,
            avg_funding_rate=avg_funding_rate,
            trading_fees=trading_fees,
            margin=margin
        )
    
    def calculate_optimal_holding_hours(
        self,
        expected_profit_percent: float,
        funding_rate: float,
        leverage: int,
        direction: str = "long",
        max_funding_impact: float = 50  # Max 50% of profit to funding
    ) -> int:
        """
        Calculate optimal maximum holding time
        
        This dynamically determines how long to hold based on:
        - Expected profit
        - Current funding rate
        - Maximum acceptable funding impact
        
        Args:
            expected_profit_percent: Expected profit as % of margin
            funding_rate: Current funding rate
            leverage: Leverage multiplier
            direction: Position direction
            max_funding_impact: Max % of profit that can go to funding
            
        Returns:
            Recommended maximum holding hours
        """
        # Determine if paying
        is_paying = (direction == "long" and funding_rate > 0) or \
                   (direction == "short" and funding_rate < 0)
        
        if not is_paying:
            # If receiving funding, longer is better (up to default max)
            return self.config.default_max_holding_hours
        
        # Calculate how much profit can go to funding
        max_funding_cost_percent = expected_profit_percent * (max_funding_impact / 100)
        
        # Cost per 8h = |rate| × leverage × 100 (as % of margin)
        cost_per_8h = abs(funding_rate) * leverage * 100
        
        if cost_per_8h <= 0:
            return self.config.default_max_holding_hours
        
        # Max settlements = max_cost / cost_per_settlement
        max_settlements = max_funding_cost_percent / cost_per_8h
        
        # Convert to hours
        optimal_hours = int(max_settlements * 8)
        
        # Clamp to reasonable range
        optimal_hours = max(8, min(optimal_hours, self.config.default_max_holding_hours))
        
        logger.info(
            f"[FundingCalc] Optimal holding: {optimal_hours}h "
            f"(profit={expected_profit_percent:.1f}%, rate={funding_rate*100:.3f}%, "
            f"max_impact={max_funding_impact}%)"
        )
        
        return optimal_hours


# Global singleton
_calculator: Optional[FundingCostCalculator] = None


def get_funding_calculator() -> FundingCostCalculator:
    """Get or create funding calculator singleton"""
    global _calculator
    if _calculator is None:
        _calculator = FundingCostCalculator()
    return _calculator
