"""
Price Scenarios Fixtures - 价格场景数据

提供完整的价格演变场景，用于测试完整的交易周期。
"""

import pytest
from typing import List, Dict, Callable


class PriceScenario:
    """价格场景类 - 模拟价格随时间变化"""
    
    def __init__(self, name: str, prices: List[float], descriptions: List[str] = None):
        self.name = name
        self.prices = prices
        self.descriptions = descriptions or [""] * len(prices)
        self.current_index = 0
    
    def get_price(self) -> float:
        """获取当前价格"""
        if self.current_index >= len(self.prices):
            return self.prices[-1]
        return self.prices[self.current_index]
    
    def advance(self) -> float:
        """前进到下一个价格"""
        if self.current_index < len(self.prices) - 1:
            self.current_index += 1
        return self.get_price()
    
    def reset(self):
        """重置到初始状态"""
        self.current_index = 0
    
    def get_description(self) -> str:
        """获取当前描述"""
        return self.descriptions[self.current_index]


@pytest.fixture
def scenario_long_tp():
    """场景: 多仓止盈"""
    return PriceScenario(
        name="多仓止盈场景",
        prices=[
            95000.0,   # T0: 开仓
            96000.0,   # T1: +1.05%
            97000.0,   # T2: +2.11%
            98500.0,   # T3: +3.68%
            99800.0,   # T4: +5.05% 触发TP
        ],
        descriptions=[
            "开仓价格",
            "小幅上涨",
            "继续上涨",
            "接近止盈",
            "触发止盈！"
        ]
    )


@pytest.fixture
def scenario_long_sl():
    """场景: 多仓止损"""
    return PriceScenario(
        name="多仓止损场景",
        prices=[
            95000.0,   # T0: 开仓
            94500.0,   # T1: -0.53%
            94000.0,   # T2: -1.05%
            93500.0,   # T3: -1.58%
            93000.0,   # T4: -2.11% 触发SL
        ],
        descriptions=[
            "开仓价格",
            "小幅下跌",
            "继续下跌",
            "接近止损",
            "触发止损！"
        ]
    )


@pytest.fixture
def scenario_short_tp():
    """场景: 空仓止盈"""
    return PriceScenario(
        name="空仓止盈场景",
        prices=[
            95000.0,   # T0: 开仓
            94000.0,   # T1: -1.05%
            93000.0,   # T2: -2.11%
            91500.0,   # T3: -3.68%
            90200.0,   # T4: -5.05% 触发TP
        ],
        descriptions=[
            "开仓价格",
            "开始下跌",
            "继续下跌",
            "接近止盈",
            "触发止盈！"
        ]
    )


@pytest.fixture
def scenario_short_sl():
    """场景: 空仓止损"""
    return PriceScenario(
        name="空仓止损场景",
        prices=[
            95000.0,   # T0: 开仓
            95500.0,   # T1: +0.53%
            96000.0,   # T2: +1.05%
            96500.0,   # T3: +1.58%
            97000.0,   # T4: +2.11% 触发SL
        ],
        descriptions=[
            "开仓价格",
            "价格上涨",
            "继续上涨",
            "接近止损",
            "触发止损！"
        ]
    )


@pytest.fixture
def scenario_add_position():
    """场景: 追加仓位"""
    return PriceScenario(
        name="追加仓位场景",
        prices=[
            95000.0,   # T0: 首次开仓
            96000.0,   # T1: 盈利中
            97000.0,   # T2: 继续盈利，考虑追加
            98000.0,   # T3: 追加后继续上涨
            100000.0,  # T4: 达到止盈
        ],
        descriptions=[
            "首次开仓",
            "小幅盈利",
            "追加仓位时机",
            "追加后上涨",
            "整体止盈"
        ]
    )


@pytest.fixture
def scenario_reverse_position():
    """场景: 反向操作"""
    return PriceScenario(
        name="反向操作场景",
        prices=[
            95000.0,   # T0: 开多仓
            96000.0,   # T1: 盈利
            95500.0,   # T2: 回落
            94000.0,   # T3: 趋势反转，平多开空
            92000.0,   # T4: 空仓盈利
        ],
        descriptions=[
            "开多仓",
            "多仓盈利",
            "价格回落",
            "平多仓，开空仓",
            "空仓盈利"
        ]
    )


@pytest.fixture
def scenario_volatile_hold():
    """场景: 剧烈波动，持有观望"""
    return PriceScenario(
        name="波动观望场景",
        prices=[
            95000.0,   # T0: 初始
            98000.0,   # T1: 大涨+3.16%
            93000.0,   # T2: 暴跌-5.10%
            97000.0,   # T3: 反弹+4.30%
            94000.0,   # T4: 再跌-3.09%
        ],
        descriptions=[
            "价格稳定",
            "突然大涨",
            "剧烈下跌",
            "快速反弹",
            "方向不明"
        ]
    )


@pytest.fixture
def scenario_consecutive_losses():
    """场景: 连续止损触发冷却"""
    return PriceScenario(
        name="连续止损场景",
        prices=[
            95000.0,   # T0: 第1次开多仓
            93000.0,   # T1: 第1次止损 -2.11%
            92000.0,   # T2: 第2次开空仓
            94000.0,   # T3: 第2次止损 +2.17%
            94500.0,   # T4: 第3次尝试，但在冷却期
        ],
        descriptions=[
            "第1次开仓",
            "第1次止损",
            "第2次开仓",
            "第2次止损",
            "冷却期中"
        ]
    )


@pytest.fixture
def scenario_insufficient_balance():
    """场景: 余额不足"""
    return PriceScenario(
        name="余额不足场景",
        prices=[
            95000.0,   # T0: 开大仓位
            94000.0,   # T1: 浮亏
            93000.0,   # T2: 大幅浮亏
            93500.0,   # T3: 想追加但余额不足
        ],
        descriptions=[
            "开大仓位",
            "开始浮亏",
            "大幅浮亏",
            "想追加但钱不够"
        ]
    )


@pytest.fixture
def scenario_reach_position_limit():
    """场景: 达到仓位上限"""
    return PriceScenario(
        name="仓位上限场景",
        prices=[
            95000.0,   # T0: 开仓30%
            96000.0,   # T1: 盈利，想追加但已到上限
        ],
        descriptions=[
            "开仓达到上限",
            "想追加但已满"
        ]
    )


# ==================== 完整交易周期场景 ====================

@pytest.fixture
def full_cycle_success():
    """完整成功交易周期"""
    return {
        "scenario": "成功交易周期",
        "steps": [
            {"time": "T0", "price": 95000, "action": "开多仓", "expected": "open_long"},
            {"time": "T1", "price": 96000, "action": "检查持仓", "expected": "has_position"},
            {"time": "T2", "price": 97000, "action": "持有", "expected": "hold"},
            {"time": "T3", "price": 98500, "action": "接近TP", "expected": "approaching_tp"},
            {"time": "T4", "price": 99800, "action": "触发TP", "expected": "tp_triggered"},
        ],
        "initial_balance": 10000.0,
        "expected_final_balance": 10950.0,  # 假设10倍杠杆，5%止盈
        "expected_pnl": 950.0,
    }


@pytest.fixture
def full_cycle_loss():
    """完整失败交易周期"""
    return {
        "scenario": "失败交易周期",
        "steps": [
            {"time": "T0", "price": 95000, "action": "开多仓", "expected": "open_long"},
            {"time": "T1", "price": 94500, "action": "小幅浮亏", "expected": "unrealized_loss"},
            {"time": "T2", "price": 94000, "action": "继续浮亏", "expected": "unrealized_loss"},
            {"time": "T3", "price": 93500, "action": "接近SL", "expected": "approaching_sl"},
            {"time": "T4", "price": 93000, "action": "触发SL", "expected": "sl_triggered"},
        ],
        "initial_balance": 10000.0,
        "expected_final_balance": 9620.0,  # 假设10倍杠杆，2%止损
        "expected_pnl": -380.0,
    }


@pytest.fixture
def full_cycle_add_position():
    """完整追加仓位周期"""
    return {
        "scenario": "追加仓位周期",
        "steps": [
            {"time": "T0", "price": 95000, "action": "首次开多仓2000U", "expected": "open_long"},
            {"time": "T1", "price": 96000, "action": "盈利中", "expected": "profitable"},
            {"time": "T2", "price": 97000, "action": "追加1500U", "expected": "add_position"},
            {"time": "T3", "price": 98000, "action": "继续盈利", "expected": "profitable"},
            {"time": "T4", "price": 100000, "action": "整体止盈", "expected": "tp_triggered"},
        ],
        "initial_balance": 10000.0,
        "expected_final_balance": 11800.0,  # 两笔仓位合计盈利
    }


@pytest.fixture
def price_generator_static():
    """静态价格生成器 - 固定价格"""
    def generator():
        return 95000.0
    return generator


@pytest.fixture
def price_generator_trend(request):
    """趋势价格生成器 - 可配置趋势"""
    trend = getattr(request, 'param', 'up')  # 'up', 'down', 'volatile'
    
    prices = {
        'up': [95000, 96000, 97000, 98000, 99000, 100000],
        'down': [95000, 94000, 93000, 92000, 91000, 90000],
        'volatile': [95000, 98000, 93000, 97000, 92000, 96000],
    }
    
    index = 0
    price_list = prices.get(trend, prices['up'])
    
    def generator():
        nonlocal index
        price = price_list[min(index, len(price_list) - 1)]
        index += 1
        return price
    
    return generator
