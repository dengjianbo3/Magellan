"""
Market Data Fixtures - 模拟市场数据

提供各种市场场景的价格数据，用于测试不同情况下的交易逻辑。
"""

import pytest
from typing import List, Dict
from datetime import datetime, timedelta


# ==================== 价格场景 ====================

@pytest.fixture
def stable_price():
    """稳定价格 - 95000"""
    return 95000.0


@pytest.fixture
def bullish_prices():
    """牛市价格序列 - 从95000逐步上涨到105000"""
    return [
        95000.0,   # Day 0
        96000.0,   # Day 1: +1.05%
        97500.0,   # Day 2: +1.56%
        99000.0,   # Day 3: +1.54%
        101000.0,  # Day 4: +2.02%
        103000.0,  # Day 5: +1.98%
        105000.0,  # Day 6: +1.94%
    ]


@pytest.fixture
def bearish_prices():
    """熊市价格序列 - 从95000逐步下跌到85000"""
    return [
        95000.0,   # Day 0
        94000.0,   # Day 1: -1.05%
        92500.0,   # Day 2: -1.60%
        91000.0,   # Day 3: -1.62%
        89000.0,   # Day 4: -2.20%
        87000.0,   # Day 5: -2.25%
        85000.0,   # Day 6: -2.30%
    ]


@pytest.fixture
def volatile_prices():
    """高波动价格序列 - 剧烈波动"""
    return [
        95000.0,   # Day 0
        98000.0,   # Day 1: +3.16%
        93000.0,   # Day 2: -5.10%
        97000.0,   # Day 3: +4.30%
        92000.0,   # Day 4: -5.15%
        99000.0,   # Day 5: +7.61%
        94000.0,   # Day 6: -5.05%
    ]


@pytest.fixture
def tp_trigger_prices_long():
    """触发多仓止盈的价格序列"""
    # 入场: 95000, TP: 99750 (+5%)
    return [
        95000.0,   # 入场价
        96000.0,   # +1.05%
        97000.0,   # +2.11%
        98500.0,   # +3.68%
        99800.0,   # +5.05% - 触发TP
    ]


@pytest.fixture
def sl_trigger_prices_long():
    """触发多仓止损的价格序列"""
    # 入场: 95000, SL: 93100 (-2%)
    return [
        95000.0,   # 入场价
        94500.0,   # -0.53%
        94000.0,   # -1.05%
        93500.0,   # -1.58%
        93000.0,   # -2.11% - 触发SL
    ]


@pytest.fixture
def tp_trigger_prices_short():
    """触发空仓止盈的价格序列"""
    # 入场: 95000, TP: 90250 (-5%)
    return [
        95000.0,   # 入场价
        94000.0,   # -1.05%
        93000.0,   # -2.11%
        91500.0,   # -3.68%
        90200.0,   # -5.05% - 触发TP
    ]


@pytest.fixture
def sl_trigger_prices_short():
    """触发空仓止损的价格序列"""
    # 入场: 95000, SL: 96900 (+2%)
    return [
        95000.0,   # 入场价
        95500.0,   # +0.53%
        96000.0,   # +1.05%
        96500.0,   # +1.58%
        97000.0,   # +2.11% - 触发SL
    ]


# ==================== K线数据 ====================

@pytest.fixture
def klines_bullish():
    """牛市K线数据"""
    return [
        {"time": "2024-01-01", "open": 90000, "high": 92000, "low": 89000, "close": 91500, "volume": 1000},
        {"time": "2024-01-02", "open": 91500, "high": 93500, "low": 91000, "close": 93000, "volume": 1200},
        {"time": "2024-01-03", "open": 93000, "high": 95000, "low": 92500, "close": 94500, "volume": 1500},
        {"time": "2024-01-04", "open": 94500, "high": 96500, "low": 94000, "close": 96000, "volume": 1800},
        {"time": "2024-01-05", "open": 96000, "high": 98000, "low": 95500, "close": 97500, "volume": 2000},
    ]


@pytest.fixture
def klines_bearish():
    """熊市K线数据"""
    return [
        {"time": "2024-01-01", "open": 100000, "high": 101000, "low": 98000, "close": 98500, "volume": 1000},
        {"time": "2024-01-02", "open": 98500, "high": 99000, "low": 96500, "close": 97000, "volume": 1200},
        {"time": "2024-01-03", "open": 97000, "high": 97500, "low": 94500, "close": 95000, "volume": 1500},
        {"time": "2024-01-04", "open": 95000, "high": 95500, "low": 92500, "close": 93000, "volume": 1800},
        {"time": "2024-01-05", "open": 93000, "high": 93500, "low": 90500, "close": 91000, "volume": 2000},
    ]


# ==================== 市场指标 ====================

@pytest.fixture
def market_indicators_bullish():
    """牛市市场指标"""
    return {
        "fear_greed_index": 75,  # 贪婪
        "rsi": 65,
        "macd": {"value": 500, "signal": 450, "histogram": 50},
        "ma20": 93000,
        "ma50": 91000,
        "funding_rate": 0.0008,  # 正向资金费率
        "volume_24h": 25000000000,
        "sentiment_score": 0.7,
    }


@pytest.fixture
def market_indicators_bearish():
    """熊市市场指标"""
    return {
        "fear_greed_index": 25,  # 恐慌
        "rsi": 35,
        "macd": {"value": -500, "signal": -450, "histogram": -50},
        "ma20": 97000,
        "ma50": 99000,
        "funding_rate": -0.0005,  # 负向资金费率
        "volume_24h": 18000000000,
        "sentiment_score": 0.3,
    }


@pytest.fixture
def market_indicators_neutral():
    """中性市场指标"""
    return {
        "fear_greed_index": 50,
        "rsi": 50,
        "macd": {"value": 0, "signal": 0, "histogram": 0},
        "ma20": 95000,
        "ma50": 95000,
        "funding_rate": 0.0001,
        "volume_24h": 20000000000,
        "sentiment_score": 0.5,
    }


# ==================== 账户状态 ====================

@pytest.fixture
def account_empty():
    """空账户状态 - 无持仓"""
    return {
        "balance": 10000.0,
        "total_equity": 10000.0,
        "used_margin": 0.0,
        "unrealized_pnl": 0.0,
        "available_balance": 10000.0,
        "has_position": False,
    }


@pytest.fixture
def account_with_long_position():
    """有多仓的账户状态"""
    return {
        "balance": 8000.0,
        "total_equity": 10200.0,  # 余额8000 + 保证金2000 + 浮盈200
        "used_margin": 2000.0,
        "unrealized_pnl": 200.0,
        "available_balance": 8000.0,
        "has_position": True,
        "position": {
            "direction": "long",
            "size": 0.21,
            "entry_price": 95000.0,
            "current_price": 96000.0,
            "leverage": 10,
            "margin": 2000.0,
            "unrealized_pnl": 200.0,
            "unrealized_pnl_percent": 10.0,  # (96000-95000)/95000 * 10x = 10.5%
            "take_profit_price": 99750.0,
            "stop_loss_price": 93100.0,
        }
    }


@pytest.fixture
def account_with_short_position():
    """有空仓的账户状态"""
    return {
        "balance": 8000.0,
        "total_equity": 9800.0,  # 余额8000 + 保证金2000 + 浮亏-200
        "used_margin": 2000.0,
        "unrealized_pnl": -200.0,
        "available_balance": 8000.0,
        "has_position": True,
        "position": {
            "direction": "short",
            "size": 0.21,
            "entry_price": 95000.0,
            "current_price": 96000.0,
            "leverage": 10,
            "margin": 2000.0,
            "unrealized_pnl": -200.0,
            "unrealized_pnl_percent": -10.5,
            "take_profit_price": 90250.0,
            "stop_loss_price": 96900.0,
        }
    }


@pytest.fixture
def account_near_position_limit():
    """接近仓位上限的账户"""
    return {
        "balance": 7000.0,
        "total_equity": 10000.0,
        "used_margin": 3000.0,  # 已用30%，上限30%
        "unrealized_pnl": 0.0,
        "available_balance": 7000.0,
        "has_position": True,
    }


@pytest.fixture
def account_low_balance():
    """余额不足的账户"""
    return {
        "balance": 500.0,  # 只剩500
        "total_equity": 2500.0,
        "used_margin": 2000.0,
        "unrealized_pnl": 0.0,
        "available_balance": 500.0,
        "has_position": True,
    }
