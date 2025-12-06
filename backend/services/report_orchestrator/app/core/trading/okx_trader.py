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

        🆕 OKX 直接返回所有计算好的值，无需本地计算！
        """
        try:
            balance = await self._okx_client.get_account_balance()

            # 🆕 OKX 直接返回 unrealized_pnl，无需本地计算
            unrealized_pnl = balance.unrealized_pnl or 0.0

            # 🆕 max_avail_size = OKX 计算的真实可开仓金额
            # 这是通过 /api/v5/account/max-avail-size API 获取的
            max_avail_size = balance.max_avail_size or 0.0

            # 🔧 优先使用 max_avail_size，否则回退到 available_balance
            true_available_margin = max_avail_size if max_avail_size > 0 else balance.available_balance

            return {
                'total_equity': balance.total_equity,
                'available_balance': balance.available_balance,
                'true_available_margin': true_available_margin,  # 🔧 现在使用 max_avail_size
                'max_avail_size': max_avail_size,  # 🆕 传递给 trading_meeting.py
                'used_margin': balance.used_margin or 0,
                'unrealized_pnl': unrealized_pnl,
                'realized_pnl': 0.0,  # 可从 API 获取
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
        
        🆕 直接从 OKX 获取所有数据，包括强平价格等
        """
        # 🆕 直接从 OKX API 获取最新持仓数据
        try:
            pos = await self._okx_client.get_current_position(symbol)
            
            if not pos:
                self._position = None
                return {'has_position': False}
            
            # 更新本地缓存
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
            
            # 🆕 计算仓位百分比
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
                'position_percent': position_percent,  # 🆕 与 PaperTrader 一致
                'unrealized_pnl': pos.unrealized_pnl,
                'unrealized_pnl_percent': pos.unrealized_pnl_percent,
                'take_profit_price': pos.take_profit_price,
                'stop_loss_price': pos.stop_loss_price,
                'liquidation_price': pos.liquidation_price,  # 🆕 交易所直接返回强平价
                'opened_at': pos.opened_at.isoformat() if pos.opened_at else None
            }
            
        except Exception as e:
            logger.error(f"Error getting position from OKX: {e}")
            
            # Fallback 到本地缓存
            if not self._position:
                return {'has_position': False}

            price = await self.get_current_price(symbol)

            # 本地计算 PnL (备用)
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
                'liquidation_price': None,  # 本地缓存无强平价
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
        开多仓 - 与 PaperTrader.open_long() 签名一致
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
        开空仓 - 与 PaperTrader.open_short() 签名一致
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
        """Open a new position on OKX demo (内部方法)，支持追加仓位"""
        # 确保类型正确（防止从LLM解析时传入字符串）
        try:
            leverage = int(leverage) if leverage else 1
            amount_usdt = float(amount_usdt) if amount_usdt else 100
            tp_price = float(tp_price) if tp_price else None
            sl_price = float(sl_price) if sl_price else None
        except (TypeError, ValueError) as e:
            return {'success': False, 'error': f'参数类型错误: {e}'}

        # 🆕 检查是否有现有仓位
        is_adding = False
        if self._position:
            if self._position.direction != direction:
                # 方向不同，不能追加（需要先平仓）
                logger.warning(f"[OKXTrader] Cannot add to position: existing={self._position.direction}, requested={direction}")
                return {'success': False, 'error': f'Cannot add {direction} to existing {self._position.direction} position'}
            else:
                # 同方向，可以追加
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
                    # 🆕 追加仓位：更新本地缓存
                    old_size = self._position.size
                    old_margin = self._position.margin
                    old_entry = self._position.entry_price

                    # 计算新的平均入场价
                    new_size = old_size + executed_amount
                    new_margin = old_margin + amount_usdt
                    new_entry = (old_entry * old_size + executed_price * executed_amount) / new_size if new_size > 0 else executed_price

                    self._position.size = new_size
                    self._position.margin = new_margin
                    self._position.entry_price = new_entry
                    self._position.current_price = executed_price

                    logger.info(f"OKX position added: {direction} +{executed_amount} BTC @ ${executed_price:.2f}, total={new_size} BTC, avg_entry=${new_entry:.2f}")
                else:
                    # 新开仓位
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

                # 🆕 返回格式与 PaperTrader 一致
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
                    'remaining_balance': 0.0,  # 需要从 API 获取
                    'remaining_available_margin': 0.0  # 需要从 API 获取
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
    
    async def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """
        Get trade history (PaperTrader compatible)
        
        Returns list of closed trades with PnL
        """
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


# Singleton
_okx_trader: Optional[OKXTrader] = None


async def get_okx_trader(initial_balance: float = 10000.0) -> OKXTrader:
    """Get or create OKX trader singleton"""
    global _okx_trader
    if _okx_trader is None:
        _okx_trader = OKXTrader(initial_balance=initial_balance)
        await _okx_trader.initialize()
    return _okx_trader
