# Trading System Architecture v2.0

## Overview

The trading system has been refactored from a monolithic `TradingMeeting` class (~4,000 lines)
into a modular, layered architecture with clear separation of concerns.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Trading System v2.0                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Orchestration Layer                            │    │
│  │                                                                     │    │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │    │
│  │  │  TradingGraph   │──│     Nodes       │──│   TradingState  │     │    │
│  │  │   (LangGraph)   │  │  (7 functions)  │  │   (TypedDict)   │     │    │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                     │                                        │
│                                     ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         Agent Layer                                  │    │
│  │                                                                     │    │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                │    │
│  │  │ TradeExecutor│ │SafetyGuard   │ │ReflectionEng │                │    │
│  │  │ + ReAct      │ │(Pre-check)   │ │(Post-trade)  │                │    │
│  │  └──────────────┘ └──────────────┘ └──────────────┘                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                     │                                        │
│                                     ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                       Execution Layer                                │    │
│  │                                                                     │    │
│  │  ┌──────────────────────────┐    ┌──────────────────────────┐      │    │
│  │  │      PaperTrader         │    │       OKXTrader          │      │    │
│  │  │   (Simulation Mode)      │    │   (Live/Demo Mode)       │      │    │
│  │  └──────────────────────────┘    └──────────────────────────┘      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                     │                                        │
│                                     ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Memory Layer                                  │    │
│  │                                                                     │    │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐    │    │
│  │  │ ReflectionMemory │ │  AgentWeights    │ │  TradeHistory    │    │    │
│  │  │    (Redis)       │ │    (Redis)       │ │    (Redis)       │    │    │
│  │  └──────────────────┘ └──────────────────┘ └──────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Module Structure

```
app/core/trading/
├── __init__.py              # Module exports
├── trading_meeting.py       # Original meeting (still works)
│
├── domain/                  # Unified models
│   ├── unified_position.py  # Position, PositionSource
│   └── account.py           # AccountInfo
│
├── safety/                  # Safety controls
│   └── guards.py            # SafetyGuard, BlockReason
│
├── reflection/              # Learning from trades
│   └── engine.py            # ReflectionEngine, TradeReflection
│
├── executor.py              # TradeExecutor with ReAct
│
└── orchestration/           # LangGraph workflow
    ├── state.py             # TradingState
    ├── nodes.py             # 7 workflow nodes
    └── graph.py             # TradingGraph
```

## Workflow Flow

```
┌─────────────────┐
│ market_analysis │ ← Gather market data, calculate indicators
└────────┬────────┘
         ↓
┌─────────────────┐
│signal_generation│ ← Run analyst agents, collect votes
└────────┬────────┘
         ↓
┌─────────────────┐
│ risk_assessment │ ← Evaluate risk, check safety limits
└────────┬────────┘
         ↓
┌─────────────────┐
│    consensus    │ ← Synthesize votes into decision
└────────┬────────┘
         ↓
    ┌────┴────┐
    │ check   │
    └────┬────┘
    ↓ success  ↓ error
┌──────────┐  ┌───────────────┐
│ execution│  │ react_fallback│ ← ReAct pattern recovery
└────┬─────┘  └───────┬───────┘
     ↓                ↓
  ┌──┴──┐           END
  │check│
  └──┬──┘
  ↓ trade  ↓ hold
┌──────────┐  │
│reflection│  │ ← Learn from trade outcome
└────┬─────┘  │
     ↓        ↓
    END      END
```

## Key Components

### 1. TradingGraph (Orchestration)

```python
from app.core.trading import TradingGraph

graph = TradingGraph()
result = await graph.run(
    trigger_reason="scheduled",
    market_data={"current_price": 95000},
    agent_votes=[...],
    agent_weights={"TechnicalAnalyst": 1.2}
)
```

### 2. SafetyGuard (Pre-execution)

```python
from app.core.trading import SafetyGuard

guard = SafetyGuard(trader, cooldown_manager, config)
check = await guard.pre_execution_check(votes, position, context)
if not check.allowed:
    print(f"Blocked: {check.reason} - {check.message}")
```

### 3. TradeExecutor (Execution)

```python
from app.core.trading import TradeExecutor

executor = TradeExecutor(llm_service, toolkit, paper_trader)
signal = await executor.execute(
    leader_summary="Consensus: LONG 75%",
    agent_votes=votes,
    position_context=context,
    enable_react_fallback=True  # Enable ReAct on failure
)
```

### 4. ReflectionEngine (Post-trade)

```python
from app.core.trading import ReflectionEngine

engine = ReflectionEngine(llm_service, redis_url)
reflection = await engine.reflect_on_trade(
    trade_id="trade_001",
    direction="long",
    pnl=150.0,
    agent_votes=votes
)
# Automatically adjusts agent weights
```

## Agent Paradigms

| Paradigm | Use Case | Implementation |
|----------|----------|----------------|
| **ReWOO** | Normal execution | Agents work in parallel, single LLM call |
| **ReAct** | Error recovery | Iterative reason-act-observe loop |
| **Reflexion** | Post-trade learning | Analyze outcomes, adjust weights |

## Safety Checks

| Check | When | Action |
|-------|------|--------|
| Startup Protection | On startup | Block auto-reverse of existing position |
| Daily Loss Limit | Pre-execution | Block if daily loss exceeds limit |
| Cooldown | Pre-execution | Block after consecutive losses |
| OKX Hedge Mode | Pre-execution | Block if hedge mode enabled |
| Concurrent Lock | During execution | Prevent parallel executions |
| Parameter Validation | Pre-execution | Validate leverage, amount, TP/SL |

## Migration Path

The refactored modules are **backward compatible**:

1. **TradingMeeting** still works and auto-initializes new modules
2. **TradingGraph** is an alternative orchestration layer
3. Both can be used simultaneously during transition

```python
# Old way (still works)
from app.core.trading import TradingMeeting
meeting = TradingMeeting(agents, llm_service)
result = await meeting.run_meeting(trigger_reason="scheduled")

# New way (LangGraph)
from app.core.trading import TradingGraph
graph = TradingGraph()
result = await graph.run(trigger_reason="scheduled", agent_votes=votes)
```

## Dependencies

```
langgraph>=0.2.0    # Workflow orchestration
redis>=5.0.0        # Persistent storage
```
