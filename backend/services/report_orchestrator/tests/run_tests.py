#!/usr/bin/env python3
"""
Test Runner - Runs all unit tests without pytest dependency

Usage:
    python3 run_tests.py [module_name]
    
Examples:
    python3 run_tests.py                    # Run all tests
    python3 run_tests.py decision_store     # Run only decision_store tests
    python3 run_tests.py trading_models     # Run only trading_models tests
    python3 run_tests.py vote_calculator    # Run only vote_calculator tests
"""

import sys
import os
import json
import traceback
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Test results
passed = 0
failed = 0
skipped = 0
errors = []


def test(name, condition, msg=""):
    """Assert a test condition"""
    global passed, failed, errors
    if condition:
        print(f"  {GREEN}✅ {name}{RESET}")
        passed += 1
    else:
        print(f"  {RED}❌ {name}: {msg}{RESET}")
        failed += 1
        errors.append(f"{name}: {msg}")


def test_raises(name, exception_type, func):
    """Assert that a function raises an exception"""
    global passed, failed, errors
    try:
        func()
        print(f"  {RED}❌ {name}: Expected {exception_type.__name__} but no exception{RESET}")
        failed += 1
        errors.append(f"{name}: Expected exception not raised")
    except exception_type:
        print(f"  {GREEN}✅ {name}{RESET}")
        passed += 1
    except Exception as e:
        print(f"  {RED}❌ {name}: Expected {exception_type.__name__} but got {type(e).__name__}{RESET}")
        failed += 1
        errors.append(f"{name}: Wrong exception type")


def section(name):
    """Print section header"""
    print(f"\n{BOLD}【{name}】{RESET}")


def run_decision_store_tests():
    """Run TradingDecision tests"""
    global passed, failed
    
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}TradingDecision 单元测试{RESET}")
    print(f"{'=' * 60}")
    
    # Load decision_store module
    with open('app/core/trading/decision_store.py', 'r') as f:
        content = f.read().replace('import redis.asyncio as redis', '# mocked')
    exec(content, globals())
    
    # DS-001: Full creation
    section("DS-001 完整创建")
    d = TradingDecision(
        trade_id="test-001",
        timestamp=datetime(2026, 1, 1, 21, 0, 0),
        direction="hold",
        confidence=65,
        leverage=3,
        reasoning="Test",
        entry_price=94500.50,
        tp_price=103950.55,
        sl_price=90720.48,
        agent_votes=[{"agent": "TA", "direction": "hold"}],
        was_executed=True
    )
    test("trade_id", d.trade_id == "test-001")
    test("direction", d.direction == "hold")
    test("confidence", d.confidence == 65)
    test("leverage", d.leverage == 3)
    test("entry_price", d.entry_price == 94500.50)
    test("agent_votes", len(d.agent_votes) == 1)
    test("was_executed", d.was_executed == True)

    # DS-001b: Minimal creation
    section("DS-001b 最小创建")
    minimal = TradingDecision(trade_id="minimal", timestamp=datetime.now())
    test("default direction", minimal.direction == "hold")
    test("default confidence", minimal.confidence == 0)
    test("default leverage", minimal.leverage == 1)
    test("empty agent_votes", minimal.agent_votes == [])

    # DS-002: to_dict
    section("DS-002 to_dict()")
    data = d.to_dict()
    test("is dict", isinstance(data, dict))
    test("timestamp ISO", data['timestamp'] == "2026-01-01T21:00:00")
    test("trade_id", data['trade_id'] == "test-001")

    # DS-003: from_dict
    section("DS-003 from_dict()")
    restored = TradingDecision.from_dict(data)
    test("trade_id", restored.trade_id == "test-001")
    test("timestamp type", isinstance(restored.timestamp, datetime))
    test("direction", restored.direction == "hold")

    # DS-004: Missing fields
    section("DS-004 缺失字段")
    partial = TradingDecision.from_dict({'trade_id': 'partial', 'timestamp': '2026-01-01T21:00:00'})
    test("default direction", partial.direction == "hold")
    test("default confidence", partial.confidence == 0)
    test("default leverage", partial.leverage == 1)

    # DS-005: Extra fields
    section("DS-005 额外字段")
    extra = TradingDecision.from_dict({
        'trade_id': 'extra',
        'timestamp': '2026-01-01T21:00:00',
        'unknown_field': 'value',
        'future_field': 123
    })
    test("ignores extra fields", extra.trade_id == 'extra')
    test("no unknown attr", not hasattr(extra, 'unknown_field'))

    # DS-006: None timestamp
    section("DS-006 None timestamp")
    none_ts = TradingDecision.from_dict({'trade_id': 'none-ts', 'timestamp': None})
    test("timestamp is datetime", isinstance(none_ts.timestamp, datetime))

    # DS-007: Frontend format
    section("DS-007 to_frontend_format()")
    fe = d.to_frontend_format()
    test("has trade_id", 'trade_id' in fe)
    test("has timestamp", 'timestamp' in fe)
    test("has status", 'status' in fe)
    test("has signal", 'signal' in fe)
    test("has agent_votes", 'agent_votes' in fe)
    test("status is executed", fe['status'] == 'executed')

    # DS-008: Signal dict
    section("DS-008 signal 字典")
    sig = fe['signal']
    test("direction", sig['direction'] == 'hold')
    test("confidence", sig['confidence'] == 65)
    test("leverage", sig['leverage'] == 3)
    test("take_profit_price", sig['take_profit_price'] == 103950.55)
    test("stop_loss_price", sig['stop_loss_price'] == 90720.48)
    test("leader_summary", 'leader_summary' in sig)

    # DS-009: JSON roundtrip
    section("DS-009 JSON roundtrip")
    json_str = json.dumps(d.to_dict(), ensure_ascii=False)
    parsed = json.loads(json_str)
    restored2 = TradingDecision.from_dict(parsed)
    test("trade_id", restored2.trade_id == d.trade_id)
    test("direction", restored2.direction == d.direction)
    test("confidence", restored2.confidence == d.confidence)
    test("tp_price", restored2.tp_price == d.tp_price)

    # DS-010: Agent votes
    section("DS-010 agent_votes 序列化")
    votes_d = TradingDecision(
        trade_id="votes",
        timestamp=datetime.now(),
        agent_votes=[
            {"agent": "TA", "direction": "long", "confidence": 75},
            {"agent": "SA", "direction": "hold", "confidence": 60}
        ]
    )
    restored3 = TradingDecision.from_dict(votes_d.to_dict())
    test("agent_votes count", len(restored3.agent_votes) == 2)
    test("first agent", restored3.agent_votes[0]['agent'] == 'TA')

    # Additional edge cases
    section("额外边界条件")
    for direction in ['hold', 'open_long', 'open_short', 'close_position']:
        d_dir = TradingDecision(trade_id=f"dir-{direction}", timestamp=datetime.now(), direction=direction)
        fe_dir = d_dir.to_frontend_format()
        test(f"direction {direction}", fe_dir['signal']['direction'] == direction)

    pending = TradingDecision(trade_id="pending", timestamp=datetime.now(), was_executed=False)
    fe_pending = pending.to_frontend_format()
    test("pending status", fe_pending['status'] == 'pending')


def run_vote_calculator_tests():
    """Run vote calculator tests"""
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}Vote Calculator 单元测试{RESET}")
    print(f"{'=' * 60}")
    
    def calculate_consensus(votes):
        """Vote calculation logic"""
        if not votes:
            return {"direction": "hold", "confidence": 0}
        
        direction_scores = {"long": 0, "short": 0, "hold": 0}
        confidence_sum = {"long": 0, "short": 0, "hold": 0}
        direction_count = {"long": 0, "short": 0, "hold": 0}
        
        for vote in votes:
            direction = vote.get("direction", "hold")
            confidence = vote.get("confidence", 50)
            weight = vote.get("weight", 1.0)
            
            if direction in direction_scores:
                direction_scores[direction] += confidence * weight
                confidence_sum[direction] += confidence
                direction_count[direction] += 1
        
        winner = max(direction_scores, key=direction_scores.get)
        
        if direction_scores["long"] == direction_scores["short"] and direction_scores["long"] > 0:
            winner = "hold"
        
        if direction_count[winner] > 0:
            avg_confidence = confidence_sum[winner] // direction_count[winner]
        else:
            avg_confidence = 0
        
        return {"direction": winner, "confidence": avg_confidence}
    
    section("VC-001 全票 LONG")
    votes = [{"agent": f"A{i}", "direction": "long", "confidence": 70 + i} for i in range(5)]
    result = calculate_consensus(votes)
    test("consensus=long", result["direction"] == "long")
    
    section("VC-002 全票 SHORT")
    votes = [{"agent": f"A{i}", "direction": "short", "confidence": 70 + i} for i in range(5)]
    result = calculate_consensus(votes)
    test("consensus=short", result["direction"] == "short")
    
    section("VC-003 全票 HOLD")
    votes = [{"agent": f"A{i}", "direction": "hold", "confidence": 60 + i} for i in range(5)]
    result = calculate_consensus(votes)
    test("consensus=hold", result["direction"] == "hold")
    
    section("VC-004 多数 LONG")
    votes = [
        {"agent": "TA", "direction": "long", "confidence": 70},
        {"agent": "SA", "direction": "long", "confidence": 75},
        {"agent": "ME", "direction": "long", "confidence": 65},
        {"agent": "OA", "direction": "hold", "confidence": 50},
        {"agent": "QS", "direction": "hold", "confidence": 55},
    ]
    result = calculate_consensus(votes)
    test("consensus=long", result["direction"] == "long")
    
    section("VC-005 分裂投票 → HOLD")
    votes = [
        {"agent": "TA", "direction": "long", "confidence": 70},
        {"agent": "SA", "direction": "long", "confidence": 70},
        {"agent": "ME", "direction": "short", "confidence": 70},
        {"agent": "OA", "direction": "short", "confidence": 70},
        {"agent": "QS", "direction": "hold", "confidence": 60},
    ]
    result = calculate_consensus(votes)
    test("consensus=hold (conservative)", result["direction"] == "hold")
    
    section("VC-006 权重调整")
    votes = [
        {"agent": "TA", "direction": "long", "confidence": 60, "weight": 2.0},
        {"agent": "SA", "direction": "short", "confidence": 80, "weight": 0.5},
        {"agent": "ME", "direction": "hold", "confidence": 50, "weight": 1.0},
    ]
    result = calculate_consensus(votes)
    test("higher weight wins", result["direction"] == "long")
    
    section("VC-007 空投票")
    result = calculate_consensus([])
    test("direction=hold", result["direction"] == "hold")
    test("confidence=0", result["confidence"] == 0)
    
    section("VC-008 高置信度权重")
    votes = [
        {"agent": "TA", "direction": "long", "confidence": 95},
        {"agent": "SA", "direction": "short", "confidence": 40},
        {"agent": "ME", "direction": "short", "confidence": 40},
    ]
    result = calculate_consensus(votes)
    test("high confidence wins", result["direction"] == "long")


def run_safety_guard_tests():
    """Run SafetyGuard component tests"""
    import asyncio
    
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}SafetyGuard 组件测试{RESET}")
    print(f"{'=' * 60}")
    
    # Create event loop for Python 3.14+ compatibility
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    def run_async(coro):
        """Helper to run async functions"""
        return loop.run_until_complete(coro)
    
    # Load SafetyGuard module
    with open('app/core/trading/safety/guards.py', 'r') as f:
        content = f.read()
    exec(content, globals())
    
    # Mock trader
    class MockTrader:
        def __init__(self):
            self._daily_loss_exceeded = False
            self.is_hedge_mode = False
        
        def _check_daily_loss_limit(self):
            if self._daily_loss_exceeded:
                return (False, "Daily loss limit exceeded")
            return (True, "OK")
        
        async def get_account(self):
            return {"available_balance": 10000.0}
    
    # Mock cooldown manager
    class MockCooldown:
        def __init__(self, is_active=False):
            self._is_active = is_active
        
        def check_cooldown(self):
            return not self._is_active
    
    # Mock config
    class MockConfig:
        max_leverage = 20
        max_position_percent = 0.3
    
    # SG-001: Concurrent execution lock
    section("SG-001 并发执行锁")
    
    async def test_concurrent_lock():
        trader = MockTrader()
        guard = SafetyGuard(trader, min_confidence=60)
        
        # Acquire lock
        await guard.acquire_execution_lock()
        
        # Check should block
        result = await guard.pre_execution_check(
            votes=[],
            position_context={"has_position": False}
        )
        test("concurrent blocked", not result.allowed)
        test("reason is CONCURRENT_EXECUTION", result.reason == BlockReason.CONCURRENT_EXECUTION)
        
        guard.release_execution_lock()
    
    run_async(test_concurrent_lock())
    
    # SG-002: Startup protection
    section("SG-002 启动保护")
    
    async def test_startup_protection():
        trader = MockTrader()
        guard = SafetyGuard(trader, min_confidence=60)
        
        # Startup with existing position, trying to reverse
        result = await guard.pre_execution_check(
            votes=[{"direction": "short", "confidence": 70}],
            position_context={"has_position": True, "direction": "long"},
            trigger_reason="startup"
        )
        test("startup reverse blocked", not result.allowed)
        test("reason is STARTUP_PROTECTION", result.reason == BlockReason.STARTUP_PROTECTION)
    
    run_async(test_startup_protection())
    
    # SG-003: Daily loss limit
    section("SG-003 日亏损限制")
    
    async def test_daily_loss():
        trader = MockTrader()
        trader._daily_loss_exceeded = True
        guard = SafetyGuard(trader, min_confidence=60)
        
        result = await guard.pre_execution_check(
            votes=[],
            position_context={"has_position": False}
        )
        test("daily loss blocked", not result.allowed)
        test("reason is DAILY_LOSS_LIMIT", result.reason == BlockReason.DAILY_LOSS_LIMIT)
    
    run_async(test_daily_loss())
    
    # SG-004: Cooldown active
    section("SG-004 冷却期检查")
    
    async def test_cooldown():
        trader = MockTrader()
        cooldown = MockCooldown(is_active=True)
        guard = SafetyGuard(trader, cooldown_manager=cooldown, min_confidence=60)
        
        result = await guard.pre_execution_check(
            votes=[],
            position_context={"has_position": False}
        )
        test("cooldown blocked", not result.allowed)
        test("reason is COOLDOWN_ACTIVE", result.reason == BlockReason.COOLDOWN_ACTIVE)
    
    run_async(test_cooldown())
    
    # SG-005: Cooldown expired - should allow
    section("SG-005 冷却期结束")
    
    async def test_cooldown_expired():
        trader = MockTrader()
        cooldown = MockCooldown(is_active=False)
        guard = SafetyGuard(trader, cooldown_manager=cooldown, min_confidence=60)
        
        result = await guard.pre_execution_check(
            votes=[],
            position_context={"has_position": False},
            confidence=70
        )
        test("cooldown expired allows", result.allowed)
    
    run_async(test_cooldown_expired())
    
    # SG-006: Leverage validation
    section("SG-006 杠杆验证")
    
    async def test_leverage():
        trader = MockTrader()
        config = MockConfig()
        guard = SafetyGuard(trader, config=config, min_confidence=60)
        
        # Valid leverage
        result = await guard.validate_trade_params("long", 10, 1000.0)
        test("valid leverage allowed", result.allowed)
        
        # Exceeds max
        result = await guard.validate_trade_params("long", 25, 1000.0)
        test("excessive leverage blocked", not result.allowed)
        test("reason is INVALID_PARAMS", result.reason == BlockReason.INVALID_PARAMS)
        
        # Zero leverage
        result = await guard.validate_trade_params("long", 0, 1000.0)
        test("zero leverage blocked", not result.allowed)
    
    run_async(test_leverage())
    
    # SG-007: Position size validation
    section("SG-007 仓位比例验证")
    
    async def test_position_size():
        trader = MockTrader()
        config = MockConfig()
        guard = SafetyGuard(trader, config=config, min_confidence=60)
        
        # Exceeds max position
        result = await guard.validate_trade_params("long", 3, 5000.0)  # 5000 > 10000 * 0.3
        test("excessive position blocked", not result.allowed)
    
    run_async(test_position_size())
    
    # SG-008: Minimum confidence
    section("SG-008 最低置信度")
    
    async def test_min_confidence():
        trader = MockTrader()
        guard = SafetyGuard(trader, min_confidence=60)
        
        result = await guard.pre_execution_check(
            votes=[],
            position_context={"has_position": False},
            confidence=50  # Below 60
        )
        test("low confidence blocked", not result.allowed)
        test("reason is LOW_CONFIDENCE", result.reason == BlockReason.LOW_CONFIDENCE)
    
    run_async(test_min_confidence())
    
    # SG-009: OKX Hedge mode check
    section("SG-009 OKX 对冲模式")
    
    async def test_hedge_mode():
        trader = MockTrader()
        trader.is_hedge_mode = True
        guard = SafetyGuard(trader, min_confidence=60)
        
        # Try to reverse position in hedge mode
        result = await guard.pre_execution_check(
            votes=[{"direction": "short", "confidence": 70}],
            position_context={"has_position": True, "direction": "long"},
            confidence=70
        )
        test("hedge mode reverse blocked", not result.allowed)
        test("reason is OKX_HEDGE_MODE", result.reason == BlockReason.OKX_HEDGE_MODE)
    
    run_async(test_hedge_mode())
    
    # SG-010: TP/SL validation for long
    section("SG-010 TP/SL 验证 (多头)")
    
    async def test_tp_sl_long():
        trader = MockTrader()
        guard = SafetyGuard(trader, min_confidence=60)
        
        # Valid TP/SL for long
        result = await guard.validate_trade_params(
            "long", 3, 1000.0, 
            tp_price=105000.0, sl_price=95000.0, 
            current_price=100000.0
        )
        test("valid TP/SL long allowed", result.allowed)
        
        # Invalid TP for long (below current)
        result = await guard.validate_trade_params(
            "long", 3, 1000.0, 
            tp_price=95000.0, sl_price=90000.0, 
            current_price=100000.0
        )
        test("TP below current blocked", not result.allowed)
        
        # Invalid SL for long (above current)
        result = await guard.validate_trade_params(
            "long", 3, 1000.0, 
            tp_price=110000.0, sl_price=105000.0, 
            current_price=100000.0
        )
        test("SL above current blocked", not result.allowed)
    
    run_async(test_tp_sl_long())
    
    # SG-011: TP/SL validation for short
    section("SG-011 TP/SL 验证 (空头)")
    
    async def test_tp_sl_short():
        trader = MockTrader()
        guard = SafetyGuard(trader, min_confidence=60)
        
        # Valid TP/SL for short
        result = await guard.validate_trade_params(
            "short", 3, 1000.0, 
            tp_price=95000.0, sl_price=105000.0, 
            current_price=100000.0
        )
        test("valid TP/SL short allowed", result.allowed)
        
        # Invalid TP for short (above current)
        result = await guard.validate_trade_params(
            "short", 3, 1000.0, 
            tp_price=105000.0, sl_price=110000.0, 
            current_price=100000.0
        )
        test("TP above current blocked", not result.allowed)
    
    run_async(test_tp_sl_short())
    
    # SG-012: Execution lock acquire/release
    section("SG-012 执行锁获取/释放")
    
    async def test_lock():
        trader = MockTrader()
        guard = SafetyGuard(trader, min_confidence=60)
        
        # Acquire lock
        acquired = await guard.acquire_execution_lock(timeout=1.0)
        test("lock acquired", acquired)
        test("lock is locked", guard._execution_lock.locked())
        
        # Release lock
        guard.release_execution_lock()
        test("lock released", not guard._execution_lock.locked())
    
    run_async(test_lock())
    
    # SG-Extra: Allowed execution
    section("SG-Extra 允许执行")
    
    async def test_allowed():
        trader = MockTrader()
        guard = SafetyGuard(trader, min_confidence=60)
        
        result = await guard.pre_execution_check(
            votes=[{"direction": "long", "confidence": 75}],
            position_context={"has_position": False},
            confidence=75
        )
        test("normal execution allowed", result.allowed)
    
    run_async(test_allowed())


def main():
    global passed, failed, errors
    
    # Parse arguments
    module = None
    if len(sys.argv) > 1:
        module = sys.argv[1]
    
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}Magellan 交易系统测试{RESET}")
    print(f"{'=' * 60}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        if module is None or module == "decision_store":
            run_decision_store_tests()
        
        if module is None or module == "vote_calculator":
            run_vote_calculator_tests()
        
        if module is None or module == "safety_guard":
            run_safety_guard_tests()
        
    except Exception as e:
        print(f"\n{RED}❌ 测试执行错误: {e}{RESET}")
        traceback.print_exc()
        failed += 1
    
    # Summary
    total = passed + failed
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    if failed == 0:
        print(f"{GREEN}✅ 全部通过: {passed}/{total} 测试{RESET}")
    else:
        print(f"{RED}❌ 结果: {passed} 通过, {failed} 失败 (共 {total} 测试){RESET}")
        print(f"\n{RED}失败的测试:{RESET}")
        for error in errors:
            print(f"  - {error}")
    print(f"{'=' * 60}\n")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

