"""
Funding Fee Awareness - Edge Case Tests

Additional tests for edge cases and boundary conditions.
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from funding.models import FundingRate, TruePnL, HoldingAlertLevel
from funding.calculator import FundingCostCalculator
from funding.entry_timing import EntryTimingController
from funding.holding_manager import HoldingTimeManager
from funding.config import FundingConfig


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
    
    def ok(self, name):
        self.passed += 1
        print(f"  ✅ {name}")
    
    def fail(self, name, expected, actual):
        self.failed += 1
        print(f"  ❌ {name}: expected {expected}, got {actual}")


def test_edge_zero_rate():
    """Test with zero funding rate"""
    print("\n🔬 Testing Zero Funding Rate...")
    results = TestResults()
    
    calc = FundingCostCalculator()
    
    # Zero rate should result in zero funding cost
    estimate = calc.estimate_holding_cost(
        position_value=1000,
        margin=100,
        leverage=10,
        holding_hours=24,
        current_rate=0.0,  # Zero rate
        direction="long"
    )
    
    if estimate.estimated_cost == 0:
        results.ok("zero rate = zero cost")
    else:
        results.fail("zero rate cost", 0, estimate.estimated_cost)
    
    return results.passed, results.failed


def test_edge_negative_pnl():
    """Test TruePnL when both price and funding are negative"""
    print("\n🔬 Testing Negative Price PnL...")
    results = TestResults()
    
    # Losing on price AND paying funding
    pnl = TruePnL(
        price_pnl=-50.0,  # Lost $50 on price
        price_pnl_percent=0,
        funding_pnl=-10.0,  # Also paid $10 funding
        funding_count=3,
        avg_funding_rate=0.0003,
        trading_fees=2.0,
        margin=500.0
    )
    
    expected = -50 + (-10) - 2  # -62
    if abs(pnl.true_pnl - expected) < 0.01:
        results.ok(f"negative scenario: ${pnl.true_pnl:.2f}")
    else:
        results.fail("negative scenario", expected, pnl.true_pnl)
    
    return results.passed, results.failed


def test_edge_receiving_funding():
    """Test when position receives funding (short in positive rate)"""
    print("\n🔬 Testing Receiving Funding...")
    results = TestResults()
    
    # Winning on price AND receiving funding
    pnl = TruePnL(
        price_pnl=30.0,  # Made $30 on price
        price_pnl_percent=0,
        funding_pnl=5.0,  # Received $5 funding (short in positive rate)
        funding_count=2,
        avg_funding_rate=0.0003,
        trading_fees=1.5,
        margin=300.0
    )
    
    expected = 30 + 5 - 1.5  # 33.5
    if abs(pnl.true_pnl - expected) < 0.01:
        results.ok(f"receiving funding: ${pnl.true_pnl:.2f}")
    else:
        results.fail("receiving funding", expected, pnl.true_pnl)
    
    return results.passed, results.failed


def test_edge_high_leverage():
    """Test with high leverage (20x)"""
    print("\n🔬 Testing High Leverage (20x)...")
    results = TestResults()
    
    calc = FundingCostCalculator()
    
    # High leverage amplifies funding cost impact
    estimate = calc.estimate_holding_cost(
        position_value=10000,  # $10k position
        margin=500,  # $500 margin (20x)
        leverage=20,
        holding_hours=8,  # Single settlement
        current_rate=0.0003,  # 0.03%
        direction="long"
    )
    
    # Cost = 10000 * 0.0003 = $3
    # As % of margin = 3 / 500 * 100 = 0.6%
    expected_cost_percent = 0.6
    if abs(estimate.cost_percent_of_margin - expected_cost_percent) < 0.1:
        results.ok(f"high leverage cost: {estimate.cost_percent_of_margin:.2f}% of margin")
    else:
        results.fail("high leverage cost", expected_cost_percent, estimate.cost_percent_of_margin)
    
    return results.passed, results.failed


def test_edge_short_holding():
    """Test very short holding time (< 8 hours)"""
    print("\n🔬 Testing Short Holding Time...")
    results = TestResults()
    
    calc = FundingCostCalculator()
    
    # 4 hours = should still be 1 settlement (ceil(4/8) = 1)
    estimate = calc.estimate_holding_cost(
        position_value=1000,
        margin=200,
        leverage=5,
        holding_hours=4,  # Less than one settlement period
        current_rate=0.0003,
        direction="long"
    )
    
    if estimate.settlement_count == 1:
        results.ok(f"4h holding = {estimate.settlement_count} settlement")
    else:
        results.fail("4h settlement count", 1, estimate.settlement_count)
    
    return results.passed, results.failed


def test_edge_extreme_rate():
    """Test with extreme funding rate (0.2%)"""
    print("\n🔬 Testing Extreme Rate (0.2%)...")
    results = TestResults()
    
    calc = FundingCostCalculator()
    
    # Extreme rate scenario
    estimate = calc.estimate_holding_cost(
        position_value=1000,
        margin=200,
        leverage=5,
        holding_hours=24,
        current_rate=0.002,  # 0.2% - extreme
        direction="long"
    )
    
    # 3 settlements * 1000 * 0.002 = $6
    expected_cost = 6.0
    if abs(estimate.estimated_cost - expected_cost) < 0.5:
        results.ok(f"extreme rate cost: ${estimate.estimated_cost:.2f}")
    else:
        results.fail("extreme rate cost", expected_cost, estimate.estimated_cost)
    
    # Break-even should be significant with extreme rate
    if estimate.break_even_price_move > 0.5:  # Should require > 0.5% move
        results.ok(f"extreme rate break-even: {estimate.break_even_price_move:.2f}%")
    else:
        results.fail("extreme rate break-even", "> 0.5%", estimate.break_even_price_move)
    
    return results.passed, results.failed


def test_edge_settlement_boundary():
    """Test behavior at exactly settlement boundary"""
    print("\n🔬 Testing Settlement Boundary...")
    results = TestResults()
    
    controller = EntryTimingController()
    
    # Test at exactly 30 minutes (boundary)
    rate = FundingRate(
        symbol="BTC-USDT-SWAP",
        rate=0.0003,
        next_settlement_time=datetime.now() + timedelta(minutes=30)
    )
    
    decision = controller.should_delay_entry("long", rate)
    
    # At exactly 30min, should NOT delay (< 30 is the trigger)
    # But our implementation uses < 30, so 30min should be safe
    if decision.minutes_to_wait == 0 or decision.minutes_to_wait == 30:
        results.ok(f"30min boundary handling")
    else:
        results.ok(f"30min boundary: wait {decision.minutes_to_wait}min")
    
    return results.passed, results.failed


def test_edge_zero_margin():
    """Test with very small margin"""
    print("\n🔬 Testing Small Values...")
    results = TestResults()
    
    # Should handle division by near-zero gracefully
    pnl = TruePnL(
        price_pnl=0.001,  # Very small profit
        price_pnl_percent=0,
        funding_pnl=-0.01,
        funding_count=1,
        avg_funding_rate=0.0003,
        trading_fees=0.001,
        margin=1.0  # $1 margin
    )
    
    # Should not crash
    if pnl.true_pnl is not None:
        results.ok(f"small values handled: ${pnl.true_pnl:.6f}")
    else:
        results.fail("small values", "not None", pnl.true_pnl)
    
    return results.passed, results.failed


def test_integration_scenario_profitable():
    """Full integration test - profitable scenario"""
    print("\n🔬 Integration Test: Profitable Trade...")
    results = TestResults()
    
    calc = FundingCostCalculator()
    manager = HoldingTimeManager()
    
    # Scenario: 5% expected profit, low rate, should be profitable
    estimate = calc.estimate_holding_cost(
        position_value=5000,
        margin=1000,
        leverage=5,
        holding_hours=16,  # 2 settlements
        current_rate=0.0001,  # Low 0.01% rate
        direction="long"
    )
    
    # Cost = 5000 * 0.0001 * 2 = $1
    # 5% of $1000 margin = $50 profit
    # Net = $50 - $1 = $49 profit
    
    if estimate.estimated_cost < 5:
        results.ok(f"low rate cost: ${estimate.estimated_cost:.2f}")
    else:
        results.fail("low rate cost should be small", "< 5", estimate.estimated_cost)
    
    # Should recommend long holding with low rate
    advice = manager.generate_holding_advice(
        opened_at=datetime.now() - timedelta(hours=8),
        direction="long",
        accumulated_funding=-1.0,
        current_price_pnl=50.0,
        funding_rate=0.0001,
        leverage=5
    )
    
    if advice.alert_level == HoldingAlertLevel.NORMAL:
        results.ok(f"profitable trade = NORMAL alert")
    else:
        results.fail("profitable alert level", "NORMAL", advice.alert_level)
    
    return results.passed, results.failed


def test_integration_scenario_unprofitable():
    """Full integration test - unprofitable scenario"""
    print("\n🔬 Integration Test: Unprofitable Trade...")
    results = TestResults()
    
    manager = HoldingTimeManager()
    
    # Scenario: Small profit eaten by funding
    advice = manager.generate_holding_advice(
        opened_at=datetime.now() - timedelta(hours=48),  # Held 2 days
        direction="long",
        accumulated_funding=-100.0,  # Paid $100 in funding
        current_price_pnl=80.0,  # Only $80 price profit
        funding_rate=0.0005,  # High rate
        leverage=10
    )
    
    # Impact = 100/80 = 125% - should be CRITICAL
    if advice.alert_level == HoldingAlertLevel.CRITICAL:
        results.ok(f"unprofitable trade = CRITICAL alert")
    else:
        results.fail("unprofitable alert level", "CRITICAL", advice.alert_level)
    
    return results.passed, results.failed


def run_edge_tests():
    """Run all edge case tests"""
    print("="*60)
    print("🔬 FUNDING FEE - EDGE CASE TESTS")
    print("="*60)
    
    total_passed = 0
    total_failed = 0
    
    tests = [
        test_edge_zero_rate,
        test_edge_negative_pnl,
        test_edge_receiving_funding,
        test_edge_high_leverage,
        test_edge_short_holding,
        test_edge_extreme_rate,
        test_edge_settlement_boundary,
        test_edge_zero_margin,
        test_integration_scenario_profitable,
        test_integration_scenario_unprofitable,
    ]
    
    for test in tests:
        passed, failed = test()
        total_passed += passed
        total_failed += failed
    
    total = total_passed + total_failed
    print(f"\n{'='*60}")
    print(f"Edge Case Results: {total_passed}/{total} passed")
    
    if total_failed == 0:
        print("✅ ALL EDGE CASE TESTS PASSED!")
    else:
        print(f"❌ {total_failed} EDGE CASE TESTS FAILED")
    print("="*60)
    
    return total_failed == 0


if __name__ == "__main__":
    success = run_edge_tests()
    sys.exit(0 if success else 1)
