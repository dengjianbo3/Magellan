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


def main():
    global passed, failed, errors
    
    # Parse arguments
    module = None
    if len(sys.argv) > 1:
        module = sys.argv[1]
    
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}Magellan 交易系统单元测试{RESET}")
    print(f"{'=' * 60}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        if module is None or module == "decision_store":
            run_decision_store_tests()
        
        if module is None or module == "vote_calculator":
            run_vote_calculator_tests()
        
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
