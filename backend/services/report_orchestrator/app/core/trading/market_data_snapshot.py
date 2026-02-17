"""
Market Data Snapshot - 周期内市场数据共享

在分析周期开始时获取一次市场数据，所有 Agent 共享使用。
避免每个 Agent 重复调用 get_market_price, get_fear_greed_index 等 API。

Context Engineering P1 策略
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field

from app.core.auth import get_current_user_id

logger = logging.getLogger(__name__)


@dataclass
class MarketDataSnapshot:
    """
    市场数据快照
    
    在分析周期开始时获取一次，所有 Agent 共享。
    """
    # 基础价格数据
    symbol: str = "BTC-USDT-SWAP"
    price: float = 0.0
    change_24h: str = "0%"
    volume_24h: str = "$0"
    high_24h: float = 0.0
    low_24h: float = 0.0
    
    # 情绪指标
    fear_greed_index: int = 50
    fear_greed_classification: str = "Neutral"
    
    # 资金费率
    funding_rate: float = 0.0
    funding_rate_str: str = "0%"
    next_funding_time: str = ""
    
    # 持仓信息
    has_position: bool = False
    position_direction: Optional[str] = None
    position_size: float = 0.0
    unrealized_pnl: float = 0.0
    
    # 账户余额
    available_balance: float = 0.0
    true_available_margin: float = 0.0
    
    # 元数据
    timestamp: datetime = field(default_factory=datetime.now)
    cycle_id: Optional[str] = None
    is_valid: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "change_24h": self.change_24h,
            "volume_24h": self.volume_24h,
            "high_24h": self.high_24h,
            "low_24h": self.low_24h,
            "fear_greed_index": self.fear_greed_index,
            "fear_greed_classification": self.fear_greed_classification,
            "funding_rate": self.funding_rate,
            "funding_rate_str": self.funding_rate_str,
            "has_position": self.has_position,
            "position_direction": self.position_direction,
            "available_balance": self.available_balance,
            "timestamp": self.timestamp.isoformat(),
            "is_valid": self.is_valid
        }
    
    def get_price_summary(self) -> str:
        """获取价格摘要字符串"""
        return (
            f"📊 Market Snapshot ({self.symbol})\n"
            f"💰 Price: ${self.price:,.2f} ({self.change_24h})\n"
            f"📈 24h Range: ${self.low_24h:,.2f} - ${self.high_24h:,.2f}\n"
            f"📊 Volume: {self.volume_24h}\n"
            f"🎭 Sentiment: {self.fear_greed_index} ({self.fear_greed_classification})\n"
            f"💵 Funding: {self.funding_rate_str}"
        )


class MarketDataSnapshotManager:
    """
    市场数据快照管理器
    
    负责在周期开始时获取数据并提供给所有 Agent
    """
    
    def __init__(self, user_id: Optional[str] = None):
        self.user_id = get_current_user_id(user_id)
        self._snapshot: Optional[MarketDataSnapshot] = None
        self._cycle_id: Optional[str] = None
        self._stats = {
            "snapshots_created": 0,
            "data_requests_served": 0,
            "api_calls_saved": 0  # 每次重用 = 节省一次 API 调用
        }
    
    async def create_snapshot(
        self, 
        symbol: str = "BTC-USDT-SWAP",
        cycle_id: str = None,
        paper_trader=None
    ) -> MarketDataSnapshot:
        """
        创建新的市场数据快照
        
        Args:
            symbol: 交易对
            cycle_id: 周期ID
            paper_trader: PaperTrader 实例（用于获取数据）
        
        Returns:
            MarketDataSnapshot
        """
        self._cycle_id = cycle_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self._snapshot = MarketDataSnapshot(
            symbol=symbol,
            cycle_id=self._cycle_id,
            timestamp=datetime.now()
        )
        
        try:
            # 获取价格数据
            await self._fetch_price_data(paper_trader)
            
            # 获取情绪指标
            await self._fetch_sentiment_data()
            
            # 获取资金费率
            await self._fetch_funding_rate()
            
            # 获取持仓数据
            await self._fetch_position_data(paper_trader)
            
            # 获取账户余额
            await self._fetch_balance_data(paper_trader)
            
            self._snapshot.is_valid = True
            self._stats["snapshots_created"] += 1
            
            logger.info(
                f"[MarketSnapshot][{self.user_id}] Created for cycle {self._cycle_id}: "
                f"price=${self._snapshot.price:,.2f}, "
                f"fear_greed={self._snapshot.fear_greed_index}"
            )
            
        except Exception as e:
            logger.error(f"[MarketSnapshot][{self.user_id}] Failed to create snapshot: {e}")
            self._snapshot.is_valid = False
        
        return self._snapshot
    
    async def _fetch_price_data(self, paper_trader=None):
        """获取价格数据"""
        try:
            from app.core.trading.price_service import get_current_btc_price
            
            price_data = await get_current_btc_price()
            if price_data:
                # price_data can be float or dict depending on source
                if isinstance(price_data, (int, float)):
                    self._snapshot.price = float(price_data)
                elif isinstance(price_data, dict):
                    self._snapshot.price = price_data.get("price", 0)
                    self._snapshot.change_24h = price_data.get("change_24h", "0%")
                    self._snapshot.volume_24h = price_data.get("volume_24h", "$0")
                    self._snapshot.high_24h = price_data.get("high_24h", 0)
                    self._snapshot.low_24h = price_data.get("low_24h", 0)
        except Exception as e:
            logger.warning(f"[MarketSnapshot] Price fetch failed: {e}")
    
    async def _fetch_sentiment_data(self):
        """获取情绪指标"""
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("https://api.alternative.me/fng/?limit=1")
                if response.status_code == 200:
                    data = response.json()
                    if data.get("data"):
                        fng = data["data"][0]
                        self._snapshot.fear_greed_index = int(fng.get("value", 50))
                        self._snapshot.fear_greed_classification = fng.get("value_classification", "Neutral")
        except Exception as e:
            logger.warning(f"[MarketSnapshot] Sentiment fetch failed: {e}")
    
    async def _fetch_funding_rate(self):
        """获取资金费率"""
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://fapi.binance.com/fapi/v1/premiumIndex",
                    params={"symbol": "BTCUSDT"}
                )
                if response.status_code == 200:
                    data = response.json()
                    rate = float(data.get("lastFundingRate", 0))
                    self._snapshot.funding_rate = rate
                    self._snapshot.funding_rate_str = f"{rate * 100:.4f}%"
        except Exception as e:
            logger.warning(f"[MarketSnapshot] Funding rate fetch failed: {e}")
    
    async def _fetch_position_data(self, paper_trader=None):
        """获取持仓数据"""
        try:
            if paper_trader and hasattr(paper_trader, 'get_position'):
                # PaperTrader uses get_position(), not get_current_position()
                position = await paper_trader.get_position()
                if position:
                    self._snapshot.has_position = position.get("size", 0) != 0
                    self._snapshot.position_direction = position.get("direction")
                    self._snapshot.position_size = abs(position.get("size", 0))
                    self._snapshot.unrealized_pnl = position.get("unrealized_pnl", 0)
        except Exception as e:
            logger.warning(f"[MarketSnapshot] Position fetch failed: {e}")
    
    async def _fetch_balance_data(self, paper_trader=None):
        """获取账户余额"""
        try:
            if paper_trader and hasattr(paper_trader, 'get_account'):
                # PaperTrader uses get_account(), not get_account_balance()
                balance = await paper_trader.get_account()
                if balance:
                    self._snapshot.available_balance = balance.get("available_balance", 0)
                    self._snapshot.true_available_margin = balance.get("true_available_margin", 0)
        except Exception as e:
            logger.warning(f"[MarketSnapshot] Balance fetch failed: {e}")
    
    def get_snapshot(self) -> Optional[MarketDataSnapshot]:
        """获取当前快照"""
        if self._snapshot:
            self._stats["data_requests_served"] += 1
            self._stats["api_calls_saved"] += 1  # 每次获取都是节省的 API 调用
        return self._snapshot
    
    def get_price(self) -> float:
        """快捷方法：获取价格"""
        return self._snapshot.price if self._snapshot else 0.0
    
    def get_fear_greed(self) -> int:
        """快捷方法：获取恐贪指数"""
        return self._snapshot.fear_greed_index if self._snapshot else 50
    
    def get_funding_rate(self) -> float:
        """快捷方法：获取资金费率"""
        return self._snapshot.funding_rate if self._snapshot else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "current_cycle": self._cycle_id,
            "snapshot_valid": self._snapshot.is_valid if self._snapshot else False
        }
    
    def clear(self):
        """清空快照（周期结束时调用）"""
        stats = self.get_stats()
        logger.info(f"[MarketSnapshot][{self.user_id}] Cleared. Stats: {stats}")
        self._snapshot = None
        self._cycle_id = None


# 按用户隔离的单例
_snapshot_managers: Dict[str, MarketDataSnapshotManager] = {}


def get_market_snapshot_manager(user_id: Optional[str] = None) -> MarketDataSnapshotManager:
    """获取用户作用域快照管理器"""
    scope = get_current_user_id(user_id)
    manager = _snapshot_managers.get(scope)
    if manager is None:
        manager = MarketDataSnapshotManager(user_id=scope)
        _snapshot_managers[scope] = manager
    return manager


def reset_market_snapshot_manager(user_id: Optional[str] = None):
    """重置管理器（用于测试）"""
    if user_id is None:
        _snapshot_managers.clear()
        return
    scope = get_current_user_id(user_id)
    _snapshot_managers.pop(scope, None)
