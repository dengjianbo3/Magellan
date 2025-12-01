"""
OKX Demo Trading Adapter

Adapts OKXClient to match the PaperTrader interface,
allowing the trading system to use OKX demo trading.
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field

from app.core.trading.okx_client import OKXClient, get_okx_client

logger = logging.getLogger(__name__)


@dataclass
class OKXTraderConfig:
    """OKX Trader 配置"""
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
    Uses OKX demo trading API (模拟盘).
    """

    def __init__(self, initial_balance: float = 10000.0, demo_mode: bool = True, config: OKXTraderConfig = None):
        self.config = config or OKXTraderConfig(initial_balance=initial_balance, demo_mode=demo_mode)
        self.initial_balance = self.config.initial_balance
        self.demo_mode = self.config.demo_mode
        self._okx_client: Optional[OKXClient] = None
        self._initialized = False

        # Current position cache
        self._position: Optional[OKXPosition] = None
        self._last_price: Optional[float] = None  # 初始化时从API获取真实价格
        self._last_price_update: datetime = datetime.now()

        # Trade history
        self._trade_history: List[Dict] = []
        self._equity_history: List[Dict] = []

        # Callbacks (compatible with PaperTrader)
        self.on_position_closed: Optional[Callable] = None
        self.on_tp_hit: Optional[Callable] = None
        self.on_sl_hit: Optional[Callable] = None
        self.on_pnl_update: Optional[Callable] = None

    async def initialize(self):
        """Initialize OKX client"""
        if self._initialized:
            return

        logger.info("Initializing OKX Demo Trader...")

        self._okx_client = await get_okx_client()

        # Get initial balance from OKX
        try:
            balance = await self._okx_client.get_account_balance()
            self.initial_balance = balance.total_equity or self.initial_balance
            logger.info(f"OKX Demo account balance: ${balance.total_equity:.2f}")
        except Exception as e:
            logger.warning(f"Failed to get OKX balance: {e}, using default")

        # Check for existing position
        await self._sync_position()

        self._initialized = True
        logger.info(f"OKX Trader initialized (demo={self.demo_mode})")

    async def _sync_position(self):
        """Sync position from OKX"""
        try:
            pos = await self._okx_client.get_current_position()
            if pos:
                self._position = OKXPosition(
                    id=f"okx-{datetime.now().timestamp()}",
                    symbol=pos.symbol,
                    direction=pos.direction,
                    size=pos.size,
                    entry_price=pos.entry_price,
                    leverage=pos.leverage,
                    margin=pos.margin or 0,
                    current_price=pos.current_price,
                    unrealized_pnl=pos.unrealized_pnl
                )
                logger.info(f"Synced position: {pos.direction} {pos.size} BTC @ ${pos.entry_price}")
            else:
                self._position = None
        except Exception as e:
            logger.error(f"Error syncing position: {e}")

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
        """Get account info (PaperTrader compatible)"""
        try:
            balance = await self._okx_client.get_account_balance()
            unrealized_pnl = 0.0

            if self._position:
                price = await self.get_current_price()
                if self._position.direction == "long":
                    unrealized_pnl = (price - self._position.entry_price) * self._position.size
                else:
                    unrealized_pnl = (self._position.entry_price - price) * self._position.size

            return {
                'total_equity': balance.total_equity,
                'available_balance': balance.available_balance,
                'unrealized_pnl': unrealized_pnl,
                'initial_balance': self.initial_balance,
                'margin_used': balance.used_margin or 0
            }
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return {
                'total_equity': self.initial_balance,
                'available_balance': self.initial_balance,
                'unrealized_pnl': 0,
                'initial_balance': self.initial_balance,
                'margin_used': 0
            }

    async def get_position(self, symbol: str = "BTC-USDT-SWAP") -> Optional[Dict]:
        """Get current position (PaperTrader compatible)"""
        await self._sync_position()

        if not self._position:
            return {'has_position': False}

        price = await self.get_current_price(symbol)

        # Calculate PnL
        if self._position.direction == "long":
            pnl = (price - self._position.entry_price) * self._position.size
        else:
            pnl = (self._position.entry_price - price) * self._position.size

        pnl_percent = (pnl / self._position.margin * 100) if self._position.margin > 0 else 0

        return {
            'has_position': True,
            'symbol': self._position.symbol,
            'direction': self._position.direction,
            'size': self._position.size,
            'entry_price': self._position.entry_price,
            'current_price': price,
            'leverage': self._position.leverage,
            'take_profit_price': self._position.take_profit_price,
            'stop_loss_price': self._position.stop_loss_price,
            'unrealized_pnl': pnl,
            'unrealized_pnl_percent': pnl_percent,
            'margin': self._position.margin
        }

    async def open_position(
        self,
        direction: str,
        leverage: int,
        amount_usdt: float,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None,
        symbol: str = "BTC-USDT-SWAP"
    ) -> Dict:
        """Open a new position on OKX demo"""
        # 确保类型正确（防止从LLM解析时传入字符串）
        try:
            leverage = int(leverage) if leverage else 1
            amount_usdt = float(amount_usdt) if amount_usdt else 100
            tp_price = float(tp_price) if tp_price else None
            sl_price = float(sl_price) if sl_price else None
        except (TypeError, ValueError) as e:
            return {'success': False, 'error': f'参数类型错误: {e}'}

        if self._position:
            return {'success': False, 'error': 'Position already exists'}

        try:
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

            if result.get('success'):
                # Create local position record
                self._position = OKXPosition(
                    id=result.get('order_id', f"okx-{datetime.now().timestamp()}"),
                    symbol=symbol,
                    direction=direction,
                    size=result.get('executed_amount', 0),
                    entry_price=result.get('executed_price', 0),
                    leverage=leverage,
                    margin=amount_usdt,
                    take_profit_price=tp_price,
                    stop_loss_price=sl_price,
                    current_price=result.get('executed_price', 0)
                )

                logger.info(f"OKX position opened: {direction} {self._position.size} BTC @ ${self._position.entry_price}")

                return {
                    'success': True,
                    'position': self._position.to_dict(),
                    'order_id': result.get('order_id')
                }
            else:
                return {'success': False, 'error': result.get('error', 'Failed to open position')}

        except Exception as e:
            logger.error(f"Error opening position: {e}")
            return {'success': False, 'error': str(e)}

    async def close_position(self, symbol: str = "BTC-USDT-SWAP", reason: str = "manual") -> Optional[Dict]:
        """Close current position on OKX demo"""
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

                logger.info(f"OKX position closed: PnL=${pnl:.2f} ({reason})")

                # Trigger callback
                if self.on_position_closed:
                    await self.on_position_closed(closed_position, pnl)

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
        return {
            'initialized': self._initialized,
            'type': 'okx_demo',
            'has_position': self._position is not None,
            'position_direction': self._position.direction if self._position else None,
            'current_price': self._last_price,
            'balance': self.initial_balance,
            'equity': self.initial_balance,
            'total_trades': len(self._trade_history),
            'win_rate': self._calculate_win_rate(),
            'realized_pnl': sum(t.get('pnl', 0) for t in self._trade_history)
        }

    def _calculate_win_rate(self) -> str:
        if not self._trade_history:
            return "0.0%"
        wins = sum(1 for t in self._trade_history if t.get('pnl', 0) > 0)
        return f"{(wins / len(self._trade_history) * 100):.1f}%"


# Singleton
_okx_trader: Optional[OKXTrader] = None


async def get_okx_trader(initial_balance: float = 10000.0) -> OKXTrader:
    """Get or create OKX trader singleton"""
    global _okx_trader
    if _okx_trader is None:
        _okx_trader = OKXTrader(initial_balance=initial_balance)
        await _okx_trader.initialize()
    return _okx_trader
