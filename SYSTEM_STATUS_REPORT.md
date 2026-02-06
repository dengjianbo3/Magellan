# Magellan 系统现状详细报告

> **生成日期**: 2026-02-06
> **审阅轮次**: 5+ 轮全面代码和文档审阅
> **当前分支**: feature/hitl-observability-v2

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术架构](#2-技术架构)
3. [核心系统组件](#3-核心系统组件)
4. [前端应用](#4-前端应用)
5. [数据模型](#5-数据模型)
6. [配置系统](#6-配置系统)
7. [当前开发状态](#7-当前开发状态)
8. [已知问题与待办事项](#8-已知问题与待办事项)
9. [改进建议](#9-改进建议)

---

## 1. 项目概述

### 1.1 项目定位

**Magellan** 是一个 AI 驱动的投资分析与自动交易平台，具有双重用途：

| 功能模块 | 描述 |
|---------|------|
| **投资尽调平台** | 多场景投资分析报告生成（早期投资、成长期、公开市场、另类投资、行业研究） |
| **自动交易系统** | 多 Agent 协作的 BTC/USDT 永续合约交易 |

### 1.2 核心特性清单

| 特性 | 状态 | 描述 |
|------|------|------|
| 多 Agent 协作 | ✅ 完成 | 7+ 专业分析 Agent（技术面、基本面、链上数据等） |
| 智能触发系统 | ✅ 完成 | 三层触发器架构（FastMonitor + TriggerAgent + Full Analysis） |
| LangGraph 编排 | ✅ 完成 | 基于状态机的工作流，支持条件分支和错误恢复 |
| 仓位管理 | ✅ 完成 | 支持加仓、减仓、反向操作的智能仓位管理 |
| 风险控制 | ✅ 完成 | 多层安全检查（启动保护、止损验证、爆仓风险） |
| 人在环路 (HITL) | ✅ 完成 | 支持 FULL_AUTO / SEMI_AUTO / MANUAL 三种模式 |
| 多时间框架分析 | ✅ 完成 | 15m/1H/4H/1D 趋势对齐分析 |
| Agent 权重学习 | ✅ 完成 | 基于历史表现动态调整 Agent 投票权重 |
| ATR 动态止损 | ✅ 完成 | 基于市场波动率自适应计算止损价格 |
| 方向中性化 | ✅ 完成 | Agent 输出 bullish/bearish 分数，消除语言偏见 |
| 回声室检测 | ✅ 完成 | 80%+ 共识时自动降低置信度，防止群体思维 |
| 资金费率感知 | ✅ 完成 | 智能入场时机、动态持仓限制、利润保护 |

### 1.3 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | FastAPI (Python 3.11+) |
| **前端框架** | Vue 3 + Vite + Tailwind CSS |
| **LLM 集成** | Google Gemini / DeepSeek / OpenAI |
| **工作流编排** | LangGraph |
| **数据库** | PostgreSQL + Redis |
| **向量数据库** | Qdrant / ChromaDB |
| **消息队列** | Redis Pub/Sub |
| **容器化** | Docker + Docker Compose |
| **交易所** | OKX API (模拟盘/实盘) |

---

## 2. 技术架构

### 2.1 系统架构图

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
│  └─────────────────────────────────────────────────────────────────────┘    │
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
│                                     │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Trading Layer (交易层)                        │    │
│  │  PaperTrader (模拟) │ OKXTrader (实盘/模拟盘)                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                     │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Memory Layer (记忆层)                         │    │
│  │  ReflectionMemory │ AgentWeights │ TradingDecisionStore (Redis)     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 微服务架构

| 服务 | 端口 | 职责 |
|------|------|------|
| **report_orchestrator** | 8000 | 核心服务：报告编排、交易系统、圆桌会议 |
| **file_service** | 8001 | 文件上传和管理 |
| **llm_gateway** | 8003 | LLM 调用网关 |
| **excel_parser** | 8004 | Excel 文件解析 |
| **word_parser** | 8005 | Word 文件解析 |
| **external_data_service** | 8006 | 外部数据获取 |
| **auth_service** | 8007 | 用户认证 |
| **user_service** | 8008 | 用户管理 |
| **internal_knowledge_service** | 8009 | 内部知识库 |
| **web_search_service** | 8010 | 网络搜索 |

### 2.3 目录结构

```
Magellan/
├── backend/services/
│   └── report_orchestrator/          # 核心服务
│       ├── app/
│       │   ├── api/                  # API 路由
│       │   │   └── trading_routes.py # 交易 API (2800+ 行)
│       │   ├── core/
│       │   │   ├── trading/          # 交易系统核心
│       │   │   │   ├── orchestration/  # LangGraph 编排
│       │   │   │   ├── trigger/        # 触发器系统
│       │   │   │   ├── domain/         # 领域模型
│       │   │   │   ├── safety/         # 安全控制
│       │   │   │   └── reflection/     # 反思学习
│       │   │   └── roundtable/       # 圆桌会议系统
│       │   └── models/               # 数据模型
│       └── config/
│           └── agents.yaml           # Agent 配置 (760 行)
├── frontend/                         # Vue 3 前端
│   └── src/
│       ├── views/
│       │   └── AutoTradingView.vue   # 交易界面 (2169 行)
│       └── components/
└── trading-standalone/               # 独立交易系统
```

---

## 3. 核心系统组件

### 3.1 LangGraph 工作流

**7 个节点的交易决策流程**：

```
market_analysis_node
        ↓
signal_generation_node (5 Agent 并行)
        ↓
risk_assessment_node (RiskAssessor LLM)
        ↓
consensus_node (Leader LLM + 回声室检测)
        ↓
execution_node (ExecutorAgent)
        ↓
reflection_node (仅对实际交易)
        ↓
react_fallback_node (错误恢复)
```

**TradingState 结构**：
- 输入：`trigger_reason`, `symbol`, `market_data`, `position_context`
- 中间状态：`agent_votes`, `risk_assessment`, `leader_summary`
- 输出：`final_signal`, `execution_result`, `execution_success`
- 控制：`completed_nodes`, `node_timings`, `error`, `should_fallback`

### 3.2 触发器系统（三层架构）

| 层级 | 组件 | 职责 | LLM 调用 |
|------|------|------|----------|
| Layer 1 | FastMonitor | 硬条件检测（价格急变、成交量异常、RSI 极值等） | ❌ 无 |
| Layer 2 | TriggerAgent | LLM 深度分析（新闻 + 技术指标 + 仓位感知） | ✅ 1 次 |
| Layer 3 | Full Analysis | 完整多 Agent 分析 | ✅ 8-10 次 |

**成本节省效果**：60-80% LLM 调用减少

### 3.3 ExecutorAgent（执行器）

**7 个交易工具**：
1. `open_long` - 开多仓（含反向逻辑）
2. `open_short` - 开空仓（含反向逻辑）
3. `hold` - 观望不操作
4. `close_position` - 完全平仓
5. `add_to_long` - 加多仓
6. `add_to_short` - 加空仓
7. `reduce_position` - 部分平仓

**安全机制**：
- `MIN_ADD_AMOUNT = 10 USDT` - 最小加仓金额
- `SAFETY_BUFFER = 50 USDT` - 保证金安全缓冲
- `_validate_stop_loss()` - 止损验证（确保在爆仓前触发）
- `_get_available_margin()` - 真实可用保证金计算

### 3.4 防偏见系统

**方案 A：方向中性化**
- Agent 输出 `bullish_score` + `bearish_score`（0-100）
- 系统计算方向：`diff >= 15 → long`, `diff <= -15 → short`, 否则 `hold`
- 消除 `long/short` 词汇带来的语言偏见

**方案 B：回声室检测**
- 80-94% 共识 → 轻度回声室 → 置信度 -15%
- ≥95% 共识 → 严重回声室 → 置信度 -30%
- 防止群体思维

### 3.5 HITL 模式管理

| 模式 | 自动开仓 | 自动平仓 | 用户干预 |
|------|---------|---------|---------|
| FULL_AUTO | ✅ | ✅ | ❌ |
| SEMI_AUTO | ❌ 需确认 | ❌ 需确认 | ✅ 审批 |
| MANUAL | ❌ | ❌ | ✅ 完全 |

**待确认交易**：
- 5 分钟 TTL
- 支持修改参数（杠杆、TP/SL）
- 存储在 Redis

### 3.6 圆桌会议系统

**16 位投资分析专家**：

| 类型 | Agent | 职责 |
|------|-------|------|
| 核心 | Leader | 主持讨论、综合判断、决定结束时机 |
| 核心 | MarketAnalyst | 市场规模、竞争格局、行业趋势 |
| 核心 | FinancialExpert | 财务报表、估值、盈利能力 |
| 核心 | TeamEvaluator | 创始团队、管理层、执行能力 |
| 核心 | RiskAssessor | 风险识别、评估、缓解建议 |
| 核心 | TechSpecialist | 技术架构、产品能力、技术壁垒 |
| 核心 | LegalAdvisor | 合规状态、监管动态、法律风险 |
| 核心 | TechnicalAnalyst | K 线形态、技术指标、支撑阻力位 |
| 高级 | MacroEconomist | 宏观经济、货币政策、经济周期 |
| 高级 | ESGAnalyst | 环境、社会、治理评估 |
| 高级 | SentimentAnalyst | 市场情绪、社交媒体、投资者情绪 |
| 高级 | QuantStrategist | 量化模型、统计分析、回测 |
| 高级 | DealStructurer | 交易结构、估值谈判、条款设计 |
| 高级 | M&AAdvisor | 并购机会、协同效应、整合风险 |
| 专业 | OnchainAnalyst | 链上数据、巨鲸监控、DeFi TVL |
| 专业 | ContrarianAnalyst | 挑战共识、发现盲点、防止群体思维 |

---

## 4. 前端应用

### 4.1 页面视图

| 视图 | 文件 | 功能 |
|------|------|------|
| Dashboard | DashboardView.vue | 仪表盘首页 |
| Analysis | AnalysisWizardView.vue | 投资分析向导 |
| AutoTrading | AutoTradingView.vue | 自动交易界面 |
| Roundtable | RoundtableView.vue | 圆桌讨论 |
| Reports | ReportsView.vue | 报告管理 |
| Agents | AgentsView.vue | Agent 管理 |
| Knowledge | KnowledgeView.vue | 知识库 |
| Settings | SettingsView.vue | 系统设置 |

### 4.2 AutoTradingView 功能

**核心功能**：
- 三种交易模式切换（手动/半自动/全自动）
- 实时账户概览（权益、盈亏、回撤、Alpha）
- 当前持仓显示（方向、杠杆、TP/SL、未实现盈亏）
- 权益曲线图表（Chart.js）
- 实时讨论面板（WebSocket）
- Agent 表现统计
- 交易历史记录
- 待确认交易弹窗（HITL）

**技术实现**：
- Vue 3 Composition API
- WebSocket 实时通信
- Pinia 状态管理
- i18n 国际化（中/英）

---

## 5. 数据模型

### 5.1 交易模型 (trading_models.py)

| 模型 | 用途 |
|------|------|
| TradingSignal | 交易信号（方向、杠杆、TP/SL、置信度） |
| TradeRecord | 交易记录（执行价格、盈亏、平仓原因） |
| Position | 持仓信息（方向、杠杆、未实现盈亏、清算价格） |
| AccountBalance | 账户余额（权益、可用余额、已用保证金） |
| AgentVote | Agent 投票（方向、置信度、建议杠杆） |
| RiskLimits | 风险限制（最大杠杆、最大仓位、每日亏损限制） |
| TradingConfig | 交易配置（分析间隔、交易对、风险限制） |

### 5.2 技术分析模型 (technical_models.py)

| 模型 | 用途 |
|------|------|
| TrendDirection | 趋势方向枚举 |
| SignalStrength | 信号强度枚举 |
| RSIIndicator | RSI 指标 |
| MACDIndicator | MACD 指标 |
| BollingerBandsIndicator | 布林带指标 |
| TechnicalAnalysisOutput | 完整技术分析输出 |

### 5.3 尽职调查模型 (dd_models.py)

| 模型 | 用途 |
|------|------|
| BPStructuredData | BP 结构化数据 |
| TeamAnalysisOutput | 团队分析输出 |
| MarketAnalysisOutput | 市场分析输出 |
| CrossCheckResult | 交叉验证结果 |
| DDQuestion | DD 问题 |
| PreliminaryIM | 初步投资备忘录 |

---

## 6. 配置系统

### 6.1 Agent 配置 (agents.yaml)

**配置结构**：
- 13 个原子 Agent（所有场景复用）
- 2 个特殊 Agent（Leader、ReportSynthesizer）
- 支持 `quick_mode` 参数
- 支持多语言（zh/en）

**Agent 组合示例**：
```yaml
# 早期投资分析
team_evaluator → market_analyst → financial_expert → risk_assessor → deal_structurer → report_synthesizer

# 公开市场投资分析
macro_economist → financial_expert → technical_analyst → quant_strategist → sentiment_analyst → risk_assessor → report_synthesizer
```

### 6.2 环境变量

```bash
# OKX API
OKX_API_KEY, OKX_SECRET_KEY, OKX_PASSPHRASE, OKX_DEMO_MODE

# 交易参数
DEFAULT_LEVERAGE=5, MAX_LEVERAGE=20
DEFAULT_POSITION_PERCENT=20, MIN_POSITION_PERCENT=10, MAX_POSITION_PERCENT=30
DEFAULT_TP_PERCENT=8, DEFAULT_SL_PERCENT=3

# 触发器
TRIGGER_INTERVAL_SECONDS=300, TRIGGER_COOLDOWN_MINUTES=30
FAST_MONITOR_ENABLED=true

# LLM
GOOGLE_API_KEY, DEEPSEEK_API_KEY

# 服务
REDIS_HOST, LLM_GATEWAY_URL
```

---

## 7. 当前开发状态

### 7.1 Git 状态

**当前分支**: `feature/hitl-observability-v2`

**已修改文件**：
- `TRADING_SYSTEM_DOCUMENTATION.md` - 交易系统文档
- `trading_routes.py` - 交易 API 路由
- `batch_config.py` - 批量配置
- `investment_agents.py` - 投资 Agent
- `executor_agent.py` - 执行器 Agent
- `mode_manager.py` - 模式管理
- `okx_trader.py` - OKX 交易接口
- `graph.py` - LangGraph 图定义
- `nodes.py` - 工作流节点
- `paper_trader.py` - 模拟交易
- `price.py` - 价格工具
- `trading_agents.py` - 交易 Agent
- `trading_meeting.py` - 交易会议
- `fast_monitor.py` - 快速监控
- `weight_learner.py` - 权重学习
- `trading_models.py` - 交易模型
- `agents.yaml` - Agent 配置
- `AutoTradingView.vue` - 前端交易视图

**新增文件**：
- `anti_bias.py` - 防偏见系统
- `test_langgraph_integration.py` - LangGraph 集成测试

### 7.2 最近提交

| 提交 | 描述 |
|------|------|
| 952ada6 | fix: add HITL mode check to trading_meeting.py tools |
| a8a53b2 | fix: implement HITL mode blocking for Semi-Auto and Manual modes |
| 84b58cf | feat: enhance HITL Mode UI with pending trades display |
| b40af19 | Merge cleanup changes into feature branch |
| 4580f44 | refactor: clean up codebase |

### 7.3 版本历史

| 版本 | 主要变更 |
|------|---------|
| v1.0 | MVP（股票分析工具） |
| v2.0 | 二级市场增强版 |
| v3.0 | 一级市场投研工作台 |
| v3.1 | LangGraph 编排 + ExecutorAgent |
| v3.2 | HITL 模式 + 防偏见系统 + 并行执行 |

---

## 8. 已知问题与待办事项

### 8.1 已修复的 Bug (2026-01)

| Bug | 根因 | 修复 |
|-----|------|------|
| OKX Demo Mode 环境变量无效 | `__init__` 默认参数覆盖环境变量 | 使用 `Optional[bool] = None` |
| Insufficient Margin 误报 | 双重执行路径导致 reasoning 错误 | 优先使用 OKX order_id 作为成功证据 |
| 前端 Dashboard 服务器 URL 硬编码 | 硬编码 IP 地址 | 改为动态主机检测 |
| 保证金计算使用错误数据源 | 使用 paper_trader 而非 OKX API | 优先使用 OKX max_avail_size |

### 8.2 待办事项

| 优先级 | 任务 | 状态 |
|--------|------|------|
| P0 | Agent 并行执行 | ✅ 已完成 |
| P1 | HITL 模式完善 | ✅ 已完成 |
| P1 | 防偏见系统 | ✅ 已完成 |
| P1 | 集成测试 | 🔄 进行中 |
| P2 | 多交易对支持 | ❌ 未开始 |
| P2 | 移动止损 (Trailing Stop) | ❌ 未开始 |
| P3 | 风控仪表板 | ❌ 未开始 |

---

## 9. 改进建议

### 9.1 短期改进（1-2 周）

1. **完善集成测试**
   - 端到端测试 LangGraph 工作流
   - 测试 HITL 模式切换
   - 测试防偏见系统

2. **日志增强**
   - 结构化日志 + 追踪 ID
   - Prometheus 指标完善

3. **错误处理优化**
   - 单 Agent 超时不阻塞整体
   - 更详细的错误消息

### 9.2 中期改进（1-2 月）

1. **多交易对支持**
   - 添加 ETH-USDT-SWAP
   - symbol 参数化

2. **移动止损**
   - 基于 ATR 动态调整
   - Trailing Stop 实现

3. **事件驱动触发**
   - 监听链上大额转账
   - 重大新闻实时触发

### 9.3 长期改进（3-6 月）

1. **策略框架**
   - 可配置的交易策略模板
   - 策略回测系统

2. **风控仪表板**
   - 可视化监控面板
   - 实时风险指标

3. **多 LLM 套利**
   - 不同 LLM 的意见对比
   - 成本优化

---

## 附录

### A. 代码统计

| 指标 | 数值 |
|------|------|
| 后端代码行数 | ~50,000+ 行 |
| 前端代码行数 | ~15,000+ 行 |
| 微服务数量 | 10 个 |
| Agent 数量 | 16 个 |
| 前端视图数量 | 8 个 |
| 测试文件数量 | 20+ 个 |

### B. 单次运行成本

| 项目 | 成本 | 占比 |
|------|------|------|
| Tavily 搜索 | $0.08-0.09 | 87% |
| LLM 调用 | $0.012-0.013 | 13% |
| 免费 API | $0.00 | 0% |
| **总计** | **~$0.10** | 100% |

### C. 文档索引

| 文档 | 位置 |
|------|------|
| 项目说明 | README.md |
| 架构演进 | ARCHITECTURE_EVOLUTION.md |
| 交易系统文档 | TRADING_SYSTEM_DOCUMENTATION.md |
| 成本分析 | TRADING_COST_ANALYSIS.md |
| 未来路线图 | docs/FUTURE_ROADMAP.md |
| 当前状态 | docs/CURRENT_STATUS.md |

---

*报告生成时间: 2026-02-06*
*审阅者: Claude Opus 4.5*
