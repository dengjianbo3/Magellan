"""
Trading Metrics

Provides execution metrics tracking and observability for the trading system.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class PhaseMetrics:
    """Metrics for a single trading phase"""
    phase_name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionMetrics:
    """Metrics for trade execution"""
    trade_id: str
    direction: str
    amount_usdt: float
    estimated_slippage: float = 0.0
    actual_slippage: float = 0.0
    expected_price: float = 0.0
    executed_price: float = 0.0
    execution_time_ms: float = 0.0
    strategy_used: str = "direct"
    success: bool = True
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def slippage_accuracy(self) -> float:
        """How close the estimated slippage was to actual"""
        if self.estimated_slippage == 0:
            return 1.0 if self.actual_slippage == 0 else 0.0
        return 1.0 - abs(self.actual_slippage - self.estimated_slippage) / abs(self.estimated_slippage)


class TradingMetricsCollector:
    """
    Collects and tracks trading metrics for observability.
    
    Usage:
        collector = TradingMetricsCollector()
        
        async with collector.track_phase("market_analysis"):
            # do analysis work
            pass
        
        collector.record_execution(metrics)
        summary = collector.get_summary()
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self._phase_metrics: List[PhaseMetrics] = []
        self._execution_metrics: List[ExecutionMetrics] = []
        self._current_meeting_id: Optional[str] = None
        self._meeting_start_time: float = 0.0
        
    def start_meeting(self, meeting_id: str):
        """Start tracking a new meeting"""
        self._current_meeting_id = meeting_id
        self._meeting_start_time = time.time()
        logger.debug(f"[Metrics] Started tracking meeting {meeting_id}")
    
    def end_meeting(self):
        """End current meeting tracking"""
        if self._meeting_start_time:
            total_time = (time.time() - self._meeting_start_time) * 1000
            logger.info(f"[Metrics] Meeting {self._current_meeting_id} completed in {total_time:.2f}ms")
        self._current_meeting_id = None
        self._meeting_start_time = 0.0
    
    @asynccontextmanager
    async def track_phase(self, phase_name: str):
        """
        Context manager to track phase duration.
        
        Usage:
            async with collector.track_phase("market_analysis"):
                await do_analysis()
        """
        metrics = PhaseMetrics(phase_name=phase_name)
        metrics.start_time = time.time()
        
        try:
            yield metrics
            metrics.success = True
        except Exception as e:
            metrics.success = False
            metrics.error = str(e)
            raise
        finally:
            metrics.end_time = time.time()
            metrics.duration_ms = (metrics.end_time - metrics.start_time) * 1000
            self._phase_metrics.append(metrics)
            
            # Trim history
            if len(self._phase_metrics) > self.max_history:
                self._phase_metrics = self._phase_metrics[-self.max_history:]
            
            status = "✅" if metrics.success else "❌"
            logger.info(f"[Metrics] Phase {phase_name} {status} in {metrics.duration_ms:.2f}ms")
    
    def record_phase(self, phase_name: str, duration_ms: float, success: bool = True, error: str = None):
        """Manually record phase metrics"""
        metrics = PhaseMetrics(
            phase_name=phase_name,
            duration_ms=duration_ms,
            success=success,
            error=error
        )
        self._phase_metrics.append(metrics)
        
        if len(self._phase_metrics) > self.max_history:
            self._phase_metrics = self._phase_metrics[-self.max_history:]
    
    def record_execution(self, metrics: ExecutionMetrics):
        """Record execution metrics"""
        self._execution_metrics.append(metrics)
        
        if len(self._execution_metrics) > self.max_history:
            self._execution_metrics = self._execution_metrics[-self.max_history:]
        
        # Log slippage comparison
        if metrics.estimated_slippage > 0 or metrics.actual_slippage > 0:
            logger.info(
                f"[Metrics] Execution {metrics.trade_id}: "
                f"slippage estimated={metrics.estimated_slippage:.3f}% vs actual={metrics.actual_slippage:.3f}%"
            )
    
    def get_phase_summary(self) -> Dict[str, Any]:
        """Get summary of phase durations"""
        if not self._phase_metrics:
            return {}
        
        # Group by phase name
        phase_stats = {}
        for m in self._phase_metrics:
            if m.phase_name not in phase_stats:
                phase_stats[m.phase_name] = {
                    "count": 0,
                    "total_ms": 0.0,
                    "success_count": 0,
                    "durations": []
                }
            stats = phase_stats[m.phase_name]
            stats["count"] += 1
            stats["total_ms"] += m.duration_ms
            stats["durations"].append(m.duration_ms)
            if m.success:
                stats["success_count"] += 1
        
        # Calculate averages
        summary = {}
        for name, stats in phase_stats.items():
            durations = stats["durations"]
            summary[name] = {
                "count": stats["count"],
                "avg_ms": stats["total_ms"] / stats["count"],
                "min_ms": min(durations),
                "max_ms": max(durations),
                "success_rate": stats["success_count"] / stats["count"] * 100
            }
        
        return summary
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of execution metrics"""
        if not self._execution_metrics:
            return {}
        
        total_trades = len(self._execution_metrics)
        successful = sum(1 for m in self._execution_metrics if m.success)
        
        total_estimated_slippage = sum(m.estimated_slippage for m in self._execution_metrics)
        total_actual_slippage = sum(m.actual_slippage for m in self._execution_metrics)
        
        # Slippage accuracy
        accuracies = [m.slippage_accuracy for m in self._execution_metrics]
        
        return {
            "total_trades": total_trades,
            "success_rate": successful / total_trades * 100 if total_trades > 0 else 0,
            "avg_estimated_slippage": total_estimated_slippage / total_trades if total_trades > 0 else 0,
            "avg_actual_slippage": total_actual_slippage / total_trades if total_trades > 0 else 0,
            "avg_slippage_accuracy": sum(accuracies) / len(accuracies) * 100 if accuracies else 0,
            "strategies_used": {
                strategy: sum(1 for m in self._execution_metrics if m.strategy_used == strategy)
                for strategy in set(m.strategy_used for m in self._execution_metrics)
            }
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get complete metrics summary"""
        return {
            "phases": self.get_phase_summary(),
            "executions": self.get_execution_summary()
        }
    
    def clear(self):
        """Clear all metrics"""
        self._phase_metrics.clear()
        self._execution_metrics.clear()


# Global metrics collector
_metrics_collector: Optional[TradingMetricsCollector] = None


def get_metrics_collector() -> TradingMetricsCollector:
    """Get or create the global metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = TradingMetricsCollector()
    return _metrics_collector
