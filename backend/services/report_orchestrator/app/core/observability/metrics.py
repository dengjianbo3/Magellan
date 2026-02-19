"""
Prometheus Metrics for Trading System

This module defines key metrics for monitoring the trading system
based on the RED (Rate, Errors, Duration) method plus custom business metrics.

Usage:
    from core.observability import signals_generated, agent_latency
    
    # Increment counter
    signals_generated.labels(direction="long", mode="semi_auto").inc()
    
    # Record histogram
    with agent_latency.labels(agent_name="TechnicalAnalyst").time():
        await agent.analyze(state)
"""

from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response


# =============================================================================
# RATE METRICS - How many requests/events are happening?
# =============================================================================

signals_generated = Counter(
    'trading_signals_generated_total',
    'Total number of trading signals generated',
    ['direction', 'mode']  # long/short/hold, semi_auto
)

notifications_sent = Counter(
    'trading_notifications_sent_total',
    'Total number of notifications sent',
    ['channel', 'status']  # telegram/websocket/email, success/failed
)

confirmations_received = Counter(
    'trading_confirmations_received_total',
    'Total number of user confirmations received (Semi-Auto mode)',
    ['action']  # confirm/modify/reject/timeout
)


# =============================================================================
# ERROR METRICS - What's failing?
# =============================================================================

execution_failures = Counter(
    'trading_execution_failures_total',
    'Total number of failed trade executions',
    ['reason']  # api_error/insufficient_margin/circuit_open/timeout/etc
)

agent_failures = Counter(
    'trading_agent_failures_total',
    'Total number of agent analysis failures',
    ['agent_name', 'error_type']
)

api_errors = Counter(
    'trading_api_errors_total',
    'Total number of external API errors',
    ['api_name', 'error_code']  # okx/tavily/llm_gateway, 429/500/timeout
)


# =============================================================================
# DURATION METRICS - How long are things taking?
# =============================================================================

agent_latency = Histogram(
    'trading_agent_latency_seconds',
    'Time taken for agent analysis',
    ['agent_name'],
    buckets=[0.5, 1, 2, 5, 10, 15, 20, 30, 45, 60]
)

signal_generation_latency = Histogram(
    'trading_signal_generation_latency_seconds',
    'Total time to generate a trading signal (all agents)',
    ['mode'],
    buckets=[5, 10, 15, 20, 25, 30, 45, 60, 90, 120]
)

notification_latency = Histogram(
    'trading_notification_latency_seconds',
    'Time taken to deliver notifications',
    ['channel'],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30]
)

execution_latency = Histogram(
    'trading_execution_latency_seconds',
    'Time taken to execute a trade',
    buckets=[0.5, 1, 2, 3, 5, 10, 30]
)


# =============================================================================
# CUSTOM BUSINESS METRICS
# =============================================================================

current_mode = Gauge(
    'trading_mode_current',
    'Current trading mode (1=semi_auto)'
)

position_pnl = Gauge(
    'trading_position_pnl_percent',
    'Current position PnL percentage'
)

position_size = Gauge(
    'trading_position_size_usd',
    'Current position size in USD'
)

agent_weights = Gauge(
    'trading_agent_weight',
    'Current weight for each agent',
    ['agent_name']
)

circuit_breaker_state = Gauge(
    'trading_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half_open)',
    ['circuit_name']
)

degradation_level = Gauge(
    'trading_degradation_level',
    'System degradation level (0=full, 1=reduced, 2=minimal, 3=offline)'
)


# =============================================================================
# SYSTEM INFO
# =============================================================================

system_info = Info(
    'trading_system',
    'Trading system information'
)


def set_system_info(version: str, environment: str):
    """Set static system information."""
    system_info.info({
        'version': version,
        'environment': environment,
        'system_name': 'Magellan Trading System'
    })


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def update_mode_metric(mode: str):
    """Update the current mode gauge."""
    mode_values = {
        "semi_auto": 1,
    }
    # HITL-only: default to semi_auto.
    current_mode.set(mode_values.get(mode, 1))


def update_circuit_state(circuit_name: str, state: str):
    """Update circuit breaker state gauge."""
    state_values = {
        "closed": 0,
        "CLOSED": 0,
        "open": 1,
        "OPEN": 1,
        "half_open": 2,
        "HALF_OPEN": 2
    }
    circuit_breaker_state.labels(circuit_name=circuit_name).set(
        state_values.get(state, 0)
    )


def update_degradation_level(level: str):
    """Update system degradation level gauge."""
    level_values = {
        "full": 0,
        "FULL": 0,
        "reduced": 1,
        "REDUCED": 1,
        "minimal": 2,
        "MINIMAL": 2,
        "offline": 3,
        "OFFLINE": 3
    }
    degradation_level.set(level_values.get(level, 0))


def setup_metrics():
    """
    Initialize metrics with default values.
    Call this at application startup.
    """
    # Set initial mode (HITL-only)
    current_mode.set(1)
    
    # Set initial degradation level (default to full)
    degradation_level.set(0)
    
    # Initialize agent weights
    default_agents = [
        "TechnicalAnalyst",
        "FundamentalAnalyst",
        "OnchainAnalyst",
        "MacroAnalyst",
        "SentimentAnalyst"
    ]
    for agent in default_agents:
        agent_weights.labels(agent_name=agent).set(1.0)
    
    # Initialize circuit breaker states
    default_circuits = ["okx_api", "llm_gateway", "tavily_search"]
    for circuit in default_circuits:
        circuit_breaker_state.labels(circuit_name=circuit).set(0)


def get_metrics_response() -> Response:
    """
    Generate Prometheus metrics response.
    Use this in a FastAPI endpoint.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
