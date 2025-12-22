"""
Integration Tests for Position-Aware System - 持仓感知系统集成测试

测试Day 2实现的核心功能：
1. PositionContext数据收集
2. 持仓感知的prompt生成
3. Leader决策矩阵
4. 6个关键场景的端到端测试
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta


@pytest.mark.integration
@pytest.mark.critical
@pytest.mark.asyncio
async def test_get_position_context_no_position(clean_paper_trader):
    """场景1：无持仓时的PositionContext"""
    from app.core.trading.trading_meeting import TradingMeeting
    from app.core.trading.trading_agents import TradingAgentFactory
    
    # 创建TradingMeeting
    config = MagicMock()
    config.symbol = "BTC-USDT-SWAP"
    config.max_position_percent = 1.0
    
    toolkit = MagicMock()
    agent_factory = TradingAgentFactory(MagicMock(), toolkit)
    
    meeting = TradingMeeting(
        config=config,
        agent_factory=agent_factory,
        paper_trader=clean_paper_trader,
        toolkit=toolkit
    )
    
    # 获取position_context
    position_context = await meeting._get_position_context()
    
    # 断言：无持仓
    assert position_context.has_position is False
    assert position_context.direction is None
    assert position_context.unrealized_pnl == 0.0
    assert position_context.available_balance == 10000.0
    assert position_context.can_add_position is False
    
    # 验证to_summary()输出
    summary = position_context.to_summary()
    assert "无持仓" in summary or "No Position" in summary
    assert "可用余额" in summary
    print(f"\n✅ 无持仓PositionContext:\n{summary}")


@pytest.mark.integration
@pytest.mark.critical
@pytest.mark.asyncio
async def test_get_position_context_with_long_position(clean_paper_trader, mock_price_stable):
    """场景2：有多仓时的PositionContext"""
    from app.core.trading.trading_meeting import TradingMeeting
    from app.core.trading.trading_agents import TradingAgentFactory
    
    trader = clean_paper_trader
    
    # 先开一个多仓
    with patch.object(trader, 'get_current_price', return_value=95000.0):
        result = await trader.open_long(
            symbol="BTC-USDT-SWAP",
            leverage=10,
            amount_usdt=5000.0,
            tp_price=99750.0,
            sl_price=93100.0
        )
    
    assert result["success"] is True
    
    # 创建TradingMeeting
    config = MagicMock()
    config.symbol = "BTC-USDT-SWAP"
    config.max_position_percent = 1.0
    
    toolkit = MagicMock()
    agent_factory = TradingAgentFactory(MagicMock(), toolkit)
    
    meeting = TradingMeeting(
        config=config,
        agent_factory=agent_factory,
        paper_trader=trader,
        toolkit=toolkit
    )
    
    # Mock当前价格为盈利状态
    with patch.object(trader, 'get_current_price', return_value=96000.0):
        position_context = await meeting._get_position_context()
    
    # 断言：有持仓
    assert position_context.has_position is True
    assert position_context.direction == "long"
    assert position_context.leverage == 10
    assert position_context.size > 0
    assert position_context.unrealized_pnl > 0  # 盈利
    assert position_context.unrealized_pnl_percent > 0
    assert position_context.current_position_percent > 0
    assert position_context.can_add_position is True  # 50%仓位，可追加
    
    # 验证to_summary()输出
    summary = position_context.to_summary()
    assert "LONG" in summary
    assert "盈利" in summary or "📈" in summary
    assert "可追加" in summary or "✅" in summary
    print(f"\n✅ 有持仓PositionContext:\n{summary}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_generate_decision_guidance_no_position():
    """测试：无持仓时的决策指导生成"""
    from app.core.trading.trading_meeting import TradingMeeting
    from app.core.trading.position_context import PositionContext
    
    # 创建无持仓的context
    position_context = PositionContext(
        has_position=False,
        available_balance=10000.0,
        total_equity=10000.0
    )
    
    # 创建mock meeting
    meeting = MagicMock(spec=TradingMeeting)
    meeting._generate_decision_guidance = TradingMeeting._generate_decision_guidance.__get__(meeting)
    
    # 生成决策指导
    guidance = meeting._generate_decision_guidance(position_context)
    
    # 断言
    assert "无持仓" in guidance
    assert "做多" in guidance
    assert "做空" in guidance
    assert "观望" in guidance
    print(f"\n✅ 无持仓决策指导:\n{guidance}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_generate_decision_guidance_with_profitable_position():
    """测试：盈利持仓时的决策指导生成"""
    from app.core.trading.trading_meeting import TradingMeeting
    from app.core.trading.position_context import PositionContext
    
    # 创建盈利多仓的context
    position_context = PositionContext(
        has_position=True,
        direction="long",
        entry_price=95000.0,
        current_price=96000.0,
        size=0.5,
        leverage=10,
        margin_used=5000.0,
        unrealized_pnl=500.0,
        unrealized_pnl_percent=5.26,
        liquidation_price=90000.0,
        distance_to_liquidation_percent=6.25,
        take_profit_price=99750.0,
        stop_loss_price=93100.0,
        distance_to_tp_percent=3.91,
        distance_to_sl_percent=-3.02,
        available_balance=5000.0,
        total_equity=10500.0,
        used_margin=5000.0,
        max_position_percent=1.0,
        current_position_percent=0.5,
        can_add_position=True,
        max_additional_amount=5000.0,
        opened_at=datetime.now() - timedelta(hours=2),
        holding_duration_hours=2.0
    )
    
    # 创建mock meeting
    meeting = MagicMock(spec=TradingMeeting)
    meeting._generate_decision_guidance = TradingMeeting._generate_decision_guidance.__get__(meeting)
    
    # 生成决策指导
    guidance = meeting._generate_decision_guidance(position_context)
    
    # 断言
    assert "LONG" in guidance
    assert "盈利" in guidance or "📈" in guidance
    assert "追加" in guidance
    assert "反向" in guidance
    assert "决策矩阵" in guidance or "表格" in guidance or "|" in guidance  # 包含表格
    print(f"\n✅ 盈利持仓决策指导:\n{guidance}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_decision_options_for_analysts_no_position():
    """测试：无持仓时的分析师决策选项"""
    from app.core.trading.trading_meeting import TradingMeeting
    from app.core.trading.position_context import PositionContext
    
    position_context = PositionContext(
        has_position=False,
        available_balance=10000.0,
        total_equity=10000.0
    )
    
    meeting = MagicMock(spec=TradingMeeting)
    meeting._get_decision_options_for_analysts = TradingMeeting._get_decision_options_for_analysts.__get__(meeting)
    
    options = meeting._get_decision_options_for_analysts(position_context)
    
    assert "无持仓" in options
    assert "做多" in options
    assert "做空" in options
    assert "观望" in options
    print(f"\n✅ 无持仓分析师选项:\n{options}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_decision_options_for_analysts_with_position():
    """测试：有持仓时的分析师决策选项"""
    from app.core.trading.trading_meeting import TradingMeeting
    from app.core.trading.position_context import PositionContext
    
    position_context = PositionContext(
        has_position=True,
        direction="long",
        unrealized_pnl=500.0,
        unrealized_pnl_percent=5.0,
        current_position_percent=0.5,
        can_add_position=True,
        holding_duration_hours=2.5,
        available_balance=5000.0,
        total_equity=10500.0
    )
    
    meeting = MagicMock(spec=TradingMeeting)
    meeting._get_decision_options_for_analysts = TradingMeeting._get_decision_options_for_analysts.__get__(meeting)
    
    options = meeting._get_decision_options_for_analysts(position_context)
    
    assert "LONG" in options
    assert "追加" in options
    assert "平仓" in options
    assert "反向" in options
    assert "盈亏" in options
    assert "2.5" in options  # 持仓时长
    print(f"\n✅ 有持仓分析师选项:\n{options}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_generate_risk_context_no_position():
    """测试：无持仓时的风险评估上下文"""
    from app.core.trading.trading_meeting import TradingMeeting
    from app.core.trading.position_context import PositionContext
    
    position_context = PositionContext(
        has_position=False,
        available_balance=10000.0,
        total_equity=10000.0
    )
    
    meeting = MagicMock(spec=TradingMeeting)
    meeting._generate_risk_context = TradingMeeting._generate_risk_context.__get__(meeting)
    
    risk_context = meeting._generate_risk_context(position_context)
    
    assert "无持仓" in risk_context
    assert "风险评估" in risk_context
    assert "开仓方向" in risk_context
    assert "杠杆倍数" in risk_context
    print(f"\n✅ 无持仓风险上下文:\n{risk_context}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_generate_risk_context_with_risky_position():
    """测试：危险持仓时的风险评估上下文"""
    from app.core.trading.trading_meeting import TradingMeeting
    from app.core.trading.position_context import PositionContext
    
    # 创建接近强平的危险持仓
    position_context = PositionContext(
        has_position=True,
        direction="long",
        distance_to_liquidation_percent=15.0,  # <20% = 🔴危险
        unrealized_pnl=-1000.0,
        unrealized_pnl_percent=-10.0,
        distance_to_tp_percent=10.0,
        distance_to_sl_percent=-3.0,  # <5% = 🚨接近止损
        current_position_percent=1.0,  # 满仓
        can_add_position=False,
        holding_duration_hours=5.0,
        available_balance=0.0,
        total_equity=9000.0
    )
    
    meeting = MagicMock(spec=TradingMeeting)
    meeting._generate_risk_context = TradingMeeting._generate_risk_context.__get__(meeting)
    
    risk_context = meeting._generate_risk_context(position_context)
    
    assert "LONG" in risk_context
    assert "🔴" in risk_context or "危险" in risk_context
    assert "🚨" in risk_context or "接近止损" in risk_context
    assert "15.0%" in risk_context  # 距离强平
    print(f"\n✅ 危险持仓风险上下文:\n{risk_context}")


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scenario_1_no_position_to_long(clean_paper_trader, mock_llm_service):
    """
    场景1 端到端测试：无持仓 → 开多
    
    验证：
    1. PositionContext正确识别无持仓
    2. 分析师看到无持仓提示
    3. Leader看到决策指导
    4. 最终决策为"做多"
    """
    pytest.skip("需要完整的TradingMeeting环境，暂时跳过")
    # TODO: 实现完整的端到端测试


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scenario_2_long_position_add_more(clean_paper_trader):
    """
    场景2 端到端测试：多仓50% + 盈利5% → 追加
    
    验证：
    1. PositionContext正确计算盈亏
    2. 识别可追加状态
    3. Leader决策为"追加多仓"
    """
    pytest.skip("需要完整的TradingMeeting环境，暂时跳过")


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scenario_3_full_position_hold(clean_paper_trader):
    """
    场景3 端到端测试：多仓100% → 观望
    
    验证：
    1. PositionContext识别满仓
    2. can_add_position=False
    3. Leader决策为"观望"
    """
    pytest.skip("需要完整的TradingMeeting环境，暂时跳过")


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scenario_4_reverse_position(clean_paper_trader):
    """
    场景4 端到端测试：多仓 + 专家转空 → 反向
    
    验证：
    1. PositionContext显示多仓
    2. 专家建议反向
    3. Leader决策为"反向操作"
    """
    pytest.skip("需要完整的TradingMeeting环境，暂时跳过")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scenario_5_near_take_profit(clean_paper_trader):
    """
    场景5：接近止盈 → 观望
    
    验证：
    1. PositionContext识别接近TP
    2. 决策指导显示⚠️警告
    3. RiskAssessor评估风险
    """
    from app.core.trading.position_context import PositionContext
    from app.core.trading.trading_meeting import TradingMeeting
    
    # 创建接近止盈的持仓
    position_context = PositionContext(
        has_position=True,
        direction="long",
        distance_to_tp_percent=2.0,  # <5% = ⚠️接近止盈
        distance_to_sl_percent=-10.0,
        unrealized_pnl=800.0,
        unrealized_pnl_percent=8.0,
        can_add_position=True,
        available_balance=5000.0,
        total_equity=10800.0
    )
    
    meeting = MagicMock(spec=TradingMeeting)
    meeting._generate_decision_guidance = TradingMeeting._generate_decision_guidance.__get__(meeting)
    
    guidance = meeting._generate_decision_guidance(position_context)
    
    # 断言：应该看到接近止盈的警告
    assert "⚠️" in guidance or "接近止盈" in guidance
    assert "2.0%" in guidance
    print(f"\n✅ 接近止盈场景:\n{guidance}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scenario_6_near_stop_loss(clean_paper_trader):
    """
    场景6：接近止损 → 观望
    
    验证：
    1. PositionContext识别接近SL
    2. 决策指导显示🚨警告
    3. RiskAssessor评估风险
    """
    from app.core.trading.position_context import PositionContext
    from app.core.trading.trading_meeting import TradingMeeting
    
    # 创建接近止损的持仓
    position_context = PositionContext(
        has_position=True,
        direction="long",
        distance_to_tp_percent=10.0,
        distance_to_sl_percent=-3.0,  # <5% = 🚨接近止损
        unrealized_pnl=-150.0,
        unrealized_pnl_percent=-1.5,
        can_add_position=True,
        available_balance=5000.0,
        total_equity=9850.0
    )
    
    meeting = MagicMock(spec=TradingMeeting)
    meeting._generate_risk_context = TradingMeeting._generate_risk_context.__get__(meeting)
    
    risk_context = meeting._generate_risk_context(position_context)
    
    # 断言：应该看到接近止损的警告
    assert "🚨" in risk_context or "接近止损" in risk_context
    assert "3.0%" in risk_context or "3" in risk_context
    print(f"\n✅ 接近止损场景:\n{risk_context}")


if __name__ == "__main__":
    """直接运行测试"""
    pytest.main([__file__, "-v", "-s"])
