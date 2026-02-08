"""
Technical Indicators Module

Centralized technical indicator calculations to eliminate code duplication.
Provides RSI, EMA, MACD, and other common indicators.

Usage:
    from app.core.trading.indicators import calculate_rsi, calculate_ema, calculate_macd

    rsi = calculate_rsi(closes, period=14)
    ema = calculate_ema(closes, period=20)
    macd, signal, histogram = calculate_macd(closes)
"""

from typing import List, Tuple, Optional, Union
from dataclasses import dataclass

# Import constants
try:
    from .constants import RSI, MACD, EMA, BOLLINGER_BANDS
except ImportError:
    RSI = None
    MACD = None
    EMA = None
    BOLLINGER_BANDS = None


# =============================================================================
# Data Classes for Results
# =============================================================================

@dataclass
class RSIResult:
    """RSI calculation result."""
    value: float
    period: int
    is_overbought: bool
    is_oversold: bool
    signal: str  # "overbought", "oversold", "neutral"

    @property
    def is_extreme(self) -> bool:
        return self.is_overbought or self.is_oversold


@dataclass
class MACDResult:
    """MACD calculation result."""
    macd: float
    signal: float
    histogram: float
    is_bullish_crossover: bool
    is_bearish_crossover: bool
    trend: str  # "bullish", "bearish", "neutral"


@dataclass
class BollingerResult:
    """Bollinger Bands calculation result."""
    upper: float
    middle: float
    lower: float
    bandwidth: float
    percent_b: float  # Position within bands (0-1)


# =============================================================================
# Core Calculation Functions
# =============================================================================

def calculate_ema(values: List[float], period: int = None) -> float:
    """
    Calculate Exponential Moving Average.

    Args:
        values: List of price values (oldest to newest)
        period: EMA period (default from constants or 20)

    Returns:
        EMA value
    """
    if period is None:
        period = EMA.PERIOD_20 if EMA else 20

    if not values or len(values) < period:
        return values[-1] if values else 0.0

    multiplier = 2 / (period + 1)
    ema = sum(values[:period]) / period

    for i in range(period, len(values)):
        ema = (values[i] - ema) * multiplier + ema

    return ema


def calculate_sma(values: List[float], period: int = 20) -> float:
    """
    Calculate Simple Moving Average.

    Args:
        values: List of price values
        period: SMA period

    Returns:
        SMA value
    """
    if not values or len(values) < period:
        return values[-1] if values else 0.0

    return sum(values[-period:]) / period


def calculate_rsi(
    closes: List[float],
    period: int = None,
    return_detailed: bool = False
) -> Union[float, RSIResult]:
    """
    Calculate Relative Strength Index.

    Args:
        closes: List of closing prices (oldest to newest)
        period: RSI period (default from constants or 14)
        return_detailed: If True, return RSIResult with additional info

    Returns:
        RSI value (0-100) or RSIResult if return_detailed=True
    """
    if period is None:
        period = RSI.PERIOD if RSI else 14

    neutral = RSI.NEUTRAL if RSI else 50
    overbought = RSI.OVERBOUGHT if RSI else 70
    oversold = RSI.OVERSOLD if RSI else 30

    if not closes or len(closes) < period + 1:
        if return_detailed:
            return RSIResult(
                value=neutral,
                period=period,
                is_overbought=False,
                is_oversold=False,
                signal="neutral"
            )
        return float(neutral)

    # Calculate gains and losses
    gains = []
    losses = []

    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))

    if len(gains) < period:
        if return_detailed:
            return RSIResult(
                value=neutral,
                period=period,
                is_overbought=False,
                is_oversold=False,
                signal="neutral"
            )
        return float(neutral)

    # Calculate average gain/loss
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Apply smoothing for remaining periods
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    rsi = round(rsi, 2)

    if return_detailed:
        is_overbought = rsi >= overbought
        is_oversold = rsi <= oversold

        if is_overbought:
            signal = "overbought"
        elif is_oversold:
            signal = "oversold"
        else:
            signal = "neutral"

        return RSIResult(
            value=rsi,
            period=period,
            is_overbought=is_overbought,
            is_oversold=is_oversold,
            signal=signal
        )

    return rsi


def calculate_macd(
    closes: List[float],
    fast_period: int = None,
    slow_period: int = None,
    signal_period: int = None,
    return_detailed: bool = False
) -> Union[Tuple[float, float, float], MACDResult]:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    Args:
        closes: List of closing prices (oldest to newest)
        fast_period: Fast EMA period (default from constants or 12)
        slow_period: Slow EMA period (default from constants or 26)
        signal_period: Signal line period (default from constants or 9)
        return_detailed: If True, return MACDResult with additional info

    Returns:
        (macd, signal, histogram) tuple or MACDResult if return_detailed=True
    """
    if fast_period is None:
        fast_period = MACD.FAST_PERIOD if MACD else 12
    if slow_period is None:
        slow_period = MACD.SLOW_PERIOD if MACD else 26
    if signal_period is None:
        signal_period = MACD.SIGNAL_PERIOD if MACD else 9

    if not closes or len(closes) < slow_period:
        if return_detailed:
            return MACDResult(
                macd=0.0,
                signal=0.0,
                histogram=0.0,
                is_bullish_crossover=False,
                is_bearish_crossover=False,
                trend="neutral"
            )
        return 0.0, 0.0, 0.0

    # Calculate EMAs
    ema_fast = calculate_ema(closes, fast_period)
    ema_slow = calculate_ema(closes, slow_period)

    # MACD line
    macd = ema_fast - ema_slow

    # Signal line (EMA of MACD)
    # For proper signal calculation, we need MACD history
    # Simplified: use current MACD as approximation
    macd_history = []
    for i in range(slow_period, len(closes) + 1):
        subset = closes[:i]
        fast = calculate_ema(subset, fast_period)
        slow = calculate_ema(subset, slow_period)
        macd_history.append(fast - slow)

    if len(macd_history) >= signal_period:
        signal_line = calculate_ema(macd_history, signal_period)
    else:
        signal_line = macd

    histogram = macd - signal_line

    macd = round(macd, 4)
    signal_line = round(signal_line, 4)
    histogram = round(histogram, 4)

    if return_detailed:
        # Detect crossovers (need previous values)
        is_bullish = macd > signal_line and histogram > 0
        is_bearish = macd < signal_line and histogram < 0

        if is_bullish:
            trend = "bullish"
        elif is_bearish:
            trend = "bearish"
        else:
            trend = "neutral"

        return MACDResult(
            macd=macd,
            signal=signal_line,
            histogram=histogram,
            is_bullish_crossover=is_bullish and len(macd_history) > 1 and macd_history[-2] <= signal_line,
            is_bearish_crossover=is_bearish and len(macd_history) > 1 and macd_history[-2] >= signal_line,
            trend=trend
        )

    return macd, signal_line, histogram


def detect_macd_crossover(closes: List[float]) -> bool:
    """
    Detect MACD crossover (golden cross or death cross).

    Args:
        closes: List of closing prices (oldest to newest)

    Returns:
        True if crossover detected in recent period
    """
    fast_period = MACD.FAST_PERIOD if MACD else 12
    slow_period = MACD.SLOW_PERIOD if MACD else 26

    if len(closes) < slow_period + 4:
        return False

    # Calculate current MACD
    current_ema_fast = calculate_ema(closes, fast_period)
    current_ema_slow = calculate_ema(closes, slow_period)
    current_macd = current_ema_fast - current_ema_slow

    # Calculate previous MACD
    prev_ema_fast = calculate_ema(closes[:-1], fast_period)
    prev_ema_slow = calculate_ema(closes[:-1], slow_period)
    prev_macd = prev_ema_fast - prev_ema_slow

    # Check for sign change (crossover)
    return (current_macd > 0 and prev_macd <= 0) or (current_macd < 0 and prev_macd >= 0)


def calculate_bollinger_bands(
    closes: List[float],
    period: int = None,
    std_dev: float = None,
    return_detailed: bool = False
) -> Union[Tuple[float, float, float], BollingerResult]:
    """
    Calculate Bollinger Bands.

    Args:
        closes: List of closing prices (oldest to newest)
        period: Moving average period (default from constants or 20)
        std_dev: Standard deviation multiplier (default from constants or 2.0)
        return_detailed: If True, return BollingerResult with additional info

    Returns:
        (upper, middle, lower) tuple or BollingerResult if return_detailed=True
    """
    if period is None:
        period = BOLLINGER_BANDS.PERIOD if BOLLINGER_BANDS else 20
    if std_dev is None:
        std_dev = BOLLINGER_BANDS.STD_DEV if BOLLINGER_BANDS else 2.0

    if not closes or len(closes) < period:
        current = closes[-1] if closes else 0.0
        if return_detailed:
            return BollingerResult(
                upper=current,
                middle=current,
                lower=current,
                bandwidth=0.0,
                percent_b=0.5
            )
        return current, current, current

    # Calculate middle band (SMA)
    middle = calculate_sma(closes, period)

    # Calculate standard deviation
    recent = closes[-period:]
    variance = sum((x - middle) ** 2 for x in recent) / period
    std = variance ** 0.5

    # Calculate bands
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)

    upper = round(upper, 2)
    middle = round(middle, 2)
    lower = round(lower, 2)

    if return_detailed:
        bandwidth = (upper - lower) / middle if middle > 0 else 0
        current_price = closes[-1]
        percent_b = (current_price - lower) / (upper - lower) if upper != lower else 0.5

        return BollingerResult(
            upper=upper,
            middle=middle,
            lower=lower,
            bandwidth=round(bandwidth, 4),
            percent_b=round(percent_b, 4)
        )

    return upper, middle, lower


def calculate_atr(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14
) -> float:
    """
    Calculate Average True Range.

    Args:
        highs: List of high prices
        lows: List of low prices
        closes: List of closing prices
        period: ATR period

    Returns:
        ATR value
    """
    if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
        return 0.0

    true_ranges = []

    for i in range(1, len(closes)):
        high = highs[i]
        low = lows[i]
        prev_close = closes[i-1]

        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0

    # Calculate ATR using EMA
    atr = sum(true_ranges[:period]) / period

    for i in range(period, len(true_ranges)):
        atr = (atr * (period - 1) + true_ranges[i]) / period

    return round(atr, 2)


def detect_volume_spike(
    volumes: List[float],
    threshold: float = 2.0,
    lookback: int = 20
) -> bool:
    """
    Detect volume spike compared to recent average.

    Args:
        volumes: List of volume values (newest first)
        threshold: Multiplier for spike detection
        lookback: Number of periods for average calculation

    Returns:
        True if current volume exceeds threshold * average
    """
    if len(volumes) < lookback:
        return False

    current_vol = volumes[0]
    avg_vol = sum(volumes[1:lookback]) / (lookback - 1)

    return current_vol > avg_vol * threshold


def determine_trend(
    closes: List[float],
    lookback: int = 10,
    threshold_percent: float = 1.0
) -> str:
    """
    Determine price trend based on recent price action.

    Args:
        closes: List of closing prices (newest first for candle data)
        lookback: Number of periods to analyze
        threshold_percent: Minimum change % to determine trend

    Returns:
        "bullish", "bearish", or "neutral"
    """
    if len(closes) < lookback:
        return "neutral"

    # Compare current vs lookback periods ago
    current = closes[0]
    past = closes[lookback - 1] if len(closes) >= lookback else closes[-1]

    if past == 0:
        return "neutral"

    change_percent = ((current - past) / past) * 100

    if change_percent >= threshold_percent:
        return "bullish"
    elif change_percent <= -threshold_percent:
        return "bearish"

    return "neutral"


# =============================================================================
# Utility Functions
# =============================================================================

def normalize_candle_data(candles: List[dict], reverse: bool = True) -> Tuple[List[float], List[float], List[float], List[float]]:
    """
    Extract and normalize candle data for indicator calculations.

    Args:
        candles: List of candle dicts with 'open', 'high', 'low', 'close', 'volume'
        reverse: If True, reverse order (OKX returns newest first)

    Returns:
        (opens, highs, lows, closes) lists in chronological order
    """
    if reverse:
        candles = list(reversed(candles))

    opens = [c.get('open', 0) for c in candles]
    highs = [c.get('high', 0) for c in candles]
    lows = [c.get('low', 0) for c in candles]
    closes = [c.get('close', 0) for c in candles]

    return opens, highs, lows, closes


def get_closes_from_candles(candles: List[dict], reverse: bool = True) -> List[float]:
    """
    Extract closing prices from candle data.

    Args:
        candles: List of candle dicts
        reverse: If True, reverse order (OKX returns newest first)

    Returns:
        List of closing prices in chronological order
    """
    closes = [c.get('close', 0) for c in candles]
    if reverse:
        closes.reverse()
    return closes
