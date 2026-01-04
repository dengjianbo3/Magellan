"""
Funding Impact Monitor

Real-time monitoring of funding fee impact on positions.
Triggers force-close when funding costs exceed threshold.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Awaitable

from .models import HoldingAlertLevel, TruePnL
from .config import get_funding_config
from .calculator import get_funding_calculator

logger = logging.getLogger(__name__)


class FundingImpact:
    """
    Funding impact assessment result
    """
    def __init__(
        self,
        impact_percent: float,
        alert_level: HoldingAlertLevel,
        should_close: bool,
        reason: str,
        true_pnl: Optional[TruePnL] = None
    ):
        self.impact_percent = impact_percent
        self.alert_level = alert_level
        self.should_close = should_close
        self.reason = reason
        self.true_pnl = true_pnl


class FundingImpactMonitor:
    """
    Funding Impact Monitor
    
    Monitors funding fee impact on open positions and triggers
    force-close when costs exceed configured threshold.
    
    Features:
    - Real-time impact calculation
    - Alert level classification
    - Force-close trigger
    - Callback support for position closing
    """
    
    def __init__(self):
        self.config = get_funding_config()
        self.calculator = get_funding_calculator()
        
        # Callback for force closing positions
        self.on_force_close: Optional[Callable[[str, str], Awaitable[Dict]]] = None
        
        # Track last check time to avoid spam
        self._last_check: Dict[str, datetime] = {}
        self._check_interval_seconds = 60  # Check at most once per minute
    
    def check_funding_impact(
        self,
        position_id: str,
        price_pnl: float,
        accumulated_funding: float,
        trading_fees: float,
        margin: float,
        funding_count: int = 0
    ) -> FundingImpact:
        """
        Check funding fee impact on position
        
        Args:
            position_id: Unique position identifier
            price_pnl: PnL from price movement
            accumulated_funding: Total funding paid (negative) or received (positive)
            trading_fees: Total trading fees
            margin: Position margin
            funding_count: Number of funding settlements
            
        Returns:
            FundingImpact assessment
        """
        # Calculate true PnL
        true_pnl = self.calculator.calculate_true_pnl(
            price_pnl=price_pnl,
            accumulated_funding=accumulated_funding,
            trading_fees=trading_fees,
            margin=margin,
            funding_count=funding_count
        )
        
        impact_percent = true_pnl.funding_impact_percent
        
        # Determine alert level and action
        if impact_percent >= self.config.force_close_threshold:
            alert_level = HoldingAlertLevel.CRITICAL
            should_close = True
            reason = (
                f"资金费已吞噬 {impact_percent:.0f}% 的价差利润，"
                f"超过阈值 {self.config.force_close_threshold}%，触发强制平仓。"
            )
        elif impact_percent >= 40:
            alert_level = HoldingAlertLevel.DANGER
            should_close = False
            reason = (
                f"资金费占价差利润的 {impact_percent:.0f}%，"
                f"接近强制平仓阈值 {self.config.force_close_threshold}%。"
            )
        elif impact_percent >= self.config.warning_threshold:
            alert_level = HoldingAlertLevel.WARNING
            should_close = False
            reason = f"资金费占价差利润的 {impact_percent:.0f}%，需要关注。"
        else:
            alert_level = HoldingAlertLevel.NORMAL
            should_close = False
            reason = f"资金费影响正常 ({impact_percent:.0f}%)。"
        
        result = FundingImpact(
            impact_percent=impact_percent,
            alert_level=alert_level,
            should_close=should_close,
            reason=reason,
            true_pnl=true_pnl
        )
        
        if alert_level != HoldingAlertLevel.NORMAL:
            logger.warning(
                f"[FundingMonitor] Position {position_id}: "
                f"impact={impact_percent:.1f}%, level={alert_level.value}, "
                f"price_pnl=${price_pnl:.2f}, funding=${accumulated_funding:.2f}"
            )
        
        return result
    
    async def check_and_act(
        self,
        position_id: str,
        symbol: str,
        price_pnl: float,
        accumulated_funding: float,
        trading_fees: float,
        margin: float,
        funding_count: int = 0
    ) -> FundingImpact:
        """
        Check funding impact and take action if needed
        
        Args:
            position_id: Position identifier
            symbol: Trading symbol
            price_pnl: PnL from price movement
            accumulated_funding: Accumulated funding fees
            trading_fees: Trading fees
            margin: Position margin
            funding_count: Number of settlements
            
        Returns:
            FundingImpact with action taken
        """
        # Rate limit checks
        now = datetime.now()
        last_check = self._last_check.get(position_id)
        if last_check and (now - last_check).seconds < self._check_interval_seconds:
            # Skip if checked recently
            return FundingImpact(
                impact_percent=0,
                alert_level=HoldingAlertLevel.NORMAL,
                should_close=False,
                reason="Recently checked, skipping"
            )
        
        self._last_check[position_id] = now
        
        # Perform check
        impact = self.check_funding_impact(
            position_id=position_id,
            price_pnl=price_pnl,
            accumulated_funding=accumulated_funding,
            trading_fees=trading_fees,
            margin=margin,
            funding_count=funding_count
        )
        
        # Take action if needed
        if impact.should_close:
            await self._trigger_force_close(position_id, symbol, impact)
        
        return impact
    
    async def _trigger_force_close(
        self,
        position_id: str,
        symbol: str,
        impact: FundingImpact
    ):
        """
        Trigger force close of position
        
        Args:
            position_id: Position to close
            symbol: Trading symbol
            impact: Impact assessment that triggered close
        """
        logger.warning(
            f"[FundingMonitor] 🚨 FORCE CLOSE triggered for {position_id}: "
            f"impact={impact.impact_percent:.1f}%, reason={impact.reason}"
        )
        
        if self.on_force_close:
            try:
                result = await self.on_force_close(symbol, "funding_limit_exceeded")
                
                if result and result.get('success'):
                    logger.info(
                        f"[FundingMonitor] ✅ Position {position_id} force-closed successfully. "
                        f"True PnL: ${impact.true_pnl.true_pnl:.2f}"
                    )
                else:
                    logger.error(
                        f"[FundingMonitor] ❌ Force close failed for {position_id}: "
                        f"{result.get('error') if result else 'No result'}"
                    )
            except Exception as e:
                logger.error(f"[FundingMonitor] Force close error: {e}")
        else:
            logger.warning(
                f"[FundingMonitor] No force-close callback registered! "
                f"Position {position_id} should be closed manually."
            )
    
    def register_close_callback(
        self,
        callback: Callable[[str, str], Awaitable[Dict]]
    ):
        """
        Register callback for force-closing positions
        
        Args:
            callback: Async function(symbol, reason) -> Dict
        """
        self.on_force_close = callback
        logger.info("[FundingMonitor] Force-close callback registered")
    
    def clear_position_tracking(self, position_id: str):
        """Clear tracking data for a closed position"""
        if position_id in self._last_check:
            del self._last_check[position_id]
    
    def get_summary(
        self,
        price_pnl: float,
        accumulated_funding: float,
        trading_fees: float
    ) -> str:
        """
        Get human-readable summary of funding impact
        
        Args:
            price_pnl: PnL from price movement
            accumulated_funding: Accumulated funding fees
            trading_fees: Trading fees
            
        Returns:
            Formatted summary string
        """
        true_pnl = price_pnl + accumulated_funding - trading_fees
        
        if abs(price_pnl) > 0.01:
            impact = abs(accumulated_funding) / abs(price_pnl) * 100
        else:
            impact = 100 if accumulated_funding < 0 else 0
        
        return f"""
📊 真实盈亏分析
─────────────
价差盈亏: ${price_pnl:+.2f}
资金费用: ${accumulated_funding:+.2f}
交易手续费: -${trading_fees:.2f}
─────────────
真实盈亏: ${true_pnl:+.2f}
资金费影响: {impact:.1f}%
"""


# Global singleton
_monitor: Optional[FundingImpactMonitor] = None


def get_funding_impact_monitor() -> FundingImpactMonitor:
    """Get or create funding impact monitor singleton"""
    global _monitor
    if _monitor is None:
        _monitor = FundingImpactMonitor()
    return _monitor
