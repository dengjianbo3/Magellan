"""
OKX Demo API Client

Provides interface to OKX exchange for trading operations.
Uses direct REST API calls to support demo trading mode.
"""

import os
import hmac
import hashlib
import base64
import logging
import json
import asyncio
import aiohttp
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

from app.models.trading_models import (
    Position, AccountBalance, MarketData, TradeRecord, TradingSignal
)

logger = logging.getLogger(__name__)


class OKXClient:
    """
    OKX Exchange Client for Demo Trading

    Supports:
    - Account balance queries
    - Open/Close positions
    - Set take-profit and stop-loss
    - Query positions and orders
    - Get market data
    """

    BASE_URL = "https://www.okx.com"

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        passphrase: Optional[str] = None,
        demo_mode: bool = True
    ):
        self.api_key = api_key or os.getenv("OKX_API_KEY", "")
        self.secret_key = secret_key or os.getenv("OKX_SECRET_KEY", "")
        self.passphrase = passphrase or os.getenv("OKX_PASSPHRASE", "")
        self.demo_mode = demo_mode or os.getenv("OKX_DEMO_MODE", "true").lower() == "true"

        self._session: Optional[aiohttp.ClientSession] = None
        self._initialized = False

    def _get_timestamp(self) -> str:
        """Get ISO format timestamp for API calls"""
        return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

    def _sign(self, timestamp: str, method: str, request_path: str, body: str = '') -> str:
        """Generate signature for API request"""
        message = timestamp + method + request_path + body
        mac = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode('utf-8')

    def _get_headers(self, method: str, request_path: str, body: str = '') -> Dict[str, str]:
        """Get headers for authenticated API request"""
        timestamp = self._get_timestamp()
        signature = self._sign(timestamp, method, request_path, body)

        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }

        if self.demo_mode:
            headers['x-simulated-trading'] = '1'

        return headers

    async def initialize(self):
        """Initialize the API client"""
        if self._initialized:
            return

        if not self.api_key or not self.secret_key or not self.passphrase:
            logger.warning("OKX API credentials not configured. Using mock mode.")
            self._initialized = True
            return

        self._session = aiohttp.ClientSession()

        # Test connection and setup
        try:
            # 1. Check and set position mode to long_short_mode (双向持仓)
            await self._ensure_long_short_mode()

            # 2. Test connection by getting balance
            balance = await self.get_account_balance()
            logger.info(f"OKX client initialized (demo={self.demo_mode}), USDT balance: ${balance.available_balance:.2f}")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize OKX client: {e}")
            self._initialized = True

    async def _ensure_long_short_mode(self):
        """
        确保账户使用双向持仓模式 (long_short_mode)

        OKX 有两种持仓模式：
        - net_mode: 单向持仓，不区分多空
        - long_short_mode: 双向持仓，区分多空（代码使用 posSide='long'/'short' 需要此模式）
        """
        try:
            # 获取当前账户配置
            config_data = await self._request('GET', '/api/v5/account/config')

            if config_data.get('code') == '0' and config_data.get('data'):
                pos_mode = config_data['data'][0].get('posMode')
                logger.info(f"OKX account position mode: {pos_mode}")

                if pos_mode == 'net_mode':
                    # 切换到双向持仓模式
                    logger.warning("OKX account is in net_mode, switching to long_short_mode...")

                    result = await self._request('POST', '/api/v5/account/set-position-mode', {
                        'posMode': 'long_short_mode'
                    })

                    if result.get('code') == '0':
                        logger.info("✅ Successfully switched to long_short_mode (双向持仓)")
                    else:
                        # 51020 = 已经是该模式
                        error_msg = result.get('msg', '')
                        if '51020' in str(result):
                            logger.info("Already in long_short_mode")
                        else:
                            logger.error(f"Failed to switch position mode: {error_msg}")
                else:
                    logger.info("✅ OKX account already in long_short_mode (双向持仓)")

        except Exception as e:
            logger.error(f"Error checking/setting position mode: {e}")

    async def close(self):
        """Close the API session"""
        if self._session:
            await self._session.close()
            self._session = None

    def _get_proxy(self) -> Optional[str]:
        """Get proxy from environment variables"""
        # 优先使用 HTTPS 代理
        proxy = os.getenv('https_proxy') or os.getenv('HTTPS_PROXY')
        if proxy:
            return proxy
        proxy = os.getenv('http_proxy') or os.getenv('HTTP_PROXY')
        return proxy
    
    async def _request(self, method: str, path: str, body: Optional[Dict] = None) -> Dict:
        """Make authenticated API request"""
        if not self._session:
            # 🔧 增加超时时间到 30 秒
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)

        body_str = json.dumps(body) if body else ''
        headers = self._get_headers(method.upper(), path, body_str)

        url = self.BASE_URL + path
        proxy = self._get_proxy()

        try:
            if method.upper() == 'GET':
                async with self._session.get(url, headers=headers, proxy=proxy) as resp:
                    result = await resp.json()
                    logger.debug(f"OKX API GET {path}: code={result.get('code')}")
                    return result
            else:
                async with self._session.post(url, headers=headers, data=body_str, proxy=proxy) as resp:
                    result = await resp.json()
                    logger.debug(f"OKX API POST {path}: code={result.get('code')}")
                    return result
        except asyncio.TimeoutError:
            logger.error(f"API request timeout: {path}")
            return {"code": "-1", "msg": f"Request timeout: {path}", "data": []}
        except aiohttp.ClientError as e:
            logger.error(f"API client error: {e}")
            return {"code": "-1", "msg": str(e), "data": []}
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return {"code": "-1", "msg": str(e), "data": []}

    async def get_account_balance(self) -> AccountBalance:
        """Get account balance - 获取完整的账户信息"""
        try:
            if self.api_key and self.secret_key:
                data = await self._request('GET', '/api/v5/account/balance')

                if data.get('code') == '0':
                    account = data.get('data', [{}])[0]
                    details = account.get('details', [])

                    usdt_balance = 0.0
                    frozen_balance = 0.0  # 🆕 冻结余额 = 已用保证金
                    unrealized_pnl = 0.0

                    for d in details:
                        if d.get('ccy') == 'USDT':
                            usdt_balance = float(d.get('availBal', 0) or 0)
                            frozen_balance = float(d.get('frozenBal', 0) or 0)  # 🆕 获取冻结余额
                            unrealized_pnl = float(d.get('upl', 0) or 0)  # 🆕 获取未实现盈亏
                            break

                    total_equity = float(account.get('totalEq', 0) or 0)

                    return AccountBalance(
                        total_equity=total_equity,
                        available_balance=usdt_balance,
                        used_margin=frozen_balance,  # 🆕 使用冻结余额作为已用保证金
                        unrealized_pnl=unrealized_pnl,
                        realized_pnl_today=0.0,
                        currency="USDT"
                    )

        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            raise RuntimeError(f"Failed to fetch account balance from OKX: {e}")

    async def get_market_price(self, symbol: str = "BTC-USDT-SWAP") -> MarketData:
        """Get current market data (public API - no auth needed)"""
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            proxy = self._get_proxy()
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Use public API for ticker
                inst_id = symbol  # e.g., "BTC-USDT-SWAP"
                url = f"{self.BASE_URL}/api/v5/market/ticker?instId={inst_id}"

                async with session.get(url, proxy=proxy) as resp:
                    data = await resp.json()

                    if data.get('code') == '0' and data.get('data'):
                        ticker = data['data'][0]
                        logger.info(f"OKX ticker: {symbol} price=${ticker.get('last')}")
                        return MarketData(
                            symbol=symbol,
                            price=float(ticker.get('last', 0)),
                            price_24h_change=float(ticker.get('sodUtc0', 0)) if ticker.get('sodUtc0') else 0,
                            volume_24h=float(ticker.get('vol24h', 0) or 0),
                            high_24h=float(ticker.get('high24h', 0) or 0),
                            low_24h=float(ticker.get('low24h', 0) or 0),
                            open_24h=float(ticker.get('open24h', 0) or 0),
                            funding_rate=None,
                            open_interest=None
                        )
                    else:
                        logger.error(f"OKX API error: {data.get('msg')}")
                        raise RuntimeError(f"OKX API error: {data.get('msg')}")

        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching market price for {symbol}")
            raise RuntimeError(f"Timeout fetching market price for {symbol}")
        except Exception as e:
            logger.error(f"Error fetching market price: {e}")
            raise RuntimeError(f"Failed to fetch market price from OKX: {e}")

    async def get_current_position(self, symbol: str = "BTC-USDT-SWAP") -> Optional[Position]:
        """Get current open position"""
        try:
            if self.api_key and self.secret_key:
                data = await self._request('GET', f'/api/v5/account/positions?instId={symbol}')

                if data.get('code') == '0':
                    positions = data.get('data', [])
                    for pos in positions:
                        pos_amt = float(pos.get('pos', 0) or 0)
                        if abs(pos_amt) > 0:
                            side = 'long' if pos_amt > 0 else 'short'
                            entry_price = float(pos.get('avgPx', 0) or 0)
                            mark_price = float(pos.get('markPx', entry_price) or entry_price)
                            leverage = int(pos.get('lever', 1) or 1)
                            upl = float(pos.get('upl', 0) or 0)
                            margin = float(pos.get('margin', 0) or 0)
                            liq_price = float(pos.get('liqPx', 0) or 0)

                            return Position(
                                symbol=symbol,
                                direction=side,
                                size=abs(pos_amt),
                                entry_price=entry_price,
                                current_price=mark_price,
                                leverage=leverage,
                                unrealized_pnl=upl,
                                unrealized_pnl_percent=(upl / margin * 100) if margin > 0 else 0,
                                margin=margin,
                                liquidation_price=liq_price,
                                opened_at=datetime.now()
                            )

        except Exception as e:
            logger.error(f"Error fetching position: {e}")

        return None

    async def open_long(
        self,
        symbol: str,
        leverage: int,
        amount_usdt: float,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Open a long position"""
        return await self._open_position(
            symbol=symbol,
            side="buy",
            pos_side="long",
            leverage=leverage,
            amount_usdt=amount_usdt,
            tp_price=tp_price,
            sl_price=sl_price
        )

    async def open_short(
        self,
        symbol: str,
        leverage: int,
        amount_usdt: float,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Open a short position"""
        return await self._open_position(
            symbol=symbol,
            side="sell",
            pos_side="short",
            leverage=leverage,
            amount_usdt=amount_usdt,
            tp_price=tp_price,
            sl_price=sl_price
        )

    async def _open_position(
        self,
        symbol: str,
        side: str,
        pos_side: str,
        leverage: int,
        amount_usdt: float,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Internal method to open position"""
        # 确保类型正确（防止从LLM解析时传入字符串）
        try:
            leverage = int(leverage) if leverage else 1
            amount_usdt = float(amount_usdt) if amount_usdt else 100
            tp_price = float(tp_price) if tp_price else None
            sl_price = float(sl_price) if sl_price else None
        except (TypeError, ValueError) as e:
            return {'success': False, 'error': f'参数类型错误: {e}'}

        try:
            if self.api_key and self.secret_key:
                # Set leverage first
                await self._request('POST', '/api/v5/account/set-leverage', {
                    'instId': symbol,
                    'lever': str(leverage),
                    'mgnMode': 'cross'
                })

                # Get current price
                market = await self.get_market_price(symbol)
                price = market.price

                # Calculate contract size (BTC-USDT-SWAP: 1 contract = 0.01 BTC)
                contract_val = 0.01  # Each contract = 0.01 BTC
                sz = int((amount_usdt * leverage) / (price * contract_val))
                sz = max(1, sz)  # At least 1 contract

                # Place market order
                order_data = {
                    'instId': symbol,
                    'tdMode': 'cross',
                    'side': side,
                    'posSide': pos_side,
                    'ordType': 'market',
                    'sz': str(sz)
                }

                logger.info(f"[OKXClient] Placing order: {order_data}")
                result = await self._request('POST', '/api/v5/trade/order', order_data)
                logger.info(f"[OKXClient] Order response: code={result.get('code')}, msg={result.get('msg')}, data={result.get('data')}")

                if result.get('code') == '0':
                    order_id = result.get('data', [{}])[0].get('ordId', '')

                    # Set TP/SL if provided
                    if tp_price or sl_price:
                        await self._set_tp_sl(symbol, pos_side, tp_price, sl_price)

                    return {
                        'success': True,
                        'order_id': order_id,
                        'executed_price': price,
                        'executed_amount': sz * contract_val,
                        'side': side,
                        'leverage': leverage
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('msg', 'Unknown error')
                    }

        except Exception as e:
            logger.error(f"Error opening position: {e}")
            return {
                'success': False,
                'error': f"Failed to open position: {e}"
            }

        # No API credentials configured
        return {
            'success': False,
            'error': "OKX API credentials not configured. Cannot execute real trades."
        }

    async def _set_tp_sl(self, symbol: str, pos_side: str, tp_price: Optional[float], sl_price: Optional[float]):
        """Set take-profit and stop-loss orders"""
        try:
            if tp_price:
                await self._request('POST', '/api/v5/trade/order-algo', {
                    'instId': symbol,
                    'tdMode': 'cross',
                    'side': 'sell' if pos_side == 'long' else 'buy',
                    'posSide': pos_side,
                    'ordType': 'conditional',
                    'sz': '-1',  # Close all
                    'tpTriggerPx': str(tp_price),
                    'tpOrdPx': '-1'  # Market price
                })

            if sl_price:
                await self._request('POST', '/api/v5/trade/order-algo', {
                    'instId': symbol,
                    'tdMode': 'cross',
                    'side': 'sell' if pos_side == 'long' else 'buy',
                    'posSide': pos_side,
                    'ordType': 'conditional',
                    'sz': '-1',
                    'slTriggerPx': str(sl_price),
                    'slOrdPx': '-1'
                })

        except Exception as e:
            logger.error(f"Error setting TP/SL: {e}")

    async def close_position(self, symbol: str = "BTC-USDT-SWAP") -> Dict[str, Any]:
        """Close current position"""
        try:
            if self.api_key and self.secret_key:
                # Get current position
                position = await self.get_current_position(symbol)

                if position:
                    # Close position with market order
                    side = 'sell' if position.direction == 'long' else 'buy'
                    pos_side = position.direction

                    result = await self._request('POST', '/api/v5/trade/close-position', {
                        'instId': symbol,
                        'mgnMode': 'cross',
                        'posSide': pos_side
                    })

                    if result.get('code') == '0':
                        return {
                            'success': True,
                            'closed_price': position.current_price,
                            'pnl': position.unrealized_pnl
                        }
                    else:
                        return {
                            'success': False,
                            'error': result.get('msg', 'Failed to close position')
                        }

                return {'success': False, 'error': 'No position to close'}

        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return {
                'success': False,
                'error': f"Failed to close position: {e}"
            }

        # No API credentials configured
        return {
            'success': False,
            'error': "OKX API credentials not configured. Cannot execute real trades."
        }

    async def get_trade_history(self, symbol: str = "BTC-USDT-SWAP", limit: int = 50) -> List[Dict]:
        """Get trade history"""
        try:
            if self.api_key and self.secret_key:
                data = await self._request('GET', f'/api/v5/trade/fills?instId={symbol}&limit={limit}')

                if data.get('code') == '0':
                    return [
                        {
                            'id': t.get('tradeId'),
                            'timestamp': int(t.get('ts', 0)),
                            'side': t.get('side'),
                            'price': float(t.get('fillPx', 0)),
                            'amount': float(t.get('fillSz', 0)),
                            'fee': float(t.get('fee', 0))
                        }
                        for t in data.get('data', [])
                    ]

        except Exception as e:
            logger.error(f"Error fetching trade history: {e}")

        return []

    async def get_klines(
        self,
        symbol: str = "BTC-USDT-SWAP",
        timeframe: str = "4H",
        limit: int = 100
    ) -> List[Dict]:
        """Get candlestick data for technical analysis"""
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            proxy = self._get_proxy()
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Map timeframe to OKX format
                bar_map = {
                    '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
                    '1h': '1H', '4h': '4H', '1d': '1D', '1w': '1W'
                }
                bar = bar_map.get(timeframe.lower(), '4H')

                url = f"{self.BASE_URL}/api/v5/market/candles?instId={symbol}&bar={bar}&limit={limit}"

                async with session.get(url, proxy=proxy) as resp:
                    data = await resp.json()

                    if data.get('code') == '0':
                        return [
                            {
                                'timestamp': int(candle[0]),
                                'open': float(candle[1]),
                                'high': float(candle[2]),
                                'low': float(candle[3]),
                                'close': float(candle[4]),
                                'volume': float(candle[5])
                            }
                            for candle in data.get('data', [])
                        ]
                    else:
                        logger.error(f"OKX klines API error: {data.get('msg')}")
                        return []

        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching klines for {symbol}")
            raise RuntimeError(f"Timeout fetching klines for {symbol}")
        except Exception as e:
            logger.error(f"Error fetching klines: {e}")
            raise RuntimeError(f"Failed to fetch klines from OKX: {e}")


# Singleton instance
_okx_client: Optional[OKXClient] = None


async def get_okx_client() -> OKXClient:
    """Get or create OKX client singleton"""
    global _okx_client
    if _okx_client is None:
        _okx_client = OKXClient()
        await _okx_client.initialize()
    return _okx_client
