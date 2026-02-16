"""
Structured Logging with Trace ID Support

This module provides structured logging using structlog with JSON output
and automatic trace ID injection for request tracing across services.

Usage:
    from core.observability import get_logger, set_trace_id
    
    # Set trace ID for current async context
    set_trace_id("abc123-def456")
    
    # Get a logger and use it
    logger = get_logger(__name__)
    logger.info("trade_signal_generated", direction="long", confidence=0.78)

Output (JSON):
    {
        "timestamp": "2026-01-08T10:30:00Z",
        "level": "info",
        "trace_id": "abc123-def456",
        "logger": "core.trading.nodes",
        "event": "trade_signal_generated",
        "direction": "long",
        "confidence": 0.78
    }
"""

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Optional, Any

try:
    import structlog
except Exception:  # Optional in some local/dev test setups
    structlog = None

# Context variable for trace ID propagation across async calls
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def set_trace_id(trace_id: Optional[str] = None) -> str:
    """
    Set the trace ID for the current async context.
    
    Args:
        trace_id: Optional trace ID. If not provided, generates a new UUID.
    
    Returns:
        The trace ID that was set.
    """
    if trace_id is None:
        trace_id = str(uuid.uuid4())
    trace_id_var.set(trace_id)
    return trace_id


def get_trace_id() -> str:
    """
    Get the current trace ID from the async context.
    
    Returns:
        The current trace ID, or empty string if not set.
    """
    return trace_id_var.get()


def add_trace_id(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict
) -> dict:
    """
    Structlog processor to inject trace_id into log entries.
    """
    trace_id = trace_id_var.get()
    if trace_id:
        event_dict["trace_id"] = trace_id
    return event_dict


def add_service_info(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict
) -> dict:
    """
    Structlog processor to add service metadata.
    """
    event_dict["service"] = "magellan-trading"
    return event_dict


def configure_logging(
    level: str = "INFO",
    json_output: bool = True,
    add_timestamp: bool = True
) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: If True, output logs as JSON. If False, use console format.
        add_timestamp: If True, add ISO format timestamps to logs.
    """
    if structlog is None:
        # Fall back to stdlib logging only (no structured processors).
        logging.basicConfig(
            format="%(asctime)s %(name)s %(levelname)s %(message)s",
            stream=sys.stdout,
            level=getattr(logging, level.upper()),
        )
        logging.getLogger(__name__).warning(
            "structlog not installed; falling back to stdlib logging only"
        )
        return

    # Define processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        add_trace_id,
        add_service_info,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if add_timestamp:
        processors.insert(0, structlog.processors.TimeStamper(fmt="iso"))
    
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Also configure standard library logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )


def get_logger(name: Optional[str] = None) -> Any:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__ of the calling module)
    
    Returns:
        A structlog BoundLogger instance.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("event_name", key1="value1", key2="value2")
    """
    if structlog is None:
        return logging.getLogger(name or __name__)
    return structlog.get_logger(name)


# Common log patterns for trading system
class TradingLogger:
    """
    Convenience wrapper for common trading log patterns.
    """
    
    def __init__(self, name: str):
        self.logger = get_logger(name)
    
    def signal_generated(
        self,
        direction: str,
        confidence: float,
        mode: str,
        agent_votes: int,
        **kwargs
    ):
        """Log when a trading signal is generated."""
        self.logger.info(
            "trade_signal_generated",
            direction=direction,
            confidence=confidence,
            mode=mode,
            agent_votes=agent_votes,
            **kwargs
        )
    
    def trade_executed(
        self,
        direction: str,
        size: float,
        price: float,
        order_id: str,
        **kwargs
    ):
        """Log when a trade is executed."""
        self.logger.info(
            "trade_executed",
            direction=direction,
            size=size,
            price=price,
            order_id=order_id,
            **kwargs
        )
    
    def trade_failed(
        self,
        reason: str,
        error: Optional[str] = None,
        **kwargs
    ):
        """Log when a trade execution fails."""
        self.logger.error(
            "trade_execution_failed",
            reason=reason,
            error=error,
            **kwargs
        )
    
    def agent_completed(
        self,
        agent_name: str,
        direction: str,
        confidence: float,
        latency_ms: float,
        **kwargs
    ):
        """Log when an agent completes analysis."""
        self.logger.info(
            "agent_analysis_completed",
            agent_name=agent_name,
            direction=direction,
            confidence=confidence,
            latency_ms=latency_ms,
            **kwargs
        )
    
    def mode_changed(
        self,
        old_mode: str,
        new_mode: str,
        user_id: str,
        **kwargs
    ):
        """Log when trading mode is changed."""
        self.logger.warning(
            "trading_mode_changed",
            old_mode=old_mode,
            new_mode=new_mode,
            user_id=user_id,
            **kwargs
        )
    
    def circuit_state_changed(
        self,
        circuit_name: str,
        old_state: str,
        new_state: str,
        **kwargs
    ):
        """Log when a circuit breaker state changes."""
        self.logger.warning(
            "circuit_breaker_state_changed",
            circuit_name=circuit_name,
            old_state=old_state,
            new_state=new_state,
            **kwargs
        )


# Export a default logger for quick access
default_logger = get_logger("magellan")
