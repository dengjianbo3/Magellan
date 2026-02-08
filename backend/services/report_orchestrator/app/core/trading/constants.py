"""
Trading System Constants

Centralized constants for technical indicators, thresholds, and configuration values.
Replaces hardcoded magic numbers throughout the codebase.
"""

from dataclasses import dataclass


# =============================================================================
# Technical Indicator Parameters
# =============================================================================

@dataclass(frozen=True)
class RSIConfig:
    """RSI (Relative Strength Index) parameters."""
    PERIOD: int = 14
    OVERBOUGHT: int = 70
    OVERSOLD: int = 30
    NEUTRAL: int = 50


@dataclass(frozen=True)
class MACDConfig:
    """MACD (Moving Average Convergence Divergence) parameters."""
    FAST_PERIOD: int = 12
    SLOW_PERIOD: int = 26
    SIGNAL_PERIOD: int = 9


@dataclass(frozen=True)
class BollingerBandsConfig:
    """Bollinger Bands parameters."""
    PERIOD: int = 20
    STD_DEV: float = 2.0


@dataclass(frozen=True)
class EMAConfig:
    """EMA (Exponential Moving Average) parameters."""
    FAST_PERIOD: int = 9
    SLOW_PERIOD: int = 21
    PERIOD_20: int = 20
    PERIOD_50: int = 50


@dataclass(frozen=True)
class KDJConfig:
    """KDJ indicator parameters."""
    K_PERIOD: int = 9
    D_PERIOD: int = 3
    J_MULTIPLIER: int = 3


@dataclass(frozen=True)
class ADXConfig:
    """ADX (Average Directional Index) parameters."""
    PERIOD: int = 14
    STRONG_TREND: int = 25
    WEAK_TREND: int = 20


@dataclass(frozen=True)
class ATRConfig:
    """ATR (Average True Range) parameters."""
    PERIOD: int = 14
    MULTIPLIER: float = 1.5
    MAX_SL_PERCENT: float = 5.0
    MIN_SL_PERCENT: float = 0.5


# Singleton instances
RSI = RSIConfig()
MACD = MACDConfig()
BOLLINGER_BANDS = BollingerBandsConfig()
EMA = EMAConfig()
KDJ = KDJConfig()
ADX = ADXConfig()
ATR = ATRConfig()


# =============================================================================
# Confidence Thresholds
# =============================================================================

@dataclass(frozen=True)
class ConfidenceThresholds:
    """Trading confidence thresholds."""
    HIGH: int = 75
    MEDIUM: int = 55
    LOW: int = 40
    MINIMUM: int = 30

    # For risk assessment
    VERY_HIGH: int = 85
    MODERATE: int = 65


CONFIDENCE = ConfidenceThresholds()


# =============================================================================
# Leverage Thresholds
# =============================================================================

@dataclass(frozen=True)
class LeverageThresholds:
    """Leverage recommendation thresholds based on confidence."""
    HIGH_CONFIDENCE: int = 85      # Use higher leverage
    MEDIUM_CONFIDENCE: int = 75    # Use medium leverage
    LOW_CONFIDENCE: int = 65       # Use lower leverage

    # Leverage values
    MAX_LEVERAGE: int = 20
    HIGH_LEVERAGE: int = 10
    MEDIUM_LEVERAGE: int = 5
    LOW_LEVERAGE: int = 3
    MIN_LEVERAGE: int = 1


LEVERAGE = LeverageThresholds()


# =============================================================================
# Timeframes
# =============================================================================

@dataclass(frozen=True)
class Timeframes:
    """Standard timeframes for analysis."""
    M1: str = "1m"
    M5: str = "5m"
    M15: str = "15m"
    M30: str = "30m"
    H1: str = "1H"
    H4: str = "4H"
    D1: str = "1D"
    W1: str = "1W"

    # Default timeframes for multi-timeframe analysis
    DEFAULT_MTF: tuple = ("15m", "1H", "4H")

    # Candle limits per timeframe
    DEFAULT_CANDLE_LIMIT: int = 100
    MAX_CANDLE_LIMIT: int = 500


TIMEFRAMES = Timeframes()


# =============================================================================
# Price Movement Thresholds
# =============================================================================

@dataclass(frozen=True)
class PriceThresholds:
    """Price movement thresholds for triggers."""
    # Spike detection (percentage)
    SPIKE_1M: float = 1.5
    SPIKE_5M: float = 2.5
    SPIKE_15M: float = 3.5

    # Trend detection (percentage)
    UPTREND_THRESHOLD: float = 1.0
    DOWNTREND_THRESHOLD: float = -1.0

    # Volatility
    HIGH_VOLATILITY: float = 3.0
    LOW_VOLATILITY: float = 0.5


PRICE = PriceThresholds()


# =============================================================================
# Volume Thresholds
# =============================================================================

@dataclass(frozen=True)
class VolumeThresholds:
    """Volume analysis thresholds."""
    SPIKE_MULTIPLIER: float = 2.0
    HIGH_VOLUME_MULTIPLIER: float = 1.5
    LOW_VOLUME_MULTIPLIER: float = 0.5


VOLUME = VolumeThresholds()


# =============================================================================
# Funding Rate Thresholds
# =============================================================================

@dataclass(frozen=True)
class FundingRateThresholds:
    """Funding rate thresholds."""
    HIGH_POSITIVE: float = 0.0005    # 0.05%
    HIGH_NEGATIVE: float = -0.0005   # -0.05%
    EXTREME_POSITIVE: float = 0.001  # 0.1%
    EXTREME_NEGATIVE: float = -0.001 # -0.1%


FUNDING_RATE = FundingRateThresholds()


# =============================================================================
# Consensus & Voting
# =============================================================================

@dataclass(frozen=True)
class ConsensusConfig:
    """Consensus calculation parameters."""
    # Echo chamber detection
    ECHO_CHAMBER_THRESHOLD: float = 0.85
    MIN_VOTES_FOR_CONSENSUS: int = 3

    # Weight bounds
    MIN_AGENT_WEIGHT: float = 0.5
    MAX_AGENT_WEIGHT: float = 2.0
    DEFAULT_AGENT_WEIGHT: float = 1.0

    # Neutral score base
    NEUTRAL_SCORE_BASE: int = 50


CONSENSUS = ConsensusConfig()


# =============================================================================
# Retry & Timeout
# =============================================================================

@dataclass(frozen=True)
class RetryConfig:
    """Retry and timeout configuration."""
    MAX_RETRIES: int = 3
    BASE_DELAY: float = 2.0
    MAX_DELAY: float = 60.0
    EXPONENTIAL_BASE: int = 2

    # Timeouts (seconds)
    HTTP_DEFAULT: float = 10.0
    HTTP_LONG: float = 30.0
    LLM_TIMEOUT: float = 60.0


RETRY = RetryConfig()


# =============================================================================
# Cache & History
# =============================================================================

@dataclass(frozen=True)
class CacheConfig:
    """Cache and history configuration."""
    PRICE_CACHE_TTL: int = 30          # seconds
    PRICE_HISTORY_MAXLEN: int = 60     # items
    MESSAGE_HISTORY_LIMIT: int = 20    # messages

    # Grace period for stale data
    PRICE_GRACE_PERIOD: int = 300      # 5 minutes


CACHE = CacheConfig()


# =============================================================================
# Risk Management
# =============================================================================

@dataclass(frozen=True)
class RiskConfig:
    """Risk management parameters."""
    # Position sizing
    MAX_POSITION_PERCENT: float = 10.0
    DEFAULT_POSITION_PERCENT: float = 5.0

    # Stop loss
    DEFAULT_SL_PERCENT: float = 2.0
    MAX_SL_PERCENT: float = 5.0
    MIN_SL_PERCENT: float = 0.5

    # Take profit
    DEFAULT_TP_RATIO: float = 2.0  # Risk:Reward ratio

    # Liquidation buffer
    LIQUIDATION_BUFFER_PERCENT: float = 0.5


RISK = RiskConfig()


# =============================================================================
# Scoring & Signals
# =============================================================================

@dataclass(frozen=True)
class ScoringConfig:
    """Signal scoring parameters."""
    # Signal strength thresholds
    STRONG_SIGNAL: int = 4
    MODERATE_SIGNAL: int = 3
    WEAK_SIGNAL: int = 2

    # Score weights
    RSI_WEIGHT: float = 0.2
    MACD_WEIGHT: float = 0.2
    TREND_WEIGHT: float = 0.3
    VOLUME_WEIGHT: float = 0.15
    PATTERN_WEIGHT: float = 0.15


SCORING = ScoringConfig()


# =============================================================================
# API Limits
# =============================================================================

@dataclass(frozen=True)
class APILimits:
    """External API limits."""
    # OKX
    OKX_MAX_CANDLES: int = 300
    OKX_MAX_ORDERBOOK: int = 400

    # Binance
    BINANCE_MAX_CANDLES: int = 1000
    BINANCE_MAX_ORDERBOOK: int = 5000

    # Rate limiting
    REQUESTS_PER_SECOND: int = 10
    REQUESTS_PER_MINUTE: int = 100


API_LIMITS = APILimits()


# =============================================================================
# Arbitrage & Spread
# =============================================================================

@dataclass(frozen=True)
class ArbitrageConfig:
    """Arbitrage detection parameters."""
    MIN_SPREAD_PERCENT: float = 0.5
    SIGNIFICANT_SPREAD_PERCENT: float = 1.0


ARBITRAGE = ArbitrageConfig()
