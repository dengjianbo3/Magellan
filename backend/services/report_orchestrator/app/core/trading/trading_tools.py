"""
Trading Tools for Agents

Provides tools that trading agents can use to analyze markets and execute trades.
"""

import logging
import os
from datetime import datetime
from typing import Optional, Dict, List, Any
import json

try:
    import pandas as pd
    import numpy as np
except ImportError:
    pd = None
    np = None

from app.core.roundtable.tool import FunctionTool
from app.models.trading_models import (
    MarketData, TechnicalIndicators, Position, AccountBalance
)
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
            description=f"获取当前市场价格和24小时行情数据，包括价格、涨跌幅、成交量等",
            parameters_schema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": f"交易对，默认{self.config.symbol}",
                        "default": self.config.symbol
                    }
                }
            },
            func=self._get_market_price
        )

        self._tools['get_klines'] = FunctionTool(
            name="get_klines",
            description="获取K线数据用于技术分析，支持不同时间周期",
            parameters_schema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": f"交易对，默认{self.config.symbol}",
                        "default": self.config.symbol
                    },
                    "timeframe": {
                        "type": "string",
                        "description": "时间周期: 1m, 5m, 15m, 1h, 4h, 1d",
                        "default": "4h"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "获取的K线数量",
                        "default": 100
                    }
                }
            },
            func=self._get_klines
        )

        self._tools['calculate_technical_indicators'] = FunctionTool(
            name="calculate_technical_indicators",
            description="计算技术指标：RSI、MACD、布林带、EMA等",
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
            description="获取账户余额和可用资金",
            parameters_schema={"type": "object", "properties": {}},
            func=self._get_account_balance
        )

        self._tools['get_current_position'] = FunctionTool(
            name="get_current_position",
            description="获取当前持仓信息，包括方向、杠杆、盈亏等",
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
            description=f"开多仓（做多）。必须指定杠杆、金额、止盈百分比和止损百分比。止盈止损是强制要求的风控参数！",
            parameters_schema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "default": self.config.symbol
                    },
                    "leverage": {
                        "type": "integer",
                        "description": f"杠杆倍数(1-{self.config.max_leverage})",
                        "minimum": 1,
                        "maximum": self.config.max_leverage
                    },
                    "amount_usdt": {
                        "type": "number",
                        "description": "投入的USDT金额"
                    },
                    "tp_percent": {
                        "type": "number",
                        "description": "止盈百分比，例如5表示涨5%止盈（必填）",
                        "minimum": 0.5,
                        "maximum": 50
                    },
                    "sl_percent": {
                        "type": "number",
                        "description": "止损百分比，例如2表示跌2%止损（必填）",
                        "minimum": 0.5,
                        "maximum": 20
                    },
                    "reason": {
                        "type": "string",
                        "description": "开仓理由"
                    }
                },
                "required": ["leverage", "amount_usdt", "tp_percent", "sl_percent"]
            },
            func=self._open_long
        )

        self._tools['open_short'] = FunctionTool(
            name="open_short",
            description=f"开空仓（做空）。必须指定杠杆、金额、止盈百分比和止损百分比。止盈止损是强制要求的风控参数！",
            parameters_schema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "default": self.config.symbol
                    },
                    "leverage": {
                        "type": "integer",
                        "description": f"杠杆倍数(1-{self.config.max_leverage})",
                        "minimum": 1,
                        "maximum": self.config.max_leverage
                    },
                    "amount_usdt": {
                        "type": "number",
                        "description": "投入的USDT金额"
                    },
                    "tp_percent": {
                        "type": "number",
                        "description": "止盈百分比，例如5表示跌5%止盈（必填）",
                        "minimum": 0.5,
                        "maximum": 50
                    },
                    "sl_percent": {
                        "type": "number",
                        "description": "止损百分比，例如2表示涨2%止损（必填）",
                        "minimum": 0.5,
                        "maximum": 20
                    },
                    "reason": {
                        "type": "string",
                        "description": "开仓理由"
                    }
                },
                "required": ["leverage", "amount_usdt", "tp_percent", "sl_percent"]
            },
            func=self._open_short
        )

        self._tools['close_position'] = FunctionTool(
            name="close_position",
            description="平仓当前持仓",
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

        # Hold Decision Tool - 观望决策
        self._tools['hold'] = FunctionTool(
            name="hold",
            description="决定观望，不进行任何交易操作。当市场不明朗或风险过高时调用此工具",
            parameters_schema={
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "观望的原因说明"
                    }
                },
                "required": ["reason"]
            },
            func=self._hold
        )

        # Analysis Tools
        self._tools['get_fear_greed_index'] = FunctionTool(
            name="get_fear_greed_index",
            description="获取加密货币恐慌贪婪指数，反映市场情绪",
            parameters_schema={"type": "object", "properties": {}},
            func=self._get_fear_greed_index
        )

        self._tools['get_funding_rate'] = FunctionTool(
            name="get_funding_rate",
            description="获取资金费率，反映多空力量对比",
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
            description="获取历史交易记录",
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
            description="使用Tavily搜索引擎搜索加密货币相关新闻和市场信息，获取最新的市场动态、重大事件、监管消息等",
            parameters_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询词，如'BTC news today'或'Bitcoin regulation 2024'"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "返回结果数量，默认5条",
                        "default": 5
                    },
                    "time_range": {
                        "type": "string",
                        "description": "时间范围: day(最近24小时), week(最近一周), month(最近一月)",
                        "enum": ["day", "week", "month"],
                        "default": None
                    },
                    "topic": {
                        "type": "string",
                        "description": "搜索主题: general(通用), news(新闻)",
                        "enum": ["general", "news"],
                        "default": "general"
                    },
                    "days": {
                        "type": "integer",
                        "description": "限制搜索结果的天数范围(1-30)",
                        "default": None
                    }
                },
                "required": ["query"]
            },
            func=self._tavily_search
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
            'tavily_search'  # Added web search capability
        ]
        return [self._tools[name] for name in analysis_tool_names if name in self._tools]

    def get_execution_tools(self) -> List[FunctionTool]:
        """Get only execution tools (including hold for decision making)"""
        exec_tool_names = ['open_long', 'open_short', 'close_position', 'hold']
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
                "message": f"无法获取市场价格，所有价格源均不可用: {str(e)}",
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
        # 确保类型正确
        limit = int(limit) if limit else 100
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
                        trend = "上涨" if closes[-1] > closes[0] else "下跌"
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
                            "message": f"获取到{len(klines_data)}根{timeframe}级别K线，趋势{trend}"
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
                    "message": f"无法获取K线数据，所有价格源均不可用: {str(e)}",
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
            "source": "Fallback (基于实时价格)",
            "message": "基于实时价格的模拟K线数据（Binance API不可用时的备选）"
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
                        rsi_signal = "超买" if rsi > 70 else "超卖" if rsi < 30 else "中性"

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
                        ema_trend = "上升趋势" if current_price > ema_20 and ema_20 > ema_50 else "下降趋势"

                        # Calculate Bollinger Bands (20-period, 2 std dev)
                        if len(closes) >= 20:
                            sma_20 = sum(closes[-20:]) / 20
                            variance = sum((x - sma_20) ** 2 for x in closes[-20:]) / 20
                            std_dev = variance ** 0.5
                            bb_upper = sma_20 + (2 * std_dev)
                            bb_lower = sma_20 - (2 * std_dev)

                            # Determine position
                            if current_price > bb_upper * 0.98:
                                bb_position = "上轨附近"
                            elif current_price < bb_lower * 1.02:
                                bb_position = "下轨附近"
                            else:
                                bb_position = "中轨区域"
                        else:
                            bb_upper = current_price * 1.03
                            bb_lower = current_price * 0.97
                            sma_20 = current_price
                            bb_position = "中轨区域"

                        # Simple MACD approximation (12, 26, 9)
                        ema_12 = calculate_ema(closes, 12)
                        ema_26 = calculate_ema(closes, 26) if len(closes) >= 26 else closes[0]
                        macd_line = ema_12 - ema_26
                        # Simplified signal line (we'd need more data for proper calculation)
                        signal_line = macd_line * 0.8  # Approximation
                        macd_histogram = macd_line - signal_line
                        macd_trend = "看涨" if macd_histogram > 0 else "看跌"

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
                            "message": f"基于真实{timeframe}级别K线计算的技术指标"
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
                    "message": f"无法计算技术指标，所有价格源均不可用: {str(e)}",
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
            "rsi_signal": "超买" if rsi > 70 else "超卖" if rsi < 30 else "中性",
            "macd": {
                "macd": round(random.uniform(-500, 500), 2),
                "signal": round(random.uniform(-400, 400), 2),
                "histogram": round(macd_histogram, 2),
                "trend": "看涨" if macd_histogram > 0 else "看跌"
            },
            "ema": {
                "ema_20": round(current_price * (1 + random.uniform(-0.01, 0.01)), 2),
                "ema_50": round(current_price * (1 + random.uniform(-0.02, 0.02)), 2),
                "trend": random.choice(["上升趋势", "下降趋势"])
            },
            "bollinger_bands": {
                "upper": round(current_price * 1.03, 2),
                "middle": round(current_price, 2),
                "lower": round(current_price * 0.97, 2),
                "position": random.choice(["上轨附近", "中轨区域", "下轨附近"])
            },
            "source": "Fallback (基于实时价格)",
            "message": "基于实时价格的模拟技术指标（Binance API不可用时的备选）"
        }, ensure_ascii=False)

    async def _get_account_balance(self) -> str:
        """Get account balance"""
        try:
            if self.paper_trader:
                account = await self.paper_trader.get_account()
                return json.dumps({
                    "total_equity": f"${account['total_equity']:,.2f}",
                    "available_balance": f"${account['available_balance']:,.2f}",
                    "used_margin": f"${account['used_margin']:,.2f}",
                    "unrealized_pnl": f"${account['unrealized_pnl']:,.2f}",
                    "realized_pnl": f"${account['realized_pnl']:,.2f}",
                    "win_rate": f"{account['win_rate'] * 100:.1f}%",
                    "total_trades": account['total_trades'],
                    "currency": "USDT"
                }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error getting balance: {e}")

        return json.dumps({
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
            "message": "当前无持仓"
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
            # 确保类型正确（LLM可能传入字符串）
            leverage = int(leverage) if leverage else 1
            amount_usdt = float(amount_usdt) if amount_usdt else 100
            tp_price = float(tp_price) if tp_price else None
            sl_price = float(sl_price) if sl_price else None
            tp_percent = float(tp_percent) if tp_percent else None
            sl_percent = float(sl_percent) if sl_percent else None

            # 校验：必须提供止盈止损参数
            if not tp_percent and not tp_price:
                return json.dumps({
                    "success": False,
                    "error": "缺少止盈参数！请提供 tp_percent（止盈百分比，如5表示涨5%止盈）。这是风控强制要求！",
                    "retry_required": True,
                    "missing_params": ["tp_percent"]
                }, ensure_ascii=False)

            if not sl_percent and not sl_price:
                return json.dumps({
                    "success": False,
                    "error": "缺少止损参数！请提供 sl_percent（止损百分比，如2表示跌2%止损）。这是风控强制要求！",
                    "retry_required": True,
                    "missing_params": ["sl_percent"]
                }, ensure_ascii=False)

            # If tp_percent/sl_percent provided, calculate tp_price/sl_price
            if (tp_percent or sl_percent) and not (tp_price and sl_price):
                try:
                    from .market_data import MarketDataService
                    market_service = MarketDataService()
                    current_price = await market_service.get_current_price(symbol)
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
                        "error": f"无法计算止盈止损价格: {e}",
                        "retry_required": True
                    }, ensure_ascii=False)

            # 最终校验：确保 tp_price 和 sl_price 都已设置
            if not tp_price or not sl_price:
                return json.dumps({
                    "success": False,
                    "error": "止盈止损价格计算失败，请重新调用并提供正确的 tp_percent 和 sl_percent 参数",
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
                    "message": "开仓成功" if result['success'] else result.get('error', '开仓失败')
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
            # 确保类型正确（LLM可能传入字符串）
            leverage = int(leverage) if leverage else 1
            amount_usdt = float(amount_usdt) if amount_usdt else 100
            tp_price = float(tp_price) if tp_price else None
            sl_price = float(sl_price) if sl_price else None
            tp_percent = float(tp_percent) if tp_percent else None
            sl_percent = float(sl_percent) if sl_percent else None

            # 校验：必须提供止盈止损参数
            if not tp_percent and not tp_price:
                return json.dumps({
                    "success": False,
                    "error": "缺少止盈参数！请提供 tp_percent（止盈百分比，如5表示跌5%止盈）。这是风控强制要求！",
                    "retry_required": True,
                    "missing_params": ["tp_percent"]
                }, ensure_ascii=False)

            if not sl_percent and not sl_price:
                return json.dumps({
                    "success": False,
                    "error": "缺少止损参数！请提供 sl_percent（止损百分比，如2表示涨2%止损）。这是风控强制要求！",
                    "retry_required": True,
                    "missing_params": ["sl_percent"]
                }, ensure_ascii=False)

            # If tp_percent/sl_percent provided, calculate tp_price/sl_price (reversed for short)
            if (tp_percent or sl_percent) and not (tp_price and sl_price):
                try:
                    from .market_data import MarketDataService
                    market_service = MarketDataService()
                    current_price = await market_service.get_current_price(symbol)
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
                        "error": f"无法计算止盈止损价格: {e}",
                        "retry_required": True
                    }, ensure_ascii=False)

            # 最终校验：确保 tp_price 和 sl_price 都已设置
            if not tp_price or not sl_price:
                return json.dumps({
                    "success": False,
                    "error": "止盈止损价格计算失败，请重新调用并提供正确的 tp_percent 和 sl_percent 参数",
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
                    "message": "开仓成功" if result['success'] else result.get('error', '开仓失败')
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
                        "message": "平仓成功"
                    }, ensure_ascii=False)
                else:
                    return json.dumps({
                        "success": False,
                        "error": result.get('error', '平仓失败')
                    }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

    async def _hold(self, reason: str = "市场不明朗", **kwargs) -> str:
        """Hold decision - do not trade"""
        logger.info(f"Hold decision made: {reason}")
        return json.dumps({
            "success": True,
            "action": "hold",
            "reason": reason,
            "message": f"决定观望: {reason}"
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

                        # Translate to Chinese
                        classification_map = {
                            "Extreme Fear": "极度恐慌",
                            "Fear": "恐慌",
                            "Neutral": "中性",
                            "Greed": "贪婪",
                            "Extreme Greed": "极度贪婪"
                        }
                        classification = classification_map.get(classification_en, classification_en)

                        logger.info(f"[TradingTools] Fetched REAL Fear & Greed Index: {index} ({classification})")

                        return json.dumps({
                            "value": index,
                            "classification": classification,
                            "timestamp": datetime.now().isoformat(),
                            "interpretation": f"当前市场情绪为{classification}，指数值{index}/100",
                            "source": "Alternative.me API (REAL DATA)"
                        }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error getting real Fear & Greed Index: {e}")

        # Fallback: use neutral value
        return json.dumps({
            "value": 50,
            "classification": "中性",
            "timestamp": datetime.now().isoformat(),
            "interpretation": "暂时无法获取恐慌贪婪指数，默认中性",
            "source": "Fallback (NEUTRAL DEFAULT)"
        }, ensure_ascii=False)

    async def _get_funding_rate(self, symbol: str = "BTC-USDT-SWAP") -> str:
        """Get funding rate - fetches REAL data from Binance Futures API"""
        try:
            import httpx
            from datetime import datetime, timedelta
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

                    time_str = f"{hours_left}小时{minutes_left}分钟后" if hours_left > 0 else f"{minutes_left}分钟后"

                    logger.info(f"[TradingTools] Fetched REAL Funding Rate: {rate*100:.4f}%")

                    return json.dumps({
                        "symbol": symbol,
                        "funding_rate": f"{rate*100:.4f}%",
                        "funding_rate_value": rate,
                        "next_funding_time": time_str,
                        "interpretation": (
                            f"资金费率为正({rate*100:.4f}%)，多头支付空头，市场偏多" if rate > 0 else
                            f"资金费率为负({rate*100:.4f}%)，空头支付多头，市场偏空" if rate < 0 else
                            "资金费率为零，多空平衡"
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
            "next_funding_time": "8小时后",
            "interpretation": "暂时无法获取资金费率数据",
            "source": "Fallback (NEUTRAL DEFAULT)"
        }, ensure_ascii=False)

    async def _get_trade_history(self, limit: int = 20) -> str:
        """Get trade history"""
        # 确保类型正确
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
            "message": "暂无交易记录"
        }, ensure_ascii=False)

    async def _tavily_search(self, query: str, max_results: int = 5, time_range: str = None, topic: str = "general", days: int = None) -> str:
        """
        Search for cryptocurrency news and market information using MCP.

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
            # 使用 MCP Client 调用 web-search 服务
            from app.core.roundtable.mcp_tools import get_mcp_client

            mcp_client = get_mcp_client()

            # 确保参数类型正确
            max_results = int(max_results) if max_results else 5
            max_results = min(max(1, max_results), 10)  # Limit between 1-10

            # 构建 MCP 调用参数
            params = {
                "query": query,
                "max_results": max_results,
                "topic": topic or "general"
            }

            # 添加可选参数
            if time_range and time_range in ["day", "week", "month", "year"]:
                params["time_range"] = time_range
            if days and isinstance(days, int) and 1 <= days <= 30:
                params["days"] = days

            logger.info(f"[TradingTools] MCP Tavily search: '{query}' (params={params})")

            # 通过 MCP 调用
            result = await mcp_client.call_tool(
                server_name="web-search",
                tool_name="search",
                **params
            )

            # MCP 响应已经是正确格式
            if result.get("success"):
                logger.info(f"[TradingTools] MCP search success: {len(result.get('result', {}).get('results', []))} results")
                # 重新格式化为trading_tools期望的格式
                mcp_results = result.get("result", {}).get("results", [])
                formatted_results = [{
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:500],
                    "score": 1.0  # MCP结果没有score，默认1.0
                } for r in mcp_results]

                return json.dumps({
                    "success": True,
                    "query": query,
                    "answer": result.get("result", {}).get("summary", ""),
                    "results": formatted_results,
                    "result_count": len(formatted_results),
                    "source": "MCP Web Search",
                    "message": f"搜索'{query}'返回{len(formatted_results)}条结果"
                }, ensure_ascii=False)
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"[TradingTools] MCP search failed: {error_msg}")
                return json.dumps({
                    "success": False,
                    "error": error_msg,
                    "message": f"搜索失败: {error_msg}"
                }, ensure_ascii=False)

        except Exception as e:
            logger.error(f"[TradingTools] Tavily search error: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "message": f"搜索出错: {str(e)}"
            }, ensure_ascii=False)
