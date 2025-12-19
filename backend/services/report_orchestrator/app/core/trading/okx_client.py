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
            # 🆕 1. Verify API key permissions
            await self._verify_api_permissions()
            
            # 2. Check and set position mode to long_short_mode (bidirectional position)
            await self._ensure_long_short_mode()

            # 3. Test connection by getting balance
            balance = await self.get_account_balance()
            logger.info(f"OKX client initialized (demo={self.demo_mode}), USDT balance: ${balance.available_balance:.2f}")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize OKX client: {e}")
            self._initialized = True

    async def _verify_api_permissions(self):
        """
        Verify API key has correct permissions.
        
        CRITICAL for real trading:
        - Should have: Trade permission
        - Should NOT have: Withdraw permission (security risk)
        - Optional: Read permission
        """
        try:
            # Get API key info
            result = await self._request('GET', '/api/v5/account/config')
            
            if result.get('code') == '0' and result.get('data'):
                config = result['data'][0]
                
                # OKX returns permission info in config
                # Note: For security, we log what we find but proceed with caution
                perm = config.get('perm', '')
                ip = config.get('ip', '')
                label = config.get('label', '')
                
                logger.info(f"[API Security] API Key label: '{label}'")
                logger.info(f"[API Security] IP whitelist: {ip if ip else 'Not configured (⚠️ risk)'}")
                logger.info(f"[API Security] Permissions: {perm}")
                
                # Check for dangerous permissions
                if 'withdraw' in perm.lower():
                    logger.warning("=" * 60)
                    logger.warning("🚨 SECURITY WARNING: API KEY HAS WITHDRAW PERMISSION!")
                    logger.warning("   This is a security risk for automated trading.")
                    logger.warning("   Recommendation: Create a new API key with only 'Trade' permission.")
                    logger.warning("=" * 60)
                    # We don't block here but strongly warn
                
                # Check for trade permission
                if 'trade' not in perm.lower() and perm:
                    logger.error("=" * 60)
                    logger.error("❌ API KEY DOES NOT HAVE TRADE PERMISSION!")
                    logger.error("   Trading operations will fail.")
                    logger.error("   Please update API key permissions in OKX.")
                    logger.error("=" * 60)
                    
                # Check IP whitelist
                if not ip:
                    logger.warning("[API Security] ⚠️ No IP whitelist configured - consider adding for extra security")
                else:
                    logger.info(f"[API Security] ✅ IP whitelist active: {ip}")
                    
        except Exception as e:
            logger.warning(f"[API Security] Could not verify API permissions: {e}")

    async def _ensure_long_short_mode(self):
        """
        Ensure account configuration is correct:
        1. Account mode = Single-currency margin mode (2)
        2. Position mode = Long/short mode (long_short_mode)
        """
        try:
            # Get current account config
            config_data = await self._request('GET', '/api/v5/account/config')

            if config_data.get('code') == '0' and config_data.get('data'):
                config = config_data['data'][0]
                acct_lv = config.get('acctLv')  # Account mode: 1=simple, 2=single-currency, 3=multi-currency, 4=portfolio
                pos_mode = config.get('posMode')  # Position mode: net_mode, long_short_mode

                logger.info(f"OKX account config: acctLv={acct_lv}, posMode={pos_mode}")

                # Check account mode
                # Error 51010 indicates account mode does not support current operation
                # Need to switch to single-currency margin mode (2) or higher
                if acct_lv == '1':
                    logger.warning("⚠️ OKX account is in Simple mode (acctLv=1)")
                    logger.warning("   Simple mode does not support contract trading!")
                    logger.warning("   Please switch to Single-currency margin mode in OKX web/app:")
                    logger.warning("   Settings -> Account mode -> Single-currency margin mode")

                    # Attempt to auto-switch account mode
                    logger.info("Attempting to switch to Single-currency margin mode...")
                    result = await self._request('POST', '/api/v5/account/set-account-level', {
                        'acctLv': '2'  # 2 = Single-currency margin mode
                    })

                    if result.get('code') == '0':
                        logger.info("✅ Successfully switched to Single-currency margin mode")
                    else:
                        logger.error(f"❌ Failed to switch account mode: {result.get('msg')}")
                        logger.error("   Please manually switch in OKX web/app settings")
                else:
                    logger.info(f"✅ OKX account mode OK (acctLv={acct_lv})")

                # Check position mode
                if pos_mode == 'net_mode':
                    logger.warning("OKX account is in net_mode, switching to long_short_mode...")

                    result = await self._request('POST', '/api/v5/account/set-position-mode', {
                        'posMode': 'long_short_mode'
                    })

                    if result.get('code') == '0':
                        logger.info("✅ Successfully switched to long_short_mode (bidirectional position)")
                    else:
                        error_msg = result.get('msg', '')
                        if '51020' in str(result):
                            logger.info("Already in long_short_mode")
                        else:
                            logger.error(f"Failed to switch position mode: {error_msg}")
                else:
                    logger.info("✅ OKX account already in long_short_mode (bidirectional position)")

        except Exception as e:
            logger.error(f"Error checking/setting account config: {e}")

    async def close(self):
        """Close the API session"""
        if self._session:
            await self._session.close()
            self._session = None

    def _get_proxy(self) -> Optional[str]:
        """Get proxy from environment variables"""
        # Prefer HTTPS proxy
        proxy = os.getenv('https_proxy') or os.getenv('HTTPS_PROXY')
        if proxy:
            return proxy
        proxy = os.getenv('http_proxy') or os.getenv('HTTP_PROXY')
        return proxy
    
    async def _request(self, method: str, path: str, body: Optional[Dict] = None, max_retries: int = 3) -> Dict:
        """
        Make authenticated API request with retry mechanism
        
        Args:
            method: HTTP method (GET/POST)
            path: API path
            body: Request body for POST
            max_retries: Maximum retry attempts for transient errors
        """
        if not self._session:
            # Increase timeout to 30 seconds
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)

        body_str = json.dumps(body) if body else ''
        url = self.BASE_URL + path
        proxy = self._get_proxy()
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Generate fresh headers for each attempt (timestamp must be current)
                headers = self._get_headers(method.upper(), path, body_str)
                
                if method.upper() == 'GET':
                    async with self._session.get(url, headers=headers, proxy=proxy) as resp:
                        result = await resp.json()
                        logger.debug(f"OKX API GET {path}: code={result.get('code')}")
                        
                        # Check for rate limit or server errors that warrant retry
                        if result.get('code') in ['50001', '50004', '50011', '50013']:
                            # Rate limit or system busy - retry with backoff
                            if attempt < max_retries - 1:
                                wait_time = (2 ** attempt) + 0.5  # Exponential backoff
                                logger.warning(f"[OKX API] Rate limited/busy, retrying in {wait_time:.1f}s (attempt {attempt + 1}/{max_retries})")
                                await asyncio.sleep(wait_time)
                                continue
                        
                        return result
                else:
                    async with self._session.post(url, headers=headers, data=body_str, proxy=proxy) as resp:
                        result = await resp.json()
                        logger.debug(f"OKX API POST {path}: code={result.get('code')}")
                        
                        # Check for rate limit or server errors
                        if result.get('code') in ['50001', '50004', '50011', '50013']:
                            if attempt < max_retries - 1:
                                wait_time = (2 ** attempt) + 0.5
                                logger.warning(f"[OKX API] Rate limited/busy, retrying in {wait_time:.1f}s (attempt {attempt + 1}/{max_retries})")
                                await asyncio.sleep(wait_time)
                                continue
                        
                        return result
                        
            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(f"[OKX API] Timeout on {path} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                    
            except aiohttp.ClientError as e:
                last_error = e
                logger.warning(f"[OKX API] Client error: {e} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                    
            except Exception as e:
                last_error = e
                logger.error(f"[OKX API] Unexpected error: {e}")
                break  # Don't retry unexpected errors
        
        # All retries exhausted
        error_msg = str(last_error) if last_error else "Max retries exceeded"
        logger.error(f"[OKX API] Request failed after {max_retries} attempts: {path} - {error_msg}")
        return {"code": "-1", "msg": error_msg, "data": [], "retry_exhausted": True}

    async def get_max_avail_size(self, symbol: str = "BTC-USDT-SWAP") -> float:
        """
        Get OKX calculated real maximum available position size

        Uses /api/v5/account/max-avail-size API
        This API returns OKX internally calculated available size, considering:
        - Existing position maintenance margin
        - New position initial margin rate
        - Account risk control requirements

        Returns:
            float: Maximum USDT amount available for opening position
        """
        try:
            if self.api_key and self.secret_key:
                data = await self._request(
                    'GET',
                    f'/api/v5/account/max-avail-size?instId={symbol}&tdMode=cross'
                )

                if data.get('code') == '0' and data.get('data'):
                    result = data['data'][0]
                    # availBuy is max buy amount in quote currency (USDT)
                    avail_buy = float(result.get('availBuy', 0) or 0)
                    logger.info(f"[OKXClient] Max avail size for {symbol}: ${avail_buy:.2f} USDT")
                    return avail_buy
                else:
                    logger.warning(f"[OKXClient] Failed to get max-avail-size: {data.get('msg')}")
                    return 0.0
        except Exception as e:
            logger.error(f"Error fetching max avail size: {e}")
            return 0.0

        return 0.0

    async def get_account_balance(self) -> AccountBalance:
        """Get account balance - including OKX calculated real max available size"""
        try:
            if self.api_key and self.secret_key:
                data = await self._request('GET', '/api/v5/account/balance')

                if data.get('code') == '0':
                    account = data.get('data', [{}])[0]
                    details = account.get('details', [])

                    usdt_balance = 0.0
                    frozen_balance = 0.0  # Frozen balance = used margin
                    unrealized_pnl = 0.0

                    for d in details:
                        if d.get('ccy') == 'USDT':
                            usdt_balance = float(d.get('availBal', 0) or 0)
                            frozen_balance = float(d.get('frozenBal', 0) or 0)  # Get frozen balance
                            unrealized_pnl = float(d.get('upl', 0) or 0)  # Get unrealized PnL
                            break

                    total_equity = float(account.get('totalEq', 0) or 0)

                    # Get OKX calculated real max available size
                    max_avail_size = await self.get_max_avail_size()

                    # 🆕 Calculate trading-specific equity: USDT balance + position value
                    # This is what we WANT for tracking BTC-USDT trading performance:
                    # - usdt_balance: Available USDT for trading
                    # - frozen_balance: USDT used as margin in positions
                    # - unrealized_pnl: Current profit/loss of open positions
                    # 
                    # OKX's totalEq includes ALL assets (BTC, ETH, etc.) which doesn't 
                    # reflect our trading performance - only this pair matters
                    trading_equity = usdt_balance + frozen_balance + unrealized_pnl
                    
                    # Log: record account status with both values for comparison
                    logger.info(
                        f"[OKXClient] Account status: maxAvail=${max_avail_size:.2f}, "
                        f"USDTBalance=${usdt_balance:.2f}, frozenBal=${frozen_balance:.2f}, "
                        f"upl=${unrealized_pnl:.2f}, totalEq(全资产)=${total_equity:.2f}, "
                        f"tradingEq(交易权益)=${trading_equity:.2f}"
                    )

                    return AccountBalance(
                        total_equity=trading_equity,  # 🔑 Use trading-specific equity
                        available_balance=usdt_balance,
                        used_margin=frozen_balance,  # USDT margin in positions
                        unrealized_pnl=unrealized_pnl,
                        realized_pnl_today=0.0,
                        max_avail_size=max_avail_size,  # OKX calculated real max available size
                        calculated_equity=trading_equity,  # Same as total_equity now
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

                            # Get TP/SL prices
                            tp_price, sl_price = await self._get_tp_sl_prices(symbol, side)

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
                                take_profit_price=tp_price,
                                stop_loss_price=sl_price,
                                opened_at=datetime.now()
                            )

        except Exception as e:
            logger.error(f"Error fetching position: {e}")

        return None

    async def _get_tp_sl_prices(self, symbol: str, pos_side: str) -> tuple[Optional[float], Optional[float]]:
        """Get take-profit and stop-loss prices for current position"""
        tp_price = None
        sl_price = None

        try:
            # Query algo orders (including conditional orders)
            data = await self._request('GET', f'/api/v5/trade/orders-algo-pending?instId={symbol}&ordType=conditional')

            if data.get('code') == '0':
                for order in data.get('data', []):
                    order_pos_side = order.get('posSide', '')
                    if order_pos_side != pos_side:
                        continue

                    # Take profit order
                    tp_trigger = order.get('tpTriggerPx')
                    if tp_trigger:
                        tp_price = float(tp_trigger)

                    # Stop loss order
                    sl_trigger = order.get('slTriggerPx')
                    if sl_trigger:
                        sl_price = float(sl_trigger)

        except Exception as e:
            logger.warning(f"Error fetching TP/SL prices: {e}")

        return tp_price, sl_price

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
        # Ensure correct types (prevent string input from LLM parsing)
        try:
            leverage = int(leverage) if leverage else 1
            amount_usdt = float(amount_usdt) if amount_usdt else 100
            tp_price = float(tp_price) if tp_price else None
            sl_price = float(sl_price) if sl_price else None
        except (TypeError, ValueError) as e:
            return {'success': False, 'error': f'Parameter type error: {e}'}

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
                    
                    # 🆕 Confirm order was filled
                    actual_price, actual_size = await self._confirm_order_filled(order_id, symbol, price, sz * contract_val)

                    # Set TP/SL if provided
                    if tp_price or sl_price:
                        await self._set_tp_sl(symbol, pos_side, tp_price, sl_price)

                    return {
                        'success': True,
                        'order_id': order_id,
                        'executed_price': actual_price,
                        'executed_amount': actual_size,
                        'side': side,
                        'leverage': leverage,
                        'confirmed': True
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

    async def _confirm_order_filled(
        self, 
        order_id: str, 
        symbol: str, 
        expected_price: float, 
        expected_size: float,
        max_wait_seconds: int = 10
    ) -> tuple[float, float]:
        """
        Confirm order was actually filled by querying order details.
        
        This is critical for real trading to ensure:
        1. Order was actually executed
        2. Get actual fill price (may differ from market price)
        3. Get actual filled size
        
        Args:
            order_id: The order ID to check
            symbol: Trading pair
            expected_price: Expected fill price (fallback)
            expected_size: Expected fill size (fallback)
            max_wait_seconds: Max time to wait for fill confirmation
            
        Returns:
            Tuple of (actual_price, actual_size)
        """
        if not order_id:
            return expected_price, expected_size
            
        try:
            # Poll for order status
            wait_intervals = [0.5, 1, 2, 3, 3.5]  # Total ~10 seconds
            
            for wait in wait_intervals:
                await asyncio.sleep(wait)
                
                # Query order details
                result = await self._request(
                    'GET', 
                    f'/api/v5/trade/order?instId={symbol}&ordId={order_id}'
                )
                
                if result.get('code') == '0' and result.get('data'):
                    order = result['data'][0]
                    state = order.get('state', '')
                    
                    # Check if filled
                    if state == 'filled':
                        actual_price = float(order.get('avgPx', expected_price) or expected_price)
                        actual_size = float(order.get('accFillSz', expected_size) or expected_size)
                        
                        # Convert contract size to BTC if needed
                        contract_val = 0.01  # BTC-USDT-SWAP: 1 contract = 0.01 BTC
                        if actual_size > 1:  # Likely in contracts not BTC
                            actual_size = actual_size * contract_val
                            
                        logger.info(f"[OKXClient] ✅ Order {order_id} CONFIRMED: price=${actual_price:.2f}, size={actual_size:.6f}")
                        return actual_price, actual_size
                    
                    elif state in ['canceled', 'cancelled']:
                        logger.error(f"[OKXClient] ❌ Order {order_id} was CANCELLED!")
                        return expected_price, 0  # Size 0 indicates failed order
                    
                    elif state == 'live':
                        logger.debug(f"[OKXClient] Order {order_id} still pending...")
                        continue
                    
                    else:
                        logger.debug(f"[OKXClient] Order {order_id} state: {state}")
                        
            # Timeout - return expected values with warning
            logger.warning(f"[OKXClient] ⚠️ Order {order_id} confirmation timeout after {max_wait_seconds}s")
            return expected_price, expected_size
            
        except Exception as e:
            logger.error(f"[OKXClient] Error confirming order {order_id}: {e}")
            return expected_price, expected_size

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
        """
        Get closed positions history with REAL realized PnL from OKX API.
        
        Uses /api/v5/account/positions-history for accurate PnL including:
        - Trading P&L
        - Funding fees
        - Trading fees
        - Liquidation penalties (if any)
        """
        try:
            if self.api_key and self.secret_key:
                # 🆕 Use positions-history API for real closed position data
                data = await self._request(
                    'GET', 
                    f'/api/v5/account/positions-history?instType=SWAP&limit={limit}'
                )

                if data.get('code') == '0':
                    trades = []
                    for pos in data.get('data', []):
                        # Only include matching symbol or all if no filter
                        inst_id = pos.get('instId', '')
                        if symbol and inst_id != symbol:
                            continue
                            
                        # Extract realized PnL components
                        pnl = float(pos.get('pnl', 0) or 0)  # Trading P&L
                        fee = float(pos.get('fee', 0) or 0)  # Trading fee (negative)
                        funding_fee = float(pos.get('fundingFee', 0) or 0)  # Funding fee
                        realized_pnl = float(pos.get('realizedPnl', 0) or 0)  # Total realized
                        
                        # If realizedPnl not available, calculate manually
                        if realized_pnl == 0:
                            realized_pnl = pnl + fee + funding_fee
                        
                        # Parse timestamps
                        open_time = int(pos.get('cTime', 0))
                        close_time = int(pos.get('uTime', 0))
                        
                        trades.append({
                            'id': pos.get('posId', ''),
                            'symbol': inst_id,
                            'direction': pos.get('direction', pos.get('posSide', 'long')),
                            'size': float(pos.get('closeTotalPos', 0) or 0),
                            'entry_price': float(pos.get('openAvgPx', 0) or 0),
                            'exit_price': float(pos.get('closeAvgPx', 0) or 0),
                            'leverage': int(float(pos.get('lever', 1) or 1)),
                            'pnl': realized_pnl,  # 🆕 Use OKX calculated real PnL
                            'pnl_component': {
                                'trading_pnl': pnl,
                                'fee': fee,
                                'funding_fee': funding_fee
                            },
                            'margin': float(pos.get('openMaxPos', 0) or 0) * float(pos.get('openAvgPx', 0) or 0) / int(float(pos.get('lever', 1) or 1)) * 0.01,  # Approximate
                            'close_reason': pos.get('type', 'unknown'),  # 1=Close by user, 2=Liquidation, 3=ADL, 4=System
                            'opened_at': datetime.fromtimestamp(open_time / 1000).isoformat() if open_time else None,
                            'closed_at': datetime.fromtimestamp(close_time / 1000).isoformat() if close_time else None
                        })
                    
                    logger.info(f"[OKXClient] Fetched {len(trades)} closed positions from positions-history API")
                    return trades

                else:
                    logger.warning(f"[OKXClient] positions-history API failed: {data.get('msg')}")
                    # Fallback to trade fills (less accurate)
                    return await self._get_trade_fills_fallback(symbol, limit)

        except Exception as e:
            logger.error(f"Error fetching positions history: {e}")

        return []
    
    async def _get_trade_fills_fallback(self, symbol: str, limit: int) -> List[Dict]:
        """Fallback to trade fills if positions-history fails"""
        try:
            data = await self._request('GET', f'/api/v5/trade/fills?instId={symbol}&limit={limit}')
            
            if data.get('code') == '0':
                return [
                    {
                        'id': t.get('tradeId'),
                        'timestamp': int(t.get('ts', 0)),
                        'side': t.get('side'),
                        'price': float(t.get('fillPx', 0)),
                        'amount': float(t.get('fillSz', 0)),
                        'fee': float(t.get('fee', 0)),
                        'pnl': 0  # fills don't have PnL, need to pair buys/sells
                    }
                    for t in data.get('data', [])
                ]
        except Exception as e:
            logger.error(f"Fallback trade fills also failed: {e}")
        
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
