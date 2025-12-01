"""
Trading Scheduler

Manages periodic analysis cycles and triggers trading decisions.
Runs every 4 hours by default, or immediately when TP/SL is triggered.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable, Any, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class SchedulerState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    ANALYZING = "analyzing"
    EXECUTING = "executing"
    PAUSED = "paused"
    STOPPED = "stopped"


class TradingScheduler:
    """
    Scheduler for periodic trading analysis.

    Features:
    - Configurable interval (default 4 hours)
    - Manual trigger support
    - Pause/Resume functionality
    - Integration with position monitor for TP/SL triggers
    """

    def __init__(
        self,
        interval_hours: int = 4,
        on_analysis_cycle: Optional[Callable] = None,
        on_state_change: Optional[Callable] = None
    ):
        self.interval_hours = interval_hours
        self.interval_seconds = interval_hours * 3600
        self.on_analysis_cycle = on_analysis_cycle
        self.on_state_change = on_state_change

        self._state = SchedulerState.IDLE
        self._task: Optional[asyncio.Task] = None
        self._next_run: Optional[datetime] = None
        self._last_run: Optional[datetime] = None
        self._run_count = 0
        self._lock = asyncio.Lock()
        self._stop_event = asyncio.Event()

    @property
    def state(self) -> SchedulerState:
        return self._state

    @property
    def next_run(self) -> Optional[datetime]:
        return self._next_run

    @property
    def last_run(self) -> Optional[datetime]:
        return self._last_run

    @property
    def time_until_next_run(self) -> Optional[timedelta]:
        if self._next_run:
            return self._next_run - datetime.now()
        return None

    def _set_state(self, new_state: SchedulerState):
        """Update state and notify callback"""
        old_state = self._state
        self._state = new_state
        logger.info(f"Scheduler state changed: {old_state.value} -> {new_state.value}")

        if self.on_state_change:
            try:
                self.on_state_change(old_state, new_state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")

    async def start(self):
        """Start the scheduler"""
        if self._state == SchedulerState.RUNNING:
            logger.warning("Scheduler is already running")
            return

        self._stop_event.clear()
        self._set_state(SchedulerState.RUNNING)
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Trading scheduler started with {self.interval_hours}h interval")

    async def stop(self):
        """Stop the scheduler"""
        if self._state == SchedulerState.STOPPED:
            return

        self._stop_event.set()
        self._set_state(SchedulerState.STOPPED)

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Trading scheduler stopped")

    async def pause(self):
        """Pause the scheduler"""
        if self._state == SchedulerState.RUNNING:
            self._set_state(SchedulerState.PAUSED)
            logger.info("Trading scheduler paused")

    async def resume(self):
        """Resume the scheduler"""
        if self._state == SchedulerState.PAUSED:
            self._set_state(SchedulerState.RUNNING)
            logger.info("Trading scheduler resumed")

    async def trigger_now(self, reason: str = "manual") -> bool:
        """
        Trigger an immediate analysis cycle.

        Args:
            reason: Reason for triggering (manual, tp_hit, sl_hit, etc.)

        Returns:
            True if triggered successfully, False otherwise
        """
        async with self._lock:
            if self._state in [SchedulerState.ANALYZING, SchedulerState.EXECUTING]:
                logger.warning(f"Cannot trigger: scheduler is {self._state.value}")
                return False

            logger.info(f"Triggering immediate analysis cycle. Reason: {reason}")
            await self._execute_cycle(reason=reason)
            return True

    async def _run_loop(self):
        """Main scheduler loop"""
        # Run first analysis immediately
        await self._execute_cycle(reason="startup")

        while not self._stop_event.is_set():
            try:
                # Calculate next run time
                self._next_run = datetime.now() + timedelta(seconds=self.interval_seconds)
                logger.info(f"Next analysis scheduled at: {self._next_run}")

                # Wait for next interval or stop event
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self.interval_seconds
                    )
                    # If we get here, stop was requested
                    break
                except asyncio.TimeoutError:
                    # Normal timeout, proceed with analysis
                    pass

                # Check if paused
                if self._state == SchedulerState.PAUSED:
                    logger.info("Scheduler paused, skipping cycle")
                    continue

                # Execute analysis cycle
                await self._execute_cycle(reason="scheduled")

            except asyncio.CancelledError:
                logger.info("Scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _execute_cycle(self, reason: str = "scheduled"):
        """Execute a single analysis cycle"""
        # Note: This method should be called from within a locked context
        # (either trigger_now which holds the lock, or _run_loop which runs serially)
        self._set_state(SchedulerState.ANALYZING)
        self._last_run = datetime.now()
        self._run_count += 1

        logger.info(f"Starting analysis cycle #{self._run_count} (reason: {reason})")

        try:
            if self.on_analysis_cycle:
                await self.on_analysis_cycle(
                    cycle_number=self._run_count,
                    reason=reason,
                    timestamp=self._last_run
                )
                logger.info(f"Analysis cycle #{self._run_count} completed")
            else:
                logger.warning("No analysis callback registered")

        except Exception as e:
            logger.error(f"Error in analysis cycle: {e}")

        finally:
            if not self._stop_event.is_set():
                self._set_state(SchedulerState.RUNNING)

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        return {
            "state": self._state.value,
            "interval_hours": self.interval_hours,
            "next_run": self._next_run.isoformat() if self._next_run else None,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "time_until_next": str(self.time_until_next_run) if self.time_until_next_run else None,
            "run_count": self._run_count
        }


class CooldownManager:
    """
    Manages cooldown periods after hitting risk limits.

    Features:
    - Track consecutive losses
    - Enforce cooldown periods
    - Auto-resume after cooldown
    """

    def __init__(
        self,
        max_consecutive_losses: int = 3,
        cooldown_hours: int = 24
    ):
        self.max_consecutive_losses = max_consecutive_losses
        self.cooldown_hours = cooldown_hours

        self._consecutive_losses = 0
        self._in_cooldown = False
        self._cooldown_until: Optional[datetime] = None

    def record_trade_result(self, pnl: float) -> bool:
        """
        Record a trade result and check if cooldown should be triggered.

        Returns:
            True if trading is allowed, False if in cooldown
        """
        if pnl < 0:
            self._consecutive_losses += 1
            logger.info(f"Consecutive losses: {self._consecutive_losses}")

            if self._consecutive_losses >= self.max_consecutive_losses:
                self._trigger_cooldown()
                return False
        else:
            self._consecutive_losses = 0
            logger.info("Win recorded, consecutive loss counter reset")

        return True

    def _trigger_cooldown(self):
        """Trigger cooldown period"""
        self._in_cooldown = True
        self._cooldown_until = datetime.now() + timedelta(hours=self.cooldown_hours)
        logger.warning(
            f"Cooldown triggered! {self._consecutive_losses} consecutive losses. "
            f"Trading paused until {self._cooldown_until}"
        )

    def check_cooldown(self) -> bool:
        """
        Check if trading is allowed.

        Returns:
            True if trading is allowed, False if in cooldown
        """
        if not self._in_cooldown:
            return True

        if datetime.now() >= self._cooldown_until:
            self._in_cooldown = False
            self._cooldown_until = None
            self._consecutive_losses = 0
            logger.info("Cooldown period ended, trading resumed")
            return True

        return False

    def get_cooldown_status(self) -> Dict[str, Any]:
        """Get cooldown status"""
        return {
            "in_cooldown": self._in_cooldown,
            "cooldown_until": self._cooldown_until.isoformat() if self._cooldown_until else None,
            "consecutive_losses": self._consecutive_losses,
            "max_consecutive_losses": self.max_consecutive_losses
        }

    def force_end_cooldown(self):
        """Force end cooldown (manual override)"""
        self._in_cooldown = False
        self._cooldown_until = None
        logger.info("Cooldown manually ended")
