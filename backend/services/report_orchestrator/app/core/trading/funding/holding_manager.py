"""
Holding Time Manager

Dynamically calculates optimal holding time based on funding costs.
Provides holding advice for agents and monitoring.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from .models import (
    FundingRate,
    HoldingAdvice,
    HoldingAlertLevel,
    FundingDirection
)
from .config import get_funding_config
from .calculator import get_funding_calculator

logger = logging.getLogger(__name__)


class HoldingTimeManager:
    """
    Holding Time Manager
    
    Dynamically calculates and recommends optimal holding times based on:
    - Expected profit target
    - Current funding rate
    - Accumulated funding costs
    - Maximum acceptable funding impact
    """
    
    def __init__(self):
        self.config = get_funding_config()
        self.calculator = get_funding_calculator()
    
    def calculate_optimal_holding(
        self,
        expected_profit_percent: float,
        funding_rate: float,
        leverage: int,
        confidence: int,
        direction: str = "long"
    ) -> int:
        """
        Calculate optimal maximum holding time
        
        Called during each analysis cycle to dynamically adjust recommendation.
        
        Args:
            expected_profit_percent: Expected profit as % of margin
            funding_rate: Current funding rate
            leverage: Leverage multiplier
            confidence: Confidence score (0-100)
            direction: Position direction
            
        Returns:
            Recommended maximum holding hours
        """
        # Adjust max funding impact based on confidence
        # Higher confidence = more tolerance for funding costs
        base_max_impact = self.config.force_close_threshold
        
        if confidence >= 80:
            max_impact = base_max_impact * 1.0  # Full tolerance
        elif confidence >= 60:
            max_impact = base_max_impact * 0.8  # 80% tolerance
        elif confidence >= 40:
            max_impact = base_max_impact * 0.6  # 60% tolerance
        else:
            max_impact = base_max_impact * 0.4  # Low confidence = stricter limit
        
        optimal_hours = self.calculator.calculate_optimal_holding_hours(
            expected_profit_percent=expected_profit_percent,
            funding_rate=funding_rate,
            leverage=leverage,
            direction=direction,
            max_funding_impact=max_impact
        )
        
        logger.info(
            f"[HoldingManager] Optimal holding: {optimal_hours}h "
            f"(profit={expected_profit_percent:.1f}%, confidence={confidence}, "
            f"rate={funding_rate*100:.3f}%, max_impact={max_impact:.0f}%)"
        )
        
        return optimal_hours
    
    def generate_holding_advice(
        self,
        opened_at: datetime,
        direction: str,
        accumulated_funding: float,
        current_price_pnl: float,
        funding_rate: float,
        leverage: int,
        expected_profit_percent: float = 5.0
    ) -> HoldingAdvice:
        """
        Generate holding advice for current position
        
        Args:
            opened_at: When position was opened
            direction: Position direction
            accumulated_funding: Total funding paid/received so far
            current_price_pnl: Current PnL from price movement
            funding_rate: Current funding rate
            leverage: Leverage multiplier
            expected_profit_percent: Expected profit target
            
        Returns:
            HoldingAdvice with alert level and recommendation
        """
        # Calculate current holding time
        now = datetime.now()
        holding_duration = now - opened_at
        current_holding_hours = holding_duration.total_seconds() / 3600
        
        # Calculate recommended max holding
        recommended_max = self.calculate_optimal_holding(
            expected_profit_percent=expected_profit_percent,
            funding_rate=funding_rate,
            leverage=leverage,
            confidence=50,  # Default confidence for existing position
            direction=direction
        )
        
        # Calculate funding impact
        if abs(current_price_pnl) > 0.01:
            funding_impact_percent = abs(accumulated_funding) / abs(current_price_pnl) * 100
        else:
            # No price PnL yet
            funding_impact_percent = 100 if accumulated_funding < 0 else 0
        
        # Determine alert level
        if funding_impact_percent >= self.config.force_close_threshold:
            alert_level = HoldingAlertLevel.CRITICAL
        elif funding_impact_percent >= 40:
            alert_level = HoldingAlertLevel.DANGER
        elif funding_impact_percent >= self.config.warning_threshold:
            alert_level = HoldingAlertLevel.WARNING
        else:
            alert_level = HoldingAlertLevel.NORMAL
        
        # Generate advice text
        advice = self._generate_advice_text(
            current_holding_hours=current_holding_hours,
            recommended_max=recommended_max,
            funding_impact_percent=funding_impact_percent,
            alert_level=alert_level,
            accumulated_funding=accumulated_funding,
            current_price_pnl=current_price_pnl
        )
        
        result = HoldingAdvice(
            current_holding_hours=current_holding_hours,
            recommended_max_hours=recommended_max,
            accumulated_funding=accumulated_funding,
            funding_impact_percent=funding_impact_percent,
            alert_level=alert_level,
            advice=advice
        )
        
        logger.info(
            f"[HoldingManager] Advice: holding={current_holding_hours:.1f}h, "
            f"max={recommended_max}h, impact={funding_impact_percent:.1f}%, "
            f"level={alert_level.value}"
        )
        
        return result
    
    def _generate_advice_text(
        self,
        current_holding_hours: float,
        recommended_max: int,
        funding_impact_percent: float,
        alert_level: HoldingAlertLevel,
        accumulated_funding: float,
        current_price_pnl: float
    ) -> str:
        """Generate human-readable advice"""
        
        if alert_level == HoldingAlertLevel.CRITICAL:
            return (
                f"⚠️ 紧急：资金费已吞噬 {funding_impact_percent:.0f}% 的价差利润！"
                f"累计资金费: ${accumulated_funding:.2f}，价差盈亏: ${current_price_pnl:.2f}。"
                f"建议立即平仓止损。"
            )
        
        if alert_level == HoldingAlertLevel.DANGER:
            return (
                f"⚠️ 危险：资金费占价差利润的 {funding_impact_percent:.0f}%。"
                f"已持仓 {current_holding_hours:.1f}h，建议最长 {recommended_max}h。"
                f"考虑尽快平仓锁定利润。"
            )
        
        if alert_level == HoldingAlertLevel.WARNING:
            return (
                f"⚠ 警告：资金费占价差利润的 {funding_impact_percent:.0f}%。"
                f"已持仓 {current_holding_hours:.1f}h / 建议 {recommended_max}h。"
                f"注意监控资金费累积。"
            )
        
        # Normal
        remaining_hours = max(0, recommended_max - current_holding_hours)
        return (
            f"✅ 正常：资金费影响 {funding_impact_percent:.0f}%。"
            f"已持仓 {current_holding_hours:.1f}h，建议最长 {recommended_max}h "
            f"(还可持有约 {remaining_hours:.0f}h)。"
        )
    
    def should_extend_holding(
        self,
        current_advice: HoldingAdvice,
        new_expected_profit: float,
        current_funding_rate: float
    ) -> bool:
        """
        Determine if holding time should be extended based on new analysis
        
        Called when a new analysis suggests continued holding.
        
        Args:
            current_advice: Current holding advice
            new_expected_profit: New expected profit from fresh analysis
            current_funding_rate: Current funding rate
            
        Returns:
            True if holding can be safely extended
        """
        # Don't extend if already in danger/critical
        if current_advice.alert_level in [HoldingAlertLevel.CRITICAL, HoldingAlertLevel.DANGER]:
            return False
        
        # Check if new profit expectation justifies extension
        if new_expected_profit > current_advice.funding_impact_percent:
            return True
        
        return False


# Global singleton
_manager: Optional[HoldingTimeManager] = None


def get_holding_time_manager() -> HoldingTimeManager:
    """Get or create holding time manager singleton"""
    global _manager
    if _manager is None:
        _manager = HoldingTimeManager()
    return _manager
