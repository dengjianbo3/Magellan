"""
Unit Tests for TradeExecutor - 交易执行专员测试

新架构测试重点：
1. TradeExecutor接收并执行Leader的TradingSignal
2. 二次验证逻辑（信号验证、账户检查、持仓冲突检查）
3. 执行不同类型的交易（long/short/hold/close）
4. 拒绝不合理的信号
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


@pytest.fixture
def mock_toolkit():
    """Mock TradingToolkit"""
    toolkit = MagicMock()
    toolkit._tools = {}
    return toolkit


@pytest.fixture
def mock_paper_trader():
    """Mock PaperTrader"""
    trader = MagicMock()
    trader.get_account_status = MagicMock(return_value={
        'balance': 10000.0,
        'used_margin': 0.0,
        'total_equity': 10000.0
    })
    trader.get_position = MagicMock(return_value=None)
    trader.open_long = AsyncMock(return_value={
        'status': 'success',
        'direction': 'long',
        'leverage': 5,
        'margin': 2000.0
    })
    trader.open_short = AsyncMock(return_value={
        'status': 'success',
        'direction': 'short',
        'leverage': 5,
        'margin': 2000.0
    })
    trader.close_position = AsyncMock(return_value={
        'status': 'success',
        'pnl': 100.0
    })
    return trader


@pytest.fixture
def mock_trading_signal_long():
    """Mock TradingSignal for long position"""
    from app.core.trading.trading_meeting import TradingSignal
    return TradingSignal(
        direction="long",
        symbol="BTC-USDT-SWAP",
        leverage=5,
        amount_percent=30.0,
        entry_price=95000.0,
        take_profit_price=100000.0,
        stop_loss_price=92000.0,
        confidence=75,
        reasoning="技术面看多，突破关键阻力位",
        agents_consensus={}
    )


@pytest.fixture
def mock_trading_signal_short():
    """Mock TradingSignal for short position"""
    from app.core.trading.trading_meeting import TradingSignal
    return TradingSignal(
        direction="short",
        symbol="BTC-USDT-SWAP",
        leverage=5,
        amount_percent=30.0,
        entry_price=95000.0,
        take_profit_price=90000.0,
        stop_loss_price=98000.0,
        confidence=75,
        reasoning="技术面看空，跌破支撑位",
        agents_consensus={}
    )


@pytest.fixture
def mock_trading_signal_hold():
    """Mock TradingSignal for hold"""
    from app.core.trading.trading_meeting import TradingSignal
    return TradingSignal(
        direction="hold",
        symbol="BTC-USDT-SWAP",
        leverage=0,
        amount_percent=0.0,
        entry_price=95000.0,
        take_profit_price=0.0,
        stop_loss_price=0.0,
        confidence=50,
        reasoning="市场不明朗，观望等待",
        agents_consensus={}
    )


@pytest.fixture
def mock_trading_signal_invalid():
    """Mock invalid TradingSignal"""
    from app.core.trading.trading_meeting import TradingSignal
    return TradingSignal(
        direction="long",
        symbol="BTC-USDT-SWAP",
        leverage=50,  # 超过限制
        amount_percent=30.0,
        entry_price=95000.0,
        take_profit_price=0.0,  # ❌ 无效：止盈未设置
        stop_loss_price=0.0,  # ❌ 无效：止损未设置
        confidence=75,
        reasoning="",
        agents_consensus={}
    )


# ============================================================================
# Test 1: Signal Validation (信号验证)
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
async def test_validate_signal_valid(mock_toolkit, mock_paper_trader, mock_trading_signal_long):
    """测试：有效信号通过验证"""
    from app.core.trading.trade_executor import TradeExecutor
    
    executor = TradeExecutor(toolkit=mock_toolkit, paper_trader=mock_paper_trader)
    
    result = executor._validate_signal(mock_trading_signal_long)
    
    assert result['valid'] is True
    assert result['reason'] == ""


@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
async def test_validate_signal_invalid_leverage(mock_toolkit, mock_paper_trader):
    """测试：不合理杠杆被拒绝"""
    from app.core.trading.trade_executor import TradeExecutor
    from app.core.trading.trading_meeting import TradingSignal
    
    executor = TradeExecutor(toolkit=mock_toolkit, paper_trader=mock_paper_trader)
    
    # 杠杆倍数不合理
    signal = TradingSignal(
        direction="long",
        symbol="BTC-USDT-SWAP",
        leverage=50,  # ❌ 超过20倍限制
        amount_percent=30.0,
        entry_price=95000.0,
        take_profit_price=100000.0,
        stop_loss_price=92000.0,
        confidence=75,
        reasoning="",
        agents_consensus={}
    )
    
    result = executor._validate_signal(signal)
    
    assert result['valid'] is False
    assert "杠杆倍数不合理" in result['reason']


@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
async def test_validate_signal_missing_tp_sl(mock_toolkit, mock_paper_trader):
    """测试：缺少止盈止损被拒绝"""
    from app.core.trading.trade_executor import TradeExecutor
    from app.core.trading.trading_meeting import TradingSignal
    
    executor = TradeExecutor(toolkit=mock_toolkit, paper_trader=mock_paper_trader)
    
    signal = TradingSignal(
        direction="long",
        symbol="BTC-USDT-SWAP",
        leverage=5,
        amount_percent=30.0,
        entry_price=95000.0,
        take_profit_price=0.0,  # ❌ 未设置
        stop_loss_price=0.0,  # ❌ 未设置
        confidence=75,
        reasoning="",
        agents_consensus={}
    )
    
    result = executor._validate_signal(signal)
    
    assert result['valid'] is False
    assert "止盈止损" in result['reason']


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_signal_invalid_amount(mock_toolkit, mock_paper_trader):
    """测试：不合理仓位比例被拒绝"""
    from app.core.trading.trade_executor import TradeExecutor
    from app.core.trading.trading_meeting import TradingSignal
    
    executor = TradeExecutor(toolkit=mock_toolkit, paper_trader=mock_paper_trader)
    
    signal = TradingSignal(
        direction="long",
        symbol="BTC-USDT-SWAP",
        leverage=5,
        amount_percent=150.0,  # ❌ 超过100%
        entry_price=95000.0,
        take_profit_price=100000.0,
        stop_loss_price=92000.0,
        confidence=75,
        reasoning="",
        agents_consensus={}
    )
    
    result = executor._validate_signal(signal)
    
    assert result['valid'] is False
    assert "仓位比例不合理" in result['reason']


# ============================================================================
# Test 2: Account Status Check (账户状态检查)
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
async def test_check_account_sufficient_balance(mock_toolkit, mock_paper_trader):
    """测试：余额充足通过检查"""
    from app.core.trading.trade_executor import TradeExecutor
    
    executor = TradeExecutor(toolkit=mock_toolkit, paper_trader=mock_paper_trader)
    
    result = await executor._check_account_status()
    
    assert result['ok'] is True
    assert result['balance'] == 10000.0


@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
async def test_check_account_insufficient_balance(mock_toolkit):
    """测试：余额不足被拒绝"""
    from app.core.trading.trade_executor import TradeExecutor
    
    # Mock低余额
    trader = MagicMock()
    trader.get_account_status = MagicMock(return_value={
        'balance': 5.0,  # ❌ 低于10 USDT最低要求
        'used_margin': 0.0,
        'total_equity': 5.0
    })
    
    executor = TradeExecutor(toolkit=mock_toolkit, paper_trader=trader)
    
    result = await executor._check_account_status()
    
    assert result['ok'] is False
    assert "余额不足" in result['reason']


# ============================================================================
# Test 3: Position Conflict Check (持仓冲突检查)
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
async def test_check_no_position_conflict(mock_toolkit, mock_paper_trader, mock_trading_signal_long):
    """测试：无持仓时无冲突"""
    from app.core.trading.trade_executor import TradeExecutor
    
    executor = TradeExecutor(toolkit=mock_toolkit, paper_trader=mock_paper_trader)
    
    position_info = {
        "has_position": False,
        "current_position": None,
        "can_add": False
    }
    
    result = executor._check_position_conflict(mock_trading_signal_long, position_info)
    
    assert result['has_conflict'] is False


@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
async def test_check_position_conflict_same_direction_can_add(mock_toolkit, mock_paper_trader, mock_trading_signal_long):
    """测试：同方向持仓，允许追加"""
    from app.core.trading.trade_executor import TradeExecutor
    
    executor = TradeExecutor(toolkit=mock_toolkit, paper_trader=mock_paper_trader)
    
    position_info = {
        "has_position": True,
        "current_position": {"direction": "long"},
        "can_add": True  # ✅ 允许追加
    }
    
    result = executor._check_position_conflict(mock_trading_signal_long, position_info)
    
    assert result['has_conflict'] is False
    assert "追加" in result['reason']


@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
async def test_check_position_conflict_same_direction_cannot_add(mock_toolkit, mock_paper_trader, mock_trading_signal_long):
    """测试：同方向持仓，但已达上限"""
    from app.core.trading.trade_executor import TradeExecutor
    
    executor = TradeExecutor(toolkit=mock_toolkit, paper_trader=mock_paper_trader)
    
    position_info = {
        "has_position": True,
        "current_position": {"direction": "long"},
        "can_add": False  # ❌ 不允许追加
    }
    
    result = executor._check_position_conflict(mock_trading_signal_long, position_info)
    
    assert result['has_conflict'] is True
    assert "已达仓位上限" in result['reason']


@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
async def test_check_position_conflict_opposite_direction(mock_toolkit, mock_paper_trader, mock_trading_signal_short):
    """测试：反向持仓冲突"""
    from app.core.trading.trade_executor import TradeExecutor
    
    executor = TradeExecutor(toolkit=mock_toolkit, paper_trader=mock_paper_trader)
    
    position_info = {
        "has_position": True,
        "current_position": {"direction": "long"},  # 当前是多仓
        "can_add": False
    }
    
    # 尝试开空仓
    result = executor._check_position_conflict(mock_trading_signal_short, position_info)
    
    assert result['has_conflict'] is True
    assert "不能直接开short仓" in result['reason']


# ============================================================================
# Test 4: Execute Trade (执行交易)
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
async def test_execute_long_success(mock_toolkit, mock_paper_trader, mock_trading_signal_long):
    """测试：成功执行做多"""
    from app.core.trading.trade_executor import TradeExecutor
    
    executor = TradeExecutor(toolkit=mock_toolkit, paper_trader=mock_paper_trader)
    
    position_info = {
        "has_position": False,
        "current_position": None,
        "can_add": False
    }
    
    result = await executor.execute_signal(mock_trading_signal_long, position_info)
    
    assert result['status'] == 'success'
    assert result['action'] == 'opened_long'
    assert mock_paper_trader.open_long.called


@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
async def test_execute_short_success(mock_toolkit, mock_paper_trader, mock_trading_signal_short):
    """测试：成功执行做空"""
    from app.core.trading.trade_executor import TradeExecutor
    
    executor = TradeExecutor(toolkit=mock_toolkit, paper_trader=mock_paper_trader)
    
    position_info = {
        "has_position": False,
        "current_position": None,
        "can_add": False
    }
    
    result = await executor.execute_signal(mock_trading_signal_short, position_info)
    
    assert result['status'] == 'success'
    assert result['action'] == 'opened_short'
    assert mock_paper_trader.open_short.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_hold_no_action(mock_toolkit, mock_paper_trader, mock_trading_signal_hold):
    """测试：观望不执行交易"""
    from app.core.trading.trade_executor import TradeExecutor
    
    executor = TradeExecutor(toolkit=mock_toolkit, paper_trader=mock_paper_trader)
    
    position_info = {
        "has_position": False,
        "current_position": None,
        "can_add": False
    }
    
    result = await executor.execute_signal(mock_trading_signal_hold, position_info)
    
    assert result['status'] == 'success'
    assert result['action'] == 'hold'
    assert not mock_paper_trader.open_long.called
    assert not mock_paper_trader.open_short.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_close_position(mock_toolkit, mock_paper_trader):
    """测试：成功平仓"""
    from app.core.trading.trade_executor import TradeExecutor
    from app.core.trading.trading_meeting import TradingSignal
    
    executor = TradeExecutor(toolkit=mock_toolkit, paper_trader=mock_paper_trader)
    
    signal = TradingSignal(
        direction="close",
        symbol="BTC-USDT-SWAP",
        leverage=0,
        amount_percent=0.0,
        entry_price=95000.0,
        take_profit_price=0.0,
        stop_loss_price=0.0,
        confidence=0,
        reasoning="市场转向，止损离场",
        agents_consensus={}
    )
    
    position_info = {
        "has_position": True,
        "current_position": {"direction": "long"},
        "can_add": False
    }
    
    result = await executor.execute_signal(signal, position_info)
    
    assert result['status'] == 'success'
    assert result['action'] == 'closed_position'
    assert mock_paper_trader.close_position.called


# ============================================================================
# Test 5: Full Execution Flow (完整执行流程)
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
async def test_full_execution_flow_success(mock_toolkit, mock_paper_trader, mock_trading_signal_long):
    """测试：完整执行流程 - 成功"""
    from app.core.trading.trade_executor import TradeExecutor
    
    executor = TradeExecutor(toolkit=mock_toolkit, paper_trader=mock_paper_trader)
    
    position_info = {
        "has_position": False,
        "current_position": None,
        "account": {"balance": 10000.0},
        "can_add": False
    }
    
    # 执行信号
    result = await executor.execute_signal(mock_trading_signal_long, position_info)
    
    # 验证流程
    assert result['status'] == 'success'
    assert result['action'] == 'opened_long'
    
    # 验证调用了paper_trader
    mock_paper_trader.open_long.assert_called_once()
    call_args = mock_paper_trader.open_long.call_args[1]
    assert call_args['symbol'] == "BTC-USDT-SWAP"
    assert call_args['leverage'] == 5
    assert call_args['take_profit_price'] == 100000.0
    assert call_args['stop_loss_price'] == 92000.0


@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
async def test_full_execution_flow_rejected_invalid_signal(mock_toolkit, mock_paper_trader, mock_trading_signal_invalid):
    """测试：完整执行流程 - 信号无效被拒绝"""
    from app.core.trading.trade_executor import TradeExecutor
    
    executor = TradeExecutor(toolkit=mock_toolkit, paper_trader=mock_paper_trader)
    
    position_info = {
        "has_position": False,
        "current_position": None,
        "can_add": False
    }
    
    # 执行信号
    result = await executor.execute_signal(mock_trading_signal_invalid, position_info)
    
    # 应该在验证阶段被拒绝
    assert result['status'] == 'rejected'
    assert result['action'] == 'validation_failed'
    
    # 不应该调用paper_trader
    assert not mock_paper_trader.open_long.called


@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
async def test_full_execution_flow_rejected_low_balance(mock_toolkit, mock_trading_signal_long):
    """测试：完整执行流程 - 余额不足被拒绝"""
    from app.core.trading.trade_executor import TradeExecutor
    
    # Mock低余额trader
    trader = MagicMock()
    trader.get_account_status = MagicMock(return_value={
        'balance': 5.0,  # ❌ 余额不足
        'used_margin': 0.0,
        'total_equity': 5.0
    })
    
    executor = TradeExecutor(toolkit=mock_toolkit, paper_trader=trader)
    
    position_info = {
        "has_position": False,
        "current_position": None,
        "can_add": False
    }
    
    # 执行信号
    result = await executor.execute_signal(mock_trading_signal_long, position_info)
    
    # 应该在账户检查阶段被拒绝
    assert result['status'] == 'rejected'
    assert result['action'] == 'account_check_failed'
    assert "余额不足" in result['reason']


@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
async def test_full_execution_flow_rejected_position_conflict(mock_toolkit, mock_paper_trader, mock_trading_signal_short):
    """测试：完整执行流程 - 持仓冲突被拒绝"""
    from app.core.trading.trade_executor import TradeExecutor
    
    executor = TradeExecutor(toolkit=mock_toolkit, paper_trader=mock_paper_trader)
    
    # 已有多仓，尝试开空仓
    position_info = {
        "has_position": True,
        "current_position": {"direction": "long"},  # 当前多仓
        "can_add": False
    }
    
    # 尝试开空仓
    result = await executor.execute_signal(mock_trading_signal_short, position_info)
    
    # 应该在持仓冲突检查阶段被拒绝
    assert result['status'] == 'rejected'
    assert result['action'] == 'position_conflict'
    assert "不能直接开short仓" in result['reason']


# ============================================================================
# Test 6: Edge Cases (边界情况)
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_executor_without_paper_trader(mock_toolkit, mock_trading_signal_hold):
    """测试：没有paper_trader的executor（简化检查）"""
    from app.core.trading.trade_executor import TradeExecutor
    
    executor = TradeExecutor(toolkit=mock_toolkit, paper_trader=None)
    
    position_info = None
    
    # 执行hold信号
    result = await executor.execute_signal(mock_trading_signal_hold, position_info)
    
    # 应该成功（hold不需要实际执行）
    assert result['status'] == 'success'
    assert result['action'] == 'hold'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_executor_with_execution_error(mock_toolkit, mock_paper_trader, mock_trading_signal_long):
    """测试：执行过程中出现异常"""
    from app.core.trading.trade_executor import TradeExecutor
    
    # Mock paper_trader抛出异常
    mock_paper_trader.open_long = AsyncMock(side_effect=Exception("Network error"))
    
    executor = TradeExecutor(toolkit=mock_toolkit, paper_trader=mock_paper_trader)
    
    position_info = {
        "has_position": False,
        "current_position": None,
        "can_add": False
    }
    
    # 执行信号
    result = await executor.execute_signal(mock_trading_signal_long, position_info)
    
    # 应该返回error
    assert result['status'] == 'error'
    assert result['action'] == 'execution_error'
    assert "Network error" in result['reason']
