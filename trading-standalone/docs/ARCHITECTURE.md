# System Architecture

This document provides a comprehensive overview of the Magellan Trading System architecture.

## Table of Contents
1. [Service Architecture](#service-architecture)
2. [Docker Topology](#docker-topology)
3. [Component Overview](#component-overview)
4. [Request Flow](#request-flow)
5. [External Integrations](#external-integrations)

---

## Service Architecture

### High-Level Overview

```mermaid
flowchart TB
    subgraph External["🌐 External Services"]
        OKX[OKX Exchange API]
        BIN[Binance API]
        DS[DeepSeek LLM]
        TAV[Tavily Search]
        ALT[Alternative.me]
    end
    
    subgraph Docker["🐳 Docker Network: trading_network"]
        subgraph Core["Core Services"]
            RO[report_orchestrator<br/>:8001]
            LLM[llm_gateway<br/>:8000]
            WS[web_search_service<br/>:8010]
        end
        
        subgraph Trading["Trading Services"]
            TS[trading_service<br/>:8020]
        end
        
        subgraph Storage["Storage"]
            REDIS[(Redis<br/>:6379)]
        end
    end
    
    TS -->|HTTP| RO
    RO -->|HTTP| LLM
    RO -->|HTTP| WS
    RO -->|TCP| REDIS
    TS -->|TCP| REDIS
    
    LLM -->|HTTPS| DS
    WS -->|HTTPS| TAV
    RO -->|HTTPS| BIN
    RO -->|HTTPS| ALT
    TS -->|HTTPS| OKX
    
    style External fill:#e3f2fd
    style Core fill:#e8f5e9
    style Trading fill:#fff3e0
    style Storage fill:#fce4ec
```

---

## Docker Topology

### Container Details

```mermaid
flowchart TB
    subgraph trading_service["📊 trading_service"]
        TS_API[FastAPI :8020]
        TS_SCH[Scheduler]
        TS_MON[Position Monitor]
        TS_PAPER[Paper Trader]
    end
    
    subgraph report_orchestrator["🤖 report_orchestrator"]
        RO_API[FastAPI :8001]
        RO_MEET[TradingMeeting]
        RO_AGENT[Agent System]
        RO_TOOLS[Trading Tools]
        RO_MEM[Memory Store]
    end
    
    subgraph llm_gateway["🧠 llm_gateway"]
        LLM_API[FastAPI :8000]
        LLM_DS[DeepSeek Client]
        LLM_GEMINI[Gemini Client]
        LLM_KIMI[Kimi Client]
    end
    
    subgraph web_search["🔍 web_search_service"]
        WS_API[FastAPI :8010]
        WS_TAV[Tavily Client]
    end
    
    subgraph redis["💾 Redis"]
        R_MEM[Agent Memory]
        R_POS[Position Store]
        R_PRED[Prediction Store]
    end
    
    TS_SCH -->|Trigger Meeting| RO_API
    RO_MEET --> RO_AGENT
    RO_AGENT --> RO_TOOLS
    RO_AGENT -->|LLM Request| LLM_API
    RO_TOOLS -->|Web Search| WS_API
    RO_MEM --> R_MEM
    
    style trading_service fill:#fff3e0
    style report_orchestrator fill:#e8f5e9
    style llm_gateway fill:#e3f2fd
    style web_search fill:#f3e5f5
    style redis fill:#fce4ec
```

### Docker Compose Services

| Service | Port | Build Context | Purpose |
|---------|------|---------------|---------|
| `trading_service` | 8020 | `./trading-service` | Main entry point, scheduler, position monitoring |
| `report_orchestrator` | 8001 | `../backend/services/report_orchestrator` | Agent system, trading meeting orchestration |
| `llm_gateway` | 8000 | `../backend/services/llm_gateway` | LLM API abstraction (DeepSeek, Gemini, Kimi) |
| `web_search_service` | 8010 | `../backend/services/web_search_service` | Tavily search integration |
| `redis` | 6379 | `redis:7-alpine` | Memory, position, and prediction storage |

---

## Component Overview

### Core Components

```mermaid
classDiagram
    class TradingMeeting {
        +run()
        +_run_phase_1_analysis()
        +_run_phase_2_signal()
        +_run_phase_3_risk()
        +_run_phase_4_consensus()
        +_run_phase_5_execution()
    }
    
    class Agent {
        +id: str
        +name: str
        +role: str
        +system_prompt: str
        +tools: List[Tool]
        +chat(prompt): Response
        +use_tool(name, args): Result
    }
    
    class PositionContext {
        +has_position: bool
        +direction: str
        +entry_price: float
        +unrealized_pnl: float
        +to_summary(): str
    }
    
    class AgentMemory {
        +agent_id: str
        +win_rate: float
        +total_pnl: float
        +lessons_learned: List
        +get_context_for_prompt(): str
    }
    
    class TradingToolkit {
        +get_market_price()
        +get_technical_indicators()
        +open_long()
        +open_short()
        +close_position()
        +hold()
    }
    
    TradingMeeting --> Agent
    Agent --> TradingToolkit
    TradingMeeting --> PositionContext
    Agent --> AgentMemory
```

### File Structure

```
trading-standalone/
├── trading-service/           # Main trading service
│   ├── app/
│   │   ├── main.py           # FastAPI app
│   │   ├── scheduler.py      # Trading scheduler
│   │   └── position_monitor.py
│   └── Dockerfile
│
├── ../backend/services/
│   ├── report_orchestrator/   # Agent system
│   │   ├── app/
│   │   │   ├── core/
│   │   │   │   ├── trading/
│   │   │   │   │   ├── trading_meeting.py    # 5-phase orchestration
│   │   │   │   │   ├── trading_tools.py      # Tool implementations
│   │   │   │   │   ├── position_context.py   # Position state
│   │   │   │   │   └── agent_memory.py       # Memory system
│   │   │   │   └── roundtable/
│   │   │   │       ├── agent.py             # Base agent class
│   │   │   │       └── tool.py              # Tool definitions
│   │   │   └── models/
│   │   │       └── trading_models.py        # Data models
│   │   └── Dockerfile
│   │
│   ├── llm_gateway/           # LLM abstraction
│   │   └── app/main.py        # Multi-provider LLM calls
│   │
│   └── web_search_service/    # Search service
│       └── app/main.py        # Tavily integration
│
└── docker-compose.yml         # Container orchestration
```

---

## Request Flow

### Trading Meeting Request Flow

```mermaid
sequenceDiagram
    autonumber
    participant SCH as Scheduler
    participant TS as trading_service
    participant RO as report_orchestrator
    participant LLM as llm_gateway
    participant DS as DeepSeek
    participant REDIS as Redis
    participant OKX as OKX Exchange

    SCH->>TS: Trigger Analysis (every 4h)
    TS->>RO: POST /api/v1/trading/meeting
    
    RO->>REDIS: Load Agent Memories
    RO->>OKX: Get Current Position
    RO->>RO: Build PositionContext
    
    loop For Each Phase (1-5)
        loop For Each Agent
            RO->>REDIS: Get Agent Memory
            RO->>LLM: POST /api/v1/chat/with-tools
            LLM->>DS: OpenAI-compatible request
            DS-->>LLM: Response with tool_calls
            LLM-->>RO: Parsed response
            RO->>RO: Execute tool if needed
        end
    end
    
    alt Trade Signal Generated
        RO->>TS: Return TradingSignal
        TS->>OKX: Execute Trade
        TS->>REDIS: Record Prediction
    else Hold Signal
        RO->>TS: Return Hold Signal
    end
```

### LLM Gateway Request Flow

```mermaid
flowchart TB
    subgraph Input["📥 Input"]
        REQ[LLM Request with Tools]
    end
    
    subgraph Gateway["🧠 llm_gateway"]
        NORM[normalize_tools_format]
        ROUTE{Provider Router}
        DS_CLIENT[DeepSeek Client]
        GEMINI_CLIENT[Gemini Client]
        KIMI_CLIENT[Kimi Client]
    end
    
    subgraph Retry["🔄 Retry Logic"]
        R1[Attempt 1]
        R2[Attempt 2]
        R3[Attempt 3]
    end
    
    subgraph Output["📤 Output"]
        RESP[Unified Response]
    end
    
    REQ --> NORM
    NORM --> ROUTE
    ROUTE -->|DeepSeek| DS_CLIENT
    ROUTE -->|Gemini| GEMINI_CLIENT
    ROUTE -->|Kimi| KIMI_CLIENT
    
    DS_CLIENT --> R1
    R1 -->|Fail| R2
    R2 -->|Fail| R3
    R3 --> RESP
    
    style Input fill:#e3f2fd
    style Gateway fill:#e8f5e9
    style Retry fill:#fff3e0
    style Output fill:#f3e5f5
```

---

## External Integrations

### API Connections

```mermaid
flowchart LR
    subgraph System["🏠 Magellan System"]
        TS[trading_service]
        RO[report_orchestrator]
        LLM[llm_gateway]
        WS[web_search_service]
    end
    
    subgraph Exchange["💹 Exchange APIs"]
        OKX[OKX API<br/>Trading & Account]
        BIN[Binance API<br/>Market Data]
    end
    
    subgraph LLM_Providers["🤖 LLM Providers"]
        DS[DeepSeek<br/>Primary]
        GEMINI[Gemini<br/>Fallback]
        KIMI[Kimi<br/>Fallback]
    end
    
    subgraph Data["📊 Data Providers"]
        TAV[Tavily<br/>Web Search]
        ALT[Alternative.me<br/>Fear & Greed]
    end
    
    TS --> OKX
    RO --> BIN
    RO --> ALT
    LLM --> DS & GEMINI & KIMI
    WS --> TAV
    
    style System fill:#e8f5e9
    style Exchange fill:#fff3e0
    style LLM_Providers fill:#e3f2fd
    style Data fill:#fce4ec
```

### Environment Variables

| Variable | Service | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | llm_gateway | DeepSeek API authentication |
| `DEEPSEEK_BASE_URL` | llm_gateway | DeepSeek API endpoint |
| `OKX_API_KEY` | trading_service | OKX trading API key |
| `OKX_SECRET_KEY` | trading_service | OKX API secret |
| `OKX_PASSPHRASE` | trading_service | OKX API passphrase |
| `OKX_DEMO_MODE` | trading_service | Enable demo trading |
| `TAVILY_API_KEY` | web_search_service | Tavily search API key |
| `SCHEDULER_INTERVAL_HOURS` | trading_service | Meeting trigger interval |
| `MAX_LEVERAGE` | report_orchestrator | Maximum allowed leverage |

---

## Related Documents

- [AGENT_DATA_FLOW.md](./AGENT_DATA_FLOW.md) - Agent-to-agent data flow
- [PHASE_DETAILS.md](./PHASE_DETAILS.md) - Detailed phase breakdown
- [TOOL_REFERENCE.md](./TOOL_REFERENCE.md) - Available tools

---

*Last Updated: 2024-12-09*
