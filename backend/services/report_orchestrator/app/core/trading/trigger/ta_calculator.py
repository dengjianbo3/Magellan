"""
Technical Analysis Calculator - 多周期技术分析计算器

计算 RSI, MACD, 成交量等技术指标，支持 15m/1h/4h 多周期。
Uses shared indicators module to eliminate code duplication.
"""

import asyncio
import aiohttp
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Import centralized config and constants
try:
    from ..trading_config import get_infra_config
    from ..constants import RSI, MACD, TIMEFRAMES
    from ..indicators import (
        calculate_rsi,
        calculate_ema,
        calculate_macd,
        detect_macd_crossover,
        detect_volume_spike,
        determine_trend,
        get_closes_from_candles
    )
    USE_SHARED_INDICATORS = True
except ImportError:
    get_infra_config = None
    RSI = None
    MACD = None
    TIMEFRAMES = None
    USE_SHARED_INDICATORS = False

logger = logging.getLogger(__name__)


@dataclass
class TAData:
    """技术分析数据"""
    # 15 分钟周期
    rsi_15m: float = 50.0
    macd_15m: float = 0.0
    macd_signal_15m: float = 0.0
    macd_crossover: bool = False
    volume_15m: float = 0.0
    volume_avg_15m: float = 0.0
    volume_spike: bool = False
    trend_15m: str = "neutral"  # bullish / bearish / neutral
    
    # 1 小时周期
    rsi_1h: float = 50.0
    ema_20_1h: float = 0.0
    ema_50_1h: float = 0.0
    trend_1h: str = "neutral"
    
    # 4 小时周期
    trend_4h: str = "neutral"
    support_4h: float = 0.0
    resistance_4h: float = 0.0
    
    # 价格数据
    current_price: float = 0.0
    price_change_15m: float = 0.0
    price_change_1h: float = 0.0
    price_change_4h: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "rsi_15m": self.rsi_15m,
            "macd_crossover": self.macd_crossover,
            "volume_spike": self.volume_spike,
            "trend_15m": self.trend_15m,
            "trend_1h": self.trend_1h,
            "trend_4h": self.trend_4h,
            "current_price": self.current_price,
            "price_change_15m": self.price_change_15m,
            "price_change_1h": self.price_change_1h
        }


class TACalculator:
    """
    技术分析计算器

    使用 OKX 公开 API 获取 K 线数据并计算指标。
    """

    def __init__(self, symbol: str = "BTC-USDT-SWAP"):
        self.symbol = symbol
        # Use centralized config for OKX base URL
        self.base_url = get_infra_config().okx_base_url if get_infra_config else "https://www.okx.com"
        self._last_data: Optional[TAData] = None

    async def _fetch_all_candles(self, session) -> Dict[str, Any]:
        """并行获取所有周期的K线数据"""
        tasks = [
            self._fetch_candles(session, "15m", 50),
            self._fetch_candles(session, "1H", 50),
            self._fetch_candles(session, "4H", 20),
            self._fetch_ticker(session)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            "candles_15m": results[0] if not isinstance(results[0], Exception) else [],
            "candles_1h": results[1] if not isinstance(results[1], Exception) else [],
            "candles_4h": results[2] if not isinstance(results[2], Exception) else [],
            "ticker": results[3] if not isinstance(results[3], Exception) else {},
        }

    def _calculate_15m_indicators(self, data: TAData, candles: List[Dict]) -> None:
        """计算15分钟周期指标"""
        if not candles:
            return
        data.rsi_15m = self._calculate_rsi(candles)
        macd, signal = self._calculate_macd(candles)
        data.macd_15m = macd
        data.macd_signal_15m = signal
        data.macd_crossover = self._detect_macd_crossover(candles)
        data.volume_spike = self._detect_volume_spike(candles)
        data.trend_15m = self._determine_trend(candles)
        data.price_change_15m = self._calculate_price_change(candles, 1)

    def _calculate_1h_indicators(self, data: TAData, candles: List[Dict]) -> None:
        """计算1小时周期指标"""
        if not candles:
            return
        data.rsi_1h = self._calculate_rsi(candles)
        data.ema_20_1h = self._calculate_ema(candles, 20)
        data.ema_50_1h = self._calculate_ema(candles, 50)
        data.trend_1h = self._determine_trend(candles)
        data.price_change_1h = self._calculate_price_change(candles, 1)

    def _calculate_4h_indicators(self, data: TAData, candles: List[Dict]) -> None:
        """计算4小时周期指标"""
        if not candles:
            return
        data.trend_4h = self._determine_trend(candles)
        data.support_4h, data.resistance_4h = self._find_support_resistance(candles)
        data.price_change_4h = self._calculate_price_change(candles, 1)

    async def calculate(self, timeframes: List[str] = None) -> TAData:
        """
        计算多周期技术指标

        Args:
            timeframes: 要计算的周期列表，如 ["15m", "1h", "4h"]
        """
        if timeframes is None:
            timeframes = ["15m", "1H", "4H"]

        data = TAData()

        try:
            async with aiohttp.ClientSession() as session:
                market_data = await self._fetch_all_candles(session)

                self._calculate_15m_indicators(data, market_data["candles_15m"])
                self._calculate_1h_indicators(data, market_data["candles_1h"])
                self._calculate_4h_indicators(data, market_data["candles_4h"])

                if market_data["ticker"]:
                    data.current_price = float(market_data["ticker"].get("last", 0))

                self._last_data = data
                logger.info(f"[TA] RSI(15m)={data.rsi_15m:.1f}, MACD_cross={data.macd_crossover}, Vol_spike={data.volume_spike}")

        except Exception as e:
            logger.error(f"[TA] Error calculating indicators: {e}")
            if self._last_data:
                return self._last_data

        return data
    
    async def _fetch_candles(self, session: aiohttp.ClientSession, bar: str, limit: int) -> List[Dict]:
        """获取 K 线数据"""
        url = f"{self.base_url}/api/v5/market/candles"
        params = {
            "instId": self.symbol,
            "bar": bar,
            "limit": str(limit)
        }
        
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("code") == "0":
                        # OKX 返回格式: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
                        return [
                            {
                                "ts": int(c[0]),
                                "open": float(c[1]),
                                "high": float(c[2]),
                                "low": float(c[3]),
                                "close": float(c[4]),
                                "volume": float(c[5])
                            }
                            for c in result.get("data", [])
                        ]
        except Exception as e:
            logger.error(f"Error fetching {bar} candles: {e}")
        
        return []
    
    async def _fetch_ticker(self, session: aiohttp.ClientSession) -> Dict:
        """获取当前行情"""
        url = f"{self.base_url}/api/v5/market/ticker"
        params = {"instId": self.symbol}
        
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("code") == "0" and result.get("data"):
                        return result["data"][0]
        except Exception as e:
            logger.error(f"Error fetching ticker: {e}")
        
        return {}
    
    def _calculate_rsi(self, candles: List[Dict], period: int = None) -> float:
        """计算 RSI - 使用共享模块"""
        if period is None:
            period = RSI.PERIOD if RSI else 14

        if USE_SHARED_INDICATORS:
            closes = get_closes_from_candles(candles, reverse=True)
            return calculate_rsi(closes, period)

        # Fallback to local implementation
        if len(candles) < period + 1:
            return float(RSI.NEUTRAL if RSI else 50)

        closes = [c["close"] for c in candles]
        closes.reverse()

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
            return 50.0

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return round(rsi, 2)

    def _calculate_macd(self, candles: List[Dict]) -> Tuple[float, float]:
        """计算 MACD - 使用共享模块"""
        slow_period = MACD.SLOW_PERIOD if MACD else 26
        fast_period = MACD.FAST_PERIOD if MACD else 12

        if len(candles) < slow_period:
            return 0.0, 0.0

        if USE_SHARED_INDICATORS:
            closes = get_closes_from_candles(candles, reverse=True)
            macd, signal, _ = calculate_macd(closes, fast_period, slow_period)
            return macd, signal

        # Fallback to local implementation
        closes = [c["close"] for c in candles]
        closes.reverse()

        ema_fast = self._ema(closes, fast_period)
        ema_slow = self._ema(closes, slow_period)

        macd = ema_fast - ema_slow
        signal = self._ema([macd], MACD.SIGNAL_PERIOD if MACD else 9) if macd else 0

        return round(macd, 2), round(signal, 2)

    def _calculate_ema(self, candles: List[Dict], period: int) -> float:
        """计算 EMA - 使用共享模块"""
        if USE_SHARED_INDICATORS:
            closes = get_closes_from_candles(candles, reverse=True)
            return calculate_ema(closes, period)

        # Fallback to local implementation
        closes = [c["close"] for c in candles]
        closes.reverse()
        return self._ema(closes, period)
    
    def _ema(self, values: List[float], period: int) -> float:
        """EMA 计算"""
        if len(values) < period:
            return values[-1] if values else 0.0
        
        multiplier = 2 / (period + 1)
        ema = sum(values[:period]) / period
        
        for i in range(period, len(values)):
            ema = (values[i] - ema) * multiplier + ema
        
        return ema
    
    def _detect_macd_crossover(self, candles: List[Dict]) -> bool:
        """检测 MACD 金叉/死叉 - 使用共享模块"""
        slow_period = MACD.SLOW_PERIOD if MACD else 26

        if len(candles) < slow_period + 4:
            return False

        if USE_SHARED_INDICATORS:
            closes = get_closes_from_candles(candles, reverse=True)
            return detect_macd_crossover(closes)

        # Fallback to local implementation
        fast_period = MACD.FAST_PERIOD if MACD else 12
        closes = [c["close"] for c in candles]
        closes.reverse()

        current_ema_fast = self._ema(closes, fast_period)
        current_ema_slow = self._ema(closes, slow_period)
        current_macd = current_ema_fast - current_ema_slow

        prev_ema_fast = self._ema(closes[:-1], fast_period)
        prev_ema_slow = self._ema(closes[:-1], slow_period)
        prev_macd = prev_ema_fast - prev_ema_slow

        return (current_macd > 0 and prev_macd <= 0) or (current_macd < 0 and prev_macd >= 0)

    def _detect_volume_spike(self, candles: List[Dict], threshold: float = 2.0) -> bool:
        """检测成交量异常 - 使用共享模块"""
        if len(candles) < 20:
            return False

        if USE_SHARED_INDICATORS:
            volumes = [c["volume"] for c in candles]
            return detect_volume_spike(volumes, threshold, lookback=20)

        # Fallback to local implementation
        volumes = [c["volume"] for c in candles]
        current_vol = volumes[0]
        avg_vol = sum(volumes[1:20]) / 19

        return current_vol > avg_vol * threshold

    def _determine_trend(self, candles: List[Dict]) -> str:
        """判断趋势 - 使用共享模块"""
        if len(candles) < 10:
            return "neutral"

        if USE_SHARED_INDICATORS:
            closes = [c["close"] for c in candles[:10]]
            return determine_trend(closes, lookback=10, threshold_percent=1.0)

        # Fallback to local implementation
        closes = [c["close"] for c in candles[:10]]

        if closes[0] > closes[-1] * 1.01:
            return "bullish"
        elif closes[0] < closes[-1] * 0.99:
            return "bearish"
        return "neutral"
    
    def _calculate_price_change(self, candles: List[Dict], periods: int) -> float:
        """计算价格变化百分比"""
        if len(candles) < periods + 1:
            return 0.0
        
        current = candles[0]["close"]
        prev = candles[periods]["close"]
        
        if prev == 0:
            return 0.0
        
        return round((current - prev) / prev * 100, 2)
    
    def _find_support_resistance(self, candles: List[Dict]) -> Tuple[float, float]:
        """找出支撑和阻力位"""
        if len(candles) < 5:
            return 0.0, 0.0
        
        lows = [c["low"] for c in candles]
        highs = [c["high"] for c in candles]
        
        support = min(lows)
        resistance = max(highs)
        
        return support, resistance


# 测试入口
if __name__ == "__main__":
    async def test():
        calc = TACalculator()
        data = await calc.calculate()
        
        print("\n=== Technical Analysis ===\n")
        print(f"Current Price: ${data.current_price:,.2f}")
        print(f"\n15m Timeframe:")
        print(f"  RSI: {data.rsi_15m}")
        print(f"  MACD Crossover: {data.macd_crossover}")
        print(f"  Volume Spike: {data.volume_spike}")
        print(f"  Trend: {data.trend_15m}")
        print(f"  Price Change: {data.price_change_15m}%")
        print(f"\n1h Timeframe:")
        print(f"  RSI: {data.rsi_1h}")
        print(f"  Trend: {data.trend_1h}")
        print(f"  Price Change: {data.price_change_1h}%")
        print(f"\n4h Timeframe:")
        print(f"  Trend: {data.trend_4h}")
        print(f"  Support: ${data.support_4h:,.2f}")
        print(f"  Resistance: ${data.resistance_4h:,.2f}")
    
    asyncio.run(test())
