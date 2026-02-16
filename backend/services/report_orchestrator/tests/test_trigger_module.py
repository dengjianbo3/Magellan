"""
Pytest suite for TriggerLock and TriggerScheduler.

This replaces a previous non-portable script-style test that hard-coded local paths.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest

from app.core.trading.trigger.lock import TriggerLock
from app.core.trading.trigger.scheduler import TriggerScheduler


class _StubTriggerContext:
    def __init__(self, confidence: int = 50, urgency: str = "low"):
        self.confidence = confidence
        self.urgency = urgency

    def to_dict(self):
        return {"confidence": self.confidence, "urgency": self.urgency}


class _StubTriggerAgent:
    async def check(self):
        return False, _StubTriggerContext(confidence=42, urgency="low")

    def get_status(self):
        return {"stub": True}


@pytest.mark.asyncio
async def test_trigger_lock_state_transitions():
    lock = TriggerLock(cooldown_minutes=1)

    assert lock.state == "idle"

    assert await lock.acquire_check() is True
    assert lock.state == "checking"

    lock.release_check()
    assert lock.state == "idle"

    assert await lock.acquire() is True
    assert lock.state == "analyzing"

    lock.release()
    assert lock.state == "cooldown"

    lock.force_release()
    assert lock.state == "idle"


@pytest.mark.asyncio
async def test_trigger_lock_acquire_fails_when_analyzing():
    lock = TriggerLock(cooldown_minutes=1)

    assert await lock.acquire() is True
    assert lock.state == "analyzing"

    # Already analyzing: should fail fast
    assert await lock.acquire(timeout=1) is False


@pytest.mark.asyncio
async def test_trigger_lock_check_timeout_auto_release():
    lock = TriggerLock(cooldown_minutes=1)
    assert await lock.acquire_check() is True
    assert lock.state == "checking"

    # Simulate a stuck check past CHECK_TIMEOUT_SECONDS
    lock._check_acquired_at = datetime.now() - timedelta(seconds=lock.CHECK_TIMEOUT_SECONDS + 5)
    assert lock.state == "idle"


@pytest.mark.asyncio
async def test_trigger_scheduler_run_check_releases_check_lock(monkeypatch):
    # Avoid network-heavy FastMonitor in unit test.
    monkeypatch.setenv("FAST_MONITOR_ENABLED", "false")

    lock = TriggerLock(cooldown_minutes=1)
    sched = TriggerScheduler(trigger_agent=_StubTriggerAgent(), trigger_lock=lock)

    res = await sched.run_check()

    # Should have executed Layer 2 check and then released the transient check lock.
    assert lock.state in ("idle", "cooldown", "analyzing")  # should not be stuck in "checking"
    assert lock.state != "checking"
    assert isinstance(res, dict)

