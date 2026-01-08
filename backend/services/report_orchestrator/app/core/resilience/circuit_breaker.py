"""
Circuit Breaker Pattern for External API Resilience

This module implements the Circuit Breaker pattern to prevent cascading failures
when external APIs (OKX, LLM Gateway, Tavily) are experiencing issues.

Circuit Breaker States:
- CLOSED: All requests pass through normally
- OPEN: All requests fail immediately (fast-fail)
- HALF_OPEN: Limited test requests to check if service recovered

Usage:
    from core.resilience import get_circuit_breaker, call_with_circuit_breaker
    
    # Option 1: Use decorator
    @circuit_breaker("okx_api")
    async def call_okx():
        return await okx_client.request()
    
    # Option 2: Use helper function
    result = await call_with_circuit_breaker(
        "okx_api",
        okx_client.request,
        endpoint="/api/v5/account/balance"
    )
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Any, Dict, TypeVar, Awaitable
from functools import wraps

from app.core.observability.logging import get_logger
from app.core.observability.metrics import update_circuit_state, api_errors

logger = get_logger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""
    failure_threshold: int = 5      # Failures before opening
    recovery_timeout: float = 30.0  # Seconds before trying half-open
    half_open_max_calls: int = 3    # Test calls in half-open state
    success_threshold: int = 2      # Successes needed to close
    
    # Expected exceptions that trigger the circuit
    expected_exceptions: tuple = field(default_factory=lambda: (Exception,))


# Default configurations for different APIs
DEFAULT_CONFIGS: Dict[str, CircuitBreakerConfig] = {
    "okx_api": CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30.0,
        half_open_max_calls=3,
        success_threshold=2
    ),
    "llm_gateway": CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=60.0,
        half_open_max_calls=2,
        success_threshold=2
    ),
    "tavily_search": CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=120.0,
        half_open_max_calls=2,
        success_threshold=2
    ),
}


class CircuitOpenError(Exception):
    """Raised when circuit is open and request is rejected."""
    
    def __init__(self, circuit_name: str, retry_after: float):
        self.circuit_name = circuit_name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit '{circuit_name}' is OPEN. Retry after {retry_after:.1f}s"
        )


class TradingCircuitBreaker:
    """
    Circuit breaker implementation for trading system.
    
    Thread-safe implementation using asyncio locks.
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or DEFAULT_CONFIGS.get(name, CircuitBreakerConfig())
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
        
        # Update metrics
        update_circuit_state(name, self._state.value)
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)."""
        return self._state == CircuitState.OPEN
    
    async def _transition_to(self, new_state: CircuitState):
        """Transition to a new state with logging."""
        old_state = self._state
        self._state = new_state
        
        logger.warning(
            "circuit_breaker_state_changed",
            circuit_name=self.name,
            old_state=old_state.value,
            new_state=new_state.value,
            failure_count=self._failure_count
        )
        
        # Update metrics
        update_circuit_state(self.name, new_state.value)
    
    async def _check_state(self):
        """Check and potentially update circuit state."""
        async with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if self._last_failure_time:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.config.recovery_timeout:
                        await self._transition_to(CircuitState.HALF_OPEN)
                        self._half_open_calls = 0
                        self._success_count = 0
    
    async def can_execute(self) -> bool:
        """Check if a request can be executed."""
        await self._check_state()
        
        if self._state == CircuitState.CLOSED:
            return True
        elif self._state == CircuitState.HALF_OPEN:
            async with self._lock:
                if self._half_open_calls < self.config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
        else:  # OPEN
            return False
    
    async def record_success(self):
        """Record a successful call."""
        async with self._lock:
            self._failure_count = 0
            
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    await self._transition_to(CircuitState.CLOSED)
    
    async def record_failure(self, error: Exception):
        """Record a failed call."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            # Log the error
            api_errors.labels(
                api_name=self.name,
                error_code=type(error).__name__
            ).inc()
            
            if self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    await self._transition_to(CircuitState.OPEN)
            
            elif self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open goes back to open
                await self._transition_to(CircuitState.OPEN)
    
    def get_retry_after(self) -> float:
        """Get seconds until next retry attempt is allowed."""
        if self._last_failure_time is None:
            return 0
        elapsed = time.time() - self._last_failure_time
        return max(0, self.config.recovery_timeout - elapsed)
    
    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs
    ) -> T:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
        
        Returns:
            Result of func
        
        Raises:
            CircuitOpenError: If circuit is open
            Exception: Any exception from func (after recording failure)
        """
        if not await self.can_execute():
            raise CircuitOpenError(self.name, self.get_retry_after())
        
        try:
            result = await func(*args, **kwargs)
            await self.record_success()
            return result
        except self.config.expected_exceptions as e:
            await self.record_failure(e)
            raise


# Global circuit breaker registry
_circuit_breakers: Dict[str, TradingCircuitBreaker] = {}
_registry_lock = asyncio.Lock()


async def get_circuit_breaker(name: str) -> TradingCircuitBreaker:
    """
    Get or create a circuit breaker by name.
    
    Args:
        name: Circuit breaker name (e.g., "okx_api", "llm_gateway")
    
    Returns:
        TradingCircuitBreaker instance
    """
    async with _registry_lock:
        if name not in _circuit_breakers:
            config = DEFAULT_CONFIGS.get(name)
            _circuit_breakers[name] = TradingCircuitBreaker(name, config)
        return _circuit_breakers[name]


def get_circuit_breaker_sync(name: str) -> TradingCircuitBreaker:
    """
    Synchronous version of get_circuit_breaker.
    Use only during initialization.
    """
    if name not in _circuit_breakers:
        config = DEFAULT_CONFIGS.get(name)
        _circuit_breakers[name] = TradingCircuitBreaker(name, config)
    return _circuit_breakers[name]


async def call_with_circuit_breaker(
    circuit_name: str,
    func: Callable[..., Awaitable[T]],
    *args,
    **kwargs
) -> T:
    """
    Execute a function with circuit breaker protection.
    
    Args:
        circuit_name: Name of the circuit breaker to use
        func: Async function to execute
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func
    
    Returns:
        Result of func
    
    Raises:
        CircuitOpenError: If circuit is open
    """
    cb = await get_circuit_breaker(circuit_name)
    return await cb.execute(func, *args, **kwargs)


def get_all_circuit_statuses() -> Dict[str, str]:
    """Get status of all registered circuit breakers."""
    return {
        name: cb.state.value
        for name, cb in _circuit_breakers.items()
    }


def circuit_breaker(circuit_name: str):
    """
    Decorator to wrap a function with circuit breaker protection.
    
    Usage:
        @circuit_breaker("okx_api")
        async def call_okx_api():
            return await client.request()
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await call_with_circuit_breaker(
                circuit_name, func, *args, **kwargs
            )
        return wrapper
    return decorator
