"""
Retry Handler for Trading System

Provides robust retry mechanisms for LLM API calls and other operations
that may fail transiently.

Features:
- Exponential backoff with jitter
- Configurable max retries
- Error categorization (retryable vs non-retryable)
- Circuit breaker pattern
- Detailed logging
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, Callable, Any, Dict, List, TypeVar
from dataclasses import dataclass, field
from functools import wraps
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorCategory(Enum):
    """Categories of errors for retry decisions"""
    RETRYABLE = "retryable"      # Temporary errors (rate limit, timeout, server error)
    NON_RETRYABLE = "non_retryable"  # Permanent errors (auth, invalid request)
    UNKNOWN = "unknown"


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    base_delay_seconds: float = 2.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    jitter_range: float = 0.5  # Random jitter as fraction of delay

    # Error patterns that should not be retried
    non_retryable_errors: List[str] = field(default_factory=lambda: [
        "invalid_api_key",
        "authentication_failed",
        "permission_denied",
        "invalid_request",
        "model_not_found",
        "content_filter",
        "safety_block"
    ])

    # Error patterns that should be retried
    retryable_errors: List[str] = field(default_factory=lambda: [
        "rate_limit",
        "quota_exceeded",
        "timeout",
        "server_error",
        "503",
        "502",
        "429",
        "connection",
        "temporary",
        "overloaded",
        "capacity"
    ])


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.

    States:
    - CLOSED: Normal operation, requests go through
    - OPEN: Too many failures, requests blocked
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 300,  # 5 minutes
        success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout_seconds)
        self.success_threshold = success_threshold

        self._failure_count = 0
        self._success_count = 0
        self._state = "closed"
        self._last_failure_time: Optional[datetime] = None
        self._lock = asyncio.Lock()

    @property
    def is_open(self) -> bool:
        return self._state == "open"

    async def can_execute(self) -> bool:
        """Check if execution is allowed"""
        async with self._lock:
            if self._state == "closed":
                return True

            if self._state == "open":
                # Check if recovery timeout has passed
                if datetime.now() - self._last_failure_time >= self.recovery_timeout:
                    self._state = "half_open"
                    self._success_count = 0
                    logger.info("Circuit breaker entering half-open state")
                    return True
                return False

            # Half-open state - allow limited traffic
            return True

    async def record_success(self):
        """Record a successful execution"""
        async with self._lock:
            if self._state == "half_open":
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = "closed"
                    self._failure_count = 0
                    logger.info("Circuit breaker closed - service recovered")
            elif self._state == "closed":
                self._failure_count = 0

    async def record_failure(self):
        """Record a failed execution"""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()

            if self._state == "half_open":
                # Immediate trip in half-open state
                self._state = "open"
                logger.warning("Circuit breaker opened from half-open state")
            elif self._failure_count >= self.failure_threshold:
                self._state = "open"
                logger.warning(
                    f"Circuit breaker opened after {self._failure_count} failures. "
                    f"Will retry in {self.recovery_timeout}"
                )

    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        return {
            "state": self._state,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "last_failure": self._last_failure_time.isoformat() if self._last_failure_time else None,
            "recovery_timeout_seconds": self.recovery_timeout.total_seconds()
        }


class RetryHandler:
    """
    Handles retry logic for async operations.

    Usage:
        handler = RetryHandler()
        result = await handler.execute_with_retry(
            async_func,
            arg1, arg2,
            operation_name="LLM Call"
        )
    """

    def __init__(
        self,
        config: Optional[RetryConfig] = None,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        self.config = config or RetryConfig()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

        self._retry_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_retries": 0,
            "circuit_breaks": 0
        }

    def categorize_error(self, error: Exception) -> ErrorCategory:
        """Determine if an error is retryable"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # Check non-retryable patterns
        for pattern in self.config.non_retryable_errors:
            if pattern in error_str or pattern in error_type:
                return ErrorCategory.NON_RETRYABLE

        # Check retryable patterns
        for pattern in self.config.retryable_errors:
            if pattern in error_str or pattern in error_type:
                return ErrorCategory.RETRYABLE

        # Default to retryable for unknown errors (safer for transient issues)
        return ErrorCategory.RETRYABLE

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter"""
        # Exponential backoff
        delay = self.config.base_delay_seconds * (self.config.exponential_base ** attempt)

        # Cap at max delay
        delay = min(delay, self.config.max_delay_seconds)

        # Add jitter
        jitter = delay * self.config.jitter_range * (random.random() * 2 - 1)
        delay = max(0, delay + jitter)

        return delay

    async def execute_with_retry(
        self,
        func: Callable[..., Any],
        *args,
        operation_name: str = "operation",
        on_retry: Optional[Callable[[int, Exception, float], Any]] = None,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            operation_name: Name for logging
            on_retry: Callback when retry occurs (attempt, error, delay)
            **kwargs: Keyword arguments for func

        Returns:
            Result of func

        Raises:
            Exception: If all retries fail
        """
        self._retry_stats["total_calls"] += 1

        # Check circuit breaker
        if not await self.circuit_breaker.can_execute():
            self._retry_stats["circuit_breaks"] += 1
            logger.warning(f"Circuit breaker is open, blocking {operation_name}")
            raise CircuitBreakerOpenError(
                f"Circuit breaker is open. {operation_name} blocked. "
                f"Retry after {self.circuit_breaker.recovery_timeout}"
            )

        last_error = None

        for attempt in range(self.config.max_retries + 1):
            try:
                result = await func(*args, **kwargs)

                # Success
                await self.circuit_breaker.record_success()
                self._retry_stats["successful_calls"] += 1

                if attempt > 0:
                    logger.info(f"{operation_name} succeeded after {attempt} retries")

                return result

            except Exception as e:
                last_error = e
                category = self.categorize_error(e)

                logger.warning(
                    f"{operation_name} failed (attempt {attempt + 1}/{self.config.max_retries + 1}): "
                    f"{type(e).__name__}: {str(e)[:200]}"
                )

                # Non-retryable errors
                if category == ErrorCategory.NON_RETRYABLE:
                    logger.error(f"{operation_name} failed with non-retryable error: {e}")
                    await self.circuit_breaker.record_failure()
                    self._retry_stats["failed_calls"] += 1
                    raise

                # Last attempt
                if attempt >= self.config.max_retries:
                    logger.error(
                        f"{operation_name} failed after {self.config.max_retries} retries: {e}"
                    )
                    await self.circuit_breaker.record_failure()
                    self._retry_stats["failed_calls"] += 1
                    raise

                # Calculate delay and wait
                delay = self.calculate_delay(attempt)
                logger.info(f"Retrying {operation_name} in {delay:.1f}s...")

                self._retry_stats["total_retries"] += 1

                if on_retry:
                    try:
                        await on_retry(attempt, e, delay) if asyncio.iscoroutinefunction(on_retry) else on_retry(attempt, e, delay)
                    except Exception as callback_error:
                        logger.error(f"Error in retry callback: {callback_error}")

                await asyncio.sleep(delay)

        # Should not reach here, but just in case
        raise last_error

    def get_stats(self) -> Dict[str, Any]:
        """Get retry statistics"""
        return {
            **self._retry_stats,
            "circuit_breaker": self.circuit_breaker.get_status()
        }

    def reset_stats(self):
        """Reset statistics"""
        self._retry_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_retries": 0,
            "circuit_breaks": 0
        }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


def with_retry(
    config: Optional[RetryConfig] = None,
    operation_name: Optional[str] = None
):
    """
    Decorator for adding retry logic to async functions.

    Usage:
        @with_retry(config=RetryConfig(max_retries=5))
        async def call_llm():
            ...
    """
    handler = RetryHandler(config=config)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            return await handler.execute_with_retry(func, *args, operation_name=name, **kwargs)
        return wrapper
    return decorator


# Global retry handler for LLM calls
_llm_retry_handler: Optional[RetryHandler] = None


def get_llm_retry_handler() -> RetryHandler:
    """Get or create the global LLM retry handler"""
    global _llm_retry_handler
    if _llm_retry_handler is None:
        _llm_retry_handler = RetryHandler(
            config=RetryConfig(
                max_retries=3,
                base_delay_seconds=5.0,
                max_delay_seconds=120.0,
                exponential_base=2.0
            ),
            circuit_breaker=CircuitBreaker(
                failure_threshold=5,
                recovery_timeout_seconds=300  # 5 minutes
            )
        )
    return _llm_retry_handler
