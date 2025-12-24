"""
Monitoring Router
Handles error reporting from frontend and exposes monitoring endpoints
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

from ...core.metrics import record_frontend_error
from ...middleware.caching import response_cache

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory error storage (in production, use a proper time-series database)
error_buffer: List[Dict[str, Any]] = []
MAX_ERROR_BUFFER_SIZE = 1000

# Metrics counters
metrics = {
    "total_errors": 0,
    "errors_by_type": {},
    "errors_by_url": {},
    "last_hour_errors": 0,
    "last_error_time": None
}


class FrontendError(BaseModel):
    timestamp: str
    message: str
    stack: Optional[str] = None
    name: Optional[str] = "Error"
    type: Optional[str] = "unknown"
    url: Optional[str] = None
    userAgent: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    componentName: Optional[str] = None
    info: Optional[str] = None
    source: Optional[str] = None
    lineno: Optional[int] = None
    colno: Optional[int] = None
    level: Optional[str] = "error"


class ErrorReportRequest(BaseModel):
    errors: List[FrontendError]


class ErrorReportResponse(BaseModel):
    received: int
    status: str


class MetricsResponse(BaseModel):
    total_errors: int
    errors_by_type: Dict[str, int]
    errors_by_url: Dict[str, int]
    last_hour_errors: int
    last_error_time: Optional[str]
    buffer_size: int


@router.post("/report", response_model=ErrorReportResponse)
async def report_errors(request: ErrorReportRequest):
    """
    Receive error reports from frontend.

    Errors are logged and stored in a buffer for analysis.
    In production, these would be sent to a proper monitoring system.
    """
    global error_buffer, metrics

    received_count = len(request.errors)

    for error in request.errors:
        # Log the error
        logger.error(
            f"[Frontend Error] {error.name}: {error.message}",
            extra={
                "error_type": error.type,
                "url": error.url,
                "component": error.componentName,
                "stack": error.stack[:500] if error.stack else None,
                "context": error.context,
                "timestamp": error.timestamp
            }
        )

        # Update metrics
        metrics["total_errors"] += 1
        metrics["last_error_time"] = error.timestamp

        # Count by type
        error_type = error.type or "unknown"
        metrics["errors_by_type"][error_type] = metrics["errors_by_type"].get(error_type, 0) + 1

        # Count by URL (strip query params for grouping)
        if error.url:
            url_path = error.url.split("?")[0]
            metrics["errors_by_url"][url_path] = metrics["errors_by_url"].get(url_path, 0) + 1

        # Record to Prometheus metrics
        record_frontend_error(error.type, error.url)

        # Add to buffer
        error_buffer.append(error.model_dump())

        # Trim buffer if too large
        if len(error_buffer) > MAX_ERROR_BUFFER_SIZE:
            error_buffer = error_buffer[-MAX_ERROR_BUFFER_SIZE:]

    logger.info(f"[Monitoring] Received {received_count} error reports from frontend")

    return ErrorReportResponse(
        received=received_count,
        status="ok"
    )


@router.get("/errors", response_model=Dict[str, Any])
async def get_recent_errors(limit: int = 50):
    """
    Get recent errors from buffer.

    Args:
        limit: Maximum number of errors to return (default 50)
    """
    return {
        "errors": error_buffer[-limit:],
        "total_in_buffer": len(error_buffer),
        "metrics": metrics
    }


@router.get("/metrics", response_model=MetricsResponse)
async def get_error_metrics():
    """
    Get error metrics summary.
    """
    return MetricsResponse(
        total_errors=metrics["total_errors"],
        errors_by_type=metrics["errors_by_type"],
        errors_by_url=metrics["errors_by_url"],
        last_hour_errors=metrics["last_hour_errors"],
        last_error_time=metrics["last_error_time"],
        buffer_size=len(error_buffer)
    )


@router.delete("/errors")
async def clear_errors():
    """
    Clear error buffer (admin operation).
    """
    global error_buffer, metrics

    cleared_count = len(error_buffer)
    error_buffer = []
    metrics = {
        "total_errors": 0,
        "errors_by_type": {},
        "errors_by_url": {},
        "last_hour_errors": 0,
        "last_error_time": None
    }

    logger.info(f"[Monitoring] Cleared {cleared_count} errors from buffer")

    return {"cleared": cleared_count, "status": "ok"}


# =============================================================================
# Cache Management Endpoints
# =============================================================================

@router.get("/cache/stats", response_model=Dict[str, Any])
async def get_cache_stats():
    """
    Get response cache statistics.

    Returns cache size, configuration, and sample entries.
    """
    return {
        "cache": response_cache.stats(),
        "config": {
            "endpoints": [
                {"path": "/api/scenarios", "ttl": 3600},
                {"path": "/api/workflows", "ttl": 3600},
                {"path": "/api/health", "ttl": 60},
                {"path": "/api/reports", "ttl": 30},
                {"path": "/api/reports/", "ttl": 300, "prefix": True}
            ]
        }
    }


@router.delete("/cache")
async def clear_cache(pattern: Optional[str] = None):
    """
    Clear response cache.

    Args:
        pattern: Optional pattern to match cache keys (e.g., "/api/reports")
                 If not provided, clears entire cache.
    """
    response_cache.invalidate(pattern)

    logger.info(f"[Monitoring] Cache cleared (pattern={pattern})")

    return {
        "status": "ok",
        "message": f"Cache cleared" + (f" for pattern: {pattern}" if pattern else ""),
        "current_stats": response_cache.stats()
    }
