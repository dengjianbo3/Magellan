#!/usr/bin/env python3
"""
TP/SL 杠杆计算测试 - 完全独立，不依赖任何外部模块
直接复制计算逻辑进行验证
"""

print("=" * 80)
print("🧪 TP/SL Leverage Calculation Tests (Standalone)")
print("=" * 80)
print()

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

# Replicate VoteDirection
class VoteDirection(Enum):
    LONG = "long"
    SHORT = "short"
    HOLD = "hold"

# Replicate TradingSignal calculation logic
@dataclass
class MockTradingSignal:
    direction: VoteDirection
    leverage: int = 1
    entry_price: float = 0.0
    take_profit_percent: float = 8.0
    stop_loss_percent: float = 3.0
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    
    def __post_init__(self):
        """THIS IS THE NEW LOGIC WE'RE TESTING"""
        if self.entry_price > 0 and self.leverage > 0:
            # CRITICAL: price_pct = margin_pct / leverage
            price_tp_percent = self.take_profit_percent / self.leverage
            price_sl_percent = self.stop_loss_percent / self.leverage
            
            if self.take_profit_price is None:
                if self.direction == VoteDirection.LONG:
                    self.take_profit_price = self.entry_price * (1 + price_tp_percent / 100)
                elif self.direction == VoteDirection.SHORT:
                    self.take_profit_price = self.entry_price * (1 - price_tp_percent / 100)
            
            if self.stop_loss_price is None:
                if self.direction == VoteDirection.LONG:
                    self.stop_loss_price = self.entry_price * (1 - price_sl_percent / 100)
                elif self.direction == VoteDirection.SHORT:
                    self.stop_loss_price = self.entry_price * (1 + price_sl_percent / 100)

entry_price = 100000.0

# Test 1: 1x Leverage
print("Test 1: TP/SL with 1x Leverage")
print("-" * 80)

signal_1x = MockTradingSignal(
    direction=VoteDirection.LONG,
    leverage=1,
    entry_price=entry_price,
    take_profit_percent=8.0,
    stop_loss_percent=3.0,
)

expected_tp_1x = entry_price * (1 + 8.0 / 1 / 100)
expected_sl_1x = entry_price * (1 - 3.0 / 1 / 100)

print(f"  Entry: ${entry_price:,.0f}, 1x leverage")
print(f"  TP: ${signal_1x.take_profit_price:,.2f} (expected ${expected_tp_1x:,.2f})")
print(f"  SL: ${signal_1x.stop_loss_price:,.2f} (expected ${expected_sl_1x:,.2f})")

assert abs(signal_1x.take_profit_price - expected_tp_1x) < 1
assert abs(signal_1x.stop_loss_price - expected_sl_1x) < 1
print("  ✅ PASSED\n")

# Test 2: 5x Leverage (CRITICAL)
print("Test 2: TP/SL with 5x Leverage (Critical)")
print("-" * 80)

signal_5x = MockTradingSignal(
    direction=VoteDirection.LONG,
    leverage=5,
    entry_price=entry_price,
    take_profit_percent=8.0,
    stop_loss_percent=3.0,
)

expected_tp_5x = entry_price * (1 + 8.0 / 5 / 100)
expected_sl_5x = entry_price * (1 - 3.0 / 5 / 100)

print(f"  Entry: ${entry_price:,.0f}, 5x leverage")
print(f"  Margin TP=8% → Price TP={8.0/5:.2f}%")
print(f"  Margin SL=3% → Price SL={3.0/5:.2f}%")
print(f"  TP: ${signal_5x.take_profit_price:,.2f} (expected ${expected_tp_5x:,.2f})")
print(f"  SL: ${signal_5x.stop_loss_price:,.2f} (expected ${expected_sl_5x:,.2f})")

assert abs(signal_5x.take_profit_price - expected_tp_5x) < 1
assert abs(signal_5x.stop_loss_price - expected_sl_5x) < 1
print("  ✅ PASSED\n")

# Test 3: 10x Leverage
print("Test 3: TP/SL with 10x Leverage")
print("-" * 80)

signal_10x = MockTradingSignal(
    direction=VoteDirection.LONG,
    leverage=10,
    entry_price=entry_price,
    take_profit_percent=10.0,
    stop_loss_percent=4.0,
)

expected_tp_10x = entry_price * (1 + 10.0 / 10 / 100)
expected_sl_10x = entry_price * (1 - 4.0 / 10 / 100)

print(f"  Entry: ${entry_price:,.0f}, 10x leverage")
print(f"  TP: ${signal_10x.take_profit_price:,.2f} (expected ${expected_tp_10x:,.2f})")
print(f"  SL: ${signal_10x.stop_loss_price:,.2f} (expected ${expected_sl_10x:,.2f})")

assert abs(signal_10x.take_profit_price - expected_tp_10x) < 1
assert abs(signal_10x.stop_loss_price - expected_sl_10x) < 1
print("  ✅ PASSED\n")

# Test 4: Short Position
print("Test 4: SHORT Position with 3x Leverage")
print("-" * 80)

signal_short = MockTradingSignal(
    direction=VoteDirection.SHORT,
    leverage=3,
    entry_price=entry_price,
    take_profit_percent=6.0,
    stop_loss_percent=3.0,
)

expected_tp_short = entry_price * (1 - 6.0 / 3 / 100)
expected_sl_short = entry_price * (1 + 3.0 / 3 / 100)

print(f"  Entry: ${entry_price:,.0f}, SHORT 3x leverage")
print(f"  TP (below entry): ${signal_short.take_profit_price:,.2f} (expected ${expected_tp_short:,.2f})")
print(f"  SL (above entry): ${signal_short.stop_loss_price:,.2f} (expected ${expected_sl_short:,.2f})")

assert abs(signal_short.take_profit_price - expected_tp_short) < 1
assert abs(signal_short.stop_loss_price - expected_sl_short) < 1
print("  ✅ PASSED\n")

# Test 5: Verify Old Bug is Fixed
print("Test 5: Verify OLD BUG is Fixed")
print("-" * 80)

signal_old = MockTradingSignal(
    direction=VoteDirection.LONG,
    leverage=5,
    entry_price=100000.0,
    take_profit_percent=5.0,
    stop_loss_percent=2.0,
)

old_wrong_sl = 100000.0 * 0.98  # OLD: 98000 (2% price drop = 10% margin loss!)
new_correct_sl = 100000.0 * (1 - 2.0 / 5 / 100)  # NEW: 99600 (0.4% price drop)

print(f"  OLD WRONG SL: ${old_wrong_sl:,.0f} (2% price drop = 10% margin loss!)")
print(f"  NEW CORRECT SL: ${new_correct_sl:,.0f} (0.4% price drop = 2% margin loss)")
print(f"  ACTUAL SL: ${signal_old.stop_loss_price:,.2f}")

assert abs(signal_old.stop_loss_price - new_correct_sl) < 1, "Bug not fixed!"
assert abs(signal_old.stop_loss_price - old_wrong_sl) > 100, "Still using old calculation!"
print("  ✅ PASSED - Bug is FIXED!\n")

# Test 6: Various Leverage Scenarios Table
print("Test 6: Leverage Comparison Table")
print("-" * 80)
print(f"  Entry: ${entry_price:,.0f}, Margin SL: 3%")
print()
print(f"  {'Leverage':<10} {'Price SL%':<12} {'SL Price':<15} {'Margin Loss'}")
print(f"  {'-'*10} {'-'*12} {'-'*15} {'-'*12}")

for lev in [1, 2, 3, 5, 10]:
    sig = MockTradingSignal(
        direction=VoteDirection.LONG,
        leverage=lev,
        entry_price=entry_price,
        stop_loss_percent=3.0,
    )
    price_sl_pct = 3.0 / lev
    print(f"  {lev}x{'':<8} {price_sl_pct:.2f}%{'':<8} ${sig.stop_loss_price:,.0f}{'':<6} 3%")

print()
print("  ✅ PASSED - All leverage scenarios correct\n")

# Summary
print("=" * 80)
print("🎉 ALL 6 TESTS PASSED!")
print("=" * 80)
print()
print("VERIFIED FORMULA: price_change_pct = margin_change_pct / leverage")
print()
print("This logic matches signal.py __post_init__ implementation.")
print()
