# Magellan - AI Investment Research Platform

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
├── backend/services/           # Microservices
│   ├── report_orchestrator/    # Main orchestration service
│   ├── llm_gateway/           # LLM API gateway
│   ├── auth_service/          # Authentication
│   └── ...                    # Other services
├── frontend/                   # Vue 3 + TypeScript frontend
├── trading-standalone/         # Standalone trading system
├── docs/                       # Documentation
└── docker-compose.yml          # Container orchestration
```

## 🛠️ Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.11+ |
| Frontend | Vue 3, TypeScript, Vite |
| LLM | Google Gemini |
| Database | Redis, PostgreSQL, Qdrant |
| Container | Docker Compose |

## 📚 Documentation

- **[📖 Full Documentation](docs/README.md)** - Complete project documentation
- **[🏗️ Architecture](SYSTEM_ARCHITECTURE.md)** - System design overview
- **[📋 Project Docs](PROJECT_DOCUMENTATION.md)** - Detailed project documentation

## 🔧 Development

```bash
# Run tests
pytest

# Check code quality
ruff check backend/

# Build frontend
cd frontend && npm run build
```

## 📄 License

Proprietary - All rights reserved
