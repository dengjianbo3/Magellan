"""
Trace Context for Distributed Tracing

This module provides a context manager for managing trace context
across async operations in the trading system.

Usage:
    from core.observability import TraceContext
    
    async def handle_request():
        with TraceContext() as trace:
            logger.info("Starting processing", trace_id=trace.trace_id)
            await process_data()
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from contextvars import ContextVar

from .logging import trace_id_var, get_logger

logger = get_logger(__name__)


@dataclass
class TraceContext:
    """
    Context manager for distributed tracing.
    
    Manages trace ID lifecycle and provides span-like functionality
    for tracking operations across the trading system.
    """
    
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_span_id: Optional[str] = None
    span_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    operation_name: str = "unknown"
    start_time: datetime = field(default_factory=datetime.utcnow)
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def __enter__(self):
        """Set trace ID in context var on entry."""
        trace_id_var.set(self.trace_id)
        self.start_time = datetime.utcnow()
        logger.debug(
            "trace_started",
            operation=self.operation_name,
            span_id=self.span_id
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log trace completion on exit."""
        duration_ms = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        
        if exc_type is not None:
            logger.error(
                "trace_failed",
                operation=self.operation_name,
                span_id=self.span_id,
                duration_ms=duration_ms,
                error_type=exc_type.__name__ if exc_type else None,
                error_message=str(exc_val) if exc_val else None
            )
        else:
            logger.debug(
                "trace_completed",
                operation=self.operation_name,
                span_id=self.span_id,
                duration_ms=duration_ms
            )
        
        # Don't suppress exceptions
        return False
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self.__enter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        return self.__exit__(exc_type, exc_val, exc_tb)
    
    def add_attribute(self, key: str, value: Any):
        """Add an attribute to the current trace."""
        self.attributes[key] = value
    
    def create_child_span(self, operation_name: str) -> "TraceContext":
        """
        Create a child span for nested operations.
        
        Args:
            operation_name: Name of the child operation
        
        Returns:
            A new TraceContext with the same trace_id but new span_id
        """
        return TraceContext(
            trace_id=self.trace_id,
            parent_span_id=self.span_id,
            operation_name=operation_name
        )


def create_trace(operation_name: str, **attributes) -> TraceContext:
    """
    Factory function to create a new trace context.
    
    Args:
        operation_name: Name of the operation being traced
        **attributes: Additional attributes to attach to the trace
    
    Returns:
        A new TraceContext instance
    
    Usage:
        with create_trace("signal_generation", mode="full_auto") as trace:
            result = await generate_signal()
    """
    return TraceContext(
        operation_name=operation_name,
        attributes=attributes
    )


def get_current_trace_id() -> str:
    """Get the current trace ID from context."""
    return trace_id_var.get() or "no-trace"
