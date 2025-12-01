"""
Paper Trading Simulator

本地模拟交易器，无需连接真实交易所。
提供完整的模拟交易功能，包括：
- 模拟账户余额
- 模拟开平仓
- 模拟止盈止损触发
- 实时价格模拟（基于真实行情或随机波动）
- 交易历史记录
"""

import asyncio
import logging
import uuid
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
import json

import redis.asyncio as redis

from app.core.trading.price_service import get_price_service, PriceService

logger = logging.getLogger(__name__)


@dataclass
class PaperTraderConfig:
    """Paper Trader 配置"""
    initial_balance: float = 10000.0
    max_leverage: int = 20
    min_price: float = 1000.0  # 最低价格限制（用于价格模拟）
    max_price: float = 500000.0  # 最高价格限制（用于价格模拟）
    redis_url: str = "redis://redis:6379"
    demo_mode: bool = False  # False = use real CoinGecko price, True = simulated price


@dataclass
class PaperPosition:
    """模拟持仓"""
    id: str
    symbol: str
    direction: str  # "long" or "short"
    size: float  # 持仓数量 (BTC)
    entry_price: float
    leverage: int
    margin: float  # 保证金
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    opened_at: datetime = field(default_factory=datetime.now)

    def calculate_pnl(self, current_price: float) -> tuple[float, float]:
        """计算未实现盈亏"""
        if self.direction == "long":
            pnl = (current_price - self.entry_price) * self.size
        else:
            pnl = (self.entry_price - current_price) * self.size

        pnl_percent = (pnl / self.margin) * 100 if self.margin > 0 else 0
        return pnl, pnl_percent

    def calculate_liquidation_price(self) -> float:
        """计算强平价格 (简化版)"""
        # 当亏损达到保证金的80%时强平
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
    """模拟交易记录"""
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
    """模拟账户"""
    initial_balance: float = 10000.0
    balance: float = 10000.0  # 可用余额
    total_equity: float = 10000.0  # 总权益 (余额 + 未实现盈亏)
    used_margin: float = 0.0  # 已用保证金
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0  # 已实现盈亏
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


class PaperTrader:
    """
    本地模拟交易器

    Features:
    - 完全本地运行，无需外部API
    - 模拟账户余额和持仓
    - 模拟止盈止损触发
    - 实时价格模拟
    - 交易历史持久化到Redis
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        redis_url: str = "redis://redis:6379",
        demo_mode: bool = False,  # False = use real CoinGecko price, True = simulated price
        config: PaperTraderConfig = None
    ):
        # 使用 config 或单独参数
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

        # 价格服务 - 使用真实或模拟价格
        self._price_service: Optional[PriceService] = None
        self._current_price: Optional[float] = None  # 缓存当前价格，初始化时从API获取
        self._price_history: List[float] = []
        self._last_price_update = datetime.now()

        # 回调
        self.on_position_closed = None
        self.on_tp_hit = None
        self.on_sl_hit = None

        self._initialized = False
        self._key_prefix = "paper_trader:"

    async def initialize(self):
        """初始化，加载历史数据"""
        if self._initialized:
            return

        try:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            await self._redis.ping()

            # 加载账户状态
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
        """从Redis加载状态"""
        if not self._redis:
            return

        try:
            # 加载账户
            account_data = await self._redis.get(f"{self._key_prefix}account")
            if account_data:
                data = json.loads(account_data)
                self._account = PaperAccount(**data)

            # 加载持仓
            position_data = await self._redis.get(f"{self._key_prefix}position")
            if position_data:
                self._position = PaperPosition.from_dict(json.loads(position_data))

            # 加载交易历史
            trades_data = await self._redis.get(f"{self._key_prefix}trades")
            if trades_data:
                self._trades = [
                    PaperTrade(**{**t,
                        'opened_at': datetime.fromisoformat(t['opened_at']),
                        'closed_at': datetime.fromisoformat(t['closed_at'])
                    })
                    for t in json.loads(trades_data)
                ]

            # 加载净值历史
            equity_data = await self._redis.get(f"{self._key_prefix}equity_history")
            if equity_data:
                self._equity_history = json.loads(equity_data)

        except Exception as e:
            logger.error(f"Error loading state: {e}")

    async def _save_state(self):
        """保存状态到Redis"""
        if not self._redis:
            return

        try:
            # 保存账户
            await self._redis.set(
                f"{self._key_prefix}account",
                json.dumps(self._account.to_dict())
            )

            # 保存持仓
            if self._position:
                await self._redis.set(
                    f"{self._key_prefix}position",
                    json.dumps(self._position.to_dict())
                )
            else:
                await self._redis.delete(f"{self._key_prefix}position")

            # 保存交易历史 (只保留最近100条)
            await self._redis.set(
                f"{self._key_prefix}trades",
                json.dumps([t.to_dict() for t in self._trades[-100:]])
            )

            # 保存净值历史 (只保留最近1000条)
            await self._redis.set(
                f"{self._key_prefix}equity_history",
                json.dumps(self._equity_history[-1000:])
            )

        except Exception as e:
            logger.error(f"Error saving state: {e}")

    async def get_current_price(self, symbol: str = "BTC-USDT-SWAP") -> float:
        """获取当前价格 - 使用价格服务获取真实/模拟价格"""
        now = datetime.now()

        # 使用价格服务获取价格（每秒最多更新一次）
        if (now - self._last_price_update).seconds >= 1:
            if self._price_service:
                self._current_price = await self._price_service.get_btc_price()
            else:
                # Fallback: 简单模拟波动
                change = random.uniform(-0.001, 0.001)
                self._current_price *= (1 + change)
                self._current_price = max(self.config.min_price, min(self.config.max_price, self._current_price))

            self._last_price_update = now
            self._price_history.append(self._current_price)
            if len(self._price_history) > 10000:
                self._price_history = self._price_history[-10000:]

        return self._current_price

    def set_price(self, price: float):
        """手动设置当前价格（用于测试或同步真实价格）"""
        self._current_price = price
        self._last_price_update = datetime.now()

    async def get_account(self) -> Dict:
        """获取账户信息"""
        await self._update_equity()
        return {
            "total_equity": self._account.total_equity,
            "available_balance": self._account.balance,
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
        """获取当前持仓"""
        if not self._position or self._position.symbol != symbol:
            return None

        current_price = await self.get_current_price(symbol)
        pnl, pnl_percent = self._position.calculate_pnl(current_price)

        return {
            "has_position": True,
            "symbol": self._position.symbol,
            "direction": self._position.direction,
            "size": self._position.size,
            "entry_price": self._position.entry_price,
            "current_price": current_price,
            "leverage": self._position.leverage,
            "margin": self._position.margin,
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
        """开多仓"""
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
        """开空仓"""
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
        """开仓"""
        if self._position:
            return {
                "success": False,
                "error": "已有持仓，请先平仓"
            }

        # 确保类型正确（防止从LLM解析时传入字符串）
        try:
            amount_usdt = float(amount_usdt)
            leverage = int(leverage)
        except (TypeError, ValueError) as e:
            return {
                "success": False,
                "error": f"参数类型错误: {e}"
            }

        # 检查余额
        if amount_usdt > self._account.balance:
            return {
                "success": False,
                "error": f"余额不足，可用: ${self._account.balance:.2f}"
            }

        # 限制杠杆 (1-max_leverage倍)
        leverage = min(max(1, leverage), self.config.max_leverage)

        current_price = await self.get_current_price(symbol)

        # 计算持仓数量
        position_value = amount_usdt * leverage
        size = position_value / current_price

        # 创建持仓
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

        # 更新账户
        self._account.balance -= amount_usdt
        self._account.used_margin += amount_usdt

        await self._save_state()

        logger.info(
            f"开仓成功: {direction.upper()} {size:.6f} BTC @ ${current_price:.2f}, "
            f"杠杆: {leverage}x, 保证金: ${amount_usdt:.2f}"
        )

        return {
            "success": True,
            "order_id": self._position.id,
            "direction": direction,
            "executed_price": current_price,
            "executed_amount": size,
            "leverage": leverage,
            "margin": amount_usdt,
            "take_profit": tp_price,
            "stop_loss": sl_price
        }

    async def close_position(self, symbol: str = "BTC-USDT-SWAP", reason: str = "manual") -> Dict:
        """平仓"""
        if not self._position:
            return {
                "success": False,
                "error": "无持仓"
            }

        current_price = await self.get_current_price(symbol)
        pnl, pnl_percent = self._position.calculate_pnl(current_price)

        # 创建交易记录
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

        # 更新账户
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
            f"平仓成功: {old_position.direction.upper()} @ ${current_price:.2f}, "
            f"盈亏: ${pnl:.2f} ({pnl_percent:.2f}%), 原因: {reason}"
        )

        # 触发回调
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
        """检查止盈止损是否触发"""
        if not self._position:
            return None

        current_price = await self.get_current_price(self._position.symbol)

        if self._position.direction == "long":
            # 多仓：价格高于TP或低于SL
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

            # 检查强平
            if current_price <= self._position.calculate_liquidation_price():
                await self.close_position(reason="liquidation")
                return "liquidation"

        else:  # short
            # 空仓：价格低于TP或高于SL
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

            # 检查强平
            if current_price >= self._position.calculate_liquidation_price():
                await self.close_position(reason="liquidation")
                return "liquidation"

        return None

    async def _update_equity(self):
        """更新权益"""
        if self._position:
            current_price = await self.get_current_price(self._position.symbol)
            pnl, _ = self._position.calculate_pnl(current_price)
            self._account.unrealized_pnl = pnl
        else:
            self._account.unrealized_pnl = 0

        self._account.total_equity = self._account.balance + self._account.used_margin + self._account.unrealized_pnl

        # 记录净值
        self._equity_history.append({
            "timestamp": datetime.now().isoformat(),
            "equity": self._account.total_equity,
            "balance": self._account.balance,
            "unrealized_pnl": self._account.unrealized_pnl,
            "has_position": self._position is not None,
            "direction": self._position.direction if self._position else None
        })

    async def get_equity_history(self, limit: int = 100) -> List[Dict]:
        """获取净值历史"""
        return self._equity_history[-limit:]

    async def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """获取交易历史"""
        return [t.to_dict() for t in self._trades[-limit:]]

    async def get_market_data(self, symbol: str = "BTC-USDT-SWAP") -> Dict:
        """获取市场数据"""
        current_price = await self.get_current_price(symbol)

        # 模拟24小时数据
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
        """重置账户到初始状态"""
        self._account = PaperAccount(
            initial_balance=self.initial_balance,
            balance=self.initial_balance,
            total_equity=self.initial_balance
        )
        self._position = None
        self._trades = []
        self._equity_history = []
        self._price_history = []

        # 重新获取真实价格
        if self._price_service:
            try:
                self._current_price = await self._price_service.get_btc_price()
                logger.info(f"Reset: Fetched current price ${self._current_price:,.2f}")
            except Exception as e:
                logger.error(f"Reset: Failed to fetch price: {e}")
                # 保持之前的价格，不使用硬编码
        else:
            self._current_price = None

        await self._save_state()
        logger.info(f"Paper trader reset. Balance: ${self.initial_balance:.2f}")

    def get_status(self) -> Dict:
        """获取Paper Trader状态"""
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


# 单例
_paper_trader: Optional[PaperTrader] = None


async def get_paper_trader(initial_balance: float = 10000.0) -> PaperTrader:
    """获取或创建Paper Trader单例"""
    global _paper_trader
    if _paper_trader is None:
        _paper_trader = PaperTrader(initial_balance=initial_balance)
        await _paper_trader.initialize()
    return _paper_trader
