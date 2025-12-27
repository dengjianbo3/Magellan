"""
OKX Demo Trading Adapter

Adapts OKXClient to match the PaperTrader interface,
allowing the trading system to use OKX demo trading.
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field

import redis.asyncio as redis

from app.core.trading.okx_client import OKXClient, get_okx_client

logger = logging.getLogger(__name__)


@dataclass
class OKXTraderConfig:
    """OKX Trader Configuration"""
    initial_balance: float = 10000.0
    symbol: str = "BTC-USDT-SWAP"
    max_leverage: int = 20
    demo_mode: bool = True


@dataclass
class OKXPosition:
    """Position representation for OKX"""
    id: str
    symbol: str
    direction: str  # "long" or "short"
    size: float  # BTC amount
    entry_price: float
    leverage: int
    margin: float
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    opened_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'symbol': self.symbol,
            'direction': self.direction,
            'size': self.size,
            'entry_price': self.entry_price,
            'leverage': self.leverage,
            'margin': self.margin,
            'take_profit_price': self.take_profit_price,
            'stop_loss_price': self.stop_loss_price,
            'current_price': self.current_price,
            'unrealized_pnl': self.unrealized_pnl,
            'opened_at': self.opened_at.isoformat()
        }


class OKXTrader:
    """
    OKX Demo Trading Adapter

    Wraps OKXClient to provide PaperTrader-compatible interface.
    Uses OKX demo trading API.
    """

    def __init__(self, initial_balance: float = 10000.0, demo_mode: bool = True, config: OKXTraderConfig = None,
                 redis_url: str = "redis://redis:6379"):
        self.config = config or OKXTraderConfig(initial_balance=initial_balance, demo_mode=demo_mode)
        self.initial_balance = self.config.initial_balance
        self.demo_mode = self.config.demo_mode
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
        self._key_prefix = "okx_trader:"
        
        self._okx_client: Optional[OKXClient] = None
        self._initialized = False

        # 🔒 Trade lock - prevents concurrent trading operations
        self._trade_lock = asyncio.Lock()

        # Current position cache
        self._position: Optional[OKXPosition] = None
        self._last_price: Optional[float] = None  # Get real price from API on init
        self._last_price_update: datetime = datetime.now()

        # Trade history
        self._trade_history: List[Dict] = []
        self._equity_history: List[Dict] = []

        # 🆕 Daily loss tracking for circuit breaker
        self._daily_pnl: float = 0.0
        self._daily_pnl_reset_date: datetime = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self._max_daily_loss_percent: float = 10.0  # 10% daily loss limit
        self._is_trading_halted: bool = False

        # 🆕 Saved TP/SL from Redis for recovery after restart
        self._saved_tp_price: Optional[float] = None
        self._saved_sl_price: Optional[float] = None
        self._saved_direction: Optional[str] = None  # 🆕 Fix: Track saved direction to prevent TP/SL mismatch

        # Callbacks (compatible with PaperTrader)
        self.on_position_closed: Optional[Callable] = None
        self.on_tp_hit: Optional[Callable] = None
        self.on_sl_hit: Optional[Callable] = None
        self.on_pnl_update: Optional[Callable] = None

    async def initialize(self):
        """Initialize OKX client"""
        if self._initialized:
            return

        # 🚨 Mode confirmation logging
        if self.demo_mode:
            logger.info("=" * 60)
            logger.info("🧪 INITIALIZING OKX DEMO TRADER")
            logger.info("   This is SIMULATED trading - no real funds at risk")
            logger.info("=" * 60)
        else:
            logger.warning("=" * 60)
            logger.warning("🚨🚨🚨 WARNING: REAL TRADING MODE ACTIVE 🚨🚨🚨")
            logger.warning("   REAL FUNDS ARE AT RISK!")
            logger.warning("   Make sure you have:")
            logger.warning("   - API key with LIMITED permissions (no withdrawal)")
            logger.warning("   - IP whitelist configured")
            logger.warning("   - Tested thoroughly on demo first")
            logger.warning("=" * 60)

        # 🆕 Initialize Redis for state persistence
        try:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            await self._redis.ping()
            logger.info(f"[Redis] Connected to {self.redis_url}")
            
            # Load saved state (trade history, daily PnL, halt status)
            await self._load_state()
        except Exception as e:
            logger.warning(f"[Redis] Not available, using memory only: {e}")
            self._redis = None

        self._okx_client = await get_okx_client()

        # Get initial balance from OKX
        try:
            balance = await self._okx_client.get_account_balance()
            self.initial_balance = balance.total_equity or self.initial_balance
            logger.info(f"OKX {'Demo' if self.demo_mode else 'REAL'} account balance: ${balance.total_equity:.2f}")
        except Exception as e:
            logger.warning(f"Failed to get OKX balance: {e}, using default")

        # Check for existing position
        await self._sync_position()

        self._initialized = True
        logger.info(f"OKX Trader initialized (demo={self.demo_mode})")

    async def _sync_position(self):
        """Sync position from OKX, preserving local TP/SL values"""
        try:
            pos = await self._okx_client.get_current_position()
            if pos:
                # 🆕 FIX: Only use saved TP/SL if direction matches to prevent SHORT TP/SL on LONG position
                # Priority for TP/SL: existing position (same direction) > saved from Redis (if direction matches) > OKX API
                existing_tp = None
                existing_sl = None
                
                if self._position and self._position.direction == pos.direction:
                    # Use existing position's TP/SL (same direction confirmed)
                    existing_tp = self._position.take_profit_price
                    existing_sl = self._position.stop_loss_price
                elif self._saved_direction == pos.direction:
                    # Use saved TP/SL only if direction matches
                    existing_tp = self._saved_tp_price
                    existing_sl = self._saved_sl_price
                    logger.info(f"[_sync_position] Using saved TP/SL (direction {self._saved_direction} matches)")
                else:
                    # Direction mismatch - do NOT use saved TP/SL
                    if self._saved_tp_price or self._saved_sl_price:
                        logger.warning(f"[_sync_position] ⚠️ Discarding saved TP/SL: saved_dir={self._saved_direction}, current_dir={pos.direction}")
                        # Clear stale saved values
                        self._saved_tp_price = None
                        self._saved_sl_price = None
                        self._saved_direction = None
                
                # Use OKX TP/SL if available, otherwise use existing (direction-validated) values
                tp_price = pos.take_profit_price if pos.take_profit_price else existing_tp
                sl_price = pos.stop_loss_price if pos.stop_loss_price else existing_sl
                
                self._position = OKXPosition(
                    id=f"okx-{datetime.now().timestamp()}",
                    symbol=pos.symbol,
                    direction=pos.direction,
                    size=pos.size,
                    entry_price=pos.entry_price,
                    leverage=pos.leverage,
                    margin=pos.margin or 0,
                    take_profit_price=tp_price,  # 🆕 Preserve TP
                    stop_loss_price=sl_price,   # 🆕 Preserve SL
                    current_price=pos.current_price,
                    unrealized_pnl=pos.unrealized_pnl
                )
                
                # 🆕 CRITICAL FIX: Final validation - ensure TP/SL makes sense for direction
                if tp_price and pos.entry_price:
                    if pos.direction == "long" and tp_price < pos.entry_price:
                        logger.critical(f"[TP/SL_VALIDATION] ❌ WRONG DIRECTION TP! LONG position has TP below entry: TP=${tp_price:.2f} < entry=${pos.entry_price:.2f}")
                        self._position.take_profit_price = None
                    elif pos.direction == "short" and tp_price > pos.entry_price:
                        logger.critical(f"[TP/SL_VALIDATION] ❌ WRONG DIRECTION TP! SHORT position has TP above entry: TP=${tp_price:.2f} > entry=${pos.entry_price:.2f}")
                        self._position.take_profit_price = None
                        
                if sl_price and pos.entry_price:
                    if pos.direction == "long" and sl_price > pos.entry_price:
                        logger.critical(f"[TP/SL_VALIDATION] ❌ WRONG DIRECTION SL! LONG position has SL above entry: SL=${sl_price:.2f} > entry=${pos.entry_price:.2f}")
                        self._position.stop_loss_price = None
                    elif pos.direction == "short" and sl_price < pos.entry_price:
                        logger.critical(f"[TP/SL_VALIDATION] ❌ WRONG DIRECTION SL! SHORT position has SL below entry: SL=${sl_price:.2f} < entry=${pos.entry_price:.2f}")
                        self._position.stop_loss_price = None
                
                logger.info(f"Synced position: {pos.direction} {pos.size} BTC @ ${pos.entry_price}, TP=${self._position.take_profit_price}, SL=${self._position.stop_loss_price}")
            else:
                self._position = None
        except Exception as e:
            logger.error(f"Error syncing position: {e}")

    async def _save_state(self):
        """Save trading state to Redis for recovery after restart"""
        if not self._redis:
            return

        try:
            # Save trade history (last 100)
            await self._redis.set(
                f"{self._key_prefix}trade_history",
                json.dumps(self._trade_history[-100:])
            )

            # Save daily tracking state
            daily_state = {
                'daily_pnl': self._daily_pnl,
                'daily_pnl_reset_date': self._daily_pnl_reset_date.isoformat(),
                'is_trading_halted': self._is_trading_halted,
                'max_daily_loss_percent': self._max_daily_loss_percent
            }
            await self._redis.set(
                f"{self._key_prefix}daily_state",
                json.dumps(daily_state)
            )

            # Save equity history (last 1000)
            await self._redis.set(
                f"{self._key_prefix}equity_history",
                json.dumps(self._equity_history[-1000:])
            )

            # 🆕 Save position TP/SL for recovery
            if self._position:
                position_tp_sl = {
                    'take_profit_price': self._position.take_profit_price,
                    'stop_loss_price': self._position.stop_loss_price,
                    'entry_price': self._position.entry_price,
                    'direction': self._position.direction
                }
                await self._redis.set(
                    f"{self._key_prefix}position_tp_sl",
                    json.dumps(position_tp_sl)
                )

            logger.debug("[Redis] State saved successfully")

        except Exception as e:
            logger.error(f"[Redis] Error saving state: {e}")

    async def _load_state(self):
        """Load trading state from Redis on startup"""
        if not self._redis:
            return

        try:
            # Load trade history
            trade_data = await self._redis.get(f"{self._key_prefix}trade_history")
            if trade_data:
                self._trade_history = json.loads(trade_data)
                logger.info(f"[Redis] Loaded {len(self._trade_history)} trades from history")

            # Load daily tracking state
            daily_data = await self._redis.get(f"{self._key_prefix}daily_state")
            if daily_data:
                state = json.loads(daily_data)
                saved_date = datetime.fromisoformat(state.get('daily_pnl_reset_date', datetime.now().isoformat()))
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                
                # Only restore if same day
                if saved_date.date() == today.date():
                    self._daily_pnl = state.get('daily_pnl', 0.0)
                    self._daily_pnl_reset_date = saved_date
                    self._is_trading_halted = state.get('is_trading_halted', False)
                    self._max_daily_loss_percent = state.get('max_daily_loss_percent', 10.0)
                    logger.info(f"[Redis] Restored daily state: PnL=${self._daily_pnl:.2f}, halted={self._is_trading_halted}")
                else:
                    logger.info("[Redis] New day detected, starting fresh daily tracking")

            # Load equity history
            equity_data = await self._redis.get(f"{self._key_prefix}equity_history")
            if equity_data:
                self._equity_history = json.loads(equity_data)
                logger.info(f"[Redis] Loaded {len(self._equity_history)} equity snapshots")

            # 🆕 Load position TP/SL for recovery (with direction validation)
            tp_sl_data = await self._redis.get(f"{self._key_prefix}position_tp_sl")
            if tp_sl_data:
                tp_sl_state = json.loads(tp_sl_data)
                self._saved_tp_price = tp_sl_state.get('take_profit_price')
                self._saved_sl_price = tp_sl_state.get('stop_loss_price')
                self._saved_direction = tp_sl_state.get('direction')  # 🆕 FIX: Load direction to prevent TP/SL mismatch
                logger.info(f"[Redis] Loaded saved TP=${self._saved_tp_price}, SL=${self._saved_sl_price}, dir={self._saved_direction}")

        except Exception as e:
            logger.error(f"[Redis] Error loading state: {e}")

    async def validate_stop_loss_against_liquidation(
        self,
        direction: str,
        entry_price: float,
        sl_price: float,
        leverage: int,
        symbol: str = "BTC-USDT-SWAP"
    ) -> tuple[bool, str, float]:
        """
        Validate stop loss price using OKX-provided liquidation price.
        
        This is more accurate than local calculation because OKX considers:
        - Actual maintenance margin rate
        - Position fees
        - Funding rate impact
        
        Args:
            direction: 'long' or 'short'
            entry_price: Entry price
            sl_price: Proposed stop loss price
            leverage: Position leverage
            symbol: Trading pair
            
        Returns:
            Tuple of (is_safe, message, suggested_sl_price)
        """
        try:
            # Get current position to retrieve OKX-calculated liquidation price
            pos = await self._okx_client.get_current_position(symbol)
            
            if pos and pos.liquidation_price:
                liq_price = pos.liquidation_price
                logger.info(f"[StopLoss] Using OKX liquidation price: ${liq_price:.2f}")
                
                # Calculate safe zone (5% buffer from liquidation)
                if direction == "long":
                    # Long: SL must be ABOVE liquidation price
                    safe_sl = liq_price * 1.05  # 5% above liquidation
                    
                    if sl_price <= liq_price:
                        return False, f"SL ${sl_price:.2f} at/below liquidation ${liq_price:.2f}", safe_sl
                    elif sl_price < safe_sl:
                        return False, f"SL ${sl_price:.2f} too close to liquidation ${liq_price:.2f}, adjusted to ${safe_sl:.2f}", safe_sl
                else:
                    # Short: SL must be BELOW liquidation price
                    safe_sl = liq_price * 0.95  # 5% below liquidation
                    
                    if sl_price >= liq_price:
                        return False, f"SL ${sl_price:.2f} at/above liquidation ${liq_price:.2f}", safe_sl
                    elif sl_price > safe_sl:
                        return False, f"SL ${sl_price:.2f} too close to liquidation ${liq_price:.2f}, adjusted to ${safe_sl:.2f}", safe_sl
                
                return True, "", sl_price
            else:
                # Fallback to local calculation if no position or no liq price
                # This happens when validating before position is opened
                logger.debug("[StopLoss] No OKX liquidation price available, using local calculation")
                
                # Simple local calculation
                margin = entry_price / leverage  # Approximate
                liq_loss = margin * 0.80  # 80% loss triggers liquidation
                size = margin * leverage / entry_price
                
                if size <= 0:
                    return True, "", sl_price
                    
                if direction == "long":
                    liq_price = entry_price - (liq_loss / size)
                    safe_sl = max(liq_price * 1.05, entry_price * 0.97)
                    if sl_price <= liq_price:
                        return False, f"SL ${sl_price:.2f} below calculated liquidation ${liq_price:.2f}", safe_sl
                else:
                    liq_price = entry_price + (liq_loss / size)
                    safe_sl = min(liq_price * 0.95, entry_price * 1.03)
                    if sl_price >= liq_price:
                        return False, f"SL ${sl_price:.2f} above calculated liquidation ${liq_price:.2f}", safe_sl
                        
                return True, "", sl_price
                
        except Exception as e:
            logger.warning(f"[StopLoss] Error validating stop loss: {e}")
            # On error, return safe default without blocking
            return True, f"Warning: Could not validate SL ({e})", sl_price

    def set_price(self, price: float):
        """
        Set price (PaperTrader compatible).

        Note: For OKX, this is a no-op since we always get real-time prices from API.
        This method exists only for interface compatibility with PaperTrader.
        """
        # OKX uses real-time prices from API, but we cache it for compatibility
        if price and price > 0:
            self._last_price = price
            self._last_price_update = datetime.now()

    async def get_current_price(self, symbol: str = "BTC-USDT-SWAP") -> float:
        """Get current market price from OKX"""
        try:
            market = await self._okx_client.get_market_price(symbol)
            self._last_price = market.price
            self._last_price_update = datetime.now()
            return market.price
        except Exception as e:
            logger.error(f"Error getting price: {e}")
            return self._last_price

    async def get_account(self) -> Dict:
        """
        Get account info (PaperTrader compatible)

        OKX directly returns all calculated values, no local calculation needed!
        """
        try:
            balance = await self._okx_client.get_account_balance()

            # OKX directly returns unrealized_pnl, no local calculation needed
            unrealized_pnl = balance.unrealized_pnl or 0.0

            # max_avail_size = OKX calculated real available margin
            # This is obtained via /api/v5/account/max-avail-size API
            max_avail_size = balance.max_avail_size or 0.0

            # Prefer max_avail_size, fallback to available_balance
            true_available_margin = max_avail_size if max_avail_size > 0 else balance.available_balance

            return {
                'total_equity': balance.total_equity,
                'available_balance': balance.available_balance,
                'true_available_margin': true_available_margin,  # Now uses max_avail_size
                'max_avail_size': max_avail_size,  # Pass to trading_meeting.py
                'used_margin': balance.used_margin or 0,
                'unrealized_pnl': unrealized_pnl,
                'realized_pnl': 0.0,  # Can be fetched from API
                'initial_balance': self.initial_balance,
                'currency': 'USDT'
            }
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return {
                'total_equity': self.initial_balance,
                'available_balance': self.initial_balance,
                'true_available_margin': self.initial_balance,
                'max_avail_size': 0,  # 🆕
                'used_margin': 0,
                'unrealized_pnl': 0,
                'realized_pnl': 0.0,
                'initial_balance': self.initial_balance,
                'currency': 'USDT'
            }

    async def get_position(self, symbol: str = "BTC-USDT-SWAP") -> Optional[Dict]:
        """
        Get current position (PaperTrader compatible)
        
        Get all data directly from OKX, including liquidation price.
        Preserves local TP/SL values since OKX algo orders may not be set.
        """
        # Get latest position data directly from OKX API
        try:
            # Save existing TP/SL before updating
            existing_tp = self._position.take_profit_price if self._position else None
            existing_sl = self._position.stop_loss_price if self._position else None
            
            pos = await self._okx_client.get_current_position(symbol)
            
            if not pos:
                self._position = None
                return {'has_position': False}
            
            # Use OKX TP/SL if available, otherwise keep local values
            tp_price = pos.take_profit_price if pos.take_profit_price else existing_tp
            sl_price = pos.stop_loss_price if pos.stop_loss_price else existing_sl
            
            # Update local cache with preserved TP/SL
            self._position = OKXPosition(
                id=f"okx-{datetime.now().timestamp()}",
                symbol=pos.symbol,
                direction=pos.direction,
                size=pos.size,
                entry_price=pos.entry_price,
                leverage=pos.leverage,
                margin=pos.margin or 0,
                take_profit_price=tp_price,  # 🆕 Preserve TP
                stop_loss_price=sl_price,    # 🆕 Preserve SL
                current_price=pos.current_price,
                unrealized_pnl=pos.unrealized_pnl
            )
            
            # Calculate position percentage
            position_percent = (pos.margin / self.initial_balance * 100) if self.initial_balance > 0 else 0
            
            return {
                'has_position': True,
                'symbol': pos.symbol,
                'direction': pos.direction,
                'size': pos.size,
                'entry_price': pos.entry_price,
                'current_price': pos.current_price,
                'leverage': pos.leverage,
                'margin': pos.margin or 0,
                'position_percent': position_percent,  # Consistent with PaperTrader
                'unrealized_pnl': pos.unrealized_pnl,
                'unrealized_pnl_percent': pos.unrealized_pnl_percent,
                'take_profit_price': tp_price,   # 🆕 Return preserved TP
                'stop_loss_price': sl_price,     # 🆕 Return preserved SL
                'liquidation_price': pos.liquidation_price,  # Exchange directly returns liquidation price
                'opened_at': pos.opened_at.isoformat() if pos.opened_at else None
            }
            
        except Exception as e:
            logger.error(f"Error getting position from OKX: {e}")
            
            # Fallback to local cache
            if not self._position:
                return {'has_position': False}

            price = await self.get_current_price(symbol)

            # Local PnL calculation (fallback)
            if self._position.direction == "long":
                pnl = (price - self._position.entry_price) * self._position.size
            else:
                pnl = (self._position.entry_price - price) * self._position.size

            pnl_percent = (pnl / self._position.margin * 100) if self._position.margin > 0 else 0
            position_percent = (self._position.margin / self.initial_balance * 100) if self.initial_balance > 0 else 0

            return {
                'has_position': True,
                'symbol': self._position.symbol,
                'direction': self._position.direction,
                'size': self._position.size,
                'entry_price': self._position.entry_price,
                'current_price': price,
                'leverage': self._position.leverage,
                'margin': self._position.margin,
                'position_percent': position_percent,
                'unrealized_pnl': pnl,
                'unrealized_pnl_percent': pnl_percent,
                'take_profit_price': self._position.take_profit_price,
                'stop_loss_price': self._position.stop_loss_price,
                'liquidation_price': None,  # Local cache has no liquidation price
                'opened_at': self._position.opened_at.isoformat()
            }

    async def open_long(
        self,
        symbol: str,
        leverage: int,
        amount_usdt: float,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None
    ) -> Dict:
        """
        Open long position - PaperTrader.open_long() compatible signature
        """
        return await self.open_position(
            direction="long",
            leverage=leverage,
            amount_usdt=amount_usdt,
            tp_price=tp_price,
            sl_price=sl_price,
            symbol=symbol
        )
    
    async def open_short(
        self,
        symbol: str,
        leverage: int,
        amount_usdt: float,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None
    ) -> Dict:
        """
        Open short position - PaperTrader.open_short() compatible signature
        """
        return await self.open_position(
            direction="short",
            leverage=leverage,
            amount_usdt=amount_usdt,
            tp_price=tp_price,
            sl_price=sl_price,
            symbol=symbol
        )

    async def open_position(
        self,
        direction: str,
        leverage: int,
        amount_usdt: float,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None,
        symbol: str = "BTC-USDT-SWAP"
    ) -> Dict:
        """Open a new position on OKX demo (internal method), supports adding to position"""
        # 🔒 Use trade lock to prevent concurrent operations
        async with self._trade_lock:
            logger.info(f"[TRADE_LOCK] Acquired lock for {direction} position")
            
            # 🆕 Check daily loss limit before opening new positions
            is_allowed, halt_msg = self._check_daily_loss_limit()
            if not is_allowed:
                logger.warning(f"[OKXTrader] Trade rejected: {halt_msg}")
                return {'success': False, 'error': halt_msg}
            
            # Ensure correct types (prevent string input from LLM parsing)
            try:
                leverage = int(leverage) if leverage else 1
                amount_usdt = float(amount_usdt) if amount_usdt else 100
                tp_price = float(tp_price) if tp_price else None
                sl_price = float(sl_price) if sl_price else None
            except (TypeError, ValueError) as e:
                return {'success': False, 'error': f'Parameter type error: {e}'}

            # 🔄 Sync position from OKX before making decisions
            await self._sync_position()

            # Check if there's an existing position
            is_adding = False
            if self._position:
                if self._position.direction != direction:
                    # Different direction, cannot add (need to close first)
                    logger.warning(f"[OKXTrader] Cannot add to position: existing={self._position.direction}, requested={direction}")
                    return {'success': False, 'error': f'Cannot add {direction} to existing {self._position.direction} position'}
                else:
                    # Same direction, can add to position
                    is_adding = True
                    logger.info(f"[OKXTrader] 🔄 Adding to existing {direction} position: +${amount_usdt:.2f}")

            try:
                action = "Adding to" if is_adding else "Opening"
                logger.info(f"[OKXTrader] {action} {direction} position: ${amount_usdt:.2f}, {leverage}x, symbol={symbol}")

                if direction == "long":
                    result = await self._okx_client.open_long(
                        symbol=symbol,
                        leverage=leverage,
                        amount_usdt=amount_usdt,
                        tp_price=tp_price,
                        sl_price=sl_price
                    )
                else:
                    result = await self._okx_client.open_short(
                        symbol=symbol,
                        leverage=leverage,
                        amount_usdt=amount_usdt,
                        tp_price=tp_price,
                        sl_price=sl_price
                    )

                logger.info(f"[OKXTrader] OKX API result: {result}")

                if result.get('success'):
                    executed_price = result.get('executed_price', 0)
                    executed_amount = result.get('executed_amount', 0)
                    order_id = result.get('order_id', f"okx-{datetime.now().timestamp()}")

                    if is_adding and self._position:
                        # Adding to position: update local cache
                        old_size = self._position.size
                        old_margin = self._position.margin
                        old_entry = self._position.entry_price

                        # Calculate new average entry price
                        new_size = old_size + executed_amount
                        new_margin = old_margin + amount_usdt
                        new_entry = (old_entry * old_size + executed_price * executed_amount) / new_size if new_size > 0 else executed_price

                        self._position.size = new_size
                        self._position.margin = new_margin
                        self._position.entry_price = new_entry
                        self._position.current_price = executed_price

                        logger.info(f"OKX position added: {direction} +{executed_amount} BTC @ ${executed_price:.2f}, total={new_size} BTC, avg_entry=${new_entry:.2f}")
                    else:
                        # New position
                        self._position = OKXPosition(
                            id=order_id,
                            symbol=symbol,
                            direction=direction,
                            size=executed_amount,
                            entry_price=executed_price,
                            leverage=leverage,
                            margin=amount_usdt,
                            take_profit_price=tp_price,
                            stop_loss_price=sl_price,
                            current_price=executed_price
                        )
                        logger.info(f"OKX position opened: {direction} {self._position.size} BTC @ ${self._position.entry_price}")
                        
                        # 🆕 FIX: Save state immediately after opening new position
                        # This ensures correct TP/SL and direction are persisted to Redis
                        await self._save_state()
                        logger.info(f"[Redis] Saved new position state: dir={direction}, TP={tp_price}, SL={sl_price}")

                    # Return format consistent with PaperTrader
                    return {
                        'success': True,
                        'order_id': order_id,
                        'direction': direction,
                        'executed_price': executed_price,
                        'executed_amount': executed_amount,
                        'leverage': leverage,
                        'margin': amount_usdt,
                        'take_profit': tp_price,
                        'stop_loss': sl_price,
                        'remaining_balance': 0.0,  # Need to fetch from API
                        'remaining_available_margin': 0.0  # Need to fetch from API
                    }
                else:
                    return {'success': False, 'error': result.get('error', 'Failed to open position')}

            except Exception as e:
                logger.error(f"Error opening position: {e}")
                return {'success': False, 'error': str(e)}

    def _check_daily_loss_limit(self) -> tuple[bool, str]:
        """
        Check if daily loss limit has been hit.
        Returns (is_allowed, message)
        """
        # Reset daily PnL at midnight
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if today > self._daily_pnl_reset_date:
            logger.info(f"[DailyLimit] Resetting daily PnL (was ${self._daily_pnl:.2f})")
            self._daily_pnl = 0.0
            self._daily_pnl_reset_date = today
            self._is_trading_halted = False

        # Check if halted
        if self._is_trading_halted:
            return False, f"Trading halted: daily loss limit hit (${self._daily_pnl:.2f})"

        # Calculate loss percentage
        if self.initial_balance > 0:
            loss_percent = abs(self._daily_pnl) / self.initial_balance * 100
            if self._daily_pnl < 0 and loss_percent >= self._max_daily_loss_percent:
                self._is_trading_halted = True
                logger.warning(f"🚨 [DailyLimit] TRADING HALTED: Daily loss {loss_percent:.1f}% >= {self._max_daily_loss_percent}%")
                return False, f"Trading halted: daily loss {loss_percent:.1f}% exceeds {self._max_daily_loss_percent}% limit"

        return True, ""

    async def reset_daily_pnl(self) -> Dict[str, Any]:
        """
        Reset daily PnL tracking.
        
        Use this when:
        1. Daily PnL data is corrupted
        2. Manual override needed after fixing bugs
        3. Starting fresh for a new trading day
        
        Returns:
            Dict with reset result
        """
        old_pnl = self._daily_pnl
        old_halted = self._is_trading_halted
        
        self._daily_pnl = 0.0
        self._daily_pnl_reset_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self._is_trading_halted = False
        
        # Save to Redis
        await self._save_state()
        
        logger.info(f"[DailyLimit] ⚠️ RESET: Daily PnL reset from ${old_pnl:.2f} to $0, halted={old_halted} -> False")
        
        return {
            "success": True,
            "old_daily_pnl": old_pnl,
            "old_is_halted": old_halted,
            "new_daily_pnl": 0.0,
            "new_is_halted": False,
            "message": f"Daily PnL reset from ${old_pnl:.2f} to $0.00"
        }

    async def close_position(self, symbol: str = "BTC-USDT-SWAP", reason: str = "manual") -> Optional[Dict]:
        """Close current position on OKX demo"""
        # 🔒 Use trade lock
        async with self._trade_lock:
            logger.info(f"[TRADE_LOCK] Acquired lock for close_position")
            
            if not self._position:
                return None

            try:
                # Get current price for PnL calculation
                price = await self.get_current_price(symbol)

                # Calculate PnL
                if self._position.direction == "long":
                    pnl = (price - self._position.entry_price) * self._position.size
                else:
                    pnl = (self._position.entry_price - price) * self._position.size

                # Close on OKX
                result = await self._okx_client.close_position(symbol)

                if result.get('success'):
                    # 🆕 Update daily PnL tracking
                    self._daily_pnl += pnl
                    logger.info(f"[DailyLimit] Trade PnL: ${pnl:.2f}, Daily total: ${self._daily_pnl:.2f}")
                    
                    # Record trade
                    trade_record = {
                        'id': self._position.id,
                        'symbol': symbol,
                        'direction': self._position.direction,
                        'size': self._position.size,
                        'entry_price': self._position.entry_price,
                        'exit_price': price,
                        'leverage': self._position.leverage,
                        'pnl': pnl,
                        'close_reason': reason,
                        'opened_at': self._position.opened_at.isoformat(),
                        'closed_at': datetime.now().isoformat()
                    }
                    self._trade_history.append(trade_record)

                    closed_position = self._position
                    self._position = None
                    
                    # 🆕 FIX: Clear saved TP/SL to prevent stale values being used for new positions
                    self._saved_tp_price = None
                    self._saved_sl_price = None
                    self._saved_direction = None

                    logger.info(f"OKX position closed: PnL=${pnl:.2f} ({reason})")

                    # 🆕 Save state to Redis after trade
                    await self._save_state()

                    # Trigger callback
                    if self.on_position_closed:
                        await self.on_position_closed(closed_position, pnl, reason)

                    return {
                        'success': True,
                        'pnl': pnl,
                        'exit_price': price,
                        'trade': trade_record
                    }
                else:
                    return {'success': False, 'error': result.get('error', 'Failed to close position')}

            except Exception as e:
                logger.error(f"Error closing position: {e}")
                return {'success': False, 'error': str(e)}

    async def check_tp_sl(self) -> Optional[str]:
        """
        Check if TP/SL is hit.
        Note: OKX handles TP/SL server-side, but we still check for local tracking.
        """
        if not self._position:
            return None

        price = await self.get_current_price()

        # Check take profit
        if self._position.take_profit_price:
            if self._position.direction == "long" and price >= self._position.take_profit_price:
                logger.info(f"Take profit hit: {price} >= {self._position.take_profit_price}")
                if self.on_tp_hit:
                    await self.on_tp_hit(self._position, price)
                return "tp"
            elif self._position.direction == "short" and price <= self._position.take_profit_price:
                logger.info(f"Take profit hit: {price} <= {self._position.take_profit_price}")
                if self.on_tp_hit:
                    await self.on_tp_hit(self._position, price)
                return "tp"

        # Check stop loss
        if self._position.stop_loss_price:
            if self._position.direction == "long" and price <= self._position.stop_loss_price:
                logger.info(f"Stop loss hit: {price} <= {self._position.stop_loss_price}")
                if self.on_sl_hit:
                    await self.on_sl_hit(self._position, price)
                return "sl"
            elif self._position.direction == "short" and price >= self._position.stop_loss_price:
                logger.info(f"Stop loss hit: {price} >= {self._position.stop_loss_price}")
                if self.on_sl_hit:
                    await self.on_sl_hit(self._position, price)
                return "sl"

        return None

    async def get_equity_history(self, limit: int = 100) -> List[Dict]:
        """Get equity history"""
        # Record current equity
        account = await self.get_account()
        self._equity_history.append({
            'timestamp': datetime.now().isoformat(),
            'equity': account.get('total_equity', self.initial_balance)
        })

        # Keep only last N records
        if len(self._equity_history) > limit * 2:
            self._equity_history = self._equity_history[-limit:]

        return self._equity_history[-limit:]

    def get_status(self) -> Dict:
        """Get trader status (PaperTrader compatible)"""
        # Calculate daily loss percentage
        daily_loss_percent = (abs(self._daily_pnl) / self.initial_balance * 100) if self.initial_balance > 0 and self._daily_pnl < 0 else 0
        
        return {
            'initialized': self._initialized,
            'type': 'okx_demo' if self.demo_mode else 'okx_real',
            'demo_mode': self.demo_mode,
            'has_position': self._position is not None,
            'position_direction': self._position.direction if self._position else None,
            'current_price': self._last_price,
            'balance': self.initial_balance,
            'equity': self.initial_balance,
            'total_trades': len(self._trade_history),
            'win_rate': self._calculate_win_rate(),
            'realized_pnl': sum(t.get('pnl', 0) for t in self._trade_history),
            # 🆕 Daily loss tracking
            'daily_pnl': self._daily_pnl,
            'daily_loss_percent': daily_loss_percent,
            'max_daily_loss_percent': self._max_daily_loss_percent,
            'is_trading_halted': self._is_trading_halted
        }

    def _calculate_win_rate(self) -> str:
        if not self._trade_history:
            return "0.0%"
        wins = sum(1 for t in self._trade_history if t.get('pnl', 0) > 0)
        return f"{(wins / len(self._trade_history) * 100):.1f}%"
    
    async def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """
        Get trade history with REAL PnL from OKX API.
        
        Uses OKX's /api/v5/account/positions-history endpoint for accurate 
        realized PnL (including fees and funding).
        
        Falls back to local history if API fails.
        """
        try:
            # 🆕 Get real trade history from OKX API
            if self._okx_client:
                okx_trades = await self._okx_client.get_trade_history(limit=limit)
                
                if okx_trades:
                    logger.info(f"[OKXTrader] Retrieved {len(okx_trades)} trades from OKX positions-history API")
                    return okx_trades
            
            logger.warning("[OKXTrader] OKX API unavailable, using local history (PnL may be inaccurate)")
            
        except Exception as e:
            logger.error(f"[OKXTrader] Error fetching OKX trade history: {e}")
        
        # Fallback to local history
        return self._trade_history[-limit:]
    
    async def reset(self):
        """
        Reset trader state (PaperTrader compatible)
        
        Note: For OKX demo, this only resets local state.
        OKX demo account balance persists on their server.
        """
        logger.info("Resetting OKX trader local state...")
        
        # Close any open position first
        if self._position:
            try:
                await self.close_position(reason="reset")
            except Exception as e:
                logger.error(f"Error closing position during reset: {e}")
        
        # Reset local state
        self._position = None
        self._trade_history = []
        self._equity_history = []
        self._last_price = None
        
        # Re-sync with OKX
        await self._sync_position()
        
        logger.info("OKX trader reset complete")

    def calculate_max_drawdown(self, start_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate maximum drawdown from trade history.
        
        Args:
            start_date: Optional start date in ISO format (YYYY-MM-DD). 
                       If provided, only trades after this date are considered.
        
        Returns:
            Dict with drawdown metrics:
            - max_drawdown_pct: Maximum drawdown percentage
            - max_drawdown_usd: Maximum drawdown in USD
            - peak_equity: Peak equity value
            - trough_equity: Trough equity value
            - current_drawdown_pct: Current drawdown from peak
            - recovery_pct: Recovery percentage from trough
            - start_date: Start date used for calculation
            - trades_analyzed: Number of trades analyzed
        """
        # Filter trades by date if provided
        trades = self._trade_history
        if start_date:
            try:
                filter_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                trades = [
                    t for t in self._trade_history 
                    if datetime.fromisoformat(t.get('closed_at', t.get('timestamp', '2000-01-01')).replace('Z', '+00:00')) >= filter_date
                ]
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid start_date format: {start_date}, using all trades. Error: {e}")
        
        if not trades:
            return {
                'max_drawdown_pct': 0.0,
                'max_drawdown_usd': 0.0,
                'peak_equity': self.initial_balance,
                'trough_equity': self.initial_balance,
                'current_drawdown_pct': 0.0,
                'recovery_pct': 100.0,
                'start_date': start_date,
                'trades_analyzed': 0
            }
        
        # Calculate cumulative equity curve
        equity_curve = [self.initial_balance]
        running_equity = self.initial_balance
        
        for trade in trades:
            pnl = trade.get('pnl', 0)
            running_equity += pnl
            equity_curve.append(running_equity)
        
        # Calculate max drawdown
        peak = equity_curve[0]
        max_drawdown = 0.0
        max_drawdown_pct = 0.0
        trough = peak
        peak_at_max_dd = peak
        trough_at_max_dd = peak
        
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            
            drawdown = peak - equity
            drawdown_pct = (drawdown / peak * 100) if peak > 0 else 0
            
            if drawdown_pct > max_drawdown_pct:
                max_drawdown_pct = drawdown_pct
                max_drawdown = drawdown
                peak_at_max_dd = peak
                trough_at_max_dd = equity
        
        # Current drawdown from current peak
        current_equity = equity_curve[-1]
        current_peak = max(equity_curve)
        current_drawdown_pct = ((current_peak - current_equity) / current_peak * 100) if current_peak > 0 else 0
        
        # Recovery percentage (how much recovered from max trough)
        if max_drawdown > 0:
            recovery_pct = min(100.0, ((current_equity - trough_at_max_dd) / max_drawdown * 100)) if max_drawdown > 0 else 100.0
        else:
            recovery_pct = 100.0
        
        return {
            'max_drawdown_pct': round(max_drawdown_pct, 2),
            'max_drawdown_usd': round(max_drawdown, 2),
            'peak_equity': round(peak_at_max_dd, 2),
            'trough_equity': round(trough_at_max_dd, 2),
            'current_equity': round(current_equity, 2),
            'current_drawdown_pct': round(current_drawdown_pct, 2),
            'recovery_pct': round(max(0, min(100, recovery_pct)), 2),
            'start_date': start_date,
            'trades_analyzed': len(trades)
        }

    async def calculate_performance_metrics(self, start_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate performance metrics: Sharpe Ratio, Sortino Ratio, Alpha, etc.
        
        Args:
            start_date: Optional start date in ISO format (YYYY-MM-DD).
        
        Returns:
            Dict with performance metrics
        """
        import math
        
        # Get trade history
        trades = await self.get_trade_history(limit=200)
        
        if start_date:
            try:
                filter_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                trades = [
                    t for t in trades 
                    if datetime.fromisoformat(t.get('closed_at', '2000-01-01').replace('Z', '+00:00')) >= filter_date
                ]
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid start_date format: {start_date}, using all trades. Error: {e}")
        
        if not trades or len(trades) < 2:
            return {
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'alpha': 0.0,
                'beta': 1.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'avg_profit': 0.0,
                'avg_loss': 0.0,
                'total_return_pct': 0.0,
                'annualized_return_pct': 0.0,
                'volatility_pct': 0.0,
                'best_trade': 0.0,
                'worst_trade': 0.0,
                'avg_holding_hours': 0.0,
                'trades_analyzed': len(trades),
                'start_date': start_date
            }
        
        # Extract PnL data
        pnl_list = [t.get('pnl', 0) for t in trades]
        # Calculate pnl_percent from pnl/margin if not provided (OKX API doesn't return pnl_percent)
        pnl_pct_list = []
        for t in trades:
            pnl = t.get('pnl', 0)
            margin = t.get('margin', 0)
            if margin > 0:
                pnl_pct_list.append((pnl / margin) * 100)
            else:
                pnl_pct_list.append(t.get('pnl_percent', 0))
        
        # Basic stats
        total_pnl = sum(pnl_list)
        wins = [p for p in pnl_list if p > 0]
        losses = [p for p in pnl_list if p < 0]
        
        win_rate = len(wins) / len(pnl_list) * 100 if pnl_list else 0
        avg_profit = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        # Profit factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
        
        # Returns
        initial = self.initial_balance
        current_equity = initial + total_pnl
        total_return_pct = ((current_equity - initial) / initial) * 100 if initial > 0 else 0
        
        # Calculate holding time
        holding_hours = []
        for t in trades:
            try:
                opened = datetime.fromisoformat(t.get('opened_at', '').replace('Z', '+00:00'))
                closed = datetime.fromisoformat(t.get('closed_at', '').replace('Z', '+00:00'))
                hours = (closed - opened).total_seconds() / 3600
                holding_hours.append(hours)
            except:
                pass
        
        avg_holding_hours = sum(holding_hours) / len(holding_hours) if holding_hours else 0
        
        # Trading days for annualization
        if trades:
            try:
                # trades are sorted NEWEST first, so:
                # trades[-1] = oldest (first) trade
                # trades[0] = newest (last) trade
                oldest_trade = datetime.fromisoformat(trades[-1].get('closed_at', '').replace('Z', '+00:00'))
                newest_trade = datetime.fromisoformat(trades[0].get('closed_at', '').replace('Z', '+00:00'))
                trading_days = max(1, (newest_trade - oldest_trade).days)
                logger.debug(f"[Annualization] Oldest trade: {oldest_trade}, Newest: {newest_trade}, Trading days: {trading_days}")
            except Exception as e:
                logger.warning(f"Failed to calculate trading days: {e}")
                trading_days = len(trades)
        else:
            trading_days = 1
        
        # Annualized return (assuming 365 days per year)
        annualized_return_pct = (total_return_pct / trading_days) * 365 if trading_days > 0 else 0
        
        # Volatility (standard deviation of returns)
        if len(pnl_pct_list) > 1:
            mean_return = sum(pnl_pct_list) / len(pnl_pct_list)
            variance = sum((r - mean_return) ** 2 for r in pnl_pct_list) / (len(pnl_pct_list) - 1)
            volatility_pct = math.sqrt(variance)
        else:
            volatility_pct = 0
            mean_return = 0
        
        # Sharpe Ratio (risk-free rate assumed 0 for crypto)
        # Sharpe = (Mean Return - Risk Free Rate) / Volatility
        # Annualized: multiply by sqrt(trades_per_year)
        trades_per_year = (len(trades) / trading_days) * 365 if trading_days > 0 else len(trades)
        if volatility_pct > 0:
            sharpe_ratio = (mean_return / volatility_pct) * math.sqrt(trades_per_year)
        else:
            sharpe_ratio = 0
        
        # Sortino Ratio (only considers downside volatility)
        downside_returns = [r for r in pnl_pct_list if r < 0]
        if len(downside_returns) > 1:
            downside_variance = sum((r) ** 2 for r in downside_returns) / (len(downside_returns) - 1)
            downside_volatility = math.sqrt(downside_variance)
            if downside_volatility > 0:
                sortino_ratio = (mean_return / downside_volatility) * math.sqrt(trades_per_year)
            else:
                sortino_ratio = float('inf') if mean_return > 0 else 0
        else:
            sortino_ratio = sharpe_ratio  # Fallback to Sharpe if not enough downside data
        
        # Beta (sensitivity to market) - simplified: using BTC price changes
        # For simplicity, assume beta = 1 for crypto trading (moves with market)
        beta = 1.0
        
        # Alpha (excess return over benchmark = strategy return - BTC return)
        # Get BTC benchmark: from first trade entry price to current price
        btc_benchmark_return = 0.0
        try:
            # Get first trade entry price (oldest trade)
            first_trade = trades[-1] if trades else None  # trades are sorted newest first
            if first_trade and first_trade.get('entry_price'):
                first_trade_price = float(first_trade.get('entry_price', 0))
                # Get current BTC price
                current_price = await self.get_current_price()
                if first_trade_price > 0 and current_price > 0:
                    btc_benchmark_return = ((current_price - first_trade_price) / first_trade_price) * 100
                    logger.info(f"[Alpha] First trade price: ${first_trade_price:.2f}, Current: ${current_price:.2f}, BTC return: {btc_benchmark_return:.2f}%")
        except Exception as e:
            logger.warning(f"Failed to calculate BTC benchmark for Alpha: {e}")
            btc_benchmark_return = 0.0
        
        # Alpha = Strategy Return - BTC Benchmark Return
        alpha = total_return_pct - btc_benchmark_return
        
        best_trade = max(pnl_list) if pnl_list else 0
        worst_trade = min(pnl_list) if pnl_list else 0
        
        return {
            'sharpe_ratio': round(sharpe_ratio, 2),
            'sortino_ratio': round(min(sortino_ratio, 99.99), 2),  # Cap extreme values
            'alpha': round(alpha, 2),
            'beta': round(beta, 2),
            'btc_benchmark_return': round(btc_benchmark_return, 2),  # BTC same-period return
            'win_rate': round(win_rate, 2),
            'profit_factor': round(min(profit_factor, 99.99), 2),  # Cap extreme values
            'avg_profit': round(avg_profit, 2),
            'avg_loss': round(avg_loss, 2),
            'total_return_pct': round(total_return_pct, 2),
            'annualized_return_pct': round(annualized_return_pct, 2),
            'volatility_pct': round(volatility_pct, 2),
            'best_trade': round(best_trade, 2),
            'worst_trade': round(worst_trade, 2),
            'avg_holding_hours': round(avg_holding_hours, 2),
            'trades_analyzed': len(trades),
            'start_date': start_date
        }


# Singleton

_okx_trader: Optional[OKXTrader] = None


async def get_okx_trader(initial_balance: float = 10000.0) -> OKXTrader:
    """Get or create OKX trader singleton"""
    global _okx_trader
    if _okx_trader is None:
        _okx_trader = OKXTrader(initial_balance=initial_balance)
        await _okx_trader.initialize()
    return _okx_trader
