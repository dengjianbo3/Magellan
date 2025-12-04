"""
Mock Price Service - 模拟价格服务

避免真实的价格API调用，使用预定义价格。
"""

import pytest
import os
from typing import Optional, Callable, List
from datetime import datetime
from unittest.mock import AsyncMock, patch


class MockPriceService:
    """Mock价格服务 - 返回固定或序列价格"""
    
    def __init__(self, price: float = 95000.0, price_sequence: List[float] = None):
        """
        Args:
            price: 固定价格（如果不使用序列）
            price_sequence: 价格序列，每次调用返回下一个
        """
        self.price = price
        self.price_sequence = price_sequence or []
        self.call_count = 0
        self.current_index = 0
    
    async def get_btc_price(self) -> float:
        """获取BTC价格"""
        self.call_count += 1
        
        if self.price_sequence:
            # 使用序列价格
            price = self.price_sequence[min(self.current_index, len(self.price_sequence) - 1)]
            self.current_index += 1
            return price
        else:
            # 使用固定价格
            return self.price
    
    async def get_klines(self, symbol: str, interval: str = "1h", limit: int = 100):
        """获取K线数据（Mock）"""
        # 返回简化的K线数据
        base_price = self.price
        klines = []
        for i in range(limit):
            klines.append({
                "time": f"2024-01-{i+1:02d}",
                "open": base_price * (1 + (i-50) * 0.001),
                "high": base_price * (1 + (i-50) * 0.001 + 0.005),
                "low": base_price * (1 + (i-50) * 0.001 - 0.005),
                "close": base_price * (1 + (i-50) * 0.001 + 0.002),
                "volume": 1000 * (1 + i * 0.01),
            })
        return klines
    
    def set_price(self, price: float):
        """设置固定价格"""
        self.price = price
    
    def set_price_sequence(self, prices: List[float]):
        """设置价格序列"""
        self.price_sequence = prices
        self.current_index = 0
    
    def advance_price(self) -> float:
        """手动前进到下一个价格（如果使用序列）"""
        if self.price_sequence:
            self.current_index = min(self.current_index + 1, len(self.price_sequence) - 1)
            return self.price_sequence[self.current_index]
        return self.price
    
    def reset(self):
        """重置状态"""
        self.call_count = 0
        self.current_index = 0


@pytest.fixture
def mock_price_service():
    """提供基础Mock价格服务"""
    return MockPriceService(price=95000.0)


@pytest.fixture
def mock_price_stable():
    """稳定价格服务 - 95000"""
    return MockPriceService(price=95000.0)


@pytest.fixture
def mock_price_bullish():
    """牛市价格服务"""
    prices = [95000, 96000, 97500, 99000, 101000, 103000, 105000]
    return MockPriceService(price_sequence=prices)


@pytest.fixture
def mock_price_bearish():
    """熊市价格服务"""
    prices = [95000, 94000, 92500, 91000, 89000, 87000, 85000]
    return MockPriceService(price_sequence=prices)


@pytest.fixture
def mock_price_for_tp_long():
    """多仓止盈价格序列"""
    prices = [95000, 96000, 97000, 98500, 99800]  # 最后触发TP
    return MockPriceService(price_sequence=prices)


@pytest.fixture
def mock_price_for_sl_long():
    """多仓止损价格序列"""
    prices = [95000, 94500, 94000, 93500, 93000]  # 最后触发SL
    return MockPriceService(price_sequence=prices)


@pytest.fixture
def mock_price_for_tp_short():
    """空仓止盈价格序列"""
    prices = [95000, 94000, 93000, 91500, 90200]  # 最后触发TP
    return MockPriceService(price_sequence=prices)


@pytest.fixture
def mock_price_for_sl_short():
    """空仓止损价格序列"""
    prices = [95000, 95500, 96000, 96500, 97000]  # 最后触发SL
    return MockPriceService(price_sequence=prices)


# ==================== 全局Mock ====================

@pytest.fixture
def patch_price_service(mocker, mock_price_service):
    """Patch全局价格服务函数"""
    async def get_mock_price(demo_mode=False):
        return await mock_price_service.get_btc_price()
    
    # Patch各种可能的价格获取函数
    mocker.patch(
        "app.core.trading.price_service.get_current_btc_price",
        side_effect=get_mock_price
    )
    mocker.patch(
        "app.core.trading.price_service.PriceService.get_btc_price",
        side_effect=get_mock_price
    )
    
    return mock_price_service


@pytest.fixture
def patch_price_api(mocker, mock_price_service):
    """Patch HTTP价格API调用"""
    import aioresponses
    
    with aioresponses.aioresponses() as m:
        # Mock Binance API
        m.get(
            "https://api.binance.com/api/v3/ticker/price",
            payload={"symbol": "BTCUSDT", "price": str(mock_price_service.price)},
            repeat=True
        )
        
        # Mock CoinGecko API
        m.get(
            "https://api.coingecko.com/api/v3/simple/price",
            payload={"bitcoin": {"usd": mock_price_service.price}},
            repeat=True
        )
        
        # Mock OKX API
        m.get(
            "https://www.okx.com/api/v5/market/ticker",
            payload={"data": [{"last": str(mock_price_service.price)}]},
            repeat=True
        )
        
        yield m


class DynamicPriceService:
    """动态价格服务 - 支持自定义价格函数"""
    
    def __init__(self, price_func: Callable[[], float]):
        """
        Args:
            price_func: 返回价格的函数
        """
        self.price_func = price_func
        self.call_count = 0
    
    async def get_btc_price(self) -> float:
        """获取BTC价格"""
        self.call_count += 1
        return self.price_func()


@pytest.fixture
def dynamic_price_service():
    """动态价格服务工厂"""
    def factory(price_func: Callable[[], float]):
        return DynamicPriceService(price_func)
    return factory


# ==================== 价格场景应用 ====================

@pytest.fixture
def apply_price_scenario(mocker):
    """应用价格场景到系统"""
    def apply(scenario):
        """
        应用价格场景
        
        Args:
            scenario: PriceScenario对象
        """
        async def get_scenario_price(symbol=None):
            return scenario.get_price()
        
        # Patch PaperTrader的get_current_price方法
        mocker.patch(
            "app.core.trading.paper_trader.PaperTrader.get_current_price",
            side_effect=get_scenario_price
        )
        
        # Patch全局价格服务
        mocker.patch(
            "app.core.trading.price_service.get_current_btc_price",
            side_effect=lambda demo_mode=False: get_scenario_price()
        )
        
        return scenario
    
    return apply


# ==================== 环境控制 ====================

@pytest.fixture
def use_real_price():
    """检查是否使用真实价格API"""
    return os.getenv("USE_REAL_PRICE", "false").lower() == "true"


@pytest.fixture
def auto_mock_price(mocker, use_real_price, mock_price_service):
    """自动Mock价格服务（除非明确要求使用真实API）"""
    if not use_real_price:
        async def get_mock_price(symbol=None):
            return await mock_price_service.get_btc_price()
        
        # Patch PaperTrader
        mocker.patch(
            "app.core.trading.paper_trader.PaperTrader.get_current_price",
            side_effect=get_mock_price
        )
        
        # Patch price service
        mocker.patch(
            "app.core.trading.price_service.get_current_btc_price",
            side_effect=lambda demo_mode=False: get_mock_price()
        )
        
        return mock_price_service
    return None


# ==================== 辅助函数 ====================

def create_price_sequence(
    start: float,
    end: float,
    steps: int,
    pattern: str = "linear"
) -> List[float]:
    """
    创建价格序列
    
    Args:
        start: 起始价格
        end: 结束价格
        steps: 步骤数
        pattern: 模式 (linear, exponential, volatile)
    
    Returns:
        价格序列
    """
    if pattern == "linear":
        # 线性变化
        step_size = (end - start) / (steps - 1)
        return [start + i * step_size for i in range(steps)]
    
    elif pattern == "exponential":
        # 指数变化
        import math
        ratio = (end / start) ** (1 / (steps - 1))
        return [start * (ratio ** i) for i in range(steps)]
    
    elif pattern == "volatile":
        # 波动变化
        import random
        random.seed(42)  # 固定随机种子
        prices = [start]
        for i in range(1, steps):
            change = (end - start) / (steps - 1)
            volatility = abs(change) * 0.5 * random.choice([-1, 1])
            prices.append(prices[-1] + change + volatility)
        return prices
    
    return [start] * steps


@pytest.fixture
def price_sequence_builder():
    """价格序列构建器"""
    return create_price_sequence
