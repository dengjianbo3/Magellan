"""
Parallel Agent Execution - Package Init

This package provides rate-limited parallel execution for trading agents.

Phase 1: Parallel Agent Execution with API Rate Limiting
"""

from .rate_limiter import (
    RateLimitConfig,
    RateLimitedExecutor,
    get_rate_limiter,
)
from .batch_config import (
    AGENT_BATCHES,
    get_agent_batch,
    get_batch_for_agent,
)

__all__ = [
    "RateLimitConfig",
    "RateLimitedExecutor",
    "get_rate_limiter",
    "AGENT_BATCHES",
    "get_agent_batch",
    "get_batch_for_agent",
]
