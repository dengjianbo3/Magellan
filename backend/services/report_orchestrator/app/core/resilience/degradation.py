"""
Graceful Degradation Strategy

This module provides automatic degradation of system capabilities
based on the health of external dependencies (circuit breaker states).

Degradation Levels:
- FULL: All services healthy, full functionality
- REDUCED: Some services degraded, using cached/simplified analysis
- MINIMAL: Critical services only, only supporting position closing
- OFFLINE: All services down, no trading operations

Usage:
    from core.resilience import get_degradation_manager
    
    degradation = get_degradation_manager()
    level = degradation.get_current_level()
    
    if degradation.can_open_position():
        await execute_trade()
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from app.core.observability.logging import get_logger
from app.core.observability.metrics import update_degradation_level
from .circuit_breaker import get_all_circuit_statuses

logger = get_logger(__name__)


class DegradationLevel(Enum):
    """System degradation levels."""
    FULL = "full"          # All services healthy
    REDUCED = "reduced"    # Non-critical services degraded
    MINIMAL = "minimal"    # Only critical operations
    OFFLINE = "offline"    # No operations possible


@dataclass
class DegradationCapabilities:
    """Capabilities available at each degradation level."""
    full_analysis: bool = True
    news_search: bool = True
    trade_execution: bool = True
    open_position: bool = True
    close_position: bool = True
    notifications: bool = True
    mode_switching: bool = True


# Define capabilities for each level
LEVEL_CAPABILITIES: Dict[DegradationLevel, DegradationCapabilities] = {
    DegradationLevel.FULL: DegradationCapabilities(
        full_analysis=True,
        news_search=True,
        trade_execution=True,
        open_position=True,
        close_position=True,
        notifications=True,
        mode_switching=True
    ),
    DegradationLevel.REDUCED: DegradationCapabilities(
        full_analysis=False,  # Use cached/simplified
        news_search=False,     # Tavily unavailable
        trade_execution=True,
        open_position=True,
        close_position=True,
        notifications=True,
        mode_switching=True
    ),
    DegradationLevel.MINIMAL: DegradationCapabilities(
        full_analysis=False,
        news_search=False,
        trade_execution=True,  # Only close
        open_position=False,
        close_position=True,
        notifications=False,
        mode_switching=False
    ),
    DegradationLevel.OFFLINE: DegradationCapabilities(
        full_analysis=False,
        news_search=False,
        trade_execution=False,
        open_position=False,
        close_position=False,
        notifications=False,
        mode_switching=False
    ),
}


# Circuit to degradation mapping
# Critical circuits that directly affect degradation level
CRITICAL_CIRCUITS = {"okx_api"}  # Exchange API is most critical
IMPORTANT_CIRCUITS = {"llm_gateway"}  # LLM is important but not critical
OPTIONAL_CIRCUITS = {"tavily_search"}  # Can work without news search


class GracefulDegradation:
    """
    Manages system degradation based on circuit breaker states.
    """
    
    def __init__(self):
        self._cached_level: Optional[DegradationLevel] = None
        self._last_level = DegradationLevel.FULL
    
    def get_current_level(self) -> DegradationLevel:
        """
        Calculate current degradation level based on circuit states.
        
        Returns:
            Current DegradationLevel
        """
        statuses = get_all_circuit_statuses()
        
        # Count open circuits by category
        critical_open = sum(
            1 for circuit in CRITICAL_CIRCUITS
            if statuses.get(circuit, "closed").upper() == "OPEN"
        )
        important_open = sum(
            1 for circuit in IMPORTANT_CIRCUITS
            if statuses.get(circuit, "closed").upper() == "OPEN"
        )
        optional_open = sum(
            1 for circuit in OPTIONAL_CIRCUITS
            if statuses.get(circuit, "closed").upper() == "OPEN"
        )
        
        # Determine level
        if critical_open > 0:
            # Critical service down
            if important_open > 0:
                level = DegradationLevel.OFFLINE
            else:
                level = DegradationLevel.MINIMAL
        elif important_open > 0:
            level = DegradationLevel.REDUCED
        elif optional_open > 0:
            level = DegradationLevel.REDUCED
        else:
            level = DegradationLevel.FULL
        
        # Log level changes
        if level != self._last_level:
            logger.warning(
                "degradation_level_changed",
                old_level=self._last_level.value,
                new_level=level.value,
                critical_open=critical_open,
                important_open=important_open,
                optional_open=optional_open
            )
            self._last_level = level
            update_degradation_level(level.value)
        
        return level
    
    def get_capabilities(self) -> DegradationCapabilities:
        """Get current available capabilities."""
        level = self.get_current_level()
        return LEVEL_CAPABILITIES[level]
    
    def can_analyze(self) -> bool:
        """Check if full analysis is available."""
        return self.get_capabilities().full_analysis
    
    def can_search_news(self) -> bool:
        """Check if news search is available."""
        return self.get_capabilities().news_search
    
    def can_execute_trade(self) -> bool:
        """Check if trade execution is available."""
        return self.get_capabilities().trade_execution
    
    def can_open_position(self) -> bool:
        """Check if opening new positions is allowed."""
        return self.get_capabilities().open_position
    
    def can_close_position(self) -> bool:
        """Check if closing positions is allowed."""
        return self.get_capabilities().close_position
    
    def can_send_notifications(self) -> bool:
        """Check if notifications can be sent."""
        return self.get_capabilities().notifications
    
    def can_switch_mode(self) -> bool:
        """Check if mode switching is allowed."""
        return self.get_capabilities().mode_switching
    
    def get_status_summary(self) -> Dict:
        """Get a summary of current degradation status."""
        level = self.get_current_level()
        caps = self.get_capabilities()
        statuses = get_all_circuit_statuses()
        
        return {
            "level": level.value,
            "capabilities": {
                "full_analysis": caps.full_analysis,
                "news_search": caps.news_search,
                "trade_execution": caps.trade_execution,
                "open_position": caps.open_position,
                "close_position": caps.close_position,
                "notifications": caps.notifications,
            },
            "circuit_statuses": statuses
        }


# Singleton instance
_degradation_manager: Optional[GracefulDegradation] = None


def get_degradation_manager() -> GracefulDegradation:
    """Get the singleton degradation manager instance."""
    global _degradation_manager
    if _degradation_manager is None:
        _degradation_manager = GracefulDegradation()
    return _degradation_manager
