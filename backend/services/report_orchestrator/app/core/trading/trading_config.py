"""
Trading Configuration

Centralized configuration for trading meetings and execution.
All values are configurable via environment variables.
"""

import os
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def _get_env_int(key: str, default: int) -> int:
    """Get integer from environment variable"""
    val = os.getenv(key)
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return default


def _get_env_float(key: str, default: float) -> float:
    """Get float from environment variable"""
    val = os.getenv(key)
    if val:
        try:
            return float(val)
        except ValueError:
            pass
    return default


@dataclass
class TradingMeetingConfig:
    """
    Configuration for trading meeting - reads from environment variables.
    
    Environment Variables:
        TRADING_SYMBOL: Trading pair (default: BTC-USDT-SWAP)
        MAX_LEVERAGE: Maximum leverage (default: 20)
        MAX_POSITION_PERCENT: Max position % (default: 30)
        MIN_POSITION_PERCENT: Min position % (default: 10)
        DEFAULT_POSITION_PERCENT: Default position % (default: 20)
        MIN_CONFIDENCE: Minimum confidence to trade (default: 60)
        DEFAULT_TP_PERCENT: Default take profit % (default: 5.0)
        DEFAULT_SL_PERCENT: Default stop loss % (default: 2.0)
    """
    # Trading pair
    symbol: str = field(default_factory=lambda: os.getenv("TRADING_SYMBOL", "BTC-USDT-SWAP"))
    
    # Leverage and position limits
    max_leverage: int = field(default_factory=lambda: _get_env_int("MAX_LEVERAGE", 20))
    max_position_percent: float = field(default_factory=lambda: _get_env_float("MAX_POSITION_PERCENT", 30) / 100)
    min_position_percent: float = field(default_factory=lambda: _get_env_float("MIN_POSITION_PERCENT", 10) / 100)
    default_position_percent: float = field(default_factory=lambda: _get_env_float("DEFAULT_POSITION_PERCENT", 20) / 100)
    
    # Confidence threshold
    min_confidence: int = field(default_factory=lambda: _get_env_int("MIN_CONFIDENCE", 60))
    
    # Meeting settings
    max_rounds: int = 3
    require_risk_manager_approval: bool = True
    
    # Default take profit / stop loss percentages
    default_tp_percent: float = field(default_factory=lambda: _get_env_float("DEFAULT_TP_PERCENT", 5.0))
    default_sl_percent: float = field(default_factory=lambda: _get_env_float("DEFAULT_SL_PERCENT", 2.0))
    
    # Default balance (for calculation if unable to get actual balance)
    default_balance: float = 10000.0
    
    # Fallback price (only used when unable to get real-time price)
    fallback_price: float = 95000.0
    
    # 🆕 LangGraph workflow (enabled by default - new architecture)
    use_langgraph: bool = field(default_factory=lambda: os.getenv("USE_LANGGRAPH", "true").lower() == "true")

    def __post_init__(self):
        """Log the configuration after initialization"""
        logger.info(
            f"TradingMeetingConfig initialized: max_leverage={self.max_leverage}, "
            f"position_range={self.min_position_percent*100:.0f}%-{self.max_position_percent*100:.0f}%, "
            f"min_confidence={self.min_confidence}%, tp/sl={self.default_tp_percent}%/{self.default_sl_percent}%"
        )
