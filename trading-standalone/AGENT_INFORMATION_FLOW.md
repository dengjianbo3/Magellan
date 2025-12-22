# Magellan Trading System - Technical Documentation

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Repository Structure](#2-repository-structure)
3. [Architecture Overview](#3-architecture-overview)
4. [Core Components Deep Dive](#4-core-components-deep-dive)
5. [Agent System Architecture](#5-agent-system-architecture)
6. [Information Flow](#6-information-flow)
7. [Tool System](#7-tool-system)
8. [Data Structures](#8-data-structures)
9. [Memory & Learning System](#9-memory--learning-system)
10. [Position Management](#10-position-management)
11. [Configuration & Deployment](#11-configuration--deployment)
12. [Future Optimization Points](#12-future-optimization-points)

---

## 1. Project Overview

### 1.1 Project Identity

**Name**: Magellan Trading System  
**Type**: AI-Powered Multi-Agent Autonomous Trading Platform  
**Primary Asset**: BTC-USDT-SWAP (Cryptocurrency Perpetual Futures)  
**Exchange**: OKX (Demo/Live Trading Mode)

### 1.2 Project Goals

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PROJECT OBJECTIVES                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  🎯 PRIMARY: Autonomous Trading Decision Making                              │
│     └─► Automated 24/7 market analysis and trade execution                  │
│                                                                              │
│  🤖 MULTI-AGENT COLLABORATION                                               │
│     └─► 5+ specialized AI agents with distinct expertise areas              │
│     └─► Voting-based consensus mechanism for balanced decisions             │
│     └─► Risk assessment checkpoints before execution                        │
│                                                                              │
│  📊 CONTINUOUS LEARNING                                                      │
│     └─► Agent memory system tracks historical performance                   │
│     └─► Reflection mechanism learns from past trades                        │
│     └─► Accumulated lessons influence future decisions                      │
│                                                                              │
│  ⚖️ RISK MANAGEMENT                                                         │
│     └─► Position context injection prevents bias                            │
│     └─► TP/SL automatic calculation                                         │
│     └─► Daily loss circuit breaker                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 System Capabilities

| Capability | Description |
|------------|-------------|
| **Market Analysis** | Technical indicators, macro trends, sentiment, quantitative metrics |
| **Signal Generation** | Each agent votes with direction, confidence, leverage, TP/SL |
| **Risk Assessment** | Independent risk evaluation before trade execution |
| **Consensus Building** | Leader synthesizes expert opinions into actionable strategy |
| **Trade Execution** | Automated order placement via OKX API |
| **Position Monitoring** | Real-time P&L tracking, TP/SL distance monitoring |
| **Learning & Memory** | Post-trade reflection, performance tracking, lesson accumulation |

### 1.4 Magellan Ecosystem Context

This trading system is part of the larger **Magellan AI Investment Platform**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MAGELLAN ECOSYSTEM                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    MAIN MAGELLAN PLATFORM                              │  │
│  │  - DD (Due Diligence) Analysis for investment research                │  │
│  │  - 5 investment scenarios: Early Stage, Growth, Public Market,        │  │
│  │    Alternative, Industry Research                                     │  │
│  │  - Vue 3 frontend with WebSocket real-time updates                    │  │
│  │  - Full PostgreSQL + Kafka infrastructure                             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
│                                      │ Shares                                │
│                                      ▼                                       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                 TRADING-STANDALONE (This System)                       │  │
│  │  - Lightweight deployment (Redis + LLM Gateway + Trading Service)     │  │
│  │  - Uses same report_orchestrator codebase                             │  │
│  │  - Only trading APIs activated, DD features dormant                   │  │
│  │  - Designed for 24/7 server deployment                                │  │
│  │  - ~1.5GB memory footprint                                            │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.5 Anti-Bias Mechanisms

The system includes multiple safeguards to prevent directional bias (e.g., "always go long"):

| Mechanism | Location | Description |
|-----------|----------|-------------|
| **Neutral Vote Prompt** | `trading_meeting.py` | Uses placeholder `"direction": "<your_vote>"` instead of example direction |
| **Ordering Balance** | `trading_meeting.py` | Short options listed before long in prompts (counters primacy effect) |
| **Text Inference Scoring** | `_infer_from_text()` | Counts both bullish and bearish keywords, defaults to `hold` on tie |
| **No Default Direction** | `analyze_execution_conditions()` | `direction` is required parameter, no fallback to "long" |
| **Position Context Injection** | `position_context.py` | All agents see current position to make aware decisions |
| **Vote Calculator Symmetry** | `vote_calculator.py` | Identical logic for long and short vote aggregation |

## 2. Repository Structure

### 2.1 Complete Project Layout

```
magellan/
├── 📂 trading-standalone/           # 独立部署包 (本文档所在位置)
│   ├── 📄 AGENT_INFORMATION_FLOW.md  # ← YOU ARE HERE
│   ├── 📄 config.yaml                # Trading configuration
│   ├── 📄 docker-compose.yml         # Service orchestration
│   ├── 📄 start.sh / stop.sh         # Control scripts
│   ├── 📄 status.html                # Web monitoring dashboard
│   └── 📂 docs/                      # Additional documentation
│
├── 📂 backend/                       # Core Backend Services
│   └── 📂 services/report_orchestrator/app/
│       ├── 📄 main.py                # FastAPI entry (186KB)
│       ├── 📂 api/                   # REST/WebSocket endpoints
│       ├── 📂 core/                  # ⭐ Core Logic
│       │   ├── 📂 trading/           # Trading-specific modules
│       │   │   ├── trading_meeting.py      # (187KB) Orchestrates 5-phase process
│       │   │   ├── trading_tools.py        # (60KB) Market data tools
│       │   │   ├── trading_agents.py       # Agent factory
│       │   │   ├── okx_client.py           # Exchange API wrapper
│       │   │   ├── okx_trader.py           # Trading execution
│       │   │   ├── paper_trader.py         # Simulation mode
│       │   │   ├── position_monitor.py     # Real-time position tracking
│       │   │   ├── position_context.py     # Position state for prompts
│       │   │   ├── agent_memory.py         # (35KB) Learning system
│       │   │   ├── vote_calculator.py      # Vote aggregation
│       │   │   ├── smart_executor.py       # Execution optimization
│       │   │   └── scheduler.py            # Cron-based analysis trigger
│       │   │
│       │   ├── 📂 roundtable/        # Agent Framework
│       │   │   ├── agent.py                # (29KB) Base agent class
│       │   │   ├── rewoo_agent.py          # ReWOO architecture
│       │   │   ├── investment_agents.py    # (146KB) Agent definitions
│       │   │   ├── meeting.py              # Meeting orchestration
│       │   │   ├── message_bus.py          # Agent communication
│       │   │   ├── 📂 tools/               # Tool implementations
│       │   │   │   ├── mcp_tools.py        # MCP integration
│       │   │   │   ├── technical_tools.py  # Technical analysis
│       │   │   │   ├── analysis_tools.py   # Market analysis
│       │   │   │   ├── enhanced_tools.py   # China market tools
│       │   │   │   └── yahoo_finance_tool.py
│       │   │   └── mcp_client.py           # MCP server client
│       │   │
│       │   ├── 📂 orchestrators/     # Scenario Orchestrators (DD)
│       │   ├── agent_registry.py     # Dynamic agent loading
│       │   └── agent_event_bus.py    # Event distribution
│       │
│       ├── 📂 models/                # Data Models
│       │   └── trading_models.py     # TradingSignal, Position, etc.
│       └── 📂 services/              # External service integrations
│
├── 📂 frontend/                      # Vue 3 Dashboard (for DD analysis)
└── 📂 docs/                          # Project-wide documentation
```

### 2.2 Key Files by Importance

| Priority | File | Lines/Size | Purpose |
|----------|------|------------|---------|
| ⭐⭐⭐ | `trading_meeting.py` | ~4000 lines/187KB | **Heart of the system** - 5-phase orchestration |
| ⭐⭐⭐ | `investment_agents.py` | ~3000 lines/146KB | Agent system prompts & factory |
| ⭐⭐ | `trading_tools.py` | ~1300 lines/60KB | All market data tools |
| ⭐⭐ | `agent_memory.py` | ~900 lines/35KB | Learning & reflection system |
| ⭐⭐ | `agent.py` | ~700 lines/29KB | Base agent with LLM integration |
| ⭐ | `okx_trader.py` | ~900 lines/37KB | OKX trading execution |
| ⭐ | `position_context.py` | ~200 lines/6KB | Position state injection |

---

## 3. Architecture Overview

### 3.1 High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           MAGELLAN TRADING SYSTEM                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│    ┌─────────────────────────────────────────────────────────────────────────┐      │
│    │                         TRIGGER LAYER                                    │      │
│    │   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │      │
│    │   │  Scheduler   │    │  Manual API  │    │ Position     │              │      │
│    │   │ (4h cycle)   │    │  Trigger     │    │ Close Event  │              │      │
│    │   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘              │      │
│    └──────────┼───────────────────┼───────────────────┼──────────────────────┘      │
│               └───────────────────┼───────────────────┘                              │
│                                   ▼                                                  │
│    ┌─────────────────────────────────────────────────────────────────────────┐      │
│    │                      ORCHESTRATION LAYER                                 │      │
│    │                                                                          │      │
│    │   ┌─────────────────────────────────────────────────────────────────┐   │      │
│    │   │                    TradingMeeting                                │   │      │
│    │   │                                                                  │   │      │
│    │   │   Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5        │   │      │
│    │   │   Analysis    Voting     Risk       Consensus   Execution        │   │      │
│    │   │                                                                  │   │      │
│    │   │   ┌───────────────────────────────────────────────────────┐     │   │      │
│    │   │   │              MessageBus (Agent Communication)          │     │   │      │
│    │   │   └───────────────────────────────────────────────────────┘     │   │      │
│    │   └─────────────────────────────────────────────────────────────────┘   │      │
│    └─────────────────────────────────────────────────────────────────────────┘      │
│                                   │                                                  │
│    ┌─────────────────────────────────────────────────────────────────────────┐      │
│    │                         AGENT LAYER                                      │      │
│    │                                                                          │      │
│    │   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │      │
│    │   │Technical │ │  Macro   │ │Sentiment │ │  Quant   │ │  Risk    │      │      │
│    │   │ Analyst  │ │Economist │ │ Analyst  │ │Strategist│ │Assessor  │      │      │
│    │   │   +1     │ │   +1     │ │   +1     │ │   +1     │ │          │      │      │
│    │   │   vote   │ │   vote   │ │   vote   │ │   vote   │ │  review  │      │      │
│    │   └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘      │      │
│    │        └────────────┴────────────┴────────────┴────────────┘            │      │
│    │                                   │                                      │      │
│    │                  ┌────────────────┴────────────────┐                    │      │
│    │                  ▼                                 ▼                    │      │
│    │          ┌──────────────┐                 ┌──────────────┐              │      │
│    │          │    Leader    │                 │TradeExecutor │              │      │
│    │          │  Moderator   │────────────────►│   (Tools)    │              │      │
│    │          └──────────────┘                 └──────────────┘              │      │
│    └─────────────────────────────────────────────────────────────────────────┘      │
│                                   │                                                  │
│    ┌─────────────────────────────────────────────────────────────────────────┐      │
│    │                       INFRASTRUCTURE LAYER                               │      │
│    │                                                                          │      │
│    │   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │      │
│    │   │   LLM    │ │  Redis   │ │   OKX    │ │  MCP     │ │  Tavily  │      │      │
│    │   │ Gateway  │ │  State   │ │   API    │ │ Servers  │ │  Search  │      │      │
│    │   │ (Gemini) │ │  Store   │ │(Exchange)│ │(Web/Doc) │ │  (News)  │      │      │
│    │   └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘      │      │
│    └─────────────────────────────────────────────────────────────────────────┘      │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Data Flow Diagram

```
                                    ┌─────────────────┐
                                    │   Market Data   │
                                    │   (BTC Price)   │
                                    └────────┬────────┘
                                             │
                 ┌───────────────────────────┼───────────────────────────┐
                 │                           │                           │
                 ▼                           ▼                           ▼
       ┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
       │   Technical     │        │     Macro       │        │   Sentiment     │
       │   Indicators    │        │    Analysis     │        │    Analysis     │
       │  RSI/MACD/BB    │        │   Fed/Economy   │        │  Fear&Greed     │
       └────────┬────────┘        └────────┬────────┘        └────────┬────────┘
                │                          │                          │
                └──────────────────────────┼──────────────────────────┘
                                           │
                                           ▼
                               ┌───────────────────────┐
                               │    Vote Collection    │
                               │ ┌─────┬─────┬─────┐  │
                               │ │LONG │SHORT│HOLD │  │
                               │ │ 3   │  0  │  1  │  │
                               │ └─────┴─────┴─────┘  │
                               └──────────┬───────────┘
                                          │
                                          ▼
                               ┌───────────────────────┐
                               │   Risk Assessment     │
                               │  Leverage/Size Check  │
                               └──────────┬───────────┘
                                          │
                                          ▼
                               ┌───────────────────────┐
                               │   Leader Consensus    │
                               │   Meeting Summary     │
                               └──────────┬───────────┘
                                          │
                                          ▼
                               ┌───────────────────────┐
                               │   Trade Execution     │
                               │   open_long/short     │
                               └──────────┬───────────┘
                                          │
                                          ▼
                               ┌───────────────────────┐
                               │      OKX Order        │
                               │   Position Created    │
                               └───────────────────────┘
```

---

## 4. Core Components Deep Dive

### 4.1 TradingMeeting (trading_meeting.py)

The **central orchestrator** of the entire trading system.

```python
class TradingMeeting:
    """
    5-Phase Trading Decision Process:
    
    Phase 1: Market Analysis     - Agents analyze market with tools
    Phase 2: Signal Generation   - Each agent votes (direction, confidence, TP/SL)
    Phase 3: Risk Assessment     - RiskAssessor evaluates proposed trade
    Phase 4: Consensus Building  - Leader synthesizes opinions
    Phase 5: Trade Execution     - TradeExecutor calls trading tools
    """
```

#### Key Methods

| Method | Purpose |
|--------|---------|
| `run_meeting()` | Main entry point, orchestrates all 5 phases |
| `_run_analysis_phase()` | Phase 1 - Market analysis with tools |
| `_run_signal_phase()` | Phase 2 - Vote collection |
| `_run_risk_assessment_phase()` | Phase 3 - Risk evaluation |
| `_run_consensus_phase()` | Phase 4 - Leader summary |
| `_run_execution_phase()` | Phase 5 - Trade execution |
| `_parse_vote_json()` | Parse agent vote from JSON |
| `_generate_risk_context()` | Build risk context for assessment |
| `_get_decision_options_for_analysts()` | Generate decision matrix |

#### Phase Execution Details

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PHASE EXECUTION FLOW                               │
└─────────────────────────────────────────────────────────────────────────────┘

Phase 1: MARKET ANALYSIS (4 Agents run in parallel)
  │
  ├─► TechnicalAnalyst  ──► get_btc_price, get_technical_indicators
  ├─► MacroEconomist    ──► tavily_search("Fed policy"), get_market_news
  ├─► SentimentAnalyst  ──► get_fear_greed_index, get_funding_rate
  └─► QuantStrategist   ──► get_historical_data, get_volatility

Phase 2: SIGNAL GENERATION (Sequential voting)
  │
  ├─► Each agent receives analysis context + position context
  ├─► Each agent outputs JSON vote:
  │   {
  │     "direction": "long/short/hold",
  │     "confidence": 0-100,
  │     "leverage": 1-20,
  │     "take_profit_percent": 3.0-10.0,
  │     "stop_loss_percent": 1.0-5.0,
  │     "reasoning": "..."
  │   }
  └─► Votes collected and summarized

Phase 3: RISK ASSESSMENT (RiskAssessor reviews)
  │
  ├─► Receives: vote summary, position context, risk context
  ├─► Evaluates: leverage appropriateness, TP/SL reasonability
  └─► Outputs: risk assessment text

Phase 4: CONSENSUS BUILDING (Leader summarizes)
  │
  ├─► Receives: full conversation history, decision guidance
  ├─► Synthesizes: expert consensus, key reasons, recommendation
  └─► Outputs: meeting summary (stored in signal.leader_summary)

Phase 5: TRADE EXECUTION (TradeExecutor acts)
  │
  ├─► Receives: vote results, position status, leader summary
  ├─► Calls tool: open_long(), open_short(), close_position(), or hold()
  └─► Tool calculates: leverage, amount, TP/SL prices from vote average
```

### 4.2 Agent System (investment_agents.py)

Defines all agent personalities, prompts, and behaviors.

#### Agent Factory Functions

```python
def create_technical_analyst(language: str = "en") -> Agent
def create_macro_economist(language: str = "en") -> Agent
def create_sentiment_analyst(language: str = "en") -> Agent
def create_quant_strategist(language: str = "en") -> Agent
def create_risk_assessor(language: str = "en") -> Agent
def create_leader(language: str = "en") -> Agent
```

#### Agent Roster

| Agent | Expertise | Key Tools | Vote Weight |
|-------|-----------|-----------|-------------|
| **TechnicalAnalyst** | K-line patterns, RSI, MACD, Bollinger | `get_btc_price`, `get_technical_indicators` | 1x |
| **MacroEconomist** | Fed policy, CPI, unemployment, geopolitics | `tavily_search`, `get_market_news` | 1x |
| **SentimentAnalyst** | Fear & Greed, funding rate, social sentiment | `get_fear_greed_index`, `get_funding_rate` | 1x |
| **QuantStrategist** | Statistical analysis, volatility, momentum | `get_historical_data`, `get_volatility` | 1x |
| **RiskAssessor** | Position risk, leverage evaluation | None (advisory) | 0x (review only) |
| **Leader** | Synthesis, consensus building | None (summary) | 0x (moderator) |
| **TradeExecutor** | Order execution | `open_long`, `open_short`, `close_position`, `hold` | N/A |

### 4.3 Position Context System (position_context.py)

Injects current position state into all agent prompts to prevent bias.

```python
class PositionContext:
    """
    Captures and serializes current trading position state.
    Injected into every agent prompt to ensure awareness.
    """
    
    def __init__(self, trader):
        self.has_position: bool
        self.direction: str           # "long" or "short"
        self.entry_price: float
        self.current_price: float
        self.unrealized_pnl: float
        self.unrealized_pnl_percent: float
        self.leverage: int
        self.position_size: float
        self.liquidation_price: float
        self.tp_price: float
        self.sl_price: float
        
    def to_summary(self) -> str:
        """
        Returns formatted string for prompt injection.
        
        Example output:
        ═══════════════════════════════════════
        📊 CURRENT POSITION STATUS
        ═══════════════════════════════════════
        ✅ Has Active Position: Yes
        📈 Direction: LONG
        💰 Entry Price: $98,500.00
        📍 Current Price: $99,200.00
        💵 Unrealized P&L: +$350.00 (+3.55%)
        ⚡ Leverage: 6x
        🎚️ Position Size: 20.0%
        🚫 Liquidation: $82,083.33 (16.7% away)
        🎯 Take Profit: $103,425.00 (5.0%)
        🛑 Stop Loss: $96,530.00 (-2.0%)
        ═══════════════════════════════════════
        """
```

---

## 5. Agent System Architecture

### 5.1 Base Agent Class (agent.py)

```python
class Agent:
    """
    Base agent with LLM integration and tool execution.
    
    Key capabilities:
    - System prompt injection
    - Multi-turn conversation
    - Tool calling (native or legacy format)
    - Memory context injection
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        role: str,
        system_prompt: str,
        tools: List[Tool] = None,
        temperature: float = 0.7
    ):
        pass
        
    async def think_and_act(
        self,
        prompt: str,
        context: Dict = None
    ) -> AgentResponse:
        """
        1. Build messages with system prompt + context
        2. Call LLM
        3. Parse tool calls (if any)
        4. Execute tools
        5. Continue conversation if needed
        6. Return final response
        """
```

### 5.2 Vote Structure

```python
@dataclass
class AgentVote:
    agent_id: str
    agent_name: str
    direction: Literal["long", "short", "hold", "close", "add_long", "add_short"]
    confidence: int  # 0-100
    leverage: int    # 1-20
    take_profit_percent: float
    stop_loss_percent: float
    reasoning: str
    raw_response: str
    timestamp: datetime
```

### 5.3 Direction Normalization

Handles various input formats to standardized directions:

```python
DIRECTION_MAP = {
    # English
    "long": "long", "buy": "long", "bullish": "long",
    "short": "short", "sell": "short", "bearish": "short", 
    "hold": "hold", "wait": "hold", "neutral": "hold",
    "close": "close",
    
    # Chinese (supported but keywords translated in search)
    "做多": "long", "开多": "long",
    "做空": "short", "开空": "short",
    "观望": "hold", "平仓": "close"
}
```

---

## 6. Information Flow

### 6.1 Complete Meeting Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              COMPLETE MEETING FLOW                                   │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                      START
                                        │
                                        ▼
                      ┌────────────────────────────────────┐
                      │  1. CONTEXT GATHERING              │
                      │  ┌──────────────────────────────┐  │
                      │  │ • Get current position       │  │
                      │  │ • Get account balance        │  │
                      │  │ • Get market price           │  │
                      │  │ • Build PositionContext      │  │
                      │  │ • Load agent memories        │  │
                      │  └──────────────────────────────┘  │
                      └───────────────┬────────────────────┘
                                      │
          ╔═══════════════════════════╧═══════════════════════════╗
          ║              PHASE 1: MARKET ANALYSIS                  ║
          ║  ┌──────────────────────────────────────────────────┐ ║
          ║  │  4 Analysts run in parallel, each:               │ ║
          ║  │  • Receives: system prompt + memory + position   │ ║
          ║  │  • Calls tools to gather market data             │ ║
          ║  │  • Produces: market analysis text                │ ║
          ║  └──────────────────────────────────────────────────┘ ║
          ╚═══════════════════════════╤═══════════════════════════╝
                                      │
          ╔═══════════════════════════╧═══════════════════════════╗
          ║              PHASE 2: SIGNAL GENERATION                ║
          ║  ┌──────────────────────────────────────────────────┐ ║
          ║  │  Each analyst votes (sequential):                │ ║
          ║  │  • Receives: analysis context + decision options │ ║
          ║  │  • Outputs: JSON vote with direction/confidence  │ ║
          ║  └──────────────────────────────────────────────────┘ ║
          ║                                                       ║
          ║  Vote Collection:                                     ║
          ║  ┌─────────┬─────────┬─────────┬─────────┐           ║
          ║  │Technical│  Macro  │Sentiment│  Quant  │           ║
          ║  │  LONG   │  LONG   │  HOLD   │  LONG   │           ║
          ║  │  75%    │  70%    │  55%    │  80%    │           ║
          ║  │  6x     │  5x     │  3x     │  8x     │           ║
          ║  └─────────┴─────────┴─────────┴─────────┘           ║
          ╚═══════════════════════════╤═══════════════════════════╝
                                      │
          ╔═══════════════════════════╧═══════════════════════════╗
          ║              PHASE 3: RISK ASSESSMENT                  ║
          ║  ┌──────────────────────────────────────────────────┐ ║
          ║  │  RiskAssessor receives:                          │ ║
          ║  │  • Vote summary (3 Long, 1 Hold)                 │ ║
          ║  │  • Position context with risk metrics            │ ║
          ║  │  • Risk context (liquidation distance)           │ ║
          ║  │                                                  │ ║
          ║  │  Evaluates:                                      │ ║
          ║  │  • Is leverage appropriate for confidence?       │ ║
          ║  │  • Are TP/SL settings reasonable?                │ ║
          ║  │  • Does position size fit risk limits?           │ ║
          ║  └──────────────────────────────────────────────────┘ ║
          ╚═══════════════════════════╤═══════════════════════════╝
                                      │
          ╔═══════════════════════════╧═══════════════════════════╗
          ║             PHASE 4: CONSENSUS BUILDING                ║
          ║  ┌──────────────────────────────────────────────────┐ ║
          ║  │  Leader (Moderator) receives:                    │ ║
          ║  │  • Full conversation history                     │ ║
          ║  │  • Decision guidance matrix                      │ ║
          ║  │                                                  │ ║
          ║  │  Summarizes:                                     │ ║
          ║  │  • Expert consensus (3/4 bullish)                │ ║
          ║  │  • Key reasons from each expert                  │ ║
          ║  │  • Risk assessment conclusions                   │ ║
          ║  │  • Recommended strategy                          │ ║
          ║  └──────────────────────────────────────────────────┘ ║
          ╚═══════════════════════════╤═══════════════════════════╝
                                      │
          ╔═══════════════════════════╧═══════════════════════════╗
          ║              PHASE 5: TRADE EXECUTION                  ║
          ║  ┌──────────────────────────────────────────────────┐ ║
          ║  │  TradeExecutor receives:                         │ ║
          ║  │  • Vote results (3 Long / 0 Short / 1 Hold)      │ ║
          ║  │  • Position status                               │ ║
          ║  │  • Leader's meeting summary                      │ ║
          ║  │                                                  │ ║
          ║  │  Calls tool based on consensus:                  │ ║
          ║  │  • High consensus → open_long() or open_short()  │ ║
          ║  │  • Split opinions → hold()                       │ ║
          ║  │  • Opposite position → close_position() first    │ ║
          ║  └──────────────────────────────────────────────────┘ ║
          ╚═══════════════════════════╤═══════════════════════════╝
                                      │
                                      ▼
                      ┌────────────────────────────────────┐
                      │  6. TRADE RESULT                   │
                      │  ┌──────────────────────────────┐  │
                      │  │ TradingSignal:               │  │
                      │  │ • direction: "long"          │  │
                      │  │ • leverage: 6x               │  │
                      │  │ • amount_percent: 0.2        │  │
                      │  │ • entry_price: $98,500       │  │
                      │  │ • take_profit: $103,425      │  │
                      │  │ • stop_loss: $96,530         │  │
                      │  │ • confidence: 75%            │  │
                      │  └──────────────────────────────┘  │
                      └───────────────┬────────────────────┘
                                      │
                                      ▼
                      ┌────────────────────────────────────┐
                      │  7. POSITION MONITORING            │
                      │  (Every 60 seconds)                │
                      │  • Check current price             │
                      │  • Calculate unrealized P&L        │
                      │  • Check TP/SL distance            │
                      │  • Detect position closed          │
                      └───────────────┬────────────────────┘
                                      │
                                      │ When position closes
                                      ▼
                      ┌────────────────────────────────────┐
                      │  8. REFLECTION & LEARNING          │
                      │  ┌──────────────────────────────┐  │
                      │  │ For each agent:              │  │
                      │  │ 1. Retrieve prediction       │  │
                      │  │ 2. Compare with result       │  │
                      │  │ 3. Generate reflection       │  │
                      │  │ 4. Update AgentMemory        │  │
                      │  │    • win_rate                │  │
                      │  │    • total_pnl               │  │
                      │  │    • lessons_learned         │  │
                      │  └──────────────────────────────┘  │
                      └────────────────────────────────────┘
                                      │
                                      ▼
                                     END
```

---

## 7. Tool System

### 7.1 Tool Categories

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TOOL ECOSYSTEM                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  📊 MARKET DATA TOOLS (trading_tools.py)                                    │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ get_btc_price()           - Current BTC price from OKX                 │ │
│  │ get_technical_indicators() - RSI, MACD, Bollinger Bands, etc.          │ │
│  │ get_funding_rate()         - Perpetual funding rate                    │ │
│  │ get_fear_greed_index()     - Crypto Fear & Greed Index                 │ │
│  │ get_historical_data()      - OHLCV historical data                     │ │
│  │ get_market_news()          - Latest crypto news                        │ │
│  │ get_volatility()           - Price volatility metrics                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  🔍 SEARCH TOOLS (mcp_tools.py)                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ tavily_search()            - Web search via Tavily API                 │ │
│  │ perplexity_search()        - AI-powered search                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  💹 TRADING TOOLS (trading_meeting.py - Phase 5 only)                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ open_long()                - Open long position                        │ │
│  │ open_short()               - Open short position                       │ │
│  │ close_position()           - Close current position                    │ │
│  │ hold()                     - No action, wait                           │ │
│  │ analyze_execution_conditions() - Pre-trade analysis                    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  📈 TECHNICAL ANALYSIS TOOLS (technical_tools.py)                           │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ calculate_rsi()            - Relative Strength Index                   │ │
│  │ calculate_macd()           - MACD indicator                            │ │
│  │ calculate_bollinger()      - Bollinger Bands                           │ │
│  │ calculate_ema()            - Exponential Moving Average                │ │
│  │ identify_patterns()        - Candlestick pattern recognition           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Tool Execution Flow

```
LLM Response
     │
     ▼
┌─────────────────────────────────┐
│ Check for native tool_calls    │
│ (OpenAI function calling)      │
└──────────────┬──────────────────┘
               │
     ┌─────────┴─────────┐
     │                   │
     ▼                   ▼
Has tool_calls      No tool_calls
     │                   │
     │                   ▼
     │          ┌──────────────────────────┐
     │          │ Check for Legacy format: │
     │          │ [USE_TOOL: xxx(...)]     │
     │          └──────────────┬───────────┘
     │                         │
     │             ┌───────────┴───────────┐
     │             │                       │
     │             ▼                       ▼
     │        Has pattern            No pattern
     │             │                       │
     ▼             ▼                       ▼
┌────────────────────────┐         Return text response
│ Execute tool function  │         (no tool called)
└───────────┬────────────┘
            │
            ▼
   Return tool result
```

---

## 8. Data Structures

### 8.1 TradingSignal

```python
@dataclass
class TradingSignal:
    """Final output of a trading meeting."""
    
    direction: Literal["long", "short", "hold"]
    symbol: str = "BTC-USDT-SWAP"
    leverage: int                    # 1-20
    amount_percent: float            # 0.0-1.0 (portion of available margin)
    entry_price: float
    take_profit_price: float
    stop_loss_price: float
    confidence: int                  # 0-100
    reasoning: str
    leader_summary: str              # Meeting summary from Leader
    agents_consensus: Dict[str, str] # {agent_name: direction}
    votes: List[AgentVote]          # All collected votes
    timestamp: datetime
    
    @property
    def risk_reward_ratio(self) -> float:
        """Calculate R:R ratio."""
        if self.direction == "long":
            risk = abs(self.entry_price - self.stop_loss_price)
            reward = abs(self.take_profit_price - self.entry_price)
        else:
            risk = abs(self.stop_loss_price - self.entry_price)
            reward = abs(self.entry_price - self.take_profit_price)
        return reward / risk if risk > 0 else 0
```

### 8.2 Position

```python
@dataclass
class Position:
    """Current trading position state."""
    
    id: str
    symbol: str
    direction: Literal["long", "short"]
    size: float                    # BTC amount
    entry_price: float
    current_price: float
    leverage: int
    margin: float                  # USDT collateral
    unrealized_pnl: float
    unrealized_pnl_percent: float
    take_profit_price: Optional[float]
    stop_loss_price: Optional[float]
    liquidation_price: Optional[float]
    opened_at: datetime
```

### 8.3 Account Balance

```python
@dataclass
class AccountBalance:
    """Account state from OKX."""
    
    total_equity: float            # Total account value
    available_balance: float       # Available for new positions
    used_margin: float             # Currently used as collateral
    unrealized_pnl: float         # Floating P&L
    max_avail_size: float         # OKX-calculated max position size
```

---

## 9. Memory & Learning System

### 9.1 Agent Memory Structure (agent_memory.py)

```python
@dataclass
class AgentMemory:
    """
    Stores and retrieves agent learning data.
    Persisted in Redis for durability.
    """
    
    agent_id: str
    
    # Performance metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    
    # Learning accumulation
    lessons_learned: List[str] = []      # Key lessons from reflections
    current_focus: str = ""              # Current improvement area
    last_trade_summary: str = ""         # Most recent trade outcome
    
    # Prediction tracking
    recent_predictions: List[Prediction] = []
    
    def get_context_for_prompt(self) -> str:
        """
        Returns formatted context for agent prompt injection.
        
        Example output:
        ══════════════════════════════════════════
        📊 YOUR HISTORICAL PERFORMANCE
        ══════════════════════════════════════════
        Total Trades: 47
        Win Rate: 63.8% (30W / 17L)
        Total P&L: +$1,234.56
        
        📚 LESSONS LEARNED:
        1. RSI divergence signals are more reliable when confirmed by volume
        2. Avoid entries during low-volume weekend periods
        3. Macro news often causes 2-3% moves within 4 hours
        
        🎯 CURRENT FOCUS:
        Improve entry timing using confluence of multiple indicators
        
        📝 LAST TRADE:
        Long @ $97,500 → Closed @ $98,200 (+0.72%)
        Reason: Technical breakout confirmed
        ══════════════════════════════════════════
        """
```

### 9.2 Reflection Generation

```python
async def generate_reflection(
    agent_id: str,
    prediction: Prediction,
    trade_result: TradeResult
) -> Reflection:
    """
    Generate post-trade reflection using LLM.
    
    Prompts agent to analyze:
    1. What went well in the analysis?
    2. What went wrong?
    3. What lessons should be remembered?
    4. What to focus on next?
    """
    
    reflection_prompt = f"""
    Your prediction:
    - Direction: {prediction.direction}
    - Confidence: {prediction.confidence}%
    - Reasoning: {prediction.reasoning}
    
    Actual result:
    - Entry: ${trade_result.entry_price}
    - Exit: ${trade_result.exit_price}
    - P&L: {trade_result.pnl_percent:+.2f}%
    - Duration: {trade_result.duration}
    
    Reflect on this trade:
    1. What aspects of your analysis were correct?
    2. What did you miss or misjudge?
    3. What lesson should you remember for future trades?
    """
```

### 9.3 Memory Flow

```
Trade Opens
     │
     ├─► Store predictions for each agent
     │
     ▼
Position Monitored
     │
     │ Position Closes (TP/SL hit or manual)
     ▼
┌─────────────────────────────────┐
│ Trigger Reflection Generation   │
│                                 │
│ For each agent:                 │
│ 1. Retrieve stored prediction   │
│ 2. Compare with actual result   │
│ 3. Call LLM for reflection      │
│ 4. Extract lessons learned      │
│ 5. Update AgentMemory in Redis  │
└─────────────────────────────────┘
     │
     ▼
Next Trading Meeting
     │
     ├─► Agent memories loaded
     ├─► Context injected into prompts
     └─► Agents reference past lessons
```

---

## 10. Position Management

### 10.1 OKX Integration (okx_trader.py, okx_client.py)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OKX INTEGRATION                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  OKXClient (Low-level API wrapper)                                          │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ • get_account_balance()      - Fetch account equity                    │ │
│  │ • get_current_position()     - Current position details                │ │
│  │ • get_ticker()               - Real-time price                         │ │
│  │ • place_order()              - Place market/limit order                │ │
│  │ • close_position()           - Close existing position                 │ │
│  │ • set_leverage()             - Configure leverage                      │ │
│  │ • get_positions_history()    - Closed positions for P&L                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  OKXTrader (High-level trading interface)                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ • open_long(symbol, leverage, amount, tp, sl)                          │ │
│  │ • open_short(symbol, leverage, amount, tp, sl)                         │ │
│  │ • close_position(symbol)                                               │ │
│  │ • get_account()              - Formatted account info                  │ │
│  │ • get_position()             - Formatted position info                 │ │
│  │ • get_trade_history()        - Historical trades with PnL              │ │
│  │                                                                        │ │
│  │ Features:                                                              │ │
│  │ • Trade lock (prevents concurrent operations)                          │ │
│  │ • Daily loss circuit breaker (10% limit)                               │ │
│  │ • Position adding support (same direction)                             │ │
│  │ • Local cache with API sync                                            │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Position Monitor (position_monitor.py)

```python
class PositionMonitor:
    """
    Real-time position monitoring.
    Runs every 60 seconds while position is open.
    """
    
    async def _check_position(self):
        """
        Each check:
        1. Fetch current position from OKX
        2. Calculate unrealized P&L
        3. Check TP/SL distance
        4. Detect if position was closed
        5. Record equity snapshot
        6. Trigger callbacks if needed
        """
        
    # Callbacks
    on_position_closed: Callable    # Triggered when position closes
    on_tp_hit: Callable            # Triggered at take profit
    on_sl_hit: Callable            # Triggered at stop loss
    on_pnl_update: Callable        # Periodic P&L updates
```

### 10.3 Paper Trading (paper_trader.py)

```python
class PaperTrader:
    """
    Simulated trading for testing.
    Mirrors OKXTrader interface but uses local state.
    
    Supports:
    • Virtual balance management
    • Position simulation
    • P&L calculation
    • TP/SL simulation
    """
```

### 10.4 SmartExecutor (smart_executor.py)

Provides execution safety and retry mechanisms:

```python
class SmartExecutor:
    """
    Wraps trading execution with intelligent retry logic.
    
    Features:
    • Exponential backoff on failures
    • Pre-execution validation
    • Circuit breaker integration
    • Execution audit logging
    """
    
    async def execute_with_retry(
        self,
        action: str,                    # "open_long", "open_short", "close"
        params: Dict,
        max_retries: int = 3
    ) -> ExecutionResult:
        """
        Attempts execution with automatic retry on transient failures.
        
        Retry Strategy:
        1. First attempt: immediate
        2. Second attempt: wait 2 seconds
        3. Third attempt: wait 4 seconds
        
        Non-retryable errors (fail immediately):
        • Insufficient margin
        • Invalid parameters
        • Circuit breaker triggered
        """
```

---

## 11. Configuration & Deployment

### 11.1 Environment Variables (.env)

```bash
# Exchange Configuration
OKX_API_KEY=your_api_key
OKX_SECRET_KEY=your_secret
OKX_PASSPHRASE=your_passphrase
OKX_DEMO_MODE=true              # true = demo, false = live

# LLM Configuration  
GEMINI_API_KEY=your_gemini_key
LLM_MODEL=gemini-1.5-pro

# Search Tools
TAVILY_API_KEY=your_tavily_key

# MCP Servers
MCP_WEB_SEARCH_ENDPOINT=http://mcp-web-search:3001
MCP_DOCUMENT_ENDPOINT=http://mcp-document:3002

# Trading Parameters
ANALYSIS_INTERVAL_HOURS=4
MAX_LEVERAGE=10
MAX_POSITION_PERCENT=0.3
```

### 11.2 Config.yaml Structure

```yaml
trading:
  symbol: "BTC-USDT-SWAP"
  leverage: 10
  position_size: 100              # USDT per trade
  take_profit_percent: 5.0
  stop_loss_percent: 3.0
  demo_mode: true

scheduler:
  interval_hours: 4
  enabled: true

risk:
  max_leverage: 20
  max_position_percent: 0.3
  daily_loss_limit_percent: 10.0

llm:
  provider: "gemini"
  model: "gemini-1.5-pro"
  temperature: 0.7

email:
  enabled: true
  notify_on:
    - decision
    - execution
    - tp_hit
    - sl_hit
    - error
```

### 11.3 Docker Services

```yaml
services:
  redis:
    image: redis:alpine
    mem_limit: 256m
    
  llm-gateway:
    image: magellan/llm-gateway
    mem_limit: 512m
    
  trading:
    image: magellan/report-orchestrator
    mem_limit: 768m
    depends_on:
      - redis
      - llm-gateway
```

---

## 12. Future Optimization Points

### 12.1 Performance Optimizations

| Area | Current State | Optimization Opportunity |
|------|---------------|--------------------------|
| **LLM Calls** | Sequential agent execution | Parallelize Phase 1 analysis |
| **Tool Caching** | No caching | Cache market data for 1-5 minutes |
| **Vote Parsing** | Multiple regex fallbacks | Pre-validate JSON schema |
| **Memory Loading** | Load all on each meeting | Lazy load, LRU cache |

### 12.2 Architecture Improvements

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      POTENTIAL ARCHITECTURE IMPROVEMENTS                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. ASYNC AGENT EXECUTION                                                   │
│     Current: Agents run sequentially in analysis phase                      │
│     Proposed: Run 4 analysts in parallel, aggregate results                 │
│     Benefit: ~3x faster Phase 1 execution                                   │
│                                                                              │
│  2. STREAMING LLM RESPONSES                                                 │
│     Current: Wait for full response before parsing                          │
│     Proposed: Stream responses, parse JSON as it arrives                    │
│     Benefit: Faster apparent response, earlier error detection              │
│                                                                              │
│  3. TOOL RESULT CACHING                                                     │
│     Current: Every tool call hits external API                              │
│     Proposed: Redis cache with TTL (price: 30s, indicators: 5min)           │
│     Benefit: Reduce API costs, faster execution                             │
│                                                                              │
│  4. MODULAR AGENT WEIGHTS                                                   │
│     Current: Equal weight for all voting agents                             │
│     Proposed: Configurable weights based on historical accuracy             │
│     Benefit: Better consensus from more accurate agents                     │
│                                                                              │
│  5. MULTI-ASSET SUPPORT                                                     │
│     Current: Hardcoded BTC-USDT-SWAP                                        │
│     Proposed: Configurable asset list, parallel analysis                    │
│     Benefit: Diversified trading opportunities                              │
│                                                                              │
│  6. BACKTESTING FRAMEWORK                                                   │
│     Current: No backtesting capability                                      │
│     Proposed: Historical data replay with agent simulation                  │
│     Benefit: Strategy validation before live deployment                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 12.3 Code Quality Improvements

| File | Lines | Complexity | Suggested Refactoring |
|------|-------|------------|----------------------|
| `trading_meeting.py` | ~4000 | Very High | Split into phase modules |
| `investment_agents.py` | ~3000 | High | Extract prompt templates |
| `trading_tools.py` | ~1300 | Medium | Group by data source |
| `agent_memory.py` | ~900 | Medium | Separate storage layer |

### 12.4 Monitoring & Observability

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MONITORING IMPROVEMENTS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Current:                                                                   │
│  • Basic logging to stdout                                                  │
│  • status.html manual refresh                                               │
│                                                                              │
│  Proposed:                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ • Structured JSON logging with correlation IDs                         │ │
│  │ • Prometheus metrics for:                                              │ │
│  │   - LLM call latency and token usage                                   │ │
│  │   - Tool execution time                                                │ │
│  │   - Vote distribution per meeting                                      │ │
│  │   - Trade outcomes (win/loss/amount)                                   │ │
│  │ • Grafana dashboards for:                                              │ │
│  │   - Real-time position P&L                                             │ │
│  │   - Agent accuracy trends                                              │ │
│  │   - System health metrics                                              │ │
│  │ • Alerting via Slack/Telegram for:                                     │ │
│  │   - Trade executions                                                   │ │
│  │   - Circuit breaker triggers                                           │ │
│  │   - System errors                                                      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix A: File Size Reference

| File | Size | Lines | Last Updated |
|------|------|-------|--------------|
| trading_meeting.py | 187 KB | ~4000 | Dec 2024 |
| investment_agents.py | 146 KB | ~3000 | Dec 2024 |
| trading_tools.py | 60 KB | ~1300 | Dec 2024 |
| enhanced_tools.py | 49 KB | ~1100 | Dec 2024 |
| okx_client.py | 41 KB | ~900 | Dec 2024 |
| okx_trader.py | 37 KB | ~900 | Dec 2024 |
| agent_memory.py | 35 KB | ~900 | Dec 2024 |
| agent.py | 29 KB | ~700 | Dec 2024 |
| paper_trader.py | 29 KB | ~700 | Dec 2024 |
| rewoo_agent.py | 23 KB | ~550 | Dec 2024 |

---

## Appendix B: Quick Reference

### Agent Prompt Injection Points

1. **System Prompt** - Agent role definition
2. **Memory Context** - Historical performance & lessons
3. **Position Context** - Current position state
4. **Analysis Context** - Previous phases' output
5. **Decision Options** - Available actions matrix
6. **Vote Prompt** - JSON output requirements

### Key Decision Logic

```python
# Vote consensus determination
if long_count >= 3 and short_count == 0:
    decision = "strong_long"
elif short_count >= 3 and long_count == 0:
    decision = "strong_short"
elif long_count > short_count:
    decision = "weak_long"
elif short_count > long_count:
    decision = "weak_short"
else:
    decision = "hold"

# Leverage calculation
consensus_strength = max(long_count, short_count) / total_voters
base_leverage = max_leverage * consensus_strength * avg_confidence / 100
```

---

*Document Version: 2.0*  
*Last Updated: December 2024*  
*Maintainer: Magellan Team*
