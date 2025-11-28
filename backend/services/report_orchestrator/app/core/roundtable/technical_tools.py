"""
Technical Analysis Tools
技术分析工具集

提供K线数据获取和技术指标计算功能
支持加密货币(Binance)和股票(Yahoo Finance)市场
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import httpx
import asyncio

from ...models.technical_models import (
    SignalStrength, TrendDirection, TrendStrength, EMAAlignment,
    IndicatorSignal, TrendAnalysis, SupportResistance,
    CandlestickPattern, PatternRecognition, TechnicalIndicators,
    RSIIndicator, MACDIndicator, BollingerBandsIndicator,
    EMAIndicator, KDJIndicator, ADXIndicator,
    TradingSuggestion, TechnicalAnalysisOutput,
    signal_to_score, score_to_signal
)


class TechnicalAnalysisTools:
    """
    技术分析工具集

    功能:
    - 获取K线数据 (加密货币/股票)
    - 计算技术指标 (RSI, MACD, BB, EMA, KDJ, ADX等)
    - 识别支撑阻力位
    - K线形态识别
    - 生成交易信号
    """

    def __init__(self):
        # API端点
        self.binance_api = "https://api.binance.com/api/v3"
        self.coingecko_api = "https://api.coingecko.com/api/v3"

        # 超时配置
        self.timeout = 30.0

    # ==================== 数据获取 ====================

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 100,
        market_type: str = "crypto"
    ) -> pd.DataFrame:
        """
        获取K线数据 (OHLCV)

        Args:
            symbol: 交易对 (如: BTC/USDT, BTC, AAPL)
            timeframe: 时间周期 (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)
            limit: 获取数量
            market_type: 市场类型 (crypto, stock)

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        if market_type == "crypto":
            return await self._get_crypto_ohlcv(symbol, timeframe, limit)
        else:
            return await self._get_stock_ohlcv(symbol, timeframe, limit)

    async def _get_crypto_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int
    ) -> pd.DataFrame:
        """从Binance、CoinGecko或Yahoo Finance获取加密货币K线数据"""

        # 首先尝试Binance API
        try:
            return await self._get_crypto_ohlcv_binance(symbol, timeframe, limit)
        except Exception as e:
            print(f"Binance API failed: {e}, trying CoinGecko...")

        # 尝试CoinGecko
        try:
            return await self._get_crypto_ohlcv_coingecko(symbol, timeframe, limit)
        except Exception as e:
            print(f"CoinGecko API failed: {e}, trying Yahoo Finance...")

        # 最后尝试Yahoo Finance (BTC-USD, ETH-USD等)
        return await self._get_crypto_ohlcv_yfinance(symbol, timeframe, limit)

    async def _get_crypto_ohlcv_yfinance(
        self,
        symbol: str,
        timeframe: str,
        limit: int
    ) -> pd.DataFrame:
        """从Yahoo Finance获取加密货币K线数据"""
        import yfinance as yf

        # 映射symbol到Yahoo Finance格式
        symbol_map = {
            "BTC": "BTC-USD", "BTCUSDT": "BTC-USD",
            "ETH": "ETH-USD", "ETHUSDT": "ETH-USD",
            "BNB": "BNB-USD", "BNBUSDT": "BNB-USD",
            "SOL": "SOL-USD", "SOLUSDT": "SOL-USD",
            "XRP": "XRP-USD", "XRPUSDT": "XRP-USD",
            "ADA": "ADA-USD", "ADAUSDT": "ADA-USD",
            "DOGE": "DOGE-USD", "DOGEUSDT": "DOGE-USD",
            "AVAX": "AVAX-USD", "AVAXUSDT": "AVAX-USD",
            "DOT": "DOT-USD", "DOTUSDT": "DOT-USD",
            "LINK": "LINK-USD", "LINKUSDT": "LINK-USD",
        }

        clean_symbol = symbol.replace("/", "").upper()
        yf_symbol = symbol_map.get(clean_symbol, f"{clean_symbol.replace('USDT', '')}-USD")

        # 转换timeframe到yfinance格式
        tf_map = {
            "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1h", "4h": "1h", "1d": "1d", "1w": "1wk", "1M": "1mo"
        }
        interval = tf_map.get(timeframe, "1d")

        # 计算获取的时间范围
        period_map = {
            "1m": "1d", "5m": "5d", "15m": "5d", "30m": "5d",
            "1h": "60d", "4h": "60d", "1d": "1y", "1w": "2y", "1M": "5y"
        }
        period = period_map.get(timeframe, "1y")

        # 在异步环境中运行同步yfinance代码
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None,
            lambda: yf.download(yf_symbol, period=period, interval=interval, progress=False)
        )

        if df.empty:
            raise Exception(f"No data returned from Yahoo Finance for {yf_symbol}")

        # 重置索引并重命名列
        df = df.reset_index()

        # 处理列名 - yfinance返回的列名可能是元组或字符串
        if isinstance(df.columns[0], tuple):
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

        df = df.rename(columns={
            'Date': 'timestamp',
            'Datetime': 'timestamp',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })

        # 确保列名小写
        df.columns = df.columns.str.lower()

        # 限制返回数量
        if len(df) > limit:
            df = df.tail(limit)

        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

    async def _get_crypto_ohlcv_binance(
        self,
        symbol: str,
        timeframe: str,
        limit: int
    ) -> pd.DataFrame:
        """从Binance获取加密货币K线数据"""

        # 标准化symbol
        if "/" in symbol:
            symbol = symbol.replace("/", "")
        elif not symbol.upper().endswith("USDT"):
            symbol = f"{symbol}USDT"
        symbol = symbol.upper()

        # 转换timeframe
        tf_map = {
            "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1h", "4h": "4h", "1d": "1d", "1w": "1w", "1M": "1M"
        }
        interval = tf_map.get(timeframe, "1d")

        url = f"{self.binance_api}/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)

            if response.status_code != 200:
                raise Exception(f"Binance API error: {response.status_code} - {response.text}")

            data = response.json()

        # 转换为DataFrame
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])

        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

    async def _get_crypto_ohlcv_coingecko(
        self,
        symbol: str,
        timeframe: str,
        limit: int
    ) -> pd.DataFrame:
        """从CoinGecko获取加密货币K线数据（备用）"""

        # 映射常见symbol到CoinGecko ID
        symbol_map = {
            "BTC": "bitcoin", "BTCUSDT": "bitcoin",
            "ETH": "ethereum", "ETHUSDT": "ethereum",
            "BNB": "binancecoin", "BNBUSDT": "binancecoin",
            "SOL": "solana", "SOLUSDT": "solana",
            "XRP": "ripple", "XRPUSDT": "ripple",
            "ADA": "cardano", "ADAUSDT": "cardano",
            "DOGE": "dogecoin", "DOGEUSDT": "dogecoin",
            "AVAX": "avalanche-2", "AVAXUSDT": "avalanche-2",
            "DOT": "polkadot", "DOTUSDT": "polkadot",
            "LINK": "chainlink", "LINKUSDT": "chainlink",
        }

        # 标准化symbol
        clean_symbol = symbol.replace("/", "").replace("USDT", "").upper()
        coin_id = symbol_map.get(clean_symbol, symbol_map.get(symbol.upper().replace("/", ""), clean_symbol.lower()))

        # 转换timeframe到days
        tf_days_map = {
            "1m": 1, "5m": 1, "15m": 1, "30m": 1,
            "1h": 7, "4h": 30, "1d": 90, "1w": 365, "1M": 365
        }
        days = tf_days_map.get(timeframe, 90)

        url = f"{self.coingecko_api}/coins/{coin_id}/ohlc"
        params = {
            "vs_currency": "usd",
            "days": days
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)

            if response.status_code != 200:
                raise Exception(f"CoinGecko API error: {response.status_code} - {response.text}")

            data = response.json()

        if not data:
            raise Exception(f"No data returned for {coin_id}")

        # CoinGecko OHLC返回格式: [timestamp, open, high, low, close]
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['volume'] = 0.0  # CoinGecko OHLC不包含volume

        # 限制返回数量
        if len(df) > limit:
            df = df.tail(limit)

        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

    async def _get_stock_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int
    ) -> pd.DataFrame:
        """获取股票K线数据 (使用yfinance库，如果可用)"""
        try:
            import yfinance as yf

            # 转换timeframe为yfinance格式
            tf_map = {
                "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                "1h": "1h", "1d": "1d", "1w": "1wk", "1M": "1mo"
            }
            interval = tf_map.get(timeframe, "1d")

            # 计算日期范围
            period_map = {
                "1m": "7d", "5m": "60d", "15m": "60d", "30m": "60d",
                "1h": "730d", "1d": "max", "1w": "max", "1M": "max"
            }
            period = period_map.get(timeframe, "1y")

            ticker = yf.Ticker(symbol.upper())
            df = ticker.history(period=period, interval=interval)

            if df.empty:
                raise Exception(f"No data found for {symbol}")

            df = df.reset_index()
            df.columns = [c.lower() for c in df.columns]

            if 'date' in df.columns:
                df = df.rename(columns={'date': 'timestamp'})
            elif 'datetime' in df.columns:
                df = df.rename(columns={'datetime': 'timestamp'})

            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail(limit)

        except ImportError:
            raise Exception("yfinance not installed. Run: pip install yfinance")

    async def get_current_price(self, symbol: str, market_type: str = "crypto") -> float:
        """获取当前价格"""
        df = await self.get_ohlcv(symbol, "1h", 1, market_type)
        return df['close'].iloc[-1]

    # ==================== 技术指标计算 ====================

    def calculate_all_indicators(
        self,
        df: pd.DataFrame,
        indicators: List[str] = None
    ) -> Dict[str, Any]:
        """
        计算所有技术指标

        Args:
            df: K线数据DataFrame
            indicators: 需要计算的指标列表，默认全部

        Returns:
            指标计算结果字典
        """
        if indicators is None:
            indicators = ["RSI", "MACD", "BB", "EMA", "KDJ", "ADX"]

        results = {}
        close = df['close']
        high = df['high']
        low = df['low']

        data_len = len(df)

        try:
            if "RSI" in indicators and data_len >= 14:
                results['rsi'] = self._calculate_rsi(close)

            if "MACD" in indicators and data_len >= 26:
                results['macd'] = self._calculate_macd(close)

            if "BB" in indicators and data_len >= 20:
                results['bb'] = self._calculate_bollinger_bands(close)

            if "EMA" in indicators and data_len >= 7:
                results['ema'] = self._calculate_ema(close)

            if "KDJ" in indicators and data_len >= 9:
                results['kdj'] = self._calculate_kdj(high, low, close)

            if "ADX" in indicators and data_len >= 28:  # ADX需要至少14*2个数据点
                results['adx'] = self._calculate_adx(high, low, close)

        except Exception as e:
            print(f"[TechnicalTools] Error calculating indicators: {e}")
            import traceback
            traceback.print_exc()

        # 添加趋势分析
        results['trend'] = self._analyze_trend(df)

        return results

    def _calculate_rsi(self, close: pd.Series, period: int = 14) -> RSIIndicator:
        """计算RSI"""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]

        # 判断信号
        if current_rsi < 30:
            signal = SignalStrength.STRONG_BUY
            desc = f"RSI={current_rsi:.1f}，严重超卖区，可能反弹"
        elif current_rsi < 40:
            signal = SignalStrength.BUY
            desc = f"RSI={current_rsi:.1f}，偏弱，接近超卖"
        elif current_rsi > 70:
            signal = SignalStrength.STRONG_SELL
            desc = f"RSI={current_rsi:.1f}，严重超买区，注意回调风险"
        elif current_rsi > 60:
            signal = SignalStrength.SELL
            desc = f"RSI={current_rsi:.1f}，偏强，接近超买"
        else:
            signal = SignalStrength.NEUTRAL
            desc = f"RSI={current_rsi:.1f}，中性区间"

        return RSIIndicator(
            value=round(current_rsi, 2),
            signal=signal,
            period=period,
            description=desc
        )

    def _calculate_macd(
        self,
        close: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> MACDIndicator:
        """计算MACD"""
        exp1 = close.ewm(span=fast, adjust=False).mean()
        exp2 = close.ewm(span=slow, adjust=False).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_hist = histogram.iloc[-1]
        prev_hist = histogram.iloc[-2] if len(histogram) > 1 else 0

        # 判断信号
        if current_hist > 0:
            if current_hist > prev_hist:
                sig = SignalStrength.BUY
                desc = "MACD柱状图在零轴上方且放大，多头动能增强"
            else:
                sig = SignalStrength.NEUTRAL
                desc = "MACD柱状图在零轴上方但缩小，多头动能减弱"
        else:
            if current_hist < prev_hist:
                sig = SignalStrength.SELL
                desc = "MACD柱状图在零轴下方且放大，空头动能增强"
            else:
                sig = SignalStrength.NEUTRAL
                desc = "MACD柱状图在零轴下方但缩小，空头动能减弱"

        # 金叉死叉检测
        if len(histogram) >= 2:
            if histogram.iloc[-2] < 0 and histogram.iloc[-1] > 0:
                sig = SignalStrength.STRONG_BUY
                desc = "MACD金叉，买入信号"
            elif histogram.iloc[-2] > 0 and histogram.iloc[-1] < 0:
                sig = SignalStrength.STRONG_SELL
                desc = "MACD死叉，卖出信号"

        return MACDIndicator(
            macd=round(current_macd, 6),
            signal_line=round(current_signal, 6),
            histogram=round(current_hist, 6),
            signal=sig,
            description=desc
        )

    def _calculate_bollinger_bands(
        self,
        close: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> BollingerBandsIndicator:
        """计算布林带"""
        middle = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        current_price = close.iloc[-1]
        current_upper = upper.iloc[-1]
        current_middle = middle.iloc[-1]
        current_lower = lower.iloc[-1]

        # 计算带宽
        width = (current_upper - current_lower) / current_middle * 100

        # 判断位置
        if current_price > current_upper:
            position = "above_upper"
            signal = SignalStrength.SELL
            desc = f"价格突破布林上轨({current_upper:.2f})，可能超买或突破走强"
        elif current_price < current_lower:
            position = "below_lower"
            signal = SignalStrength.BUY
            desc = f"价格跌破布林下轨({current_lower:.2f})，可能超卖或破位走弱"
        elif current_price > current_middle:
            position = "upper_half"
            signal = SignalStrength.NEUTRAL
            desc = f"价格在布林带上半区运行，偏强"
        else:
            position = "lower_half"
            signal = SignalStrength.NEUTRAL
            desc = f"价格在布林带下半区运行，偏弱"

        desc += f"，波动率{width:.1f}%"

        return BollingerBandsIndicator(
            upper=round(current_upper, 2),
            middle=round(current_middle, 2),
            lower=round(current_lower, 2),
            width=round(width, 2),
            position=position,
            signal=signal,
            description=desc
        )

    def _calculate_ema(self, close: pd.Series) -> EMAIndicator:
        """计算EMA均线 (7, 25, 99)"""
        ema7 = close.ewm(span=7, adjust=False).mean().iloc[-1]
        ema25 = close.ewm(span=25, adjust=False).mean().iloc[-1]
        ema99 = close.ewm(span=99, adjust=False).mean().iloc[-1]

        # 判断排列
        if ema7 > ema25 > ema99:
            alignment = EMAAlignment.BULLISH_ALIGNMENT
            signal = SignalStrength.BUY
            desc = f"EMA多头排列 (7>{ema7:.2f} > 25>{ema25:.2f} > 99>{ema99:.2f})，趋势向上"
        elif ema7 < ema25 < ema99:
            alignment = EMAAlignment.BEARISH_ALIGNMENT
            signal = SignalStrength.SELL
            desc = f"EMA空头排列 (7<{ema7:.2f} < 25<{ema25:.2f} < 99<{ema99:.2f})，趋势向下"
        else:
            alignment = EMAAlignment.MIXED
            signal = SignalStrength.NEUTRAL
            desc = "EMA均线纠缠，趋势不明"

        return EMAIndicator(
            ema_7=round(ema7, 2),
            ema_25=round(ema25, 2),
            ema_99=round(ema99, 2),
            alignment=alignment,
            signal=signal,
            description=desc
        )

    def _calculate_kdj(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        k_period: int = 9,
        d_period: int = 3
    ) -> KDJIndicator:
        """计算KDJ指标"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        rsv = (close - lowest_low) / (highest_high - lowest_low) * 100

        k = rsv.ewm(com=d_period-1, adjust=False).mean()
        d = k.ewm(com=d_period-1, adjust=False).mean()
        j = 3 * k - 2 * d

        current_k = k.iloc[-1]
        current_d = d.iloc[-1]
        current_j = j.iloc[-1]

        # 判断信号
        if current_j < 20 and current_k < 20:
            signal = SignalStrength.STRONG_BUY
            desc = f"KDJ超卖区 (J={current_j:.1f}, K={current_k:.1f})，可能反弹"
        elif current_j > 80 and current_k > 80:
            signal = SignalStrength.STRONG_SELL
            desc = f"KDJ超买区 (J={current_j:.1f}, K={current_k:.1f})，注意回调"
        elif current_k > current_d:
            signal = SignalStrength.BUY
            desc = f"K线({current_k:.1f})在D线({current_d:.1f})上方，短期多头"
        elif current_k < current_d:
            signal = SignalStrength.SELL
            desc = f"K线({current_k:.1f})在D线({current_d:.1f})下方，短期空头"
        else:
            signal = SignalStrength.NEUTRAL
            desc = "KDJ中性区间"

        return KDJIndicator(
            k=round(current_k, 2),
            d=round(current_d, 2),
            j=round(current_j, 2),
            signal=signal,
            description=desc
        )

    def _calculate_adx(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> ADXIndicator:
        """计算ADX指标"""
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        # Directional Movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low

        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0)

        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        current_adx = adx.iloc[-1]

        # 判断趋势强度
        if current_adx > 50:
            strength = TrendStrength.VERY_STRONG
            desc = f"ADX={current_adx:.1f}，非常强劲的趋势"
        elif current_adx > 25:
            strength = TrendStrength.STRONG
            desc = f"ADX={current_adx:.1f}，明确的趋势市场"
        elif current_adx > 20:
            strength = TrendStrength.MODERATE
            desc = f"ADX={current_adx:.1f}，趋势正在形成"
        else:
            strength = TrendStrength.WEAK
            desc = f"ADX={current_adx:.1f}，弱趋势或震荡市场"

        return ADXIndicator(
            value=round(current_adx, 2),
            trend_strength=strength,
            description=desc
        )

    def _analyze_trend(self, df: pd.DataFrame) -> TrendAnalysis:
        """分析趋势"""
        close = df['close']

        # 计算EMA用于判断均线排列
        ema_alignment = EMAAlignment.MIXED
        if len(close) >= 99:
            ema7 = close.ewm(span=7, adjust=False).mean().iloc[-1]
            ema25 = close.ewm(span=25, adjust=False).mean().iloc[-1]
            ema99 = close.ewm(span=99, adjust=False).mean().iloc[-1]
            if ema7 > ema25 > ema99:
                ema_alignment = EMAAlignment.BULLISH_ALIGNMENT
            elif ema7 < ema25 < ema99:
                ema_alignment = EMAAlignment.BEARISH_ALIGNMENT
        elif len(close) >= 25:
            ema7 = close.ewm(span=7, adjust=False).mean().iloc[-1]
            ema25 = close.ewm(span=25, adjust=False).mean().iloc[-1]
            if ema7 > ema25:
                ema_alignment = EMAAlignment.BULLISH_ALIGNMENT
            elif ema7 < ema25:
                ema_alignment = EMAAlignment.BEARISH_ALIGNMENT

        # 使用简单移动平均判断趋势
        if len(close) >= 20:
            sma_short = close.rolling(window=5).mean().iloc[-1]
            sma_long = close.rolling(window=20).mean().iloc[-1]
            current_price = close.iloc[-1]

            if current_price > sma_short > sma_long:
                direction = TrendDirection.BULLISH
                strength = 0.8  # float 0-1
                desc = "价格在均线上方，均线多头排列，上涨趋势明确"
            elif current_price < sma_short < sma_long:
                direction = TrendDirection.BEARISH
                strength = 0.8
                desc = "价格在均线下方，均线空头排列，下跌趋势明确"
            elif current_price > sma_long:
                direction = TrendDirection.BULLISH
                strength = 0.6
                desc = "价格在长期均线上方，中期看涨"
            elif current_price < sma_long:
                direction = TrendDirection.BEARISH
                strength = 0.6
                desc = "价格在长期均线下方，中期看跌"
            else:
                direction = TrendDirection.SIDEWAYS
                strength = 0.3
                desc = "趋势不明确，横盘整理"
        else:
            # 数据不足时使用简单判断
            if len(close) >= 5:
                change = (close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100
                if change > 5:
                    direction = TrendDirection.BULLISH
                    strength = 0.5
                    desc = f"近期上涨 {change:.1f}%"
                elif change < -5:
                    direction = TrendDirection.BEARISH
                    strength = 0.5
                    desc = f"近期下跌 {abs(change):.1f}%"
                else:
                    direction = TrendDirection.SIDEWAYS
                    strength = 0.3
                    desc = f"近期变化 {change:.1f}%，横盘整理"
            else:
                direction = TrendDirection.SIDEWAYS
                strength = 0.2
                desc = "数据不足，无法判断趋势"

        return TrendAnalysis(
            direction=direction,
            strength=strength,
            ema_alignment=ema_alignment,
            description=desc
        )

    # ==================== 支撑阻力位 ====================

    def calculate_support_resistance(
        self,
        df: pd.DataFrame,
        method: str = "fibonacci"
    ) -> SupportResistance:
        """
        计算支撑阻力位

        Args:
            df: K线数据
            method: 计算方法 (fibonacci, pivot)
        """
        current = df['close'].iloc[-1]
        high = df['high'].max()
        low = df['low'].min()
        diff = high - low

        if method == "fibonacci":
            # 斐波那契回撤位
            resistance = [
                round(low + diff * 0.618, 2),
                round(low + diff * 0.786, 2),
                round(high, 2),
            ]
            support = [
                round(low + diff * 0.382, 2),
                round(low + diff * 0.236, 2),
                round(low, 2),
            ]
        else:  # pivot
            pivot = (df['high'].iloc[-1] + df['low'].iloc[-1] + df['close'].iloc[-1]) / 3
            resistance = [
                round(2 * pivot - df['low'].iloc[-1], 2),
                round(pivot + diff, 2),
                round(pivot + 2 * diff, 2),
            ]
            support = [
                round(2 * pivot - df['high'].iloc[-1], 2),
                round(pivot - diff, 2),
                round(pivot - 2 * diff, 2),
            ]

        # 找最近的支撑阻力
        nearest_res = min([r for r in resistance if r > current], default=resistance[0])
        nearest_sup = max([s for s in support if s < current], default=support[-1])

        return SupportResistance(
            current_price=round(current, 2),
            support_levels=support,
            resistance_levels=resistance,
            nearest_support=nearest_sup,
            nearest_resistance=nearest_res,
            method=method
        )

    # ==================== K线形态识别 ====================

    def detect_candlestick_patterns(self, df: pd.DataFrame) -> PatternRecognition:
        """
        识别K线形态

        Args:
            df: K线数据

        Returns:
            PatternRecognition结果
        """
        patterns = []

        open_ = df['open']
        high = df['high']
        low = df['low']
        close = df['close']

        # 最近3根K线
        if len(df) < 3:
            return PatternRecognition(
                patterns_found=[],
                dominant_pattern=None,
                pattern_signal=SignalStrength.NEUTRAL
            )

        # 十字星 (Doji)
        if self._is_doji(open_.iloc[-1], high.iloc[-1], low.iloc[-1], close.iloc[-1]):
            patterns.append(CandlestickPattern(
                name="十字星",
                english_name="doji",
                type="indecision",
                direction="neutral",
                strength="medium"
            ))

        # 锤子线 (Hammer) - 下影线长，实体短，在下跌趋势末端
        if self._is_hammer(open_, high, low, close):
            patterns.append(CandlestickPattern(
                name="锤子线",
                english_name="hammer",
                type="bullish_reversal",
                direction="bullish",
                strength="medium"
            ))

        # 倒锤子 (Inverted Hammer)
        if self._is_inverted_hammer(open_, high, low, close):
            patterns.append(CandlestickPattern(
                name="倒锤子",
                english_name="inverted_hammer",
                type="bullish_reversal",
                direction="bullish",
                strength="weak"
            ))

        # 吞没形态 (Engulfing)
        engulfing = self._is_engulfing(open_, high, low, close)
        if engulfing == "bullish":
            patterns.append(CandlestickPattern(
                name="看涨吞没",
                english_name="bullish_engulfing",
                type="bullish_reversal",
                direction="bullish",
                strength="strong"
            ))
        elif engulfing == "bearish":
            patterns.append(CandlestickPattern(
                name="看跌吞没",
                english_name="bearish_engulfing",
                type="bearish_reversal",
                direction="bearish",
                strength="strong"
            ))

        # 晨星 (Morning Star)
        if self._is_morning_star(open_, high, low, close):
            patterns.append(CandlestickPattern(
                name="启明星",
                english_name="morning_star",
                type="bullish_reversal",
                direction="bullish",
                strength="strong"
            ))

        # 黄昏星 (Evening Star)
        if self._is_evening_star(open_, high, low, close):
            patterns.append(CandlestickPattern(
                name="黄昏星",
                english_name="evening_star",
                type="bearish_reversal",
                direction="bearish",
                strength="strong"
            ))

        # 确定主导形态和信号
        dominant = None
        signal = SignalStrength.NEUTRAL

        if patterns:
            # 优先选择强信号形态
            strong_patterns = [p for p in patterns if p.strength == "strong"]
            if strong_patterns:
                dominant = strong_patterns[0].name
                if strong_patterns[0].direction == "bullish":
                    signal = SignalStrength.BUY
                elif strong_patterns[0].direction == "bearish":
                    signal = SignalStrength.SELL
            else:
                dominant = patterns[0].name

        return PatternRecognition(
            patterns_found=patterns,
            dominant_pattern=dominant,
            pattern_signal=signal
        )

    def _is_doji(self, open_: float, high: float, low: float, close: float) -> bool:
        """判断是否为十字星"""
        body = abs(close - open_)
        total_range = high - low
        if total_range == 0:
            return False
        return body / total_range < 0.1

    def _is_hammer(self, open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> bool:
        """判断是否为锤子线"""
        body = abs(close.iloc[-1] - open_.iloc[-1])
        lower_shadow = min(open_.iloc[-1], close.iloc[-1]) - low.iloc[-1]
        upper_shadow = high.iloc[-1] - max(open_.iloc[-1], close.iloc[-1])

        if body == 0:
            return False

        return (lower_shadow > 2 * body and
                upper_shadow < body and
                close.iloc[-1] > open_.iloc[-1])

    def _is_inverted_hammer(self, open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> bool:
        """判断是否为倒锤子"""
        body = abs(close.iloc[-1] - open_.iloc[-1])
        lower_shadow = min(open_.iloc[-1], close.iloc[-1]) - low.iloc[-1]
        upper_shadow = high.iloc[-1] - max(open_.iloc[-1], close.iloc[-1])

        if body == 0:
            return False

        return (upper_shadow > 2 * body and
                lower_shadow < body)

    def _is_engulfing(self, open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> Optional[str]:
        """判断是否为吞没形态"""
        if len(open_) < 2:
            return None

        prev_body = close.iloc[-2] - open_.iloc[-2]
        curr_body = close.iloc[-1] - open_.iloc[-1]

        # 看涨吞没
        if (prev_body < 0 and  # 前一天阴线
            curr_body > 0 and  # 今天阳线
            open_.iloc[-1] < close.iloc[-2] and  # 今天开盘价低于昨天收盘价
            close.iloc[-1] > open_.iloc[-2]):  # 今天收盘价高于昨天开盘价
            return "bullish"

        # 看跌吞没
        if (prev_body > 0 and  # 前一天阳线
            curr_body < 0 and  # 今天阴线
            open_.iloc[-1] > close.iloc[-2] and  # 今天开盘价高于昨天收盘价
            close.iloc[-1] < open_.iloc[-2]):  # 今天收盘价低于昨天开盘价
            return "bearish"

        return None

    def _is_morning_star(self, open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> bool:
        """判断是否为启明星"""
        if len(open_) < 3:
            return False

        # 第一天: 长阴线
        day1_body = close.iloc[-3] - open_.iloc[-3]
        # 第二天: 小实体(星)
        day2_body = abs(close.iloc[-2] - open_.iloc[-2])
        day2_range = high.iloc[-2] - low.iloc[-2]
        # 第三天: 长阳线
        day3_body = close.iloc[-1] - open_.iloc[-1]

        if day2_range == 0:
            return False

        return (day1_body < 0 and  # 第一天阴线
                day2_body / day2_range < 0.3 and  # 第二天小实体
                day3_body > 0 and  # 第三天阳线
                close.iloc[-1] > (open_.iloc[-3] + close.iloc[-3]) / 2)  # 收盘价超过第一天实体中点

    def _is_evening_star(self, open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> bool:
        """判断是否为黄昏星"""
        if len(open_) < 3:
            return False

        # 第一天: 长阳线
        day1_body = close.iloc[-3] - open_.iloc[-3]
        # 第二天: 小实体(星)
        day2_body = abs(close.iloc[-2] - open_.iloc[-2])
        day2_range = high.iloc[-2] - low.iloc[-2]
        # 第三天: 长阴线
        day3_body = close.iloc[-1] - open_.iloc[-1]

        if day2_range == 0:
            return False

        return (day1_body > 0 and  # 第一天阳线
                day2_body / day2_range < 0.3 and  # 第二天小实体
                day3_body < 0 and  # 第三天阴线
                close.iloc[-1] < (open_.iloc[-3] + close.iloc[-3]) / 2)  # 收盘价低于第一天实体中点

    # ==================== 综合分析 ====================

    def analyze_trend(
        self,
        df: pd.DataFrame,
        indicators: Dict[str, Any]
    ) -> TrendAnalysis:
        """
        综合趋势分析

        Args:
            df: K线数据
            indicators: 已计算的指标
        """
        # 从EMA判断排列
        ema_data = indicators.get('EMA')
        if ema_data:
            alignment = ema_data.alignment
        else:
            alignment = EMAAlignment.MIXED

        # 从ADX判断强度
        adx_data = indicators.get('ADX')
        adx_value = adx_data.value if adx_data else None

        # 综合判断趋势方向
        bullish_signals = 0
        bearish_signals = 0

        for key, ind in indicators.items():
            if hasattr(ind, 'signal'):
                if ind.signal in [SignalStrength.BUY, SignalStrength.STRONG_BUY]:
                    bullish_signals += 1
                elif ind.signal in [SignalStrength.SELL, SignalStrength.STRONG_SELL]:
                    bearish_signals += 1

        # 确定趋势方向
        if bullish_signals >= 4:
            direction = TrendDirection.STRONG_BULLISH
            strength = 0.9
        elif bullish_signals >= 3:
            direction = TrendDirection.BULLISH
            strength = 0.7
        elif bearish_signals >= 4:
            direction = TrendDirection.STRONG_BEARISH
            strength = 0.9
        elif bearish_signals >= 3:
            direction = TrendDirection.BEARISH
            strength = 0.7
        else:
            direction = TrendDirection.NEUTRAL
            strength = 0.5

        # 生成描述
        desc = f"趋势方向: {direction.value}, 强度: {strength*100:.0f}%"
        if alignment == EMAAlignment.BULLISH_ALIGNMENT:
            desc += ", 均线多头排列"
        elif alignment == EMAAlignment.BEARISH_ALIGNMENT:
            desc += ", 均线空头排列"

        return TrendAnalysis(
            direction=direction,
            strength=strength,
            ema_alignment=alignment,
            adx_value=adx_value,
            description=desc
        )

    def generate_trading_suggestion(
        self,
        df: pd.DataFrame,
        trend: TrendAnalysis,
        indicators: Dict[str, Any],
        support_resistance: SupportResistance
    ) -> TradingSuggestion:
        """
        生成交易建议

        Args:
            df: K线数据
            trend: 趋势分析结果
            indicators: 技术指标
            support_resistance: 支撑阻力位
        """
        current_price = df['close'].iloc[-1]

        # 计算综合信号
        signal_scores = []
        for key, ind in indicators.items():
            if hasattr(ind, 'signal'):
                signal_scores.append(signal_to_score(ind.signal))

        avg_score = sum(signal_scores) / len(signal_scores) if signal_scores else 50
        action = score_to_signal(avg_score)

        # 生成入场区间
        if action in [SignalStrength.BUY, SignalStrength.STRONG_BUY]:
            entry_zone = f"{support_resistance.nearest_support:.2f} - {current_price:.2f}"
            stop_loss = support_resistance.support_levels[-1] if support_resistance.support_levels else current_price * 0.95
            take_profit = support_resistance.resistance_levels[:2] if support_resistance.resistance_levels else [current_price * 1.05]
        elif action in [SignalStrength.SELL, SignalStrength.STRONG_SELL]:
            entry_zone = f"{current_price:.2f} - {support_resistance.nearest_resistance:.2f}"
            stop_loss = support_resistance.resistance_levels[0] if support_resistance.resistance_levels else current_price * 1.05
            take_profit = support_resistance.support_levels[:2] if support_resistance.support_levels else [current_price * 0.95]
        else:
            entry_zone = "建议观望，等待明确信号"
            stop_loss = None
            take_profit = None

        # 计算风险收益比
        rr_ratio = None
        if stop_loss and take_profit and action != SignalStrength.NEUTRAL:
            risk = abs(current_price - stop_loss)
            reward = abs(take_profit[0] - current_price) if take_profit else 0
            rr_ratio = round(reward / risk, 2) if risk > 0 else None

        # 生成理由
        reasons = []
        if trend.direction in [TrendDirection.BULLISH, TrendDirection.STRONG_BULLISH]:
            reasons.append("趋势向上")
        elif trend.direction in [TrendDirection.BEARISH, TrendDirection.STRONG_BEARISH]:
            reasons.append("趋势向下")

        if 'RSI' in indicators:
            rsi = indicators['RSI']
            if rsi.value < 30:
                reasons.append("RSI超卖")
            elif rsi.value > 70:
                reasons.append("RSI超买")

        if 'MACD' in indicators:
            macd = indicators['MACD']
            if macd.histogram > 0:
                reasons.append("MACD多头")
            else:
                reasons.append("MACD空头")

        reasoning = "，".join(reasons) if reasons else "综合技术指标分析"

        return TradingSuggestion(
            action=action,
            entry_zone=entry_zone,
            stop_loss=stop_loss,
            take_profit_levels=take_profit,
            risk_reward_ratio=rr_ratio,
            reasoning=reasoning
        )

    # ==================== 完整分析流程 ====================

    async def full_analysis(
        self,
        symbol: str,
        timeframe: str = "1d",
        market_type: str = "crypto",
        indicators: List[str] = None,
        include_patterns: bool = True
    ) -> TechnicalAnalysisOutput:
        """
        执行完整的技术分析

        Args:
            symbol: 交易对
            timeframe: 时间周期
            market_type: 市场类型
            indicators: 需要计算的指标
            include_patterns: 是否识别K线形态

        Returns:
            完整的技术分析输出
        """
        # 1. 获取K线数据
        df = await self.get_ohlcv(symbol, timeframe, 100, market_type)
        current_price = df['close'].iloc[-1]

        # 计算24小时涨跌幅
        price_change_24h = None
        if len(df) >= 2:
            prev_close = df['close'].iloc[-2]
            price_change_24h = round((current_price - prev_close) / prev_close * 100, 2)

        # 2. 计算技术指标
        if indicators is None:
            indicators = ["RSI", "MACD", "BB", "EMA", "KDJ", "ADX"]

        ind_results = self.calculate_all_indicators(df, indicators)

        # 3. 计算支撑阻力位
        sr = self.calculate_support_resistance(df, method="fibonacci")

        # 4. K线形态识别
        if include_patterns:
            patterns = self.detect_candlestick_patterns(df)
        else:
            patterns = PatternRecognition(
                patterns_found=[],
                dominant_pattern=None,
                pattern_signal=SignalStrength.NEUTRAL
            )

        # 5. 趋势分析
        trend = self.analyze_trend(df, ind_results)

        # 6. 生成交易建议
        suggestion = self.generate_trading_suggestion(df, trend, ind_results, sr)

        # 7. 计算综合评分
        signal_scores = []
        for key, ind in ind_results.items():
            if hasattr(ind, 'signal'):
                signal_scores.append(signal_to_score(ind.signal))

        technical_score = sum(signal_scores) / len(signal_scores) if signal_scores else 50
        overall_signal = score_to_signal(technical_score)

        # 8. 计算置信度
        confidence = min(len(signal_scores) / 6, 1.0)  # 基于指标数量
        if trend.strength > 0.7:
            confidence = min(confidence + 0.1, 1.0)

        # 9. 构建指标信号列表
        indicator_signals = []
        for name, ind in ind_results.items():
            if hasattr(ind, 'signal') and hasattr(ind, 'description'):
                indicator_signals.append(IndicatorSignal(
                    name=name,
                    value=getattr(ind, 'value', 0) if hasattr(ind, 'value') else 0,
                    signal=ind.signal,
                    description=ind.description
                ))

        # 10. 构建技术指标对象
        tech_indicators = TechnicalIndicators(
            rsi=ind_results.get('RSI'),
            macd=ind_results.get('MACD'),
            bollinger_bands=ind_results.get('BB'),
            ema=ind_results.get('EMA'),
            kdj=ind_results.get('KDJ'),
            adx=ind_results.get('ADX')
        )

        # 11. 风险提示
        risk_warning = (
            "⚠️ 技术分析仅供参考，不构成投资建议。"
            "市场有风险，投资需谨慎。"
            "短期价格波动具有不可预测性，请根据自身风险承受能力做出决策。"
        )

        return TechnicalAnalysisOutput(
            symbol=symbol,
            timeframe=timeframe,
            market_type=market_type,
            timestamp=datetime.now().isoformat(),
            current_price=round(current_price, 2),
            price_change_24h=price_change_24h,
            technical_score=round(technical_score, 1),
            overall_signal=overall_signal,
            confidence=round(confidence, 2),
            trend_analysis=trend,
            indicators=tech_indicators,
            indicator_signals=indicator_signals,
            support_resistance=sr,
            pattern_recognition=patterns,
            trading_suggestion=suggestion,
            risk_warning=risk_warning
        )
