# Magellan - AI Investment Research & Trading Platform

AI-powered investment analysis platform with multi-agent collaboration for due diligence, market analysis, and automated trading.

## 🚀 Quick Start

```bash
# Start backend services
docker compose up -d

# Start frontend development server
cd frontend && npm run dev

# Access the application
open http://localhost:5174
```

## 📦 Project Structure

```
Magellan/
├── backend/services/           # Microservices (10 services)
│   ├── report_orchestrator/    # Core: trading, roundtable, reports
│   ├── llm_gateway/           # LLM API gateway
│   ├── web_search_service/    # Tavily search integration
│   └── ...                    # Other services
├── frontend/                   # Vue 3 + TypeScript frontend
├── docs/                       # Documentation
│   ├── FUTURE_ROADMAP.md      # Development roadmap
│   └── V4/                    # V4 planning docs
└── docker-compose.yml          # Container orchestration
```

## 🛠️ Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.11+ |
| Frontend | Vue 3, TypeScript, Vite, Tailwind CSS |
| LLM | Google Gemini, DeepSeek |
| Orchestration | LangGraph |
| Database | Redis, PostgreSQL, Qdrant |
| Exchange | OKX API (Demo/Live) |
| Container | Docker Compose |

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [TRADING_SYSTEM_DOCUMENTATION.md](TRADING_SYSTEM_DOCUMENTATION.md) | Complete trading system docs |
| [ARCHITECTURE_EVOLUTION.md](ARCHITECTURE_EVOLUTION.md) | Architecture design evolution |
| [SYSTEM_STATUS_REPORT.md](SYSTEM_STATUS_REPORT.md) | Current system status |
| [docs/FUTURE_ROADMAP.md](docs/FUTURE_ROADMAP.md) | Development roadmap |

## ✨ Core Features

### Investment Analysis
- Multi-agent roundtable discussions (16 expert agents)
- Due diligence workflow (BP parsing, team/market analysis)
- Investment memo generation

### Auto Trading System
- LangGraph workflow orchestration (7 nodes)
- Three-layer trigger system (FastMonitor → TriggerAgent → Full Analysis)
- HITL: Semi-Auto only (all trades require human confirmation)
- Anti-bias system (direction neutralization, echo chamber detection)
- ATR-based dynamic stop loss
- Funding rate awareness

## 🔧 Development

```bash
# Run tests
cd backend/services/report_orchestrator && pytest

# Check code quality
ruff check backend/

# Build frontend
cd frontend && npm run build
```

## 📊 Current Version

**Version**: 3.2 (HITL Observability)
**Branch**: feature/hitl-observability-v2

## 📄 License

Proprietary - All rights reserved
