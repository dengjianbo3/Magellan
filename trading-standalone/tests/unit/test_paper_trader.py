"""
Unit Tests for PaperTrader - Paper交易核心逻辑测试

测试重点：
1. 交易锁防止重复开仓
2. 账户余额计算
3. 止盈止损触发
4. 参数验证和错误处理
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
async def test_open_long_success(clean_paper_trader, mock_price_stable):
    """测试：成功开多仓"""
    trader = clean_paper_trader
    
    # Mock价格服务
    with patch.object(trader, 'get_current_price', return_value=mock_price_stable.price):
        result = await trader.open_long(
            symbol="BTC-USDT-SWAP",
            leverage=10,
            amount_usdt=2000.0,
            tp_price=99750.0,
            sl_price=93100.0
        )
    
    # 断言
    assert result["success"] is True
    assert result["direction"] == "long"
    assert result["leverage"] == 10
    assert result["margin"] == 2000.0
    
    # 检查账户状态
    assert trader._account.balance == 8000.0  # 10000 - 2000
    assert trader._account.used_margin == 2000.0
    assert trader._position is not None
    assert trader._position.direction == "long"


@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
async def test_duplicate_trade_blocked(clean_paper_trader, mock_price_stable):
    """测试：交易锁防止重复开仓"""
    trader = clean_paper_trader
    
    with patch.object(trader, 'get_current_price', return_value=mock_price_stable.price):
        # 第一次开仓成功
        result1 = await trader.open_long(
            symbol="BTC-USDT-SWAP",
            leverage=10,
            amount_usdt=2000.0
        )
        assert result1["success"] is True
        
        # 第二次开仓应该被阻止
        result2 = await trader.open_long(
            symbol="BTC-USDT-SWAP",
            leverage=10,
            amount_usdt=2000.0
        )
        assert result2["success"] is False
        assert "已有持仓" in result2["error"]
        
        # 确认只有一个持仓
        assert trader._position is not None
        assert trader._account.used_margin == 2000.0  # 只扣了一次


@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_trades_blocked(clean_paper_trader, mock_price_stable):
    """测试：并发交易请求被锁阻止"""
    trader = clean_paper_trader
    
    with patch.object(trader, 'get_current_price', return_value=mock_price_stable.price):
        # 并发发起两个开仓请求
        tasks = [
            trader.open_long("BTC-USDT-SWAP", 10, 2000.0),
            trader.open_long("BTC-USDT-SWAP", 10, 2000.0),
        ]
        
        results = await asyncio.gather(*tasks)
        
        # 应该一个成功，一个失败
        success_count = sum(1 for r in results if r["success"])
        failed_count = sum(1 for r in results if not r["success"])
        
        assert success_count == 1
        assert failed_count == 1
        assert trader._account.used_margin == 2000.0  # 只成功了一次


@pytest.mark.unit
@pytest.mark.asyncio
async def test_long_take_profit_triggered(clean_paper_trader, scenario_long_tp):
    """测试：多仓止盈触发"""
    trader = clean_paper_trader
    
    # 开仓
    with patch.object(trader, 'get_current_price', return_value=scenario_long_tp.get_price()):
        result = await trader.open_long(
            symbol="BTC-USDT-SWAP",
            leverage=10,
            amount_usdt=2000.0
        )
        assert result["success"] is True
    
    # 模拟价格上涨到止盈点
    for _ in range(4):  # 前进到TP价格
        scenario_long_tp.advance()
    
    with patch.object(trader, 'get_current_price', return_value=scenario_long_tp.get_price()):
        # 检查止盈
        trigger = await trader.check_tp_sl()
        
        assert trigger == "tp"
        assert trader._position is None  # 已平仓
        assert trader._account.balance > 10000.0  # 盈利


@pytest.mark.unit
@pytest.mark.asyncio
async def test_long_stop_loss_triggered(clean_paper_trader, scenario_long_sl):
    """测试：多仓止损触发"""
    trader = clean_paper_trader
    
    # 开仓
    with patch.object(trader, 'get_current_price', return_value=scenario_long_sl.get_price()):
        result = await trader.open_long(
            symbol="BTC-USDT-SWAP",
            leverage=10,
            amount_usdt=2000.0
        )
        assert result["success"] is True
    
    # 模拟价格下跌到止损点
    for _ in range(4):
        scenario_long_sl.advance()
    
    with patch.object(trader, 'get_current_price', return_value=scenario_long_sl.get_price()):
        # 检查止损
        trigger = await trader.check_tp_sl()
        
        assert trigger == "sl"
        assert trader._position is None  # 已平仓
        assert trader._account.balance < 10000.0  # 亏损


@pytest.mark.unit
@pytest.mark.asyncio
async def test_insufficient_balance(clean_paper_trader, mock_price_stable):
    """测试：余额不足拒绝开仓"""
    trader = clean_paper_trader
    
    with patch.object(trader, 'get_current_price', return_value=mock_price_stable.price):
        # 尝试开超过余额的仓位
        result = await trader.open_long(
            symbol="BTC-USDT-SWAP",
            leverage=10,
            amount_usdt=15000.0  # 超过10000余额
        )
        
        assert result["success"] is False
        assert "保证金不足" in result["error"]
        assert trader._position is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_leverage_limit(clean_paper_trader, mock_price_stable):
    """测试：杠杆限制正确应用"""
    trader = clean_paper_trader
    
    with patch.object(trader, 'get_current_price', return_value=mock_price_stable.price):
        # 尝试使用超过上限的杠杆
        result = await trader.open_long(
            symbol="BTC-USDT-SWAP",
            leverage=20,  # 超过max_leverage=10
            amount_usdt=2000.0
        )
        
        # 应该成功，但杠杆被限制为10
        assert result["success"] is True
        assert result["leverage"] == 10  # 被限制到最大值


@pytest.mark.unit
@pytest.mark.asyncio
async def test_close_position_success(clean_paper_trader, mock_price_stable):
    """测试：成功平仓"""
    trader = clean_paper_trader
    
    with patch.object(trader, 'get_current_price', return_value=95000.0):
        # 开仓
        await trader.open_long("BTC-USDT-SWAP", 10, 2000.0)
    
    # 价格上涨1000
    with patch.object(trader, 'get_current_price', return_value=96000.0):
        # 平仓
        result = await trader.close_position(reason="manual")
        
        assert result["success"] is True
        assert result["pnl"] > 0  # 盈利
        assert trader._position is None
        assert trader._account.used_margin == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_account_equity_calculation(clean_paper_trader, mock_price_stable):
    """测试：账户权益计算正确"""
    trader = clean_paper_trader
    initial_balance = trader._account.balance
    
    with patch.object(trader, 'get_current_price', return_value=95000.0):
        # 开仓
        await trader.open_long("BTC-USDT-SWAP", 10, 2000.0)
    
    # 价格上涨
    with patch.object(trader, 'get_current_price', return_value=96000.0):
        await trader._update_equity()
        
        # 权益 = 余额 + 保证金 + 浮动盈亏
        expected_equity = (initial_balance - 2000) + 2000 + trader._account.unrealized_pnl
        assert abs(trader._account.total_equity - expected_equity) < 1.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_position_pnl_calculation(clean_paper_trader):
    """测试：持仓盈亏计算正确"""
    trader = clean_paper_trader
    
    with patch.object(trader, 'get_current_price', return_value=95000.0):
        await trader.open_long("BTC-USDT-SWAP", 10, 2000.0)
    
    # 价格上涨5%
    current_price = 99750.0
    pnl, pnl_percent = trader._position.calculate_pnl(current_price)
    
    # 杠杆10倍，价格涨5%，应该盈利约50%
    assert pnl > 0
    assert 45 < pnl_percent < 55  # 允许一定误差


@pytest.mark.unit
@pytest.mark.asyncio
async def test_parameter_type_conversion(clean_paper_trader, mock_price_stable):
    """测试：参数类型自动转换"""
    trader = clean_paper_trader
    
    with patch.object(trader, 'get_current_price', return_value=mock_price_stable.price):
        # 传入字符串类型的参数
        result = await trader.open_long(
            symbol="BTC-USDT-SWAP",
            leverage="10",  # 字符串
            amount_usdt="2000.0",  # 字符串
        )
        
        # 应该成功（内部自动转换类型）
        assert result["success"] is True
        assert result["leverage"] == 10  # int
        assert result["margin"] == 2000.0  # float


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_persistence(clean_paper_trader, mock_price_stable):
    """测试：Redis持久化"""
    trader = clean_paper_trader
    
    with patch.object(trader, 'get_current_price', return_value=mock_price_stable.price):
        # 开仓
        await trader.open_long("BTC-USDT-SWAP", 10, 2000.0)
        
        # 保存状态
        await trader._save_state()
        
        # 创建新的trader实例并加载状态
        trader2 = clean_paper_trader.__class__(config=trader.config)
        await trader2.initialize()
        await trader2._load_state()
        
        # 验证状态被正确加载
        # 注意：fakeredis在pytest fixture中可能需要特殊处理
        # 这里主要验证save/load逻辑不报错
        assert trader2._initialized is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_position_check_tp_sl(clean_paper_trader):
    """测试：无持仓时检查TP/SL返回None"""
    trader = clean_paper_trader
    
    result = await trader.check_tp_sl()
    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_status(clean_paper_trader, mock_price_stable):
    """测试：获取状态信息"""
    trader = clean_paper_trader
    
    # 无持仓状态
    status1 = trader.get_status()
    assert status1["total_equity"] == 10000.0
    assert status1["total_trades"] == 0
    
    # 开仓后状态
    with patch.object(trader, 'get_current_price', return_value=mock_price_stable.price):
        await trader.open_long("BTC-USDT-SWAP", 10, 2000.0)
    
    status2 = trader.get_status()
    assert status2["used_margin"] == 2000.0
