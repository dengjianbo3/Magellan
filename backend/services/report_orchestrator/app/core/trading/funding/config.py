"""
Funding Fee Configuration

Environment variable based configuration for funding fee awareness system.
"""

from dataclasses import dataclass
from typing import Optional

from app.core.trading.trading_config import (
    get_env_int as _get_env_int,
    get_env_float as _get_env_float,
    get_env_bool as _get_env_bool,
)


@dataclass
class FundingConfig:
    """
    Configuration for Funding Fee Awareness System
    
    All values are read from environment variables with sensible defaults.
    """
    
    # ===== 入场时机控制 =====
    # 结算前多少分钟不开仓 (如果是付费方)
    pre_settlement_buffer_minutes: int = _get_env_int('FUNDING_PRE_SETTLEMENT_BUFFER', 30)
    
    # ===== 强制平仓阈值 =====
    # 资金费占价差利润超过此比例时强制平仓 (%)
    force_close_threshold: float = _get_env_float('FUNDING_FORCE_CLOSE_THRESHOLD', 50)
    
    # 资金费占价差利润超过此比例时警告 (%)
    warning_threshold: float = _get_env_float('FUNDING_WARNING_THRESHOLD', 30)
    
    # ===== 持仓时间控制 =====
    # 默认最大持仓时间 (小时)
    default_max_holding_hours: int = _get_env_int('FUNDING_MAX_HOLDING_HOURS', 72)
    
    # ===== 交易可行性评估 =====
    # 预期利润需要大于成本的倍数才认为可行
    profit_buffer_multiplier: float = _get_env_float('FUNDING_PROFIT_BUFFER', 1.5)
    
    # ===== 费率阈值 =====
    # 费率警告阈值 (0.0003 = 0.03%)
    rate_warning_threshold: float = _get_env_float('FUNDING_RATE_WARNING', 0.0003)
    
    # 极端费率阈值 (0.001 = 0.1%)
    rate_extreme_threshold: float = _get_env_float('FUNDING_RATE_EXTREME', 0.001)
    
    # ===== 结算时间 (UTC) =====
    settlement_hours_utc: list = None  # [0, 8, 16]
    
    # ===== 默认手续费率 =====
    default_trading_fee: float = _get_env_float('TRADING_FEE_RATE', 0.001)  # 0.1%
    
    def __post_init__(self):
        if self.settlement_hours_utc is None:
            self.settlement_hours_utc = [0, 8, 16]  # 00:00, 08:00, 16:00 UTC
    
    def should_delay_entry(self, minutes_to_settlement: int, is_paying: bool) -> bool:
        """
        Determine if entry should be delayed based on settlement timing
        
        Args:
            minutes_to_settlement: Minutes until next settlement
            is_paying: True if position would pay funding
            
        Returns:
            True if entry should be delayed
        """
        if not is_paying:
            # If receiving, enter now to collect funding
            return False
        
        # If paying and within buffer, delay
        return minutes_to_settlement < self.pre_settlement_buffer_minutes
    
    def should_force_close(self, funding_impact_percent: float) -> bool:
        """
        Determine if position should be force-closed
        
        Args:
            funding_impact_percent: Funding cost as % of price PnL
            
        Returns:
            True if position should be closed
        """
        return funding_impact_percent >= self.force_close_threshold
    
    def is_rate_extreme(self, rate: float) -> bool:
        """Check if funding rate is extreme"""
        return abs(rate) >= self.rate_extreme_threshold
    
    def is_rate_warning(self, rate: float) -> bool:
        """Check if funding rate warrants a warning"""
        return abs(rate) >= self.rate_warning_threshold


# Global singleton
_config: Optional[FundingConfig] = None


def get_funding_config() -> FundingConfig:
    """Get or create funding config singleton"""
    global _config
    if _config is None:
        _config = FundingConfig()
    return _config
