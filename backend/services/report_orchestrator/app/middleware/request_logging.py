"""
Request Logging Middleware
Logs all HTTP requests with timing and response information
"""
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import logging

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all incoming HTTP requests with:
    - Request ID for tracing
    - Method and path
    - Response status code
    - Response time
    - Client IP
    """

    # Paths to exclude from logging (health checks, metrics, etc.)
    EXCLUDED_PATHS = {
        "/health",
        "/metrics",
        "/api/health",
        "/_health",
        "/favicon.ico"
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Generate request ID
        request_id = str(uuid.uuid4())[:8]

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        # Start timing
        start_time = time.time()

        # Log request start
        logger.info(
            f"[{request_id}] --> {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params) if request.query_params else None,
                "client_ip": client_ip,
                "user_agent": request.headers.get("User-Agent", "")[:100],
                "event": "request_start"
            }
        )

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            error_detail = None
        except Exception as e:
            # Log exception
            status_code = 500
            error_detail = str(e)
            logger.exception(
                f"[{request_id}] !!! Exception during request: {e}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "event": "request_error"
                }
            )
            raise

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Determine log level based on status code
        if status_code >= 500:
            log_level = logging.ERROR
            status_emoji = "❌"
        elif status_code >= 400:
            log_level = logging.WARNING
            status_emoji = "⚠️"
        else:
            log_level = logging.INFO
            status_emoji = "✓"

        # Log request completion
        logger.log(
            log_level,
            f"[{request_id}] <-- {status_emoji} {status_code} {request.method} {request.url.path} ({duration_ms:.2f}ms)",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
                "client_ip": client_ip,
                "event": "request_complete",
                "error": error_detail
            }
        )

        # Add request ID to response headers for client-side debugging
        response.headers["X-Request-ID"] = request_id

        return response
