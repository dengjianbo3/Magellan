"""
Technical Analysis Calculator - 多周期技术分析计算器

计算 RSI, MACD, 成交量等技术指标，支持 15m/1h/4h 多周期。
"""

import asyncio
import aiohttp
import logging
import os
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

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
        self.base_url = "https://www.okx.com"
        self._last_data: Optional[TAData] = None
    
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
                # 并行获取各周期 K 线
                tasks = [
                    self._fetch_candles(session, "15m", 50),
                    self._fetch_candles(session, "1H", 50),
                    self._fetch_candles(session, "4H", 20),
                    self._fetch_ticker(session)
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                candles_15m = results[0] if not isinstance(results[0], Exception) else []
                candles_1h = results[1] if not isinstance(results[1], Exception) else []
                candles_4h = results[2] if not isinstance(results[2], Exception) else []
                ticker = results[3] if not isinstance(results[3], Exception) else {}
                
                # 计算 15m 指标
                if candles_15m:
                    data.rsi_15m = self._calculate_rsi(candles_15m)
                    macd, signal = self._calculate_macd(candles_15m)
                    data.macd_15m = macd
                    data.macd_signal_15m = signal
                    data.macd_crossover = self._detect_macd_crossover(candles_15m)
                    data.volume_spike = self._detect_volume_spike(candles_15m)
                    data.trend_15m = self._determine_trend(candles_15m)
                    data.price_change_15m = self._calculate_price_change(candles_15m, 1)
                
                # 计算 1h 指标
                if candles_1h:
                    data.rsi_1h = self._calculate_rsi(candles_1h)
                    data.ema_20_1h = self._calculate_ema(candles_1h, 20)
                    data.ema_50_1h = self._calculate_ema(candles_1h, 50)
                    data.trend_1h = self._determine_trend(candles_1h)
                    data.price_change_1h = self._calculate_price_change(candles_1h, 1)
                
                # 计算 4h 指标
                if candles_4h:
                    data.trend_4h = self._determine_trend(candles_4h)
                    data.support_4h, data.resistance_4h = self._find_support_resistance(candles_4h)
                    data.price_change_4h = self._calculate_price_change(candles_4h, 1)
                
                # 当前价格
                if ticker:
                    data.current_price = float(ticker.get("last", 0))
                
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
    
    def _calculate_rsi(self, candles: List[Dict], period: int = 14) -> float:
        """计算 RSI"""
        if len(candles) < period + 1:
            return 50.0
        
        closes = [c["close"] for c in candles]
        closes.reverse()  # OKX 返回的是新到旧，需要反转
        
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
        """计算 MACD"""
        if len(candles) < 26:
            return 0.0, 0.0
        
        closes = [c["close"] for c in candles]
        closes.reverse()
        
        ema_12 = self._ema(closes, 12)
        ema_26 = self._ema(closes, 26)
        
        macd = ema_12 - ema_26
        signal = self._ema([macd], 9) if macd else 0  # 简化
        
        return round(macd, 2), round(signal, 2)
    
    def _calculate_ema(self, candles: List[Dict], period: int) -> float:
        """计算 EMA"""
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
        """检测 MACD 金叉/死叉"""
        if len(candles) < 30:
            return False
        
        closes = [c["close"] for c in candles]
        closes.reverse()
        
        # 计算当前和前一根的 MACD
        current_ema12 = self._ema(closes, 12)
        current_ema26 = self._ema(closes, 26)
        current_macd = current_ema12 - current_ema26
        
        prev_ema12 = self._ema(closes[:-1], 12)
        prev_ema26 = self._ema(closes[:-1], 26)
        prev_macd = prev_ema12 - prev_ema26
        
        # 简化：只检测是否有符号变化
        return (current_macd > 0 and prev_macd <= 0) or (current_macd < 0 and prev_macd >= 0)
    
    def _detect_volume_spike(self, candles: List[Dict], threshold: float = 2.0) -> bool:
        """检测成交量异常"""
        if len(candles) < 20:
            return False
        
        volumes = [c["volume"] for c in candles]
        current_vol = volumes[0]  # 最新一根
        avg_vol = sum(volumes[1:20]) / 19
        
        return current_vol > avg_vol * threshold
    
    def _determine_trend(self, candles: List[Dict]) -> str:
        """判断趋势"""
        if len(candles) < 10:
            return "neutral"
        
        closes = [c["close"] for c in candles[:10]]
        
        # 简单判断：当前价格 vs 10 根 K 线前
        if closes[0] > closes[-1] * 1.01:  # 上涨 1%+
            return "bullish"
        elif closes[0] < closes[-1] * 0.99:  # 下跌 1%+
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
