"""
Comprehensive Test Suite for TriggerLock and TriggerScheduler

Tests:
1. TriggerLock state transitions
2. TriggerLock acquire/release behavior
3. TriggerLock timeout forcing
4. TriggerScheduler check flow
5. Lock cooldown expiration
"""

import asyncio
import sys
import os

# Add the trigger module directly to path
sys.path.insert(0, '/Users/dengjianbo/Documents/Magellan/backend/services/report_orchestrator/app/core/trading/trigger')

from datetime import datetime, timedelta

# Import directly from the trigger module (avoiding circular imports)
from lock import TriggerLock, LockStatus
from scheduler import TriggerScheduler, SchedulerState

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def check(self, name: str, condition: bool, details: str = ""):
        if condition:
            self.passed += 1
            print(f"  ✅ {name}")
        else:
            self.failed += 1
            self.errors.append(f"{name}: {details}")
            print(f"  ❌ {name} - {details}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Results: {self.passed}/{total} passed")
        if self.errors:
            print("\nFailed tests:")
            for e in self.errors:
                print(f"  - {e}")
        return self.failed == 0


async def test_lock_state_transitions():
    """Test 1: Lock state transitions"""
    print("\n" + "="*60)
    print("TEST 1: Lock State Transitions")
    print("="*60)
    
    results = TestResults()
    lock = TriggerLock(cooldown_minutes=1)
    
    # Initial state should be idle
    results.check("Initial state is idle", lock.state == "idle", f"Got: {lock.state}")
    
    # acquire_check should change to checking
    acquired = await lock.acquire_check()
    results.check("acquire_check returns True", acquired == True)
    results.check("State is checking after acquire_check", lock.state == "checking", f"Got: {lock.state}")
    
    # release_check should return to idle
    lock.release_check()
    results.check("State is idle after release_check", lock.state == "idle", f"Got: {lock.state}")
    
    # acquire should change to analyzing
    acquired = await lock.acquire()
    results.check("acquire returns True", acquired == True)
    results.check("State is analyzing after acquire", lock.state == "analyzing", f"Got: {lock.state}")
    
    # release should change to cooldown
    lock.release()
    results.check("State is cooldown after release", lock.state == "cooldown", f"Got: {lock.state}")
    
    # force_release should change to idle
    lock.force_release()
    results.check("State is idle after force_release", lock.state == "idle", f"Got: {lock.state}")
    
    return results.summary()


async def test_lock_acquire_blocking():
    """Test 2: Lock acquire behavior when another process is analyzing"""
    print("\n" + "="*60)
    print("TEST 2: Lock Acquire Blocking")
    print("="*60)
    
    results = TestResults()
    lock = TriggerLock(cooldown_minutes=1)
    
    # First acquire
    await lock.acquire()
    results.check("First acquire succeeds", lock.state == "analyzing")
    
    # Second acquire should fail (already analyzing)
    acquired2 = await lock.acquire(timeout=2)
    results.check("Second acquire fails when already analyzing", acquired2 == False)
    
    # Release and try again
    lock.release()
    results.check("State is cooldown", lock.state == "cooldown")
    
    # Acquire from cooldown should succeed (force override)
    acquired3 = await lock.acquire()
    results.check("Acquire from cooldown succeeds (force)", acquired3 == True)
    results.check("State is analyzing after force acquire", lock.state == "analyzing", f"Got: {lock.state}")
    
    return results.summary()


async def test_lock_timeout_forcing():
    """Test 3: Lock acquire timeout forcing"""
    print("\n" + "="*60)
    print("TEST 3: Lock Acquire Timeout Forcing")
    print("="*60)
    
    results = TestResults()
    lock = TriggerLock(cooldown_minutes=1)
    
    # Acquire check lock
    await lock.acquire_check()
    results.check("Acquired check lock", lock.state == "checking")
    
    # Try to acquire main lock with short timeout
    # This should wait, then force acquire after timeout
    start = datetime.now()
    acquired = await lock.acquire(timeout=3)  # 3 second timeout
    elapsed = (datetime.now() - start).total_seconds()
    
    results.check("Acquire eventually succeeds", acquired == True)
    results.check("Timeout was waited (>2s)", elapsed >= 2, f"Elapsed: {elapsed:.2f}s")
    results.check("State is now analyzing (forced)", lock.state == "analyzing", f"Got: {lock.state}")
    
    return results.summary()


async def test_cooldown_expiration():
    """Test 4: Cooldown automatic expiration"""
    print("\n" + "="*60)
    print("TEST 4: Cooldown Expiration")
    print("="*60)
    
    results = TestResults()
    lock = TriggerLock(cooldown_minutes=1)
    
    # Acquire and release to enter cooldown
    await lock.acquire()
    lock.release(cooldown_minutes=0)  # 0 minute cooldown = immediate expiration
    
    # Manually set cooldown to past
    lock._cooldown_until = datetime.now() - timedelta(seconds=10)
    
    # Check state - should auto-expire to idle
    current_state = lock.state
    results.check("Cooldown auto-expires to idle", current_state == "idle", f"Got: {current_state}")
    
    return results.summary()


async def test_can_trigger():
    """Test 5: can_trigger() method"""
    print("\n" + "="*60)
    print("TEST 5: can_trigger() Method")
    print("="*60)
    
    results = TestResults()
    lock = TriggerLock(cooldown_minutes=1)
    
    # Idle: can trigger
    can, reason = lock.can_trigger()
    results.check("Can trigger when idle", can == True)
    
    # Analyzing: cannot trigger
    await lock.acquire()
    can, reason = lock.can_trigger()
    results.check("Cannot trigger when analyzing", can == False)
    results.check("Reason mentions analysis", "analysis" in reason.lower(), f"Got: {reason}")
    
    # Cooldown: cannot trigger
    lock.release()
    can, reason = lock.can_trigger()
    results.check("Cannot trigger when in cooldown", can == False)
    results.check("Reason mentions cooldown", "cooldown" in reason.lower(), f"Got: {reason}")
    
    return results.summary()


async def test_scheduler_check_flow():
    """Test 6: Scheduler run_check flow"""
    print("\n" + "="*60)
    print("TEST 6: Scheduler Check Flow")
    print("="*60)
    
    results = TestResults()
    
    # Create a mock trigger callback
    trigger_called = False
    async def mock_trigger(context):
        nonlocal trigger_called
        trigger_called = True
    
    scheduler = TriggerScheduler(
        interval_minutes=1,
        cooldown_minutes=1,
        on_trigger=mock_trigger
    )
    
    # Initial state
    results.check("Scheduler initial state is idle", scheduler.state == "idle")
    results.check("Check count starts at 0", scheduler._check_count == 0)
    
    # Run check (will call LLM, may timeout but should work)
    try:
        result = await asyncio.wait_for(scheduler.run_check(), timeout=90)
        results.check("run_check completes", True)
        results.check("Check count incremented", scheduler._check_count == 1, f"Got: {scheduler._check_count}")
        results.check("Result has skipped field", "skipped" in result)
        
        if not result.get("skipped"):
            results.check("Result has should_trigger field", "should_trigger" in result)
            results.check("Result has confidence field", "confidence" in result)
    except asyncio.TimeoutError:
        results.check("run_check completes within 90s", False, "Timeout")
    except Exception as e:
        results.check("run_check completes without error", False, str(e))
    
    return results.summary()


async def test_scheduler_skip_when_busy():
    """Test 7: Scheduler skips when lock is busy"""
    print("\n" + "="*60)
    print("TEST 7: Scheduler Skips When Lock Busy")
    print("="*60)
    
    results = TestResults()
    
    scheduler = TriggerScheduler(interval_minutes=1, cooldown_minutes=30)
    
    # Manually set lock to analyzing
    await scheduler.trigger_lock.acquire()
    results.check("Lock is analyzing", scheduler.trigger_lock.state == "analyzing")
    
    # Run check should be skipped
    result = await scheduler.run_check()
    results.check("Check was skipped", result.get("skipped") == True)
    results.check("Reason mentions busy", "busy" in result.get("reason", "").lower(), f"Got: {result.get('reason')}")
    
    # Release lock to cooldown
    scheduler.trigger_lock.release()
    results.check("Lock is in cooldown", scheduler.trigger_lock.state == "cooldown")
    
    # Run check should be skipped again (cooldown)
    result = await scheduler.run_check()
    results.check("Check skipped during cooldown", result.get("skipped") == True)
    
    return results.summary()


async def main():
    print("\n" + "#"*60)
    print("# TriggerLock & TriggerScheduler Comprehensive Test Suite")
    print("#"*60)
    
    all_passed = True
    
    # Run all tests
    all_passed &= await test_lock_state_transitions()
    all_passed &= await test_lock_acquire_blocking()
    all_passed &= await test_lock_timeout_forcing()
    all_passed &= await test_cooldown_expiration()
    all_passed &= await test_can_trigger()
    all_passed &= await test_scheduler_check_flow()
    all_passed &= await test_scheduler_skip_when_busy()
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️ SOME TESTS FAILED - Review output above")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
