"""
Entry Timing Controller

Controls entry timing based on funding rate settlement schedules.
Implements pre-settlement delay for paying positions.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from .models import FundingRate, EntryDecision, EntryAction, FundingDirection
from .config import get_funding_config

logger = logging.getLogger(__name__)


class EntryTimingController:
    """
    Entry Timing Controller
    
    Controls when positions should be opened based on funding settlement timing.
    
    Key rule:
    - If position would PAY funding and settlement is within buffer time,
      delay entry until after settlement to avoid paying.
    - If position would RECEIVE funding and settlement is soon,
      enter now to collect the payment.
    """
    
    def __init__(self):
        self.config = get_funding_config()
    
    def should_delay_entry(
        self,
        direction: str,
        funding_rate: FundingRate
    ) -> EntryDecision:
        """
        Determine if entry should be delayed
        
        Args:
            direction: "long" or "short"
            funding_rate: Current funding rate data
            
        Returns:
            EntryDecision with action and reasoning
        """
        # Get minutes until settlement
        minutes_to_settlement = funding_rate.minutes_to_settlement
        
        # Determine if this position would pay or receive
        payment_direction = funding_rate.direction_for_position(direction)
        is_paying = payment_direction == FundingDirection.PAYING
        
        # Get next settlement time
        next_settlement = funding_rate.next_settlement_time
        
        # Calculate recommended entry time (right after settlement)
        if next_settlement:
            recommended_entry = next_settlement + timedelta(minutes=1)
        else:
            recommended_entry = None
        
        # Check if should delay
        should_delay = self.config.should_delay_entry(minutes_to_settlement, is_paying)
        
        if should_delay:
            reason = (
                f"距离下次结算仅 {minutes_to_settlement} 分钟，"
                f"当前费率 {funding_rate.rate_percent:.3f}%，"
                f"作为{direction}方需支付资金费。"
                f"建议等待结算后入场，节省一次费用。"
            )
            
            logger.info(
                f"[EntryTiming] DELAY entry: {direction} position, "
                f"{minutes_to_settlement}min to settlement, rate={funding_rate.rate_percent:.3f}%"
            )
            
            return EntryDecision(
                action=EntryAction.DELAY,
                minutes_to_wait=minutes_to_settlement + 1,
                reason=reason,
                next_settlement=next_settlement,
                recommended_entry_time=recommended_entry
            )
        
        # Check if should enter now for receiving
        if not is_paying and minutes_to_settlement <= 30:
            reason = (
                f"距离下次结算仅 {minutes_to_settlement} 分钟，"
                f"当前费率 {funding_rate.rate_percent:.3f}%，"
                f"作为{direction}方将收取资金费。"
                f"建议立即入场，白拿一次费用！"
            )
            
            logger.info(
                f"[EntryTiming] ENTER NOW to receive funding: {direction} position, "
                f"{minutes_to_settlement}min to settlement"
            )
            
            return EntryDecision(
                action=EntryAction.ENTER_NOW,
                minutes_to_wait=0,
                reason=reason,
                next_settlement=next_settlement
            )
        
        # Normal entry
        payment_note = "将支付" if is_paying else "将收取"
        reason = (
            f"距离下次结算 {minutes_to_settlement} 分钟，"
            f"作为{direction}方{payment_note}资金费 ({funding_rate.rate_percent:.3f}%)。"
        )
        
        return EntryDecision(
            action=EntryAction.ENTER_NOW,
            minutes_to_wait=0,
            reason=reason,
            next_settlement=next_settlement
        )
    
    def get_optimal_entry_time(
        self,
        direction: str,
        funding_rate: FundingRate
    ) -> Optional[datetime]:
        """
        Get optimal entry time
        
        For payers: Enter right after settlement
        For receivers: Enter right before settlement
        
        Args:
            direction: Position direction
            funding_rate: Current funding rate data
            
        Returns:
            Optimal entry time or None if enter now
        """
        decision = self.should_delay_entry(direction, funding_rate)
        
        if decision.action == EntryAction.DELAY:
            return decision.recommended_entry_time
        
        return None
    
    def get_next_settlement_time(self) -> datetime:
        """
        Calculate next settlement time based on current time
        
        OKX settles at 00:00, 08:00, 16:00 UTC
        """
        now = datetime.now(timezone.utc)
        
        settlement_hours = self.config.settlement_hours_utc
        
        for hour in settlement_hours:
            settlement = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if settlement > now:
                return settlement
        
        # Next day's first settlement
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=settlement_hours[0], minute=0, second=0, microsecond=0)
    
    def get_settlement_countdown(self) -> int:
        """Get minutes until next settlement"""
        next_settlement = self.get_next_settlement_time()
        now = datetime.now(timezone.utc)
        delta = next_settlement - now
        return max(0, int(delta.total_seconds() / 60))


# Global singleton
_controller: Optional[EntryTimingController] = None


def get_entry_timing_controller() -> EntryTimingController:
    """Get or create entry timing controller singleton"""
    global _controller
    if _controller is None:
        _controller = EntryTimingController()
    return _controller
