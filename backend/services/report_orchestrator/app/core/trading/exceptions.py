"""
Trading System Custom Exceptions

Centralized exception definitions for the trading system.
Provides specific exception types for better error handling and debugging.
"""


class TradingError(Exception):
    """Base exception for all trading-related errors."""
    pass


class MarketDataError(TradingError):
    """Error fetching or processing market data."""
    pass


class PriceServiceError(MarketDataError):
    """Error from price service (CoinGecko, OKX, etc.)."""
    pass


class CandleDataError(MarketDataError):
    """Error fetching candle/OHLCV data."""
    pass


class OrderbookError(MarketDataError):
    """Error fetching orderbook data."""
    pass


class TradingExecutionError(TradingError):
    """Error during trade execution."""
    pass


class InsufficientBalanceError(TradingExecutionError):
    """Insufficient balance to execute trade."""
    pass


class PositionError(TradingExecutionError):
    """Error related to position management."""
    pass


class PositionAlreadyExistsError(PositionError):
    """Attempted to open position when one already exists."""
    pass


class NoPositionError(PositionError):
    """Attempted to close/modify position when none exists."""
    pass


class LLMError(TradingError):
    """Error from LLM service."""
    pass


class LLMTimeoutError(LLMError):
    """LLM request timed out."""
    pass


class LLMParseError(LLMError):
    """Failed to parse LLM response."""
    pass


class ConfigurationError(TradingError):
    """Configuration or environment variable error."""
    pass


class RedisConnectionError(TradingError):
    """Error connecting to Redis."""
    pass


class TriggerError(TradingError):
    """Error in trigger system."""
    pass


class NewsServiceError(TriggerError):
    """Error fetching news data."""
    pass


class TechnicalAnalysisError(TriggerError):
    """Error in technical analysis calculation."""
    pass


class SafetyCheckError(TradingError):
    """Safety check failed."""
    pass


class RiskLimitExceededError(SafetyCheckError):
    """Risk limit exceeded."""
    pass


class CooldownActiveError(SafetyCheckError):
    """Trade blocked due to cooldown period."""
    pass
