"""
Custom Business Metrics
Custom Prometheus metrics for business-level monitoring
"""
from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps
from typing import Callable, Any

# =============================================================================
# Analysis Metrics
# =============================================================================

# Analysis counters
analysis_started_total = Counter(
    'magellan_analysis_started_total',
    'Total number of analyses started',
    ['scenario', 'depth']
)

analysis_completed_total = Counter(
    'magellan_analysis_completed_total',
    'Total number of analyses completed',
    ['scenario', 'depth', 'status']  # status: success, error
)

# Analysis duration
analysis_duration_seconds = Histogram(
    'magellan_analysis_duration_seconds',
    'Analysis duration in seconds',
    ['scenario', 'depth'],
    buckets=(30, 60, 120, 300, 600, 900, 1800, 3600)  # 30s to 1h
)

# Active sessions
active_sessions_count = Gauge(
    'magellan_active_sessions',
    'Number of currently active analysis sessions'
)

# =============================================================================
# LLM Metrics
# =============================================================================

llm_calls_total = Counter(
    'magellan_llm_calls_total',
    'Total number of LLM API calls',
    ['provider', 'model', 'status']  # status: success, error
)

llm_call_duration_seconds = Histogram(
    'magellan_llm_call_duration_seconds',
    'LLM API call duration in seconds',
    ['provider', 'model'],
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 120)
)

llm_tokens_total = Counter(
    'magellan_llm_tokens_total',
    'Total number of tokens used',
    ['provider', 'model', 'type']  # type: prompt, completion
)

# =============================================================================
# Agent Metrics
# =============================================================================

agent_executions_total = Counter(
    'magellan_agent_executions_total',
    'Total number of agent executions',
    ['agent_type', 'status']
)

agent_execution_duration_seconds = Histogram(
    'magellan_agent_execution_duration_seconds',
    'Agent execution duration in seconds',
    ['agent_type'],
    buckets=(1, 5, 10, 30, 60, 120, 300)
)

# =============================================================================
# Roundtable Metrics
# =============================================================================

roundtable_sessions_total = Counter(
    'magellan_roundtable_sessions_total',
    'Total number of roundtable sessions',
    ['status']
)

roundtable_messages_total = Counter(
    'magellan_roundtable_messages_total',
    'Total number of roundtable messages',
    ['message_type']
)

# =============================================================================
# Error Metrics
# =============================================================================

frontend_errors_total = Counter(
    'magellan_frontend_errors_total',
    'Total number of frontend errors reported',
    ['error_type', 'url_path']
)

# =============================================================================
# Application Info
# =============================================================================

app_info = Info(
    'magellan_app',
    'Magellan application information'
)


# =============================================================================
# Helper Functions
# =============================================================================

def track_analysis(scenario: str, depth: str):
    """
    Decorator to track analysis metrics.

    Usage:
        @track_analysis('early_stage_dd', 'quick')
        async def run_analysis():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Record start
            analysis_started_total.labels(scenario=scenario, depth=depth).inc()
            active_sessions_count.inc()

            start_time = time.time()
            status = 'success'

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'error'
                raise
            finally:
                # Record completion
                duration = time.time() - start_time
                analysis_completed_total.labels(
                    scenario=scenario,
                    depth=depth,
                    status=status
                ).inc()
                analysis_duration_seconds.labels(
                    scenario=scenario,
                    depth=depth
                ).observe(duration)
                active_sessions_count.dec()

        return wrapper
    return decorator


def track_llm_call(provider: str, model: str):
    """
    Context manager to track LLM call metrics.

    Usage:
        with track_llm_call('moonshot', 'moonshot-v1-8k') as tracker:
            response = await call_llm(...)
            tracker.record_tokens(prompt_tokens=100, completion_tokens=50)
    """
    class LLMCallTracker:
        def __init__(self, provider: str, model: str):
            self.provider = provider
            self.model = model
            self.start_time = None
            self.status = 'success'

        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = time.time() - self.start_time

            if exc_type is not None:
                self.status = 'error'

            llm_calls_total.labels(
                provider=self.provider,
                model=self.model,
                status=self.status
            ).inc()

            llm_call_duration_seconds.labels(
                provider=self.provider,
                model=self.model
            ).observe(duration)

            return False  # Don't suppress exceptions

        def record_tokens(self, prompt_tokens: int = 0, completion_tokens: int = 0):
            if prompt_tokens > 0:
                llm_tokens_total.labels(
                    provider=self.provider,
                    model=self.model,
                    type='prompt'
                ).inc(prompt_tokens)
            if completion_tokens > 0:
                llm_tokens_total.labels(
                    provider=self.provider,
                    model=self.model,
                    type='completion'
                ).inc(completion_tokens)

    return LLMCallTracker(provider, model)


def track_agent_execution(agent_type: str):
    """
    Decorator to track agent execution metrics.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            status = 'success'

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'error'
                raise
            finally:
                duration = time.time() - start_time
                agent_executions_total.labels(
                    agent_type=agent_type,
                    status=status
                ).inc()
                agent_execution_duration_seconds.labels(
                    agent_type=agent_type
                ).observe(duration)

        return wrapper
    return decorator


def record_frontend_error(error_type: str, url_path: str):
    """Record a frontend error."""
    # Normalize URL path (remove query params, limit length)
    normalized_path = url_path.split('?')[0][:100] if url_path else 'unknown'
    frontend_errors_total.labels(
        error_type=error_type or 'unknown',
        url_path=normalized_path
    ).inc()


def set_app_info(version: str, environment: str):
    """Set application info metrics."""
    app_info.info({
        'version': version,
        'environment': environment
    })
