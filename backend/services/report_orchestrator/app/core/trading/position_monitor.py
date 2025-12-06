"""
Position Monitor

Real-time monitoring of open positions.
Tracks PnL, checks TP/SL triggers, and initiates new analysis cycles when needed.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field, asdict

from app.models.trading_models import Position, EquitySnapshot

logger = logging.getLogger(__name__)


@dataclass
class MonitoringState:
    """Current state of position monitoring"""
    is_monitoring: bool = False
    has_position: bool = False
    current_position: Optional[Dict] = None
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0
    tp_distance_percent: Optional[float] = None
    sl_distance_percent: Optional[float] = None
    last_check: Optional[datetime] = None
    check_count: int = 0


@dataclass
class EquityHistory:
    """Track equity over time for charting"""
    snapshots: List[EquitySnapshot] = field(default_factory=list)
    max_snapshots: int = 1000  # Keep last 1000 snapshots (~7 days at 10min intervals)

    def add_snapshot(self, snapshot: EquitySnapshot):
        self.snapshots.append(snapshot)
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots = self.snapshots[-self.max_snapshots:]

    def get_chart_data(self, limit: int = 100) -> List[Dict]:
        """Get data formatted for charting"""
        return [
            {
                "timestamp": s.timestamp.isoformat(),
                "equity": s.equity,
                "balance": s.balance,
                "unrealized_pnl": s.unrealized_pnl,
                "has_position": s.has_position,
                "direction": s.position_direction
            }
            for s in self.snapshots[-limit:]
        ]


@dataclass
class PositionMonitorConfig:
    """Position Monitor 配置"""
    default_balance: float = 10000.0  # 默认余额（用于模拟/测试）
    check_interval_seconds: int = 60
    tp_warning_threshold: float = 2.0  # TP 接近警告阈值（百分比）
    sl_warning_threshold: float = 2.0  # SL 接近警告阈值（百分比）


class PositionMonitor:
    """
    Real-time position monitoring service.

    Features:
    - Monitor open positions at configurable intervals
    - Track unrealized PnL
    - Detect TP/SL proximity
    - Trigger callbacks on position close
    - Maintain equity history for charting
    """

    def __init__(
        self,
        okx_client=None,
        check_interval_seconds: int = 60,
        on_position_closed: Optional[Callable] = None,
        on_tp_hit: Optional[Callable] = None,
        on_sl_hit: Optional[Callable] = None,
        on_pnl_update: Optional[Callable] = None,
        config: PositionMonitorConfig = None
    ):
        self.config = config or PositionMonitorConfig(check_interval_seconds=check_interval_seconds)
        self.okx_client = okx_client
        self.check_interval = check_interval_seconds
        self.on_position_closed = on_position_closed
        self.on_tp_hit = on_tp_hit
        self.on_sl_hit = on_sl_hit
        self.on_pnl_update = on_pnl_update

        self._state = MonitoringState()
        self._equity_history = EquityHistory()
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._last_position: Optional[Position] = None

    @property
    def state(self) -> MonitoringState:
        return self._state

    @property
    def equity_history(self) -> EquityHistory:
        return self._equity_history

    async def start(self):
        """Start position monitoring"""
        if self._state.is_monitoring:
            logger.warning("Position monitor already running")
            return

        self._stop_event.clear()
        self._state.is_monitoring = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(f"Position monitor started (interval: {self.check_interval}s)")

    async def stop(self):
        """Stop position monitoring"""
        if not self._state.is_monitoring:
            return

        self._stop_event.set()
        self._state.is_monitoring = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Position monitor stopped")

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while not self._stop_event.is_set():
            try:
                await self._check_position()

                # Wait for next check or stop event
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self.check_interval
                    )
                    break  # Stop was requested
                except asyncio.TimeoutError:
                    pass  # Normal timeout, continue monitoring

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(10)  # Brief pause before retrying

    async def _check_position(self):
        """Check current position status"""
        self._state.check_count += 1
        self._state.last_check = datetime.now()

        try:
            # Get current position
            position = None
            balance = None

            if self.okx_client:
                position = await self.okx_client.get_current_position()
                balance = await self.okx_client.get_account_balance()
            else:
                # Mock data for testing - use config default balance
                balance = type('Balance', (), {
                    'total_equity': self.config.default_balance,
                    'available_balance': self.config.default_balance,
                    'unrealized_pnl': 0.0
                })()

            # Check if position was closed
            if self._last_position and not position:
                await self._handle_position_closed()

            # Update state
            if position:
                self._state.has_position = True
                self._state.current_position = {
                    "symbol": position.symbol,
                    "direction": position.direction,
                    "size": position.size,
                    "entry_price": position.entry_price,
                    "current_price": position.current_price,
                    "leverage": position.leverage,
                    "unrealized_pnl": position.unrealized_pnl,
                    "unrealized_pnl_percent": position.unrealized_pnl_percent
                }
                self._state.unrealized_pnl = position.unrealized_pnl
                self._state.unrealized_pnl_percent = position.unrealized_pnl_percent

                # Calculate distance to TP/SL
                if position.take_profit_price:
                    if position.direction == "long":
                        self._state.tp_distance_percent = (
                            (position.take_profit_price - position.current_price) /
                            position.current_price * 100
                        )
                    else:
                        self._state.tp_distance_percent = (
                            (position.current_price - position.take_profit_price) /
                            position.current_price * 100
                        )

                if position.stop_loss_price:
                    if position.direction == "long":
                        self._state.sl_distance_percent = (
                            (position.current_price - position.stop_loss_price) /
                            position.current_price * 100
                        )
                    else:
                        self._state.sl_distance_percent = (
                            (position.stop_loss_price - position.current_price) /
                            position.current_price * 100
                        )

                # Check for TP/SL triggers
                await self._check_tp_sl_triggers(position)

                # Callback for PnL update
                if self.on_pnl_update:
                    try:
                        await self.on_pnl_update(
                            pnl=position.unrealized_pnl,
                            pnl_percent=position.unrealized_pnl_percent,
                            position=position
                        )
                    except Exception as e:
                        logger.error(f"Error in PnL update callback: {e}")

            else:
                self._state.has_position = False
                self._state.current_position = None
                self._state.unrealized_pnl = 0.0
                self._state.unrealized_pnl_percent = 0.0
                self._state.tp_distance_percent = None
                self._state.sl_distance_percent = None

            # Record equity snapshot
            equity = balance.total_equity if balance else self.config.default_balance
            available = balance.available_balance if balance else self.config.default_balance
            unrealized = balance.unrealized_pnl if balance else 0.0

            snapshot = EquitySnapshot(
                timestamp=datetime.now(),
                equity=equity,
                balance=available,
                unrealized_pnl=unrealized,
                has_position=self._state.has_position,
                position_direction=position.direction if position else None
            )
            self._equity_history.add_snapshot(snapshot)

            # Update last position
            self._last_position = position

        except Exception as e:
            logger.error(f"Error checking position: {e}")

    async def _check_tp_sl_triggers(self, position: Position):
        """Check if TP or SL is about to be triggered"""
        if not position.take_profit_price and not position.stop_loss_price:
            return

        current = position.current_price
        tp = position.take_profit_price
        sl = position.stop_loss_price

        if position.direction == "long":
            # Check TP (price above TP)
            if tp and current >= tp:
                logger.info(f"Take profit triggered! Price {current} >= TP {tp}")
                if self.on_tp_hit:
                    await self.on_tp_hit(position=position, price=current)

            # Check SL (price below SL)
            if sl and current <= sl:
                logger.info(f"Stop loss triggered! Price {current} <= SL {sl}")
                if self.on_sl_hit:
                    await self.on_sl_hit(position=position, price=current)

        else:  # Short position
            # Check TP (price below TP)
            if tp and current <= tp:
                logger.info(f"Take profit triggered! Price {current} <= TP {tp}")
                if self.on_tp_hit:
                    await self.on_tp_hit(position=position, price=current)

            # Check SL (price above SL)
            if sl and current >= sl:
                logger.info(f"Stop loss triggered! Price {current} >= SL {sl}")
                if self.on_sl_hit:
                    await self.on_sl_hit(position=position, price=current)

    async def _handle_position_closed(self):
        """Handle position closure"""
        if not self._last_position:
            return

        logger.info(f"Position closed detected")

        # Calculate final PnL
        final_pnl = self._last_position.unrealized_pnl

        if self.on_position_closed:
            try:
                await self.on_position_closed(
                    position=self._last_position,
                    pnl=final_pnl,
                    reason="position_monitor_detected"
                )
            except Exception as e:
                logger.error(f"Error in position closed callback: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        return {
            "is_monitoring": self._state.is_monitoring,
            "has_position": self._state.has_position,
            "current_position": self._state.current_position,
            "unrealized_pnl": self._state.unrealized_pnl,
            "unrealized_pnl_percent": self._state.unrealized_pnl_percent,
            "tp_distance_percent": self._state.tp_distance_percent,
            "sl_distance_percent": self._state.sl_distance_percent,
            "last_check": self._state.last_check.isoformat() if self._state.last_check else None,
            "check_count": self._state.check_count
        }

    def get_equity_chart_data(self, limit: int = 100) -> List[Dict]:
        """Get equity history for charting"""
        return self._equity_history.get_chart_data(limit)
