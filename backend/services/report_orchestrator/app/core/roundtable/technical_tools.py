"""
Technical Analysis Tools

Provides K-line data fetching and technical indicator calculation.
Supports crypto (Binance) and stock (Yahoo Finance) markets.
"""

import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime
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
    Technical Analysis Tools

    Features:
    - Fetch K-line data (crypto/stock)
    - Calculate technical indicators (RSI, MACD, BB, EMA, KDJ, ADX, etc.)
    - Identify support/resistance levels
    - Candlestick pattern recognition
    - Generate trading signals
    """

    def __init__(self):
        # API endpoints - OKX first (available in mainland China), then Binance, finally CoinGecko
        self.okx_api = "https://www.okx.com/api/v5"
        self.binance_api = "https://api.binance.com/api/v3"
        self.coingecko_api = "https://api.coingecko.com/api/v3"

        # Timeout configuration
        self.timeout = 30.0

    # ==================== Data Fetching ====================

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 100,
        market_type: str = "crypto"
    ) -> pd.DataFrame:
        """
        Fetch K-line data (OHLCV)

        Args:
            symbol: Trading pair (e.g. BTC/USDT, BTC, AAPL)
            timeframe: Time period (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)
            limit: Number of candles to fetch
            market_type: Market type (crypto, stock)

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
        """Fetch crypto K-line data from OKX, Binance, CoinGecko, or Yahoo Finance"""

        # First try OKX API (available in mainland China)
        try:
            return await self._get_crypto_ohlcv_okx(symbol, timeframe, limit)
        except Exception as e:
            print(f"OKX API failed: {e}, trying Binance...")

        # Then try Binance API
        try:
            return await self._get_crypto_ohlcv_binance(symbol, timeframe, limit)
        except Exception as e:
            print(f"Binance API failed: {e}, trying CoinGecko...")

        # Try CoinGecko
        try:
            return await self._get_crypto_ohlcv_coingecko(symbol, timeframe, limit)
        except Exception as e:
            print(f"CoinGecko API failed: {e}, trying Yahoo Finance...")

        # Finally try Yahoo Finance (BTC-USD, ETH-USD, etc.)
        return await self._get_crypto_ohlcv_yfinance(symbol, timeframe, limit)

    async def _get_crypto_ohlcv_okx(
        self,
        symbol: str,
        timeframe: str,
        limit: int
    ) -> pd.DataFrame:
        """Fetch crypto K-line data from OKX (preferred, available in mainland China)"""

        # Normalize symbol to OKX format (BTC-USDT)
        clean_symbol = symbol.replace("/", "").upper()
        if clean_symbol.endswith("USDT"):
            okx_symbol = clean_symbol.replace("USDT", "-USDT")
        else:
            okx_symbol = f"{clean_symbol}-USDT"

        # Convert timeframe to OKX format
        tf_map = {
            "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1H", "4h": "4H", "1d": "1D", "1w": "1W", "1M": "1M"
        }
        bar = tf_map.get(timeframe, "1D")

        url = f"{self.okx_api}/market/candles"
        params = {
            "instId": okx_symbol,
            "bar": bar,
            "limit": str(min(limit, 300))  # OKX最大300
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)

            if response.status_code != 200:
                raise Exception(f"OKX API error: {response.status_code} - {response.text}")

            data = response.json()

            if data.get("code") != "0":
                raise Exception(f"OKX API error: {data.get('msg', 'Unknown error')}")

            candles = data.get("data", [])
            if not candles:
                raise Exception(f"No data returned for {okx_symbol}")

        # OKX returns: [timestamp, open, high, low, close, vol, volCcy, volCcyQuote, confirm]
        # Note: OKX data is descending (newest first), needs to be reversed
        df = pd.DataFrame(candles, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'vol_ccy', 'vol_ccy_quote', 'confirm'
        ])

        # Reverse order so oldest is first
        df = df.iloc[::-1].reset_index(drop=True)

        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        print(f"[TechnicalTools] Fetched {len(df)} candles from OKX: {okx_symbol}, latest close: ${df['close'].iloc[-1]:,.2f}")

        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

    async def _get_crypto_ohlcv_yfinance(
        self,
        symbol: str,
        timeframe: str,
        limit: int
    ) -> pd.DataFrame:
        """Fetch crypto K-line data from Yahoo Finance"""
        import yfinance as yf

        # Map symbol to Yahoo Finance format
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

        # Convert timeframe to yfinance format
        tf_map = {
            "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1h", "4h": "1h", "1d": "1d", "1w": "1wk", "1M": "1mo"
        }
        interval = tf_map.get(timeframe, "1d")

        # Calculate time range to fetch
        period_map = {
            "1m": "1d", "5m": "5d", "15m": "5d", "30m": "5d",
            "1h": "60d", "4h": "60d", "1d": "1y", "1w": "2y", "1M": "5y"
        }
        period = period_map.get(timeframe, "1y")

        # Run synchronous yfinance code in async context
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None,
            lambda: yf.download(yf_symbol, period=period, interval=interval, progress=False)
        )

        if df.empty:
            raise Exception(f"No data returned from Yahoo Finance for {yf_symbol}")

        # Reset index and rename columns
        df = df.reset_index()

        # Handle column names - yfinance may return tuple or string column names
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

        # Ensure column names are lowercase
        df.columns = df.columns.str.lower()

        # Limit returned count
        if len(df) > limit:
            df = df.tail(limit)

        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

    async def _get_crypto_ohlcv_binance(
        self,
        symbol: str,
        timeframe: str,
        limit: int
    ) -> pd.DataFrame:
        """Fetch crypto K-line data from Binance"""

        # Normalize symbol
        if "/" in symbol:
            symbol = symbol.replace("/", "")
        elif not symbol.upper().endswith("USDT"):
            symbol = f"{symbol}USDT"
        symbol = symbol.upper()

        # Convert timeframe
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

        # Convert to DataFrame
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
        """Fetch crypto K-line data from CoinGecko (fallback)"""

        # Map common symbols to CoinGecko ID
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

        # Normalize symbol
        clean_symbol = symbol.replace("/", "").replace("USDT", "").upper()
        coin_id = symbol_map.get(clean_symbol, symbol_map.get(symbol.upper().replace("/", ""), clean_symbol.lower()))

        # Convert timeframe to days
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

        # Limit returned count
        if len(df) > limit:
            df = df.tail(limit)

        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

    async def _get_stock_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int
    ) -> pd.DataFrame:
        """Fetch stock K-line data (using yfinance library if available)"""
        try:
            import yfinance as yf

            # Convert timeframe to yfinance format
            tf_map = {
                "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                "1h": "1h", "1d": "1d", "1w": "1wk", "1M": "1mo"
            }
            interval = tf_map.get(timeframe, "1d")

            # Calculate date range
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
        """Get current price"""
        df = await self.get_ohlcv(symbol, "1h", 1, market_type)
        return df['close'].iloc[-1]

    # ==================== Technical Indicator Calculation ====================

    def calculate_all_indicators(
        self,
        df: pd.DataFrame,
        indicators: List[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate all technical indicators

        Args:
            df: K-line data DataFrame
            indicators: List of indicators to calculate, default all

        Returns:
            Dictionary of indicator calculation results
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

            if "ADX" in indicators and data_len >= 28:  # ADX needs at least 14*2 data points
                results['adx'] = self._calculate_adx(high, low, close)

        except Exception as e:
            print(f"[TechnicalTools] Error calculating indicators: {e}")
            import traceback
            traceback.print_exc()

        # Add trend analysis
        results['trend'] = self._analyze_trend(df)

        return results

    def _calculate_rsi(self, close: pd.Series, period: int = 14) -> RSIIndicator:
        """Calculate RSI"""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]

        # Determine signal
        if current_rsi < 30:
            signal = SignalStrength.STRONG_BUY
            desc = f"RSI={current_rsi:.1f}, severely oversold, possible bounce"
        elif current_rsi < 40:
            signal = SignalStrength.BUY
            desc = f"RSI={current_rsi:.1f}, weak, approaching oversold"
        elif current_rsi > 70:
            signal = SignalStrength.STRONG_SELL
            desc = f"RSI={current_rsi:.1f}, severely overbought, watch for pullback"
        elif current_rsi > 60:
            signal = SignalStrength.SELL
            desc = f"RSI={current_rsi:.1f}, strong, approaching overbought"
        else:
            signal = SignalStrength.NEUTRAL
            desc = f"RSI={current_rsi:.1f}, neutral zone"

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
        """Calculate MACD"""
        exp1 = close.ewm(span=fast, adjust=False).mean()
        exp2 = close.ewm(span=slow, adjust=False).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_hist = histogram.iloc[-1]
        prev_hist = histogram.iloc[-2] if len(histogram) > 1 else 0

        # Determine signal
        if current_hist > 0:
            if current_hist > prev_hist:
                sig = SignalStrength.BUY
                desc = "MACD histogram above zero and expanding, bullish momentum strengthening"
            else:
                sig = SignalStrength.NEUTRAL
                desc = "MACD histogram above zero but shrinking, bullish momentum weakening"
        else:
            if current_hist < prev_hist:
                sig = SignalStrength.SELL
                desc = "MACD histogram below zero and expanding, bearish momentum strengthening"
            else:
                sig = SignalStrength.NEUTRAL
                desc = "MACD histogram below zero but shrinking, bearish momentum weakening"

        # Golden cross / Death cross detection
        if len(histogram) >= 2:
            if histogram.iloc[-2] < 0 and histogram.iloc[-1] > 0:
                sig = SignalStrength.STRONG_BUY
                desc = "MACD golden cross, buy signal"
            elif histogram.iloc[-2] > 0 and histogram.iloc[-1] < 0:
                sig = SignalStrength.STRONG_SELL
                desc = "MACD death cross, sell signal"

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
        """Calculate Bollinger Bands"""
        middle = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        current_price = close.iloc[-1]
        current_upper = upper.iloc[-1]
        current_middle = middle.iloc[-1]
        current_lower = lower.iloc[-1]

        # Calculate bandwidth
        width = (current_upper - current_lower) / current_middle * 100

        # Determine position
        if current_price > current_upper:
            position = "above_upper"
            signal = SignalStrength.SELL
            desc = f"Price broke above upper band ({current_upper:.2f}), possibly overbought or breakout"
        elif current_price < current_lower:
            position = "below_lower"
            signal = SignalStrength.BUY
            desc = f"Price broke below lower band ({current_lower:.2f}), possibly oversold or breakdown"
        elif current_price > current_middle:
            position = "upper_half"
            signal = SignalStrength.NEUTRAL
            desc = f"Price in upper half of Bollinger Bands, bullish bias"
        else:
            position = "lower_half"
            signal = SignalStrength.NEUTRAL
            desc = f"Price in lower half of Bollinger Bands, bearish bias"

        desc += f", volatility {width:.1f}%"

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
        """Calculate EMA (7, 25, 99)"""
        ema7 = close.ewm(span=7, adjust=False).mean().iloc[-1]
        ema25 = close.ewm(span=25, adjust=False).mean().iloc[-1]
        ema99 = close.ewm(span=99, adjust=False).mean().iloc[-1]

        # Determine alignment
        if ema7 > ema25 > ema99:
            alignment = EMAAlignment.BULLISH_ALIGNMENT
            signal = SignalStrength.BUY
            desc = f"EMA bullish alignment (7>{ema7:.2f} > 25>{ema25:.2f} > 99>{ema99:.2f}), uptrend"
        elif ema7 < ema25 < ema99:
            alignment = EMAAlignment.BEARISH_ALIGNMENT
            signal = SignalStrength.SELL
            desc = f"EMA bearish alignment (7<{ema7:.2f} < 25<{ema25:.2f} < 99<{ema99:.2f}), downtrend"
        else:
            alignment = EMAAlignment.MIXED
            signal = SignalStrength.NEUTRAL
            desc = "EMA mixed, trend unclear"

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
        """Calculate KDJ indicator"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        rsv = (close - lowest_low) / (highest_high - lowest_low) * 100

        k = rsv.ewm(com=d_period-1, adjust=False).mean()
        d = k.ewm(com=d_period-1, adjust=False).mean()
        j = 3 * k - 2 * d

        current_k = k.iloc[-1]
        current_d = d.iloc[-1]
        current_j = j.iloc[-1]

        # Determine signal
        if current_j < 20 and current_k < 20:
            signal = SignalStrength.STRONG_BUY
            desc = f"KDJ oversold zone (J={current_j:.1f}, K={current_k:.1f}), possible bounce"
        elif current_j > 80 and current_k > 80:
            signal = SignalStrength.STRONG_SELL
            desc = f"KDJ overbought zone (J={current_j:.1f}, K={current_k:.1f}), watch for pullback"
        elif current_k > current_d:
            signal = SignalStrength.BUY
            desc = f"K line ({current_k:.1f}) above D line ({current_d:.1f}), short-term bullish"
        elif current_k < current_d:
            signal = SignalStrength.SELL
            desc = f"K line ({current_k:.1f}) below D line ({current_d:.1f}), short-term bearish"
        else:
            signal = SignalStrength.NEUTRAL
            desc = "KDJ neutral zone"

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
        """Calculate ADX indicator"""
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

        # Determine trend strength
        if current_adx > 50:
            strength = TrendStrength.VERY_STRONG
            desc = f"ADX={current_adx:.1f}, very strong trend"
        elif current_adx > 25:
            strength = TrendStrength.STRONG
            desc = f"ADX={current_adx:.1f}, clear trending market"
        elif current_adx > 20:
            strength = TrendStrength.MODERATE
            desc = f"ADX={current_adx:.1f}, trend forming"
        else:
            strength = TrendStrength.WEAK
            desc = f"ADX={current_adx:.1f}, weak trend or ranging market"

        return ADXIndicator(
            value=round(current_adx, 2),
            trend_strength=strength,
            description=desc
        )

    def _analyze_trend(self, df: pd.DataFrame) -> TrendAnalysis:
        """Analyze trend"""
        close = df['close']

        # Calculate EMA for alignment determination
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

        # Use simple moving average to determine trend
        if len(close) >= 20:
            sma_short = close.rolling(window=5).mean().iloc[-1]
            sma_long = close.rolling(window=20).mean().iloc[-1]
            current_price = close.iloc[-1]

            if current_price > sma_short > sma_long:
                direction = TrendDirection.BULLISH
                strength = 0.8  # float 0-1
                desc = "Price above MA, bullish MA alignment, clear uptrend"
            elif current_price < sma_short < sma_long:
                direction = TrendDirection.BEARISH
                strength = 0.8
                desc = "Price below MA, bearish MA alignment, clear downtrend"
            elif current_price > sma_long:
                direction = TrendDirection.BULLISH
                strength = 0.6
                desc = "Price above long-term MA, medium-term bullish"
            elif current_price < sma_long:
                direction = TrendDirection.BEARISH
                strength = 0.6
                desc = "Price below long-term MA, medium-term bearish"
            else:
                direction = TrendDirection.SIDEWAYS
                strength = 0.3
                desc = "Trend unclear, ranging"
        else:
            # Simple judgment when insufficient data
            if len(close) >= 5:
                change = (close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100
                if change > 5:
                    direction = TrendDirection.BULLISH
                    strength = 0.5
                    desc = f"Recent rise {change:.1f}%"
                elif change < -5:
                    direction = TrendDirection.BEARISH
                    strength = 0.5
                    desc = f"Recent drop {abs(change):.1f}%"
                else:
                    direction = TrendDirection.SIDEWAYS
                    strength = 0.3
                    desc = f"Recent change {change:.1f}%, ranging"
            else:
                direction = TrendDirection.SIDEWAYS
                strength = 0.2
                desc = "Insufficient data to determine trend"

        return TrendAnalysis(
            direction=direction,
            strength=strength,
            ema_alignment=ema_alignment,
            description=desc
        )

    # ==================== Support/Resistance Levels ====================

    def calculate_support_resistance(
        self,
        df: pd.DataFrame,
        method: str = "fibonacci"
    ) -> SupportResistance:
        """
        Calculate support/resistance levels

        Args:
            df: K-line data
            method: Calculation method (fibonacci, pivot)
        """
        current = df['close'].iloc[-1]
        high = df['high'].max()
        low = df['low'].min()
        diff = high - low

        if method == "fibonacci":
            # Fibonacci retracement levels
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

        # Find nearest support/resistance
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

    # ==================== Candlestick Pattern Recognition ====================

    def detect_candlestick_patterns(self, df: pd.DataFrame) -> PatternRecognition:
        """
        Detect candlestick patterns

        Args:
            df: K-line data

        Returns:
            PatternRecognition result
        """
        patterns = []

        open_ = df['open']
        high = df['high']
        low = df['low']
        close = df['close']

        # Last 3 candles
        if len(df) < 3:
            return PatternRecognition(
                patterns_found=[],
                dominant_pattern=None,
                pattern_signal=SignalStrength.NEUTRAL
            )

        # Doji
        if self._is_doji(open_.iloc[-1], high.iloc[-1], low.iloc[-1], close.iloc[-1]):
            patterns.append(CandlestickPattern(
                name="Doji",
                english_name="doji",
                type="indecision",
                direction="neutral",
                strength="medium"
            ))

        # Hammer - long lower shadow, short body, at end of downtrend
        if self._is_hammer(open_, high, low, close):
            patterns.append(CandlestickPattern(
                name="Hammer",
                english_name="hammer",
                type="bullish_reversal",
                direction="bullish",
                strength="medium"
            ))

        # Inverted Hammer
        if self._is_inverted_hammer(open_, high, low, close):
            patterns.append(CandlestickPattern(
                name="Inverted Hammer",
                english_name="inverted_hammer",
                type="bullish_reversal",
                direction="bullish",
                strength="weak"
            ))

        # Engulfing pattern
        engulfing = self._is_engulfing(open_, high, low, close)
        if engulfing == "bullish":
            patterns.append(CandlestickPattern(
                name="Bullish Engulfing",
                english_name="bullish_engulfing",
                type="bullish_reversal",
                direction="bullish",
                strength="strong"
            ))
        elif engulfing == "bearish":
            patterns.append(CandlestickPattern(
                name="Bearish Engulfing",
                english_name="bearish_engulfing",
                type="bearish_reversal",
                direction="bearish",
                strength="strong"
            ))

        # Morning Star
        if self._is_morning_star(open_, high, low, close):
            patterns.append(CandlestickPattern(
                name="Morning Star",
                english_name="morning_star",
                type="bullish_reversal",
                direction="bullish",
                strength="strong"
            ))

        # Evening Star
        if self._is_evening_star(open_, high, low, close):
            patterns.append(CandlestickPattern(
                name="Evening Star",
                english_name="evening_star",
                type="bearish_reversal",
                direction="bearish",
                strength="strong"
            ))

        # Determine dominant pattern and signal
        dominant = None
        signal = SignalStrength.NEUTRAL

        if patterns:
            # Prioritize strong signal patterns
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
        """Check if doji pattern"""
        body = abs(close - open_)
        total_range = high - low
        if total_range == 0:
            return False
        return body / total_range < 0.1

    def _is_hammer(self, open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> bool:
        """Check if hammer pattern"""
        body = abs(close.iloc[-1] - open_.iloc[-1])
        lower_shadow = min(open_.iloc[-1], close.iloc[-1]) - low.iloc[-1]
        upper_shadow = high.iloc[-1] - max(open_.iloc[-1], close.iloc[-1])

        if body == 0:
            return False

        return (lower_shadow > 2 * body and
                upper_shadow < body and
                close.iloc[-1] > open_.iloc[-1])

    def _is_inverted_hammer(self, open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> bool:
        """Check if inverted hammer pattern"""
        body = abs(close.iloc[-1] - open_.iloc[-1])
        lower_shadow = min(open_.iloc[-1], close.iloc[-1]) - low.iloc[-1]
        upper_shadow = high.iloc[-1] - max(open_.iloc[-1], close.iloc[-1])

        if body == 0:
            return False

        return (upper_shadow > 2 * body and
                lower_shadow < body)

    def _is_engulfing(self, open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> Optional[str]:
        """Check if engulfing pattern"""
        if len(open_) < 2:
            return None

        prev_body = close.iloc[-2] - open_.iloc[-2]
        curr_body = close.iloc[-1] - open_.iloc[-1]

        # Bullish engulfing
        if (prev_body < 0 and  # Previous day bearish
            curr_body > 0 and  # Today bullish
            open_.iloc[-1] < close.iloc[-2] and  # Today open below yesterday close
            close.iloc[-1] > open_.iloc[-2]):  # Today close above yesterday open
            return "bullish"

        # Bearish engulfing
        if (prev_body > 0 and  # Previous day bullish
            curr_body < 0 and  # Today bearish
            open_.iloc[-1] > close.iloc[-2] and  # Today open above yesterday close
            close.iloc[-1] < open_.iloc[-2]):  # Today close below yesterday open
            return "bearish"

        return None

    def _is_morning_star(self, open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> bool:
        """Check if morning star pattern"""
        if len(open_) < 3:
            return False

        # Day 1: Long bearish candle
        day1_body = close.iloc[-3] - open_.iloc[-3]
        # Day 2: Small body (star)
        day2_body = abs(close.iloc[-2] - open_.iloc[-2])
        day2_range = high.iloc[-2] - low.iloc[-2]
        # Day 3: Long bullish candle
        day3_body = close.iloc[-1] - open_.iloc[-1]

        if day2_range == 0:
            return False

        return (day1_body < 0 and  # Day 1 bearish
                day2_body / day2_range < 0.3 and  # Day 2 small body
                day3_body > 0 and  # Day 3 bullish
                close.iloc[-1] > (open_.iloc[-3] + close.iloc[-3]) / 2)  # Close above day 1 body midpoint

    def _is_evening_star(self, open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> bool:
        """Check if evening star pattern"""
        if len(open_) < 3:
            return False

        # Day 1: Long bullish candle
        day1_body = close.iloc[-3] - open_.iloc[-3]
        # Day 2: Small body (star)
        day2_body = abs(close.iloc[-2] - open_.iloc[-2])
        day2_range = high.iloc[-2] - low.iloc[-2]
        # Day 3: Long bearish candle
        day3_body = close.iloc[-1] - open_.iloc[-1]

        if day2_range == 0:
            return False

        return (day1_body > 0 and  # Day 1 bullish
                day2_body / day2_range < 0.3 and  # Day 2 small body
                day3_body < 0 and  # Day 3 bearish
                close.iloc[-1] < (open_.iloc[-3] + close.iloc[-3]) / 2)  # Close below day 1 body midpoint

    # ==================== Comprehensive Analysis ====================

    def analyze_trend(
        self,
        df: pd.DataFrame,
        indicators: Dict[str, Any]
    ) -> TrendAnalysis:
        """
        Comprehensive trend analysis

        Args:
            df: K-line data
            indicators: Already calculated indicators
        """
        # Determine alignment from EMA
        ema_data = indicators.get('EMA')
        if ema_data:
            alignment = ema_data.alignment
        else:
            alignment = EMAAlignment.MIXED

        # Determine strength from ADX
        adx_data = indicators.get('ADX')
        adx_value = adx_data.value if adx_data else None

        # Determine overall trend direction
        bullish_signals = 0
        bearish_signals = 0

        for key, ind in indicators.items():
            if hasattr(ind, 'signal'):
                if ind.signal in [SignalStrength.BUY, SignalStrength.STRONG_BUY]:
                    bullish_signals += 1
                elif ind.signal in [SignalStrength.SELL, SignalStrength.STRONG_SELL]:
                    bearish_signals += 1

        # Determine trend direction
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

        # Generate description
        desc = f"Trend direction: {direction.value}, Strength: {strength*100:.0f}%"
        if alignment == EMAAlignment.BULLISH_ALIGNMENT:
            desc += ", bullish MA alignment"
        elif alignment == EMAAlignment.BEARISH_ALIGNMENT:
            desc += ", bearish MA alignment"

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
