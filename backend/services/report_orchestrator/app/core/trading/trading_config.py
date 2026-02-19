"""
Trading Configuration

Centralized configuration for trading meetings and execution.
All values are configurable via environment variables.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List

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


def _get_env_str(key: str, default: str) -> str:
    """Get string from environment variable"""
    return os.getenv(key, default)


def _get_env_bool(key: str, default: bool) -> bool:
    """Get boolean from environment variable"""
    val = os.getenv(key)
    if val:
        return val.lower() in ('true', '1', 'yes', 'on')
    return default


# Public aliases for use by other modules (avoids duplication)
get_env_int = _get_env_int
get_env_float = _get_env_float
get_env_str = _get_env_str
get_env_bool = _get_env_bool


@dataclass
class InfrastructureConfig:
    """
    Infrastructure configuration - URLs and connection settings.

    Environment Variables:
        REDIS_URL: Redis connection URL (default: redis://redis:6379)
        LLM_GATEWAY_URL: LLM gateway service URL (default: http://llm_gateway:8003)
        OKX_BASE_URL: OKX API base URL (default: https://www.okx.com)
        BINANCE_BASE_URL: Binance API base URL (default: https://api.binance.com)
        COINGECKO_BASE_URL: CoinGecko API base URL (default: https://api.coingecko.com)
        TAVILY_API_URL: Tavily search API URL (default: https://api.tavily.com/search)
        FNG_API_URL: Fear & Greed Index API URL
    """
    # Redis
    redis_url: str = field(default_factory=lambda: _get_env_str("REDIS_URL", "redis://redis:6379"))

    # Internal services
    llm_gateway_url: str = field(default_factory=lambda: _get_env_str("LLM_GATEWAY_URL", "http://llm_gateway:8003"))

    # External APIs
    okx_base_url: str = field(default_factory=lambda: _get_env_str("OKX_BASE_URL", "https://www.okx.com"))
    binance_base_url: str = field(default_factory=lambda: _get_env_str("BINANCE_BASE_URL", "https://api.binance.com"))
    coingecko_base_url: str = field(default_factory=lambda: _get_env_str("COINGECKO_BASE_URL", "https://api.coingecko.com"))
    tavily_api_url: str = field(default_factory=lambda: _get_env_str("TAVILY_API_URL", "https://api.tavily.com/search"))
    fng_api_url: str = field(default_factory=lambda: _get_env_str("FNG_API_URL", "https://api.alternative.me/fng"))


@dataclass
class TimeoutConfig:
    """
    Timeout configuration for HTTP requests and operations.

    Environment Variables:
        HTTP_TIMEOUT_DEFAULT: Default HTTP timeout in seconds (default: 10)
        HTTP_TIMEOUT_LONG: Long HTTP timeout for slow operations (default: 30)
        LLM_TIMEOUT: LLM call timeout in seconds (default: 60)
        REDIS_TIMEOUT: Redis operation timeout in seconds (default: 5)
    """
    http_default: float = field(default_factory=lambda: _get_env_float("HTTP_TIMEOUT_DEFAULT", 10.0))
    http_long: float = field(default_factory=lambda: _get_env_float("HTTP_TIMEOUT_LONG", 30.0))
    llm_timeout: float = field(default_factory=lambda: _get_env_float("LLM_TIMEOUT", 60.0))
    redis_timeout: float = field(default_factory=lambda: _get_env_float("REDIS_TIMEOUT", 5.0))


@dataclass
class RetryConfig:
    """
    Retry and circuit breaker configuration.

    Environment Variables:
        MAX_RETRIES: Maximum retry attempts (default: 3)
        RETRY_BASE_DELAY: Base delay between retries in seconds (default: 2.0)
        RETRY_MAX_DELAY: Maximum delay between retries in seconds (default: 60.0)
        CIRCUIT_BREAKER_THRESHOLD: Failures before circuit opens (default: 5)
        CIRCUIT_BREAKER_RECOVERY: Recovery timeout in seconds (default: 300)
    """
    max_retries: int = field(default_factory=lambda: _get_env_int("MAX_RETRIES", 3))
    base_delay: float = field(default_factory=lambda: _get_env_float("RETRY_BASE_DELAY", 2.0))
    max_delay: float = field(default_factory=lambda: _get_env_float("RETRY_MAX_DELAY", 60.0))
    exponential_base: float = 2.0
    jitter_range: float = 0.5

    # Circuit breaker
    circuit_breaker_threshold: int = field(default_factory=lambda: _get_env_int("CIRCUIT_BREAKER_THRESHOLD", 5))
    circuit_breaker_recovery: int = field(default_factory=lambda: _get_env_int("CIRCUIT_BREAKER_RECOVERY", 300))


@dataclass
class RiskConfig:
    """
    Risk management configuration.

    Environment Variables:
        RISK_CONFIDENCE_HIGH: High confidence threshold (default: 75)
        RISK_CONFIDENCE_MEDIUM: Medium confidence threshold (default: 55)
        RISK_CONFIDENCE_LOW: Low confidence threshold (default: 40)
        STARTUP_PROTECTION_SECONDS: Startup protection window (default: 300)
    """
    confidence_high: int = field(default_factory=lambda: _get_env_int("RISK_CONFIDENCE_HIGH", 75))
    confidence_medium: int = field(default_factory=lambda: _get_env_int("RISK_CONFIDENCE_MEDIUM", 55))
    confidence_low: int = field(default_factory=lambda: _get_env_int("RISK_CONFIDENCE_LOW", 40))
    startup_protection_seconds: int = field(default_factory=lambda: _get_env_int("STARTUP_PROTECTION_SECONDS", 300))


@dataclass
class WeightLearningConfig:
    """
    Agent weight learning configuration.

    Environment Variables:
        WEIGHT_MIN: Minimum agent weight (default: 0.5)
        WEIGHT_MAX: Maximum agent weight (default: 2.0)
        WEIGHT_DEFAULT: Default agent weight (default: 1.0)
        WEIGHT_LEARNING_RATE: Learning rate per trade (default: 0.1)
        WEIGHT_MIN_TRADES: Minimum trades before adjustment (default: 5)
    """
    min_weight: float = field(default_factory=lambda: _get_env_float("WEIGHT_MIN", 0.5))
    max_weight: float = field(default_factory=lambda: _get_env_float("WEIGHT_MAX", 2.0))
    default_weight: float = field(default_factory=lambda: _get_env_float("WEIGHT_DEFAULT", 1.0))
    learning_rate: float = field(default_factory=lambda: _get_env_float("WEIGHT_LEARNING_RATE", 0.1))
    min_trades_for_adjustment: int = field(default_factory=lambda: _get_env_int("WEIGHT_MIN_TRADES", 5))
    recent_window: int = field(default_factory=lambda: _get_env_int("WEIGHT_RECENT_WINDOW", 20))


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


# Singleton instances
_infra_config: InfrastructureConfig = None
_timeout_config: TimeoutConfig = None
_retry_config: RetryConfig = None
_risk_config: RiskConfig = None
_weight_config: WeightLearningConfig = None
_trading_config: TradingMeetingConfig = None


def get_infra_config() -> InfrastructureConfig:
    """Get singleton InfrastructureConfig instance."""
    global _infra_config
    if _infra_config is None:
        _infra_config = InfrastructureConfig()
    return _infra_config


def get_timeout_config() -> TimeoutConfig:
    """Get singleton TimeoutConfig instance."""
    global _timeout_config
    if _timeout_config is None:
        _timeout_config = TimeoutConfig()
    return _timeout_config


def get_retry_config() -> RetryConfig:
    """Get singleton RetryConfig instance."""
    global _retry_config
    if _retry_config is None:
        _retry_config = RetryConfig()
    return _retry_config


def get_risk_config() -> RiskConfig:
    """Get singleton RiskConfig instance."""
    global _risk_config
    if _risk_config is None:
        _risk_config = RiskConfig()
    return _risk_config


def get_weight_config() -> WeightLearningConfig:
    """Get singleton WeightLearningConfig instance."""
    global _weight_config
    if _weight_config is None:
        _weight_config = WeightLearningConfig()
    return _weight_config


def get_trading_config() -> TradingMeetingConfig:
    """Get singleton TradingMeetingConfig instance."""
    global _trading_config
    if _trading_config is None:
        _trading_config = TradingMeetingConfig()
    return _trading_config


# Convenience function to get Redis URL
def get_redis_url() -> str:
    """Get Redis URL from configuration."""
    return get_infra_config().redis_url


# Convenience function to get LLM Gateway URL
def get_llm_gateway_url() -> str:
    """Get LLM Gateway URL from configuration."""
    return get_infra_config().llm_gateway_url
