# Resilience Module
# Provides Circuit Breaker and Graceful Degradation capabilities

from .circuit_breaker import (
    CircuitBreakerConfig,
    CircuitState,
    TradingCircuitBreaker,
    get_circuit_breaker,
    call_with_circuit_breaker,
    get_all_circuit_statuses,
)
from .degradation import (
    DegradationLevel,
    GracefulDegradation,
    get_degradation_manager,
)

__all__ = [
    # Circuit Breaker
    "CircuitBreakerConfig",
    "CircuitState",
    "TradingCircuitBreaker",
    "get_circuit_breaker",
    "call_with_circuit_breaker",
    "get_all_circuit_statuses",
    # Degradation
    "DegradationLevel",
    "GracefulDegradation",
    "get_degradation_manager",
]
