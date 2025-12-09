"""
Paper Trading Simulator

Local trading simulator, no real exchange connection required.
Provides complete simulated trading features:
- Simulated account balance
- Simulated open/close positions
- Simulated TP/SL triggers
- Real-time price simulation (based on real market data or random fluctuation)
- Trade history records
"""

import asyncio
import logging
import os
import uuid
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
import json

import redis.asyncio as redis

from app.core.trading.price_service import get_price_service, PriceService
from app.core.trading.base_trader import BaseTrader

logger = logging.getLogger(__name__)


def _get_env_float(key: str, default: float) -> float:
    """Get float from environment variable"""
    val = os.getenv(key)
    if val:
        try:
            return float(val)
        except ValueError:
            pass
    return default


@dataclass
class PaperTraderConfig:
    """Paper Trader Configuration"""
    initial_balance: float = 10000.0
    max_leverage: int = 20
    min_price: float = 1000.0  # Min price limit (for price simulation)
    max_price: float = 500000.0  # Max price limit (for price simulation)
    redis_url: str = "redis://redis:6379"
    demo_mode: bool = False  # False = use real CoinGecko price, True = simulated price
    # Default TP/SL percentages - read from environment variables
    default_tp_percent: float = field(default_factory=lambda: _get_env_float("DEFAULT_TP_PERCENT", 5.0))
    default_sl_percent: float = field(default_factory=lambda: _get_env_float("DEFAULT_SL_PERCENT", 2.0))


@dataclass
class PaperPosition:
    """Simulated Position"""
    id: str
    symbol: str
    direction: str  # "long" or "short"
    size: float  # Position size (BTC)
    entry_price: float
    leverage: int
    margin: float  # Margin used
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    opened_at: datetime = field(default_factory=datetime.now)

    def calculate_pnl(self, current_price: float) -> tuple[float, float]:
        """Calculate unrealized PnL"""
        if self.direction == "long":
            pnl = (current_price - self.entry_price) * self.size
        else:
            pnl = (self.entry_price - current_price) * self.size

        pnl_percent = (pnl / self.margin) * 100 if self.margin > 0 else 0
        return pnl, pnl_percent

    def calculate_liquidation_price(self) -> float:
        """Calculate liquidation price (simplified)"""
        # FIX: Prevent division by zero
        if self.size <= 0:
            # Cannot calculate liquidation price, return extreme value
            return 0 if self.direction == "long" else float('inf')

        # Liquidate when loss reaches 80% of margin
        liquidation_loss = self.margin * 0.8
        if self.direction == "long":
            return self.entry_price - (liquidation_loss / self.size)
        else:
            return self.entry_price + (liquidation_loss / self.size)

    def to_dict(self) -> Dict:
        data = asdict(self)
        data['opened_at'] = self.opened_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'PaperPosition':
        if 'opened_at' in data and isinstance(data['opened_at'], str):
            data['opened_at'] = datetime.fromisoformat(data['opened_at'])
        return cls(**data)


@dataclass
class PaperTrade:
    """Simulated Trade Record"""
    id: str
    symbol: str
    direction: str
    size: float
    entry_price: float
    exit_price: float
    leverage: int
    pnl: float
    pnl_percent: float
    close_reason: str  # "tp", "sl", "manual", "signal", "liquidation"
    opened_at: datetime
    closed_at: datetime

    def to_dict(self) -> Dict:
        data = asdict(self)
        data['opened_at'] = self.opened_at.isoformat()
        data['closed_at'] = self.closed_at.isoformat()
        return data


@dataclass
class PaperAccount:
    """Simulated Account"""
    initial_balance: float = 10000.0
    balance: float = 10000.0  # Available balance
    total_equity: float = 10000.0  # Total equity (balance + unrealized PnL)
    used_margin: float = 0.0  # Used margin
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0  # Realized PnL
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0

    @property
    def win_rate(self) -> float:
        return self.winning_trades / self.total_trades if self.total_trades > 0 else 0

    @property
    def total_pnl(self) -> float:
        return self.realized_pnl + self.unrealized_pnl

    @property
    def total_pnl_percent(self) -> float:
        return (self.total_pnl / self.initial_balance) * 100

    def to_dict(self) -> Dict:
        return asdict(self)


class PaperTrader(BaseTrader):
    """
    Local Paper Trading Simulator

    Inherits from BaseTrader to provide consistent interface.
    
    Features:
    - Runs fully locally, no external API required
    - Simulated account balance and positions
    - Simulated TP/SL triggers
    - Real-time price simulation
    - Trade history persisted to Redis
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        redis_url: str = "redis://redis:6379",
        demo_mode: bool = False,  # False = use real CoinGecko price, True = simulated price
        config: PaperTraderConfig = None
    ):
        # Use config or individual parameters
        self.config = config or PaperTraderConfig(
            initial_balance=initial_balance,
            redis_url=redis_url,
            demo_mode=demo_mode
        )
        self.initial_balance = self.config.initial_balance
        self.redis_url = self.config.redis_url
        self.demo_mode = self.config.demo_mode

        self._redis: Optional[redis.Redis] = None
        self._account = PaperAccount(
            initial_balance=self.initial_balance,
            balance=self.initial_balance,
            total_equity=self.initial_balance
        )
        self._position: Optional[PaperPosition] = None
        self._trades: List[PaperTrade] = []
        self._equity_history: List[Dict] = []

        # Price service - use real or simulated price
        self._price_service: Optional[PriceService] = None
        self._current_price: Optional[float] = None  # Cache current price, fetched from API on init
        self._price_history: List[float] = []
        self._last_price_update = datetime.now()

        # Callbacks
        self.on_position_closed = None
        self.on_tp_hit = None
        self.on_sl_hit = None

        self._initialized = False
        self._key_prefix = "paper_trader:"
        
        # 🔒 CRITICAL: Add trade lock to prevent duplicate trades
        self._trade_lock = asyncio.Lock()

    async def initialize(self):
        """Initialize and load historical data"""
        if self._initialized:
            return

        try:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            await self._redis.ping()

            # Load account state
            await self._load_state()
            logger.info(f"Paper trader initialized. Balance: ${self._account.balance:.2f}")

        except Exception as e:
            logger.warning(f"Redis not available, using memory only: {e}")

        # Initialize price service
        self._price_service = await get_price_service(demo_mode=self.demo_mode)
        self._current_price = await self._price_service.get_btc_price()
        logger.info(f"Price service initialized. Current BTC price: ${self._current_price:,.2f}")

        self._initialized = True

    async def _load_state(self):
        """Load state from Redis"""
        if not self._redis:
            return

        try:
            # Load account
            account_data = await self._redis.get(f"{self._key_prefix}account")
            if account_data:
                data = json.loads(account_data)
                self._account = PaperAccount(**data)

            # Load position
            position_data = await self._redis.get(f"{self._key_prefix}position")
            if position_data:
                self._position = PaperPosition.from_dict(json.loads(position_data))

            # Load trade history
            trades_data = await self._redis.get(f"{self._key_prefix}trades")
            if trades_data:
                self._trades = [
                    PaperTrade(**{**t,
                        'opened_at': datetime.fromisoformat(t['opened_at']),
                        'closed_at': datetime.fromisoformat(t['closed_at'])
                    })
                    for t in json.loads(trades_data)
                ]

            # Load equity history
            equity_data = await self._redis.get(f"{self._key_prefix}equity_history")
            if equity_data:
                self._equity_history = json.loads(equity_data)

        except Exception as e:
            logger.error(f"Error loading state: {e}")

    async def _save_state(self):
        """Save state to Redis"""
        if not self._redis:
            return

        try:
            # Save account
            await self._redis.set(
                f"{self._key_prefix}account",
                json.dumps(self._account.to_dict())
            )

            # Save position
            if self._position:
                await self._redis.set(
                    f"{self._key_prefix}position",
                    json.dumps(self._position.to_dict())
                )
            else:
                await self._redis.delete(f"{self._key_prefix}position")

            # Save trade history (keep last 100 only)
            await self._redis.set(
                f"{self._key_prefix}trades",
                json.dumps([t.to_dict() for t in self._trades[-100:]])
            )

            # Save equity history (keep last 1000 only)
            await self._redis.set(
                f"{self._key_prefix}equity_history",
                json.dumps(self._equity_history[-1000:])
            )

        except Exception as e:
            logger.error(f"Error saving state: {e}")

    async def get_current_price(self, symbol: str = "BTC-USDT-SWAP") -> float:
        """Get current price - use price service for real/simulated price"""
        now = datetime.now()

        # Use price service to get price (update at most once per second)
        if (now - self._last_price_update).seconds >= 1:
            if self._price_service:
                self._current_price = await self._price_service.get_btc_price()
            else:
                # Fallback: simple simulated fluctuation
                change = random.uniform(-0.001, 0.001)
                self._current_price *= (1 + change)
                self._current_price = max(self.config.min_price, min(self.config.max_price, self._current_price))

            self._last_price_update = now
            self._price_history.append(self._current_price)
            if len(self._price_history) > 10000:
                self._price_history = self._price_history[-10000:]

        return self._current_price

    def set_price(self, price: float):
        """Manually set current price (for testing or syncing real price)"""
        self._current_price = price
        self._last_price_update = datetime.now()

    async def update_price(self, price: float):
        """
        Update current market price (implements BaseTrader interface).
        
        Args:
            price: Current market price
        """
        self._current_price = price
        self._last_price_update = datetime.now()
        self._price_history.append(price)
        if len(self._price_history) > 10000:
            self._price_history = self._price_history[-10000:]

    async def get_account(self) -> Dict:
        """Get account info - including true available margin"""
        await self._update_equity()

        # True available margin = total equity - used margin
        # This accounts for unrealized PnL impact on available funds
        true_available_margin = self._account.total_equity - self._account.used_margin

        return {
            "total_equity": self._account.total_equity,
            "available_balance": self._account.balance,
            "true_available_margin": true_available_margin,  # True available margin
            "used_margin": self._account.used_margin,
            "unrealized_pnl": self._account.unrealized_pnl,
            "realized_pnl": self._account.realized_pnl,
            "total_pnl": self._account.total_pnl,
            "total_pnl_percent": self._account.total_pnl_percent,
            "win_rate": self._account.win_rate,
            "total_trades": self._account.total_trades,
            "currency": "USDT"
        }

    async def get_position(self, symbol: str = "BTC-USDT-SWAP") -> Optional[Dict]:
        """Get current position"""
        if not self._position or self._position.symbol != symbol:
            return None

        current_price = await self.get_current_price(symbol)
        pnl, pnl_percent = self._position.calculate_pnl(current_price)

        # Calculate position percentage (margin / initial_balance * 100)
        position_percent = (self._position.margin / self.initial_balance * 100) if self.initial_balance > 0 else 0

        return {
            "has_position": True,
            "symbol": self._position.symbol,
            "direction": self._position.direction,
            "size": self._position.size,
            "entry_price": self._position.entry_price,
            "current_price": current_price,
            "leverage": self._position.leverage,
            "margin": self._position.margin,
            "position_percent": position_percent,  # Position percentage
            "unrealized_pnl": pnl,
            "unrealized_pnl_percent": pnl_percent,
            "take_profit_price": self._position.take_profit_price,
            "stop_loss_price": self._position.stop_loss_price,
            "liquidation_price": self._position.calculate_liquidation_price(),
            "opened_at": self._position.opened_at.isoformat()
        }

    async def open_long(
        self,
        symbol: str,
        leverage: int,
        amount_usdt: float,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None
    ) -> Dict:
        """Open long position"""
        return await self._open_position(
            symbol=symbol,
            direction="long",
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
    ) -> Dict:
        """Open short position"""
        return await self._open_position(
            symbol=symbol,
            direction="short",
            leverage=leverage,
            amount_usdt=amount_usdt,
            tp_price=tp_price,
            sl_price=sl_price
        )

    async def _open_position(
        self,
        symbol: str,
        direction: str,
        leverage: int,
        amount_usdt: float,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None
    ) -> Dict:
        """Open position - enhanced balance check"""
        # CRITICAL: Use lock to prevent duplicate trades
        async with self._trade_lock:
            logger.info(f"[TRADE_LOCK] Acquired lock for {direction} position")

            if self._position:
                logger.warning(f"[TRADE_LOCK] Cannot open {direction}: already have a {self._position.direction} position")
                return {
                    "success": False,
                    "error": f"Already have position ({self._position.direction}), please close it first"
                }

            # Ensure correct types (prevent string input from LLM parsing)
            try:
                amount_usdt = float(amount_usdt)
                leverage = int(leverage)
            except (TypeError, ValueError) as e:
                return {
                    "success": False,
                    "error": f"Parameter type error: {e}"
                }

            # Update equity, calculate true available margin
            await self._update_equity()
            true_available_margin = self._account.total_equity - self._account.used_margin

            # Check 1: Is true available margin sufficient
            if amount_usdt > true_available_margin:
                return {
                    "success": False,
                    "error": (
                        f"Insufficient margin! Required: ${amount_usdt:.2f}, "
                        f"True available: ${true_available_margin:.2f} "
                        f"(Total equity: ${self._account.total_equity:.2f} - "
                        f"Used: ${self._account.used_margin:.2f})"
                    )
                }

            # Check 2: Is account balance sufficient (for deduction)
            if amount_usdt > self._account.balance:
                unrealized_loss = -self._account.unrealized_pnl if self._account.unrealized_pnl < 0 else 0
                return {
                    "success": False,
                    "error": (
                        f"Insufficient balance! Required: ${amount_usdt:.2f}, "
                        f"Available balance: ${self._account.balance:.2f}. "
                        f"{'Unrealized loss: $' + f'{unrealized_loss:.2f}, ' if unrealized_loss > 0 else ''}"
                        f"Suggest closing position or reducing amount"
                    )
                }

            # Limit leverage (1 to max_leverage)
            leverage = min(max(1, leverage), self.config.max_leverage)

            current_price = await self.get_current_price(symbol)

            # Calculate position size
            position_value = amount_usdt * leverage
            size = position_value / current_price

            # Recalculate TP/SL prices (based on actual entry price, not LLM expected price)
            # If provided tp/sl prices don't match actual entry price, use default percentages
            if tp_price is not None and sl_price is not None:
                if direction == "long":
                    # Long: TP should be above entry, SL should be below entry
                    if tp_price <= current_price or sl_price >= current_price:
                        # Invalid TP/SL prices, recalculate using default percentages
                        logger.warning(
                            f"Invalid TP/SL prices (tp={tp_price}, sl={sl_price}, entry={current_price}), "
                            f"recalculating using default percentages"
                        )
                        tp_price = current_price * (1 + self.config.default_tp_percent / 100)
                        sl_price = current_price * (1 - self.config.default_sl_percent / 100)
                else:  # short
                    # Short: TP should be below entry, SL should be above entry
                    if tp_price >= current_price or sl_price <= current_price:
                        logger.warning(
                            f"Invalid TP/SL prices (tp={tp_price}, sl={sl_price}, entry={current_price}), "
                            f"recalculating using default percentages"
                        )
                        tp_price = current_price * (1 - self.config.default_tp_percent / 100)
                        sl_price = current_price * (1 + self.config.default_sl_percent / 100)

            logger.info(f"Open position params: entry={current_price}, tp={tp_price}, sl={sl_price}")

            # Create position
            self._position = PaperPosition(
            id=str(uuid.uuid4()),
            symbol=symbol,
            direction=direction,
            size=size,
            entry_price=current_price,
            leverage=leverage,
            margin=amount_usdt,
            take_profit_price=tp_price,
            stop_loss_price=sl_price
        )

        # Update account
        self._account.balance -= amount_usdt
        self._account.used_margin += amount_usdt

        await self._save_state()

        logger.info(
            f"✅ [TRADE_LOCK] Position opened: {direction.upper()} {size:.6f} BTC @ ${current_price:.2f}, "
            f"leverage: {leverage}x, margin: ${amount_usdt:.2f}, "
            f"remaining: ${self._account.balance:.2f}"
        )
        logger.info(f"[TRADE_LOCK] Releasing lock after successful {direction} position")

        return {
            "success": True,
            "order_id": self._position.id,
            "direction": direction,
            "executed_price": current_price,
            "executed_amount": size,
            "leverage": leverage,
            "margin": amount_usdt,
            "take_profit": tp_price,
            "stop_loss": sl_price,
            "remaining_balance": self._account.balance,
            "remaining_available_margin": self._account.total_equity - self._account.used_margin
        }

    async def close_position(self, symbol: str = "BTC-USDT-SWAP", reason: str = "manual") -> Dict:
        """Close position"""
        if not self._position:
            return {
                "success": False,
                "error": "No position to close"
            }

        current_price = await self.get_current_price(symbol)
        pnl, pnl_percent = self._position.calculate_pnl(current_price)

        # Create trade record
        trade = PaperTrade(
            id=str(uuid.uuid4()),
            symbol=self._position.symbol,
            direction=self._position.direction,
            size=self._position.size,
            entry_price=self._position.entry_price,
            exit_price=current_price,
            leverage=self._position.leverage,
            pnl=pnl,
            pnl_percent=pnl_percent,
            close_reason=reason,
            opened_at=self._position.opened_at,
            closed_at=datetime.now()
        )
        self._trades.append(trade)

        # Update account
        self._account.balance += self._position.margin + pnl
        self._account.used_margin -= self._position.margin
        self._account.realized_pnl += pnl
        self._account.total_trades += 1
        if pnl > 0:
            self._account.winning_trades += 1
        else:
            self._account.losing_trades += 1

        old_position = self._position
        self._position = None

        await self._update_equity()
        await self._save_state()

        logger.info(
            f"Position closed: {old_position.direction.upper()} @ ${current_price:.2f}, "
            f"PnL: ${pnl:.2f} ({pnl_percent:.2f}%), reason: {reason}"
        )

        # Trigger callback
        if self.on_position_closed:
            await self.on_position_closed(old_position, pnl, reason)

        return {
            "success": True,
            "order_id": trade.id,
            "closed_price": current_price,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "reason": reason
        }

    async def check_tp_sl(self) -> Optional[str]:
        """Check if TP/SL is triggered"""
        if not self._position:
            return None

        current_price = await self.get_current_price(self._position.symbol)

        if self._position.direction == "long":
            # Long: price above TP or below SL
            if self._position.take_profit_price and current_price >= self._position.take_profit_price:
                await self.close_position(reason="tp")
                if self.on_tp_hit:
                    await self.on_tp_hit(self._position, current_price)
                return "tp"

            if self._position.stop_loss_price and current_price <= self._position.stop_loss_price:
                await self.close_position(reason="sl")
                if self.on_sl_hit:
                    await self.on_sl_hit(self._position, current_price)
                return "sl"

            # Check liquidation
            if current_price <= self._position.calculate_liquidation_price():
                await self.close_position(reason="liquidation")
                return "liquidation"

        else:  # short
            # Short: price below TP or above SL
            if self._position.take_profit_price and current_price <= self._position.take_profit_price:
                await self.close_position(reason="tp")
                if self.on_tp_hit:
                    await self.on_tp_hit(self._position, current_price)
                return "tp"

            if self._position.stop_loss_price and current_price >= self._position.stop_loss_price:
                await self.close_position(reason="sl")
                if self.on_sl_hit:
                    await self.on_sl_hit(self._position, current_price)
                return "sl"

            # Check liquidation
            if current_price >= self._position.calculate_liquidation_price():
                await self.close_position(reason="liquidation")
                return "liquidation"

        return None

    async def _update_equity(self):
        """Update equity"""
        if self._position:
            current_price = await self.get_current_price(self._position.symbol)
            pnl, _ = self._position.calculate_pnl(current_price)
            self._account.unrealized_pnl = pnl
        else:
            self._account.unrealized_pnl = 0

        self._account.total_equity = self._account.balance + self._account.used_margin + self._account.unrealized_pnl

        # Record equity
        self._equity_history.append({
            "timestamp": datetime.now().isoformat(),
            "equity": self._account.total_equity,
            "balance": self._account.balance,
            "unrealized_pnl": self._account.unrealized_pnl,
            "has_position": self._position is not None,
            "direction": self._position.direction if self._position else None
        })

    async def get_equity_history(self, limit: int = 100) -> List[Dict]:
        """Get equity history"""
        return self._equity_history[-limit:]

    async def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """Get trade history"""
        return [t.to_dict() for t in self._trades[-limit:]]

    async def get_market_data(self, symbol: str = "BTC-USDT-SWAP") -> Dict:
        """Get market data"""
        current_price = await self.get_current_price(symbol)

        # Simulate 24h data
        if len(self._price_history) > 100:
            prices = self._price_history[-100:]
            high_24h = max(prices)
            low_24h = min(prices)
            open_24h = prices[0]
            change = ((current_price - open_24h) / open_24h) * 100
        else:
            high_24h = current_price * 1.02
            low_24h = current_price * 0.98
            open_24h = current_price * 0.995
            change = random.uniform(-3, 3)

        return {
            "symbol": symbol,
            "price": current_price,
            "price_24h_change": change,
            "volume_24h": random.uniform(1e9, 3e9),
            "high_24h": high_24h,
            "low_24h": low_24h,
            "open_24h": open_24h,
            "funding_rate": random.uniform(-0.001, 0.003),
            "timestamp": datetime.now().isoformat()
        }

    async def reset(self):
        """Reset account to initial state"""
        self._account = PaperAccount(
            initial_balance=self.initial_balance,
            balance=self.initial_balance,
            total_equity=self.initial_balance
        )
        self._position = None
        self._trades = []
        self._equity_history = []
        self._price_history = []

        # Re-fetch real price
        if self._price_service:
            try:
                self._current_price = await self._price_service.get_btc_price()
                logger.info(f"Reset: Fetched current price ${self._current_price:,.2f}")
            except Exception as e:
                logger.error(f"Reset: Failed to fetch price: {e}")
                # Keep previous price, don't use hardcoded value
        else:
            self._current_price = None

        await self._save_state()
        logger.info(f"Paper trader reset. Balance: ${self.initial_balance:.2f}")

    def get_status(self) -> Dict:
        """Get Paper Trader status"""
        return {
            "initialized": self._initialized,
            "has_position": self._position is not None,
            "position_direction": self._position.direction if self._position else None,
            "current_price": self._current_price,
            "balance": self._account.balance,
            "equity": self._account.total_equity,
            "total_trades": self._account.total_trades,
            "win_rate": f"{self._account.win_rate * 100:.1f}%",
            "realized_pnl": self._account.realized_pnl
        }


# Singleton
_paper_trader: Optional[PaperTrader] = None


async def get_paper_trader(initial_balance: float = 10000.0) -> PaperTrader:
    """Get or create Paper Trader singleton"""
    global _paper_trader
    if _paper_trader is None:
        _paper_trader = PaperTrader(initial_balance=initial_balance)
        await _paper_trader.initialize()
    return _paper_trader
