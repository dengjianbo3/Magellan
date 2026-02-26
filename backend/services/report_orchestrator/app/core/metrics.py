"""
Custom Business Metrics
Custom Prometheus metrics for business-level monitoring
"""
from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps
from typing import Callable, Any, Dict, Optional, Iterable

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
# Context Optimization Metrics (Skills + Cache + Routing Blueprint Phase 0)
# =============================================================================

context_tokens_total = Counter(
    'magellan_context_tokens_total',
    'Context token usage for orchestration and chat flows',
    ['source', 'model', 'type']  # type: prompt / completion
)

context_chars_total = Counter(
    'magellan_context_chars_total',
    'Character volume sent to / received from LLM calls',
    ['source', 'model', 'type']  # type: prompt / completion
)

context_tool_calls_total = Counter(
    'magellan_context_tool_calls_total',
    'Tool call count in context-intensive flows',
    ['channel', 'agent', 'tool', 'status']  # status: success / error / timeout
)

context_tool_call_duration_seconds = Histogram(
    'magellan_context_tool_call_duration_seconds',
    'Tool call latency in seconds',
    ['channel', 'agent', 'tool'],
    buckets=(0.1, 0.3, 0.5, 1, 2, 5, 10, 20, 30, 60)
)

context_route_decisions_total = Counter(
    'magellan_context_route_decisions_total',
    'Route decision count for leader/expert routing',
    ['channel', 'mode', 'status']  # mode: direct / leader / delegated
)

context_route_decision_latency_seconds = Histogram(
    'magellan_context_route_decision_latency_seconds',
    'Latency for route decision',
    ['channel', 'mode'],
    buckets=(0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 30)
)

context_cache_events_total = Counter(
    'magellan_context_cache_events_total',
    'Cache hit/miss/store/error by layer',
    ['layer', 'event']  # layer: search_memory/search_cache/... ; event: hit/miss/store/error
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


def _estimate_tokens_from_chars(text: str) -> int:
    """
    Heuristic token estimation fallback.
    Approximation: 1 token ~= 4 chars for mixed zh/en payload.
    """
    if not text:
        return 0
    return max(1, int(round(len(text) / 4)))


def _normalize_usage_tokens(usage: Optional[Dict[str, Any]]) -> Dict[str, int]:
    if not isinstance(usage, dict):
        return {"prompt": 0, "completion": 0}

    prompt = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    completion = usage.get("completion_tokens") or usage.get("output_tokens") or 0

    try:
        prompt = int(prompt or 0)
    except Exception:
        prompt = 0
    try:
        completion = int(completion or 0)
    except Exception:
        completion = 0

    return {"prompt": max(0, prompt), "completion": max(0, completion)}


def _join_texts(texts: Optional[Iterable[str]]) -> str:
    if not texts:
        return ""
    parts = [str(t) for t in texts if t is not None]
    return "\n".join(parts)


def record_llm_context_usage(
    source: str,
    model: str,
    usage: Optional[Dict[str, Any]] = None,
    prompt_texts: Optional[Iterable[str]] = None,
    completion_text: Optional[str] = None,
):
    """
    Record context usage using provider usage first, then char-estimate fallback.
    """
    safe_source = str(source or "unknown")
    safe_model = str(model or "default")

    prompt_text = _join_texts(prompt_texts)
    completion = str(completion_text or "")

    if prompt_text:
        context_chars_total.labels(source=safe_source, model=safe_model, type='prompt').inc(len(prompt_text))
    if completion:
        context_chars_total.labels(source=safe_source, model=safe_model, type='completion').inc(len(completion))

    normalized = _normalize_usage_tokens(usage)
    prompt_tokens = normalized["prompt"] or _estimate_tokens_from_chars(prompt_text)
    completion_tokens = normalized["completion"] or _estimate_tokens_from_chars(completion)

    if prompt_tokens > 0:
        context_tokens_total.labels(source=safe_source, model=safe_model, type='prompt').inc(prompt_tokens)
    if completion_tokens > 0:
        context_tokens_total.labels(source=safe_source, model=safe_model, type='completion').inc(completion_tokens)


def record_route_decision(
    channel: str,
    mode: str,
    status: str = "success",
    latency_seconds: Optional[float] = None,
):
    safe_channel = str(channel or "unknown")
    safe_mode = str(mode or "unknown")
    safe_status = str(status or "success")
    context_route_decisions_total.labels(
        channel=safe_channel,
        mode=safe_mode,
        status=safe_status,
    ).inc()
    if latency_seconds is not None and latency_seconds >= 0:
        context_route_decision_latency_seconds.labels(
            channel=safe_channel,
            mode=safe_mode,
        ).observe(latency_seconds)


def record_tool_call(
    channel: str,
    agent: str,
    tool: str,
    status: str = "success",
    duration_seconds: Optional[float] = None,
):
    safe_channel = str(channel or "unknown")
    safe_agent = str(agent or "unknown")
    safe_tool = str(tool or "unknown")
    safe_status = str(status or "success")
    context_tool_calls_total.labels(
        channel=safe_channel,
        agent=safe_agent,
        tool=safe_tool,
        status=safe_status,
    ).inc()
    if duration_seconds is not None and duration_seconds >= 0:
        context_tool_call_duration_seconds.labels(
            channel=safe_channel,
            agent=safe_agent,
            tool=safe_tool,
        ).observe(duration_seconds)


def record_cache_event(layer: str, event: str):
    context_cache_events_total.labels(
        layer=str(layer or "unknown"),
        event=str(event or "unknown"),
    ).inc()
