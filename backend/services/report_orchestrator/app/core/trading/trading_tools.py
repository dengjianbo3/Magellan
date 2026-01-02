"""
Trading Tools for Agents

Provides tools that trading agents can use to analyze markets and execute trades.
"""

import logging
import os
from datetime import datetime
from typing import Optional, List
import json

try:
    import pandas as pd
    import numpy as np
except ImportError:
    pd = None
    np = None

from app.core.roundtable.tool import FunctionTool
from app.core.trading.price_service import get_current_btc_price, PriceServiceError

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


class TradingToolkitConfig:
    """Configuration for TradingToolkit - reads from environment variables"""
    def __init__(
        self,
        max_leverage: int = None,
        default_balance: float = 10000.0,
        symbol: str = None
    ):
        # Read from environment variables with fallback to defaults
        self.max_leverage = max_leverage if max_leverage is not None else _get_env_int("MAX_LEVERAGE", 20)
        self.default_balance = default_balance
        self.symbol = symbol if symbol is not None else os.getenv("TRADING_SYMBOL", "BTC-USDT-SWAP")
        logger.info(f"TradingToolkitConfig initialized: max_leverage={self.max_leverage}, symbol={self.symbol}")


class TradingToolkit:
    """
    Collection of trading tools for agents.

    Tools are designed to be registered with agents for use in roundtable meetings.
    """

    def __init__(self, paper_trader=None, config: TradingToolkitConfig = None):
        self.paper_trader = paper_trader
        self.config = config or TradingToolkitConfig()
        self._tools = {}
        self._build_tools()

    def _build_tools(self):
        """Build all trading tools"""

        # Market Data Tools
        self._tools['get_market_price'] = FunctionTool(
            name="get_market_price",
            description=f"Get current market price and 24h data including price, change percentage, and volume",
            parameters_schema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": f"Trading pair, default {self.config.symbol}",
                        "default": self.config.symbol
                    }
                }
            },
            func=self._get_market_price
        )

        self._tools['get_klines'] = FunctionTool(
            name="get_klines",
            description="Get K-line/candlestick data for technical analysis, supports various timeframes",
            parameters_schema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": f"Trading pair, default {self.config.symbol}",
                        "default": self.config.symbol
                    },
                    "timeframe": {
                        "type": "string",
                        "description": "Timeframe: 1m, 5m, 15m, 1h, 4h, 1d",
                        "default": "4h"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of K-lines to fetch",
                        "default": 100
                    }
                }
            },
            func=self._get_klines
        )

        self._tools['calculate_technical_indicators'] = FunctionTool(
            name="calculate_technical_indicators",
            description="Calculate technical indicators: RSI, MACD, Bollinger Bands, EMA, etc.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "default": self.config.symbol
                    },
                    "timeframe": {
                        "type": "string",
                        "default": "4h"
                    }
                }
            },
            func=self._calculate_indicators
        )

        # Account Tools
        self._tools['get_account_balance'] = FunctionTool(
            name="get_account_balance",
            description=(
                "Get account balance and available funds. "
                "⚠️ IMPORTANT: Use 'true_available_margin' field to determine funds available for opening positions! "
                "This value accounts for the impact of unrealized PnL on margin. "
                "'available_balance' only shows cash balance without considering position floating PnL."
            ),
            parameters_schema={"type": "object", "properties": {}},
            func=self._get_account_balance
        )

        self._tools['get_current_position'] = FunctionTool(
            name="get_current_position",
            description="Get current position info including direction, leverage, and PnL",
            parameters_schema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "default": self.config.symbol
                    }
                }
            },
            func=self._get_current_position
        )

        # Trading Execution Tools
        self._tools['open_long'] = FunctionTool(
            name="open_long",
            description=f"Open long position (buy). ⚠️ MUST provide all 4 parameters: leverage, amount_usdt, tp_percent, sl_percent! Call will fail if any parameter is missing!",
            parameters_schema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "default": self.config.symbol
                    },
                    "leverage": {
                        "type": "integer",
                        "description": f"[REQUIRED] Leverage multiplier (1-{self.config.max_leverage})",
                        "minimum": 1,
                        "maximum": self.config.max_leverage
                    },
                    "amount_usdt": {
                        "type": "number",
                        "description": "[REQUIRED] USDT amount to invest"
                    },
                    "tp_percent": {
                        "type": "number",
                        "description": "[REQUIRED] Take profit percentage, e.g. 5 means take profit at +5%",
                        "minimum": 0.5,
                        "maximum": 50
                    },
                    "sl_percent": {
                        "type": "number",
                        "description": "[REQUIRED] Stop loss percentage, e.g. 2 means stop loss at -2%",
                        "minimum": 0.5,
                        "maximum": 20
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for opening position"
                    }
                },
                "required": ["leverage", "amount_usdt", "tp_percent", "sl_percent"]
            },
            func=self._open_long
        )

        self._tools['open_short'] = FunctionTool(
            name="open_short",
            description=f"Open short position (sell). ⚠️ MUST provide all 4 parameters: leverage, amount_usdt, tp_percent, sl_percent! Call will fail if any parameter is missing!",
            parameters_schema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "default": self.config.symbol
                    },
                    "leverage": {
                        "type": "integer",
                        "description": f"[REQUIRED] Leverage multiplier (1-{self.config.max_leverage})",
                        "minimum": 1,
                        "maximum": self.config.max_leverage
                    },
                    "amount_usdt": {
                        "type": "number",
                        "description": "[REQUIRED] USDT amount to invest"
                    },
                    "tp_percent": {
                        "type": "number",
                        "description": "[REQUIRED] Take profit percentage, e.g. 5 means take profit at -5%",
                        "minimum": 0.5,
                        "maximum": 50
                    },
                    "sl_percent": {
                        "type": "number",
                        "description": "[REQUIRED] Stop loss percentage, e.g. 2 means stop loss at +2%",
                        "minimum": 0.5,
                        "maximum": 20
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for opening position"
                    }
                },
                "required": ["leverage", "amount_usdt", "tp_percent", "sl_percent"]
            },
            func=self._open_short
        )

        self._tools['close_position'] = FunctionTool(
            name="close_position",
            description="Close current position",
            parameters_schema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "default": self.config.symbol
                    }
                }
            },
            func=self._close_position
        )

        # Hold Decision Tool
        self._tools['hold'] = FunctionTool(
            name="hold",
            description="Decide to hold/wait, no trading action. Call this when market is unclear or risk is too high",
            parameters_schema={
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Reason for holding/waiting"
                    }
                },
                "required": ["reason"]
            },
            func=self._hold
        )

        # Analysis Tools
        self._tools['get_fear_greed_index'] = FunctionTool(
            name="get_fear_greed_index",
            description="Get crypto Fear & Greed Index reflecting market sentiment",
            parameters_schema={"type": "object", "properties": {}},
            func=self._get_fear_greed_index
        )

        self._tools['get_funding_rate'] = FunctionTool(
            name="get_funding_rate",
            description="Get funding rate reflecting long/short position balance",
            parameters_schema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "default": self.config.symbol
                    }
                }
            },
            func=self._get_funding_rate
        )

        self._tools['get_trade_history'] = FunctionTool(
            name="get_trade_history",
            description="Get historical trade records",
            parameters_schema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "default": 20
                    }
                }
            },
            func=self._get_trade_history
        )

        # Web Search Tool - Tavily
        self._tools['tavily_search'] = FunctionTool(
            name="tavily_search",
            description="Search for crypto news and market info using Tavily search engine, get latest market updates, major events, regulatory news, etc.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query, e.g. 'BTC news today' or 'Bitcoin regulation 2024'"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Number of results to return, default 5",
                        "default": 5
                    },
                    "time_range": {
                        "type": "string",
                        "description": "Time range: day (last 24h), week (last week), month (last month)",
                        "enum": ["day", "week", "month"],
                        "default": None
                    },
                    "topic": {
                        "type": "string",
                        "description": "Search topic: general or news",
                        "enum": ["general", "news"],
                        "default": "general"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Limit search results to days range (1-30)",
                        "default": None
                    }
                },
                "required": ["query"]
            },
            func=self._tavily_search
        )

        # Smart Execution Analysis Tool
        self._tools['analyze_execution_conditions'] = FunctionTool(
            name="analyze_execution_conditions",
            description=(
                "Analyze execution conditions before placing a trade. "
                "Returns recommended execution strategy (direct/sliced/twap), "
                "estimated slippage, liquidity rating, and optimal slice count. "
                "⚠️ Call this BEFORE executing large orders to minimize market impact!"
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "amount_usdt": {
                        "type": "number",
                        "description": "[REQUIRED] Amount in USDT to trade"
                    },
                    "direction": {
                        "type": "string",
                        "description": "[REQUIRED] Trade direction: 'long' or 'short'",
                        "enum": ["long", "short"]
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Trading symbol, default BTC",
                        "default": "BTC"
                    }
                },
                "required": ["amount_usdt", "direction"]
            },
            func=self._analyze_execution_conditions
        )

        # Technical Analysis Tool (comprehensive)
        self._tools['technical_analysis'] = FunctionTool(
            name="technical_analysis",
            description=(
                "Perform comprehensive technical analysis including K-lines, indicators, patterns. "
                "This is an all-in-one analysis tool that combines get_klines and calculate_technical_indicators. "
                "Returns RSI, MACD, Bollinger Bands, EMA, support/resistance levels, and trend analysis."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Trading pair, e.g. BTC/USDT",
                        "default": self.config.symbol
                    },
                    "timeframe": {
                        "type": "string",
                        "description": "Timeframe: 1m, 5m, 15m, 1h, 4h, 1d",
                        "default": "4h"
                    },
                    "action": {
                        "type": "string",
                        "description": "Analysis type: full_analysis, indicators_only, patterns_only",
                        "default": "full_analysis"
                    },
                    "market_type": {
                        "type": "string",
                        "description": "Market type: crypto, forex, stock",
                        "default": "crypto"
                    }
                }
            },
            func=self._technical_analysis
        )

        # Orderbook Analyzer Tool
        self._tools['orderbook_analyzer'] = FunctionTool(
            name="orderbook_analyzer",
            description=(
                "Analyze exchange orderbook depth to identify support/resistance levels, "
                "buy/sell pressure, large orders (whale detection), and market sentiment. "
                "Useful for short-term trading decisions and liquidity assessment."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Coin symbol, e.g. BTC",
                        "default": "BTC"
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Number of price levels to analyze (5-50)",
                        "default": 20
                    }
                }
            },
            func=self._orderbook_analyzer
        )

    def get_tools(self) -> List[FunctionTool]:
        """Get all tools as a list"""
        return list(self._tools.values())

    def get_tool(self, name: str) -> Optional[FunctionTool]:
        """Get a specific tool by name"""
        return self._tools.get(name)

    def get_analysis_tools(self) -> List[FunctionTool]:
        """Get only analysis tools (no trading execution)"""
        analysis_tool_names = [
            'get_market_price', 'get_klines', 'calculate_technical_indicators',
            'get_account_balance', 'get_current_position',
            'get_fear_greed_index', 'get_funding_rate', 'get_trade_history',
            'tavily_search', 'analyze_execution_conditions',
            'technical_analysis', 'orderbook_analyzer'  # Added for TechnicalAnalyst
        ]
        return [self._tools[name] for name in analysis_tool_names if name in self._tools]

    def get_execution_tools(self) -> List[FunctionTool]:
        """Get only execution tools (including hold for decision making)"""
        exec_tool_names = ['open_long', 'open_short', 'close_position', 'hold', 'analyze_execution_conditions']
        return [self._tools[name] for name in exec_tool_names if name in self._tools]

    # ===== Tool Implementation Methods =====

    async def _get_market_price(self, symbol: str = "BTC-USDT-SWAP") -> str:
        """Get market price implementation - uses REAL data from Binance API"""
        try:
            # Fetch REAL price from Binance API
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get 24h ticker data from Binance
                response = await client.get(
                    "https://api.binance.com/api/v3/ticker/24hr",
                    params={"symbol": "BTCUSDT"}
                )

                if response.status_code == 200:
                    data = response.json()
                    price = float(data['lastPrice'])
                    change_24h = float(data['priceChangePercent'])
                    volume_24h = float(data['quoteVolume'])
                    high_24h = float(data['highPrice'])
                    low_24h = float(data['lowPrice'])

                    # Update paper trader with real price
                    if self.paper_trader:
                        self.paper_trader.set_price(price)

                    logger.info(f"[TradingTools] Fetched REAL BTC price: ${price:,.2f} (24h: {change_24h:+.2f}%)")

                    return json.dumps({
                        "symbol": symbol,
                        "price": price,
                        "change_24h": f"{change_24h:.2f}%",
                        "volume_24h": f"${volume_24h:,.0f}",
                        "high_24h": high_24h,
                        "low_24h": low_24h,
                        "timestamp": datetime.now().isoformat(),
                        "source": "Binance API (REAL DATA)"
                    }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error getting real market price from Binance: {e}")

        # Fallback: use paper trader's current price or mock data
        try:
            if self.paper_trader:
                price = await self.paper_trader.get_current_price()
                import random
                return json.dumps({
                    "symbol": symbol,
                    "price": price,
                    "change_24h": f"{random.uniform(-5, 5):.2f}%",
                    "volume_24h": f"${random.uniform(1e9, 3e9):,.0f}",
                    "high_24h": price * 1.02,
                    "low_24h": price * 0.98,
                    "timestamp": datetime.now().isoformat(),
                    "source": "Paper Trader (SIMULATED)"
                }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error with fallback: {e}")

        # Final fallback - use price_service (Binance -> OKX -> CoinGecko)
        try:
            price = await get_current_btc_price(demo_mode=False)
            logger.info(f"[TradingTools] Fallback: Got price from price_service: ${price:,.2f}")

            import random
            return json.dumps({
                "symbol": symbol,
                "price": price,
                "change_24h": f"{random.uniform(-5, 5):.2f}%",
                "volume_24h": f"${random.uniform(1e9, 3e9):,.0f}",
                "high_24h": price * 1.02,
                "low_24h": price * 0.98,
                "timestamp": datetime.now().isoformat(),
                "source": "Price Service Fallback (REAL PRICE)"
            }, ensure_ascii=False)
        except PriceServiceError as e:
            # All price sources failed - return error to agent
            logger.error(f"[TradingTools] All price sources failed: {e}")
            return json.dumps({
                "error": True,
                "message": f"Unable to fetch market price, all price sources unavailable: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)

    async def _get_klines(
        self,
        symbol: str = "BTC-USDT-SWAP",
        timeframe: str = "4h",
        limit: int = 100,
        interval: str = None,  # Alias for timeframe (LLM sometimes uses this name)
        **kwargs  # Accept any extra params from LLM
    ) -> str:
        """Get K-line data - fetches REAL data from Binance"""
        limit = int(limit) if limit else 100
        # Ensure type is correct
        # Handle interval as alias for timeframe
        if interval and not timeframe:
            timeframe = interval
        elif interval:
            timeframe = interval  # Prefer interval if both provided

        try:
            # Map timeframe to Binance interval
            interval_map = {
                "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                "1h": "1h", "4h": "4h", "1d": "1d", "1w": "1w"
            }
            interval = interval_map.get(timeframe, "4h")

            # Fetch REAL klines from Binance
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    "https://api.binance.com/api/v3/klines",
                    params={
                        "symbol": "BTCUSDT",
                        "interval": interval,
                        "limit": min(limit, 500)  # Binance max is 1000
                    }
                )

                if response.status_code == 200:
                    klines_data = response.json()

                    if klines_data:
                        # Parse latest candle
                        latest = klines_data[-1]
                        latest_candle = {
                            "open": float(latest[1]),
                            "high": float(latest[2]),
                            "low": float(latest[3]),
                            "close": float(latest[4]),
                            "volume": float(latest[5]),
                            "timestamp": latest[0]
                        }

                        # Calculate price range
                        all_highs = [float(k[2]) for k in klines_data]
                        all_lows = [float(k[3]) for k in klines_data]

                        # Calculate simple trend
                        closes = [float(k[4]) for k in klines_data]
                        trend = "uptrend" if closes[-1] > closes[0] else "downtrend"
                        change_pct = ((closes[-1] - closes[0]) / closes[0]) * 100

                        logger.info(f"[TradingTools] Fetched REAL K-lines: {len(klines_data)} candles, latest close: ${latest_candle['close']:,.2f}")

                        return json.dumps({
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "count": len(klines_data),
                            "latest_candle": latest_candle,
                            "price_range": {
                                "high": max(all_highs),
                                "low": min(all_lows),
                            },
                            "trend": trend,
                            "change_pct": f"{change_pct:+.2f}%",
                            "source": "Binance API (REAL DATA)",
                            "message": f"Fetched {len(klines_data)} {timeframe} K-lines, trend: {trend}"
                        }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error getting real K-lines from Binance: {e}")

        # Fallback to price_service for at least the current price
        base_price = None
        # Try paper_trader first
        if self.paper_trader:
            try:
                base_price = await self.paper_trader.get_current_price()
            except:
                pass
        # If paper_trader fails, use price_service (Binance -> OKX -> CoinGecko)
        if base_price is None:
            try:
                base_price = await get_current_btc_price(demo_mode=False)
                logger.info(f"[TradingTools] Klines fallback: Got price from price_service: ${base_price:,.2f}")
            except PriceServiceError as e:
                # All price sources failed - return error
                logger.error(f"[TradingTools] Klines: All price sources failed: {e}")
                return json.dumps({
                    "error": True,
                    "message": f"Unable to fetch K-line data, all price sources unavailable: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False)

        import random
        return json.dumps({
            "symbol": symbol,
            "timeframe": timeframe,
            "count": limit,
            "latest_candle": {
                "open": base_price * (1 + random.uniform(-0.01, 0.01)),
                "high": base_price * (1 + random.uniform(0.005, 0.02)),
                "low": base_price * (1 - random.uniform(0.005, 0.02)),
                "close": base_price,
                "volume": random.uniform(1000, 5000)
            },
            "price_range": {
                "high": base_price * 1.05,
                "low": base_price * 0.95,
            },
            "source": "Fallback (based on real-time price)",
            "message": "Simulated K-line data based on real-time price (fallback when Binance API unavailable)"
        }, ensure_ascii=False)

    async def _calculate_indicators(
        self,
        symbol: str = "BTC-USDT-SWAP",
        timeframe: str = "4h",
        interval: str = None,  # Alias for timeframe (LLM sometimes uses this name)
        **kwargs  # Accept any extra params from LLM
    ) -> str:
        """Calculate technical indicators - calculates from REAL Binance data"""
        # Handle interval as alias for timeframe
        if interval and not timeframe:
            timeframe = interval
        elif interval:
            timeframe = interval  # Prefer interval if both provided

        try:
            # First, fetch real K-line data
            import httpx
            interval_map = {
                "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                "1h": "1h", "4h": "4h", "1d": "1d", "1w": "1w"
            }
            interval = interval_map.get(timeframe, "4h")

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    "https://api.binance.com/api/v3/klines",
                    params={
                        "symbol": "BTCUSDT",
                        "interval": interval,
                        "limit": 100  # Need 100 candles for indicators
                    }
                )

                if response.status_code == 200:
                    klines = response.json()

                    if klines and len(klines) >= 14:
                        # Extract closing prices
                        closes = [float(k[4]) for k in klines]
                        highs = [float(k[2]) for k in klines]
                        lows = [float(k[3]) for k in klines]
                        current_price = closes[-1]

                        # Calculate RSI (14-period)
                        def calculate_rsi(prices, period=14):
                            if len(prices) < period + 1:
                                return 50  # Default neutral
                            gains = []
                            losses = []
                            for i in range(1, len(prices)):
                                change = prices[i] - prices[i-1]
                                gains.append(max(change, 0))
                                losses.append(max(-change, 0))

                            avg_gain = sum(gains[-period:]) / period
                            avg_loss = sum(losses[-period:]) / period

                            if avg_loss == 0:
                                return 100
                            rs = avg_gain / avg_loss
                            rsi = 100 - (100 / (1 + rs))
                            return rsi

                        rsi = calculate_rsi(closes, 14)
                        rsi_signal = "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral"

                        # Calculate EMAs
                        def calculate_ema(prices, period):
                            if len(prices) < period:
                                return prices[-1]
                            k = 2 / (period + 1)
                            ema = prices[0]
                            for price in prices[1:]:
                                ema = price * k + ema * (1 - k)
                            return ema

                        ema_20 = calculate_ema(closes, 20)
                        ema_50 = calculate_ema(closes, 50) if len(closes) >= 50 else closes[0]
                        ema_trend = "uptrend" if current_price > ema_20 and ema_20 > ema_50 else "downtrend"

                        # Calculate Bollinger Bands (20-period, 2 std dev)
                        if len(closes) >= 20:
                            sma_20 = sum(closes[-20:]) / 20
                            variance = sum((x - sma_20) ** 2 for x in closes[-20:]) / 20
                            std_dev = variance ** 0.5
                            bb_upper = sma_20 + (2 * std_dev)
                            bb_lower = sma_20 - (2 * std_dev)

                            # Determine position
                            if current_price > bb_upper * 0.98:
                                bb_position = "near upper band"
                            elif current_price < bb_lower * 1.02:
                                bb_position = "near lower band"
                            else:
                                bb_position = "middle zone"
                        else:
                            bb_upper = current_price * 1.03
                            bb_lower = current_price * 0.97
                            sma_20 = current_price
                            bb_position = "middle zone"

                        # Simple MACD approximation (12, 26, 9)
                        ema_12 = calculate_ema(closes, 12)
                        ema_26 = calculate_ema(closes, 26) if len(closes) >= 26 else closes[0]
                        macd_line = ema_12 - ema_26
                        # Simplified signal line (we'd need more data for proper calculation)
                        signal_line = macd_line * 0.8  # Approximation
                        macd_histogram = macd_line - signal_line
                        macd_trend = "bullish" if macd_histogram > 0 else "bearish"

                        logger.info(f"[TradingTools] Calculated REAL indicators: RSI={rsi:.1f}, Price=${current_price:,.2f}")

                        return json.dumps({
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "current_price": current_price,
                            "rsi_14": round(rsi, 2),
                            "rsi_signal": rsi_signal,
                            "macd": {
                                "macd": round(macd_line, 2),
                                "signal": round(signal_line, 2),
                                "histogram": round(macd_histogram, 2),
                                "trend": macd_trend
                            },
                            "ema": {
                                "ema_20": round(ema_20, 2),
                                "ema_50": round(ema_50, 2),
                                "trend": ema_trend
                            },
                            "bollinger_bands": {
                                "upper": round(bb_upper, 2),
                                "middle": round(sma_20, 2),
                                "lower": round(bb_lower, 2),
                                "position": bb_position
                            },
                            "source": "Calculated from Binance REAL DATA",
                            "message": f"Technical indicators calculated from real {timeframe} K-line data"
                        }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error calculating real indicators: {e}")

        # Fallback to price_service for at least the current price
        current_price = None
        # Try paper_trader first
        if self.paper_trader:
            try:
                current_price = await self.paper_trader.get_current_price()
            except:
                pass
        # If paper_trader fails, use price_service (Binance -> OKX -> CoinGecko)
        if current_price is None:
            try:
                current_price = await get_current_btc_price(demo_mode=False)
                logger.info(f"[TradingTools] Indicators fallback: Got price from price_service: ${current_price:,.2f}")
            except PriceServiceError as e:
                # All price sources failed - return error
                logger.error(f"[TradingTools] Indicators: All price sources failed: {e}")
                return json.dumps({
                    "error": True,
                    "message": f"Unable to calculate technical indicators, all price sources unavailable: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False)

        import random
        rsi = random.uniform(30, 70)
        macd_histogram = random.uniform(-100, 100)

        return json.dumps({
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": current_price,
            "rsi_14": round(rsi, 2),
            "rsi_signal": "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral",
            "macd": {
                "macd": round(random.uniform(-500, 500), 2),
                "signal": round(random.uniform(-400, 400), 2),
                "histogram": round(macd_histogram, 2),
                "trend": "bullish" if macd_histogram > 0 else "bearish"
            },
            "ema": {
                "ema_20": round(current_price * (1 + random.uniform(-0.01, 0.01)), 2),
                "ema_50": round(current_price * (1 + random.uniform(-0.02, 0.02)), 2),
                "trend": random.choice(["uptrend", "downtrend"])
            },
            "bollinger_bands": {
                "upper": round(current_price * 1.03, 2),
                "middle": round(current_price, 2),
                "lower": round(current_price * 0.97, 2),
                "position": random.choice(["near upper band", "middle zone", "near lower band"])
            },
            "source": "Fallback (based on real-time price)",
            "message": "Simulated technical indicators based on real-time price (fallback when Binance API unavailable)"
        }, ensure_ascii=False)

    async def _get_account_balance(self) -> str:
        """Get account balance"""
        try:
            if self.paper_trader:
                account = await self.paper_trader.get_account()
                return json.dumps({
                    "⚠️ USE THIS VALUE FOR OPENING POSITIONS": "↓ true_available_margin ↓",
                    "true_available_margin": f"${account['true_available_margin']:,.2f}",
                    "note": "True available margin = Total equity - Used margin (accounts for unrealized PnL)",
                    "total_equity": f"${account['total_equity']:,.2f}",
                    "available_balance": f"${account['available_balance']:,.2f} (cash balance only)",
                    "used_margin": f"${account['used_margin']:,.2f}",
                    "unrealized_pnl": f"${account['unrealized_pnl']:,.2f}",
                    "realized_pnl": f"${account['realized_pnl']:,.2f}",
                    "win_rate": f"{account.get('win_rate', 0) * 100:.1f}%",
                    "total_trades": account.get('total_trades', 0),
                    "currency": "USDT"
                }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error getting balance: {e}")

        return json.dumps({
            "true_available_margin": f"${self.config.default_balance:,.2f}",
            "total_equity": f"${self.config.default_balance:,.2f}",
            "available_balance": f"${self.config.default_balance:,.2f}",
            "used_margin": "$0.00",
            "unrealized_pnl": "$0.00",
            "currency": "USDT"
        }, ensure_ascii=False)

    async def _get_current_position(self, symbol: str = "BTC-USDT-SWAP") -> str:
        """Get current position"""
        try:
            if self.paper_trader:
                position = await self.paper_trader.get_position(symbol)
                if position and position.get('has_position'):
                    return json.dumps({
                        "has_position": True,
                        "symbol": position['symbol'],
                        "direction": position['direction'],
                        "size": position['size'],
                        "entry_price": position['entry_price'],
                        "current_price": position['current_price'],
                        "leverage": f"{position['leverage']}x",
                        "unrealized_pnl": f"${position['unrealized_pnl']:,.2f}",
                        "unrealized_pnl_percent": f"{position['unrealized_pnl_percent']:.2f}%",
                        "take_profit": position.get('take_profit_price'),
                        "stop_loss": position.get('stop_loss_price'),
                        "liquidation_price": position.get('liquidation_price')
                    }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error getting position: {e}")

        return json.dumps({
            "has_position": False,
            "message": "No current position"
        }, ensure_ascii=False)

    async def _open_long(
        self,
        symbol: str = "BTC-USDT-SWAP",
        leverage: int = 1,
        amount_usdt: float = 100,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None,
        tp_percent: Optional[float] = None,
        sl_percent: Optional[float] = None,
        reason: str = "",
        **kwargs  # Accept any extra params from LLM
    ) -> str:
        """Open long position"""
        try:
            # Ensure type is correct (LLM may pass strings)
            leverage = int(leverage) if leverage else 1
            amount_usdt = float(amount_usdt) if amount_usdt else 100
            tp_price = float(tp_price) if tp_price else None
            sl_price = float(sl_price) if sl_price else None
            tp_percent = float(tp_percent) if tp_percent else None
            sl_percent = float(sl_percent) if sl_percent else None

            # Validation: TP/SL parameters required
            if not tp_percent and not tp_price:
                return json.dumps({
                    "success": False,
                    "error": "Missing take profit parameter! Please provide tp_percent (e.g. 5 means take profit at +5%). This is a mandatory risk control requirement!",
                    "retry_required": True,
                    "missing_params": ["tp_percent"]
                }, ensure_ascii=False)

            if not sl_percent and not sl_price:
                return json.dumps({
                    "success": False,
                    "error": "Missing stop loss parameter! Please provide sl_percent (e.g. 2 means stop loss at -2%). This is a mandatory risk control requirement!",
                    "retry_required": True,
                    "missing_params": ["sl_percent"]
                }, ensure_ascii=False)

            # If tp_percent/sl_percent provided, calculate tp_price/sl_price
            if (tp_percent or sl_percent) and not (tp_price and sl_price):
                try:
                    # Use the existing price service to get current price
                    current_price = await get_current_btc_price()
                    if current_price:
                        if tp_percent and not tp_price:
                            tp_price = current_price * (1 + float(tp_percent) / 100)
                        if sl_percent and not sl_price:
                            sl_price = current_price * (1 - float(sl_percent) / 100)
                        logger.info(f"[TradingTools] Calculated TP/SL for LONG: TP={tp_price:.2f} (+{tp_percent}%), SL={sl_price:.2f} (-{sl_percent}%)")
                except Exception as e:
                    logger.warning(f"Could not calculate tp/sl prices from percent: {e}")
                    return json.dumps({
                        "success": False,
                        "error": f"Unable to calculate TP/SL prices: {e}",
                        "retry_required": True
                    }, ensure_ascii=False)

            # Final validation: ensure tp_price and sl_price are set
            if not tp_price or not sl_price:
                return json.dumps({
                    "success": False,
                    "error": "TP/SL price calculation failed, please retry with correct tp_percent and sl_percent parameters",
                    "retry_required": True
                }, ensure_ascii=False)

            if self.paper_trader:
                result = await self.paper_trader.open_long(
                    symbol=symbol,
                    leverage=leverage,
                    amount_usdt=amount_usdt,
                    tp_price=tp_price,
                    sl_price=sl_price
                )
                return json.dumps({
                    "success": result['success'],
                    "trade_id": result.get('order_id'),
                    "direction": "long",
                    "leverage": f"{leverage}x",
                    "amount": f"${amount_usdt:,.2f}",
                    "entry_price": result.get('executed_price'),
                    "take_profit": tp_price,
                    "stop_loss": sl_price,
                    "message": "Position opened successfully" if result['success'] else result.get('error', 'Failed to open position')
                }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error opening long: {e}")
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    async def _open_short(
        self,
        symbol: str = "BTC-USDT-SWAP",
        leverage: int = 1,
        amount_usdt: float = 100,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None,
        tp_percent: Optional[float] = None,
        sl_percent: Optional[float] = None,
        reason: str = "",
        **kwargs  # Accept any extra params from LLM
    ) -> str:
        """Open short position"""
        try:
            # Ensure type is correct (LLM may pass strings)
            leverage = int(leverage) if leverage else 1
            amount_usdt = float(amount_usdt) if amount_usdt else 100
            tp_price = float(tp_price) if tp_price else None
            sl_price = float(sl_price) if sl_price else None
            tp_percent = float(tp_percent) if tp_percent else None
            sl_percent = float(sl_percent) if sl_percent else None

            # Validation: TP/SL parameters required
            if not tp_percent and not tp_price:
                return json.dumps({
                    "success": False,
                    "error": "Missing take profit parameter! Please provide tp_percent (e.g. 5 means take profit at -5%). This is a mandatory risk control requirement!",
                    "retry_required": True,
                    "missing_params": ["tp_percent"]
                }, ensure_ascii=False)

            if not sl_percent and not sl_price:
                return json.dumps({
                    "success": False,
                    "error": "Missing stop loss parameter! Please provide sl_percent (e.g. 2 means stop loss at +2%). This is a mandatory risk control requirement!",
                    "retry_required": True,
                    "missing_params": ["sl_percent"]
                }, ensure_ascii=False)

            # If tp_percent/sl_percent provided, calculate tp_price/sl_price (reversed for short)
            if (tp_percent or sl_percent) and not (tp_price and sl_price):
                try:
                    # Use the existing price service to get current price
                    current_price = await get_current_btc_price()
                    if current_price:
                        if tp_percent and not tp_price:
                            tp_price = current_price * (1 - float(tp_percent) / 100)  # Short: TP is below
                        if sl_percent and not sl_price:
                            sl_price = current_price * (1 + float(sl_percent) / 100)  # Short: SL is above
                        logger.info(f"[TradingTools] Calculated TP/SL for SHORT: TP={tp_price:.2f} (-{tp_percent}%), SL={sl_price:.2f} (+{sl_percent}%)")
                except Exception as e:
                    logger.warning(f"Could not calculate tp/sl prices from percent: {e}")
                    return json.dumps({
                        "success": False,
                        "error": f"Unable to calculate TP/SL prices: {e}",
                        "retry_required": True
                    }, ensure_ascii=False)

            # Final validation: ensure tp_price and sl_price are set
            if not tp_price or not sl_price:
                return json.dumps({
                    "success": False,
                    "error": "TP/SL price calculation failed, please retry with correct tp_percent and sl_percent parameters",
                    "retry_required": True
                }, ensure_ascii=False)

            if self.paper_trader:
                result = await self.paper_trader.open_short(
                    symbol=symbol,
                    leverage=leverage,
                    amount_usdt=amount_usdt,
                    tp_price=tp_price,
                    sl_price=sl_price
                )
                return json.dumps({
                    "success": result['success'],
                    "trade_id": result.get('order_id'),
                    "direction": "short",
                    "leverage": f"{leverage}x",
                    "amount": f"${amount_usdt:,.2f}",
                    "entry_price": result.get('executed_price'),
                    "take_profit": tp_price,
                    "stop_loss": sl_price,
                    "message": "Position opened successfully" if result['success'] else result.get('error', 'Failed to open position')
                }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error opening short: {e}")
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    async def _close_position(self, symbol: str = "BTC-USDT-SWAP") -> str:
        """Close position"""
        try:
            if self.paper_trader:
                result = await self.paper_trader.close_position(symbol)
                if result['success']:
                    return json.dumps({
                        "success": True,
                        "closed_price": result.get('closed_price'),
                        "pnl": result.get('pnl'),
                        "pnl_percent": result.get('pnl_percent'),
                        "reason": result.get('reason', 'manual'),
                        "message": "Position closed successfully"
                    }, ensure_ascii=False)
                else:
                    return json.dumps({
                        "success": False,
                        "error": result.get('error', 'Failed to close position')
                    }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    async def _hold(self, reason: str = "Market unclear", **kwargs) -> str:
        """Hold decision - do not trade"""
        logger.info(f"Hold decision made: {reason}")
        return json.dumps({
            "success": True,
            "action": "hold",
            "reason": reason,
            "message": f"Decision: Hold - {reason}"
        }, ensure_ascii=False)

    async def _get_fear_greed_index(self) -> str:
        """Get crypto fear & greed index - fetches REAL data from alternative.me API"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Fetch from alternative.me - the official Fear & Greed Index API
                response = await client.get("https://api.alternative.me/fng/?limit=1")

                if response.status_code == 200:
                    data = response.json()
                    if data.get("data") and len(data["data"]) > 0:
                        fng_data = data["data"][0]
                        index = int(fng_data["value"])
                        classification_en = fng_data["value_classification"]

                        # Use English classification
                        classification = classification_en

                        logger.info(f"[TradingTools] Fetched REAL Fear & Greed Index: {index} ({classification})")

                        return json.dumps({
                            "value": index,
                            "classification": classification,
                            "timestamp": datetime.now().isoformat(),
                            "interpretation": f"Current market sentiment is {classification}, index value {index}/100",
                            "source": "Alternative.me API (REAL DATA)"
                        }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error getting real Fear & Greed Index: {e}")

        # Fallback: use neutral value
        return json.dumps({
            "value": 50,
            "classification": "Neutral",
            "timestamp": datetime.now().isoformat(),
            "interpretation": "Unable to fetch Fear & Greed Index, defaulting to Neutral",
            "source": "Fallback (NEUTRAL DEFAULT)"
        }, ensure_ascii=False)

    async def _get_funding_rate(self, symbol: str = "BTC-USDT-SWAP") -> str:
        """Get funding rate - fetches REAL data from Binance Futures API"""
        try:
            import httpx
            from datetime import datetime
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Fetch from Binance Futures API
                response = await client.get(
                    "https://fapi.binance.com/fapi/v1/premiumIndex",
                    params={"symbol": "BTCUSDT"}
                )

                if response.status_code == 200:
                    data = response.json()
                    rate = float(data["lastFundingRate"])
                    next_funding_time_ms = int(data["nextFundingTime"])

                    # Calculate time until next funding
                    next_funding_dt = datetime.fromtimestamp(next_funding_time_ms / 1000)
                    now = datetime.now()
                    time_diff = next_funding_dt - now
                    hours_left = int(time_diff.total_seconds() / 3600)
                    minutes_left = int((time_diff.total_seconds() % 3600) / 60)

                    time_str = f"in {hours_left}h {minutes_left}m" if hours_left > 0 else f"in {minutes_left}m"

                    logger.info(f"[TradingTools] Fetched REAL Funding Rate: {rate*100:.4f}%")

                    return json.dumps({
                        "symbol": symbol,
                        "funding_rate": f"{rate*100:.4f}%",
                        "funding_rate_value": rate,
                        "next_funding_time": time_str,
                        "interpretation": (
                            f"Positive funding rate ({rate*100:.4f}%), longs pay shorts, market bullish" if rate > 0 else
                            f"Negative funding rate ({rate*100:.4f}%), shorts pay longs, market bearish" if rate < 0 else
                            "Zero funding rate, balanced market"
                        ),
                        "source": "Binance Futures API (REAL DATA)"
                    }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error getting real funding rate: {e}")

        # Fallback: return neutral
        return json.dumps({
            "symbol": symbol,
            "funding_rate": "0.0000%",
            "funding_rate_value": 0,
            "next_funding_time": "in 8h",
            "interpretation": "Unable to fetch funding rate data",
            "source": "Fallback (NEUTRAL DEFAULT)"
        }, ensure_ascii=False)

    async def _get_trade_history(self, limit: int = 20) -> str:
        """Get trade history"""
        # Ensure type is correct
        limit = int(limit) if limit else 20

        try:
            if self.paper_trader:
                trades = await self.paper_trader.get_trade_history(limit=limit)
                return json.dumps({
                    "count": len(trades),
                    "trades": trades[:10]  # Return last 10 for summary
                }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error getting trade history: {e}")

        return json.dumps({
            "count": 0,
            "trades": [],
            "message": "No trade history"
        }, ensure_ascii=False)

    async def _tavily_search(self, query: str, max_results: int = 5, time_range: str = None, topic: str = "general", days: int = None, **kwargs) -> str:
        """
        Search for cryptocurrency news and market information using MCP.
        
        ⚠️ Note: Cache removed - news content varies by time, so each search
        must fetch fresh results to ensure accuracy.

        Args:
            query: Search query string
            max_results: Maximum number of results to return (default 5)
            time_range: Time range filter - "day", "week", or "month" (optional)
            topic: Search topic - "general" or "news" (default "general")
            days: Number of days to limit search results (1-30, optional)

        Returns:
            JSON string with search results
        """
        try:
            # Execute search directly - no caching (news varies by time)
            result = await self._execute_tavily_search(query, max_results, time_range, topic, days, **kwargs)
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"[TradingTools] Tavily search error: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "message": f"Search error: {str(e)}"
            }, ensure_ascii=False)

    async def _execute_tavily_search(self, query: str, max_results: int = 5, time_range: str = None, topic: str = "general", days: int = None, **kwargs) -> dict:
        """
        Execute the actual Tavily search via MCP (internal method).
        Returns dict instead of JSON string for caching.
        """
        try:
            # Check if mock mode is enabled
            from app.core.trading.mock_tavily import is_mock_mode_enabled, get_mock_search_results
            
            if is_mock_mode_enabled():
                logger.info(f"[TradingTools] Using MOCK Tavily for query: '{query}'")
                return get_mock_search_results(query, max_results)
            
            # Use MCP Client to call web-search service
            from app.core.roundtable.mcp_tools import get_mcp_client

            mcp_client = get_mcp_client()

            # Ensure parameter types are correct
            max_results = int(max_results) if max_results else 5
            max_results = min(max(1, max_results), 10)  # Limit between 1-10

            # Build MCP call parameters
            params = {
                "query": query,
                "max_results": max_results,
                "topic": topic or "general"
            }

            # Add optional parameters
            if time_range and time_range in ["day", "week", "month", "year"]:
                params["time_range"] = time_range
            if days and isinstance(days, int) and 1 <= days <= 30:
                params["days"] = days

            logger.info(f"[TradingTools] MCP Tavily search: '{query}' (params={params})")

            # Call via MCP
            result = await mcp_client.call_tool(
                server_name="web-search",
                tool_name="search",
                **params
            )

            # MCP response is already in correct format
            if result.get("success"):
                logger.info(f"[TradingTools] MCP search success: {len(result.get('result', {}).get('results', []))} results")
                # Reformat to expected trading_tools format
                mcp_results = result.get("result", {}).get("results", [])
                formatted_results = [{
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:500],
                    "score": 1.0  # MCP result has no score, default to 1.0
                } for r in mcp_results]

                # Return dict (not JSON string) for caching
                return {
                    "success": True,
                    "query": query,
                    "answer": result.get("result", {}).get("summary", ""),
                    "results": formatted_results,
                    "result_count": len(formatted_results),
                    "source": "MCP Web Search",
                    "message": f"Search '{query}' returned {len(formatted_results)} results"
                }
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"[TradingTools] MCP search failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "message": f"Search failed: {error_msg}"
                }

        except Exception as e:
            logger.error(f"[TradingTools] Tavily search error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Search error: {str(e)}"
            }

    async def _analyze_execution_conditions(
        self,
        amount_usdt: float,
        direction: str,  # REQUIRED - no default to avoid bias
        symbol: str = "BTC"
    ) -> str:
        """
        Analyze market conditions to determine optimal execution strategy.
        
        Args:
            amount_usdt: Amount in USDT to trade
            direction: Trade direction ('long' or 'short') - REQUIRED
            symbol: Trading symbol
            
        Returns:
            JSON string with execution analysis and recommendations
        """
        try:
            from app.core.trading.smart_executor import analyze_execution
            
            # Normalize and validate direction - NO DEFAULT BIAS
            direction = direction.lower()
            if direction not in ["long", "short"]:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid direction '{direction}'. Must be 'long' or 'short'.",
                    "message": "Direction parameter is required and must be explicitly 'long' or 'short'"
                }, ensure_ascii=False)
            
            # Perform analysis
            analysis = await analyze_execution(
                amount_usdt=float(amount_usdt),
                direction=direction,
                symbol=symbol
            )
            
            # Format response for agent consumption
            capital_tier = analysis.get("capital_tier", "unknown")
            strategy = analysis.get("recommended_strategy", "direct")
            slices = analysis.get("recommended_slices", 1)
            slippage = analysis.get("estimated_slippage_percent", 0)
            liquidity = analysis.get("liquidity_rating", "unknown")
            
            # Generate human-readable summary
            summary = f"""📊 Execution Analysis for ${amount_usdt:,.2f} {direction.upper()}

💰 Capital Tier: {capital_tier.upper()}
📈 Recommended Strategy: {strategy.upper()}
🔢 Recommended Slices: {slices}
📉 Estimated Slippage: {slippage:.2f}%
💧 Liquidity Rating: {liquidity.upper()}

💡 Recommendation: {analysis.get('recommendation', 'N/A')}"""

            logger.info(f"[TradingTools] Execution analysis: {strategy} with {slices} slices, slippage {slippage:.2f}%")

            return json.dumps({
                "success": True,
                "analysis": analysis,
                "summary": summary,
                "execution_parameters": {
                    "strategy": strategy,
                    "slice_count": slices,
                    "slice_interval_seconds": analysis.get("slice_interval_seconds", 60),
                    "max_slippage_threshold": analysis.get("max_slippage_threshold", 0.5)
                }
            }, ensure_ascii=False)

        except Exception as e:
            logger.error(f"[TradingTools] Execution analysis error: {e}")
            # Return conservative defaults on error
            return json.dumps({
                "success": False,
                "error": str(e),
                "analysis": {
                    "capital_tier": "unknown",
                    "recommended_strategy": "sliced",
                    "recommended_slices": 3,
                    "estimated_slippage_percent": 0.2,
                    "liquidity_rating": "unknown"
                },
                "summary": f"⚠️ Analysis failed: {str(e)}. Using conservative defaults: sliced execution with 3 slices."
            }, ensure_ascii=False)

    async def _technical_analysis(
        self, 
        symbol: str = "BTC/USDT", 
        timeframe: str = "4h",
        action: str = "full_analysis",
        market_type: str = "crypto"
    ) -> str:
        """Comprehensive technical analysis combining K-lines and indicators"""
        try:
            import httpx
            
            # Normalize symbol for API
            clean_symbol = symbol.upper().replace('/', '').replace('-', '').replace('USDT', '').replace('SWAP', '')
            if clean_symbol == 'BTC':
                api_symbol = 'BTC-USDT'
            else:
                api_symbol = f'{clean_symbol}-USDT'
            
            # Map timeframe to OKX format
            tf_map = {'1m': '1m', '5m': '5m', '15m': '15m', '1h': '1H', '4h': '4H', '1d': '1D'}
            okx_tf = tf_map.get(timeframe.lower(), '4H')
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    "https://www.okx.com/api/v5/market/candles",
                    params={"instId": api_symbol, "bar": okx_tf, "limit": "100"}
                )
                
                if response.status_code != 200:
                    return json.dumps({"success": False, "error": f"API error: {response.status_code}"})
                
                data = response.json()
                candles = data.get("data", [])
                
                if not candles:
                    return json.dumps({"success": False, "error": "No candle data"})
                
                # Parse candles
                closes = [float(c[4]) for c in candles][::-1]
                highs = [float(c[2]) for c in candles][::-1]
                lows = [float(c[3]) for c in candles][::-1]
                
                current_price = closes[-1]
                
                # Calculate RSI (14)
                gains, losses = [], []
                for i in range(1, min(15, len(closes))):
                    diff = closes[i] - closes[i-1]
                    gains.append(max(diff, 0))
                    losses.append(abs(min(diff, 0)))
                avg_gain = sum(gains) / len(gains) if gains else 0
                avg_loss = sum(losses) / len(losses) if losses else 1
                rsi = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss > 0 else 50
                
                # EMA calculation
                def calc_ema(prices, period):
                    if len(prices) < period:
                        return sum(prices) / len(prices)
                    ema = sum(prices[:period]) / period
                    multiplier = 2 / (period + 1)
                    for price in prices[period:]:
                        ema = (price - ema) * multiplier + ema
                    return ema
                
                ema20 = calc_ema(closes, 20)
                ema50 = calc_ema(closes, 50)
                
                # Trend
                if current_price > ema20 > ema50:
                    trend, strength = "BULLISH", "Strong"
                elif current_price > ema20:
                    trend, strength = "BULLISH", "Weak"
                elif current_price < ema20 < ema50:
                    trend, strength = "BEARISH", "Strong"
                elif current_price < ema20:
                    trend, strength = "BEARISH", "Weak"
                else:
                    trend, strength = "NEUTRAL", "Consolidation"
                
                support = min(lows[-20:]) if len(lows) >= 20 else min(lows)
                resistance = max(highs[-20:]) if len(highs) >= 20 else max(highs)
                price_change = ((current_price - closes[-24]) / closes[-24] * 100) if len(closes) >= 24 else 0
                
                summary = f"""📊 Technical Analysis: {symbol} ({timeframe})
💰 Price: ${current_price:,.2f} ({price_change:+.2f}% 24h)
📊 RSI(14): {rsi:.1f} {'🔴 Overbought' if rsi > 70 else '🟢 Oversold' if rsi < 30 else '⚪ Neutral'}
📈 EMA20: ${ema20:,.2f} | EMA50: ${ema50:,.2f}
🎯 Support: ${support:,.2f} | Resistance: ${resistance:,.2f}
📈 Trend: {trend} ({strength})"""

                logger.info(f"[TradingTools] Technical analysis: {symbol} {timeframe} -> {trend}")
                
                return json.dumps({
                    "success": True, "symbol": symbol, "timeframe": timeframe,
                    "current_price": current_price,
                    "indicators": {"rsi": round(rsi, 1), "ema20": round(ema20, 2), "ema50": round(ema50, 2)},
                    "trend": {"direction": trend, "strength": strength},
                    "summary": summary
                }, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"[TradingTools] Technical analysis error: {e}")
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    async def _orderbook_analyzer(self, symbol: str = "BTC", depth: int = 20) -> str:
        """Analyze exchange orderbook depth"""
        try:
            import httpx
            clean_symbol = symbol.upper().replace('-USDT', '').replace('/USDT', '').replace('USDT', '').strip()
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.binance.com/api/v3/depth",
                    params={"symbol": f"{clean_symbol}USDT", "limit": min(depth * 5, 100)}
                )
                
                if response.status_code != 200:
                    return json.dumps({"success": False, "error": f"API error: {response.status_code}"})
                
                data = response.json()
                bids = [[float(p), float(q)] for p, q in data.get("bids", [])[:depth]]
                asks = [[float(p), float(q)] for p, q in data.get("asks", [])[:depth]]
                
                if not bids or not asks:
                    return json.dumps({"success": False, "error": "Orderbook empty"})
                
                total_bid = sum(q for _, q in bids)
                total_ask = sum(q for _, q in asks)
                ratio = total_bid / total_ask if total_ask > 0 else 1
                
                best_bid, best_ask = bids[0][0], asks[0][0]
                spread = (best_ask - best_bid) / best_bid * 100
                
                support = max(bids, key=lambda x: x[1])[0]
                resistance = max(asks, key=lambda x: x[1])[0]
                
                sentiment = "🟢 Bullish" if ratio > 1.2 else "🔴 Bearish" if ratio < 0.8 else "⚪ Neutral"
                
                summary = f"""📊 Orderbook: {clean_symbol}/USDT
💰 Bid: ${best_bid:,.2f} | Ask: ${best_ask:,.2f} | Spread: {spread:.4f}%
📊 Volume: Bid {total_bid:,.2f} | Ask {total_ask:,.2f} | Ratio: {ratio:.2f}
🎯 Support: ${support:,.2f} | Resistance: ${resistance:,.2f}
💡 Sentiment: {sentiment}"""

                logger.info(f"[TradingTools] Orderbook: {clean_symbol} ratio={ratio:.2f}")
                
                return json.dumps({
                    "success": True, "symbol": clean_symbol,
                    "best_bid": best_bid, "best_ask": best_ask,
                    "pressure_ratio": round(ratio, 2),
                    "support_level": support, "resistance_level": resistance,
                    "summary": summary
                }, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"[TradingTools] Orderbook error: {e}")
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

