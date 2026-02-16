# Magellan Documentation Center

**Project**: Magellan - AI Investment Research & Trading Platform
**Current Version**: V3.2 (HITL Observability)
**Last Updated**: 2026-02-06

---

## 📚 Documentation Structure

### Root-Level Documentation (Primary)

| Document | Description |
|----------|-------------|
| [README.md](../README.md) | Project overview and quick start |
| [TRADING_SYSTEM_DOCUMENTATION.md](../TRADING_SYSTEM_DOCUMENTATION.md) | **Complete trading system documentation** |
| [ARCHITECTURE_EVOLUTION.md](../ARCHITECTURE_EVOLUTION.md) | Architecture design evolution |
| [SYSTEM_STATUS_REPORT.md](../SYSTEM_STATUS_REPORT.md) | Current system status report |
| [TRADING_COST_ANALYSIS.md](../TRADING_COST_ANALYSIS.md) | Trading cost analysis |

### Planning Documentation

| Document | Description |
|----------|-------------|
| [FUTURE_ROADMAP.md](FUTURE_ROADMAP.md) | Development roadmap (Phase 0-4) |
| [V4/](V4/) | V4 planning documents |

### Archived Documentation

| Directory | Description | Era |
|-----------|-------------|-----|
| [archive/v1/](archive/v1/) | V1 MVP design docs | Early 2025 |
| [archive/v3/](archive/v3/) | V3 UI/UX and testing docs | Late 2025 |
| [archive/old_root/](archive/old_root/) | Legacy root documentation | 2025 |
| [archive/refactoring/](archive/refactoring/) | Architecture refactoring docs | Dec 2025 |

---

## 🎯 Quick Navigation

### For New Developers
1. Start with [README.md](../README.md) for project overview
2. Read [TRADING_SYSTEM_DOCUMENTATION.md](../TRADING_SYSTEM_DOCUMENTATION.md) for trading system details
3. Check [SYSTEM_STATUS_REPORT.md](../SYSTEM_STATUS_REPORT.md) for current status

### For Architecture Understanding
1. [ARCHITECTURE_EVOLUTION.md](../ARCHITECTURE_EVOLUTION.md) - How the system evolved
2. [FUTURE_ROADMAP.md](FUTURE_ROADMAP.md) - Where we're heading

### For Historical Reference
- See [archive/](archive/) directory for previous version documentation

---

## 🏗️ System Overview

### Current Architecture (V3.2)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Magellan Trading System v3.2                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                       Trigger Layer (触发层)                         │    │
│  │  FastMonitor (硬条件) → TriggerAgent (LLM) → TriggerLock (状态机)   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                     │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Orchestration Layer (编排层)                      │    │
│  │  TradingGraph (LangGraph) → 7 Nodes → TradingState                  │    │
│  └────────────────���────────────────────────────────────────────────────┘    │
│                                     │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         Agent Layer (分析层)                         │    │
│  │  TA_Analyst │ Fund_Analyst │ Chain_Analyst │ Macro_Expert │ ...     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                     │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                       Execution Layer (执行层)                       │    │
│  │  ExecutorAgent (7 Tools) + SafetyGuard + FundingMonitor             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Features

| Feature | Status | Description |
|---------|--------|-------------|
| Multi-Agent Collaboration | ✅ | 16 expert agents for analysis |
| LangGraph Orchestration | ✅ | 7-node state machine workflow |
| Three-Layer Trigger | ✅ | FastMonitor → TriggerAgent → Full Analysis |
| HITL | ✅ | Semi-Auto only (all trades require human confirmation) |
| Anti-Bias System | ✅ | Direction neutralization + Echo chamber detection |
| ATR Dynamic Stop Loss | ✅ | Volatility-based stop loss calculation |
| Funding Rate Awareness | ✅ | Smart entry timing and position limits |

---

## 📊 Version History

| Version | Description | Status |
|---------|-------------|--------|
| V1.0 | MVP - Stock analysis tool | ✅ Completed |
| V2.0 | Secondary market enhancement | ✅ Completed |
| V3.0 | Primary market research platform | ✅ Completed |
| V3.1 | LangGraph + ExecutorAgent | ✅ Completed |
| V3.2 | HITL + Anti-bias + Parallel execution | ✅ Current |
| V4.0 | Intelligent research assistant | 📋 Planning |

---

*Last Updated: 2026-02-06*
