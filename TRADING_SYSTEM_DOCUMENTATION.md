# Magellan Trading System - 完整架构与能力文档 v3.1

> **文档更新日期**: 2026-01-06
> **适用版本**: dev 分支 (LangGraph + ExecutorAgent 增强版 + 生产环境支持)

## 📋 目录

**第一部分：系统概述**

1. [系统概述](#系统概述)
2. [技术架构](#技术架构)
3. [目录结构](#目录结构)

**第二部分：核心系统**
4. [交易决策流程](#交易决策流程)
5. [触发器系统 (TriggerAgent)](#触发器系统-triggeragent)
6. [执行系统 (ExecutorAgent)](#执行系统-executoragent)
7. [资金费率感知系统](#资金费率感知系统-funding-fee-system)
8. [LangGraph 工作流](#langgraph-工作流)

**第三部分：交易模式**
9. [人在环路模式设计](#人在环路模式设计-human-in-the-loop)

**第四部分：开发与部署**
10. [快速开始指南](#快速开始指南)
11. [生产环境部署指南](#生产环境部署指南)

**第五部分：演进与规划**
12. [重构变更记录](#重构变更记录)
13. [改进建议与未来规划](#改进建议与未来规划)
14. [未实现与移除的能力](#未实现与移除的能力)

**第六部分：附录**
15. [Bug 修复记录](#bug-修复记录-2026-01)
16. [常见问题排查](#常见问题排查)
17. [附录：配置与规范](#附录配置与规范)

---

# 第一部分：系统概述

## 系统概述

### 项目定位

**Magellan** 是一个 AI 驱动的加密货币交易系统，具有双重用途：

1. **投资尽调平台** - 多场景投资分析报告生成
2. **自动交易系统** - 多 Agent 协作的 BTC/USDT 永续合约交易

### 核心特性

| 特性 | 描述 |
|------|------|
| **多 Agent 协作** | 7+ 专业分析 Agent (技术面、基本面、链上数据等) |
| **智能触发** | TriggerAgent 监控市场，智能决定何时启动分析 |
| **LangGraph 编排** | 基于状态机的工作流，支持条件分支和错误恢复 |
| **仓位管理** | 支持加仓、减仓、反向操作的智能仓位管理 |
| **风险控制** | 多层安全检查 (启动保护、止损验证、爆仓风险) |
| **人在环路 (HITL)** | 支持 FULL_AUTO / SEMI_AUTO / MANUAL 三种模式 |
| **多时间框架分析** | 15m/1H/4H/1D 趋势对齐分析，提供一致性评分 |
| **Agent 权重学习** | 基于历史表现动态调整 Agent 投票权重 |
| **用户偏好学习** | 从 SEMI_AUTO 决策中学习用户的杠杆和方向偏好 |
| **ATR 动态止损** | 基于市场波动率自适应计算止损价格 |
| **优雅降级** | 服务故障时自动降级，确保系统稳定运行 |

---

## 技术架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Magellan Trading System v3.1                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                       Trigger Layer (触发层)                         │    │
│  │                                                                     │    │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │    │
│  │  │ FastMonitor  │ │ TriggerAgent │ │ NewsCrawler │ │TACalculator│ │    │
│  │  │ (硬条件检测) │ │  (LLM分析)   │ │  (新闻抓取) │ │ (技术指标) │ │    │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘ │    │
│  │                          │                                          │    │
│  │                    TriggerLock (状态机)                              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                     │ (触发时调用)                           │
│                                     ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Orchestration Layer (编排层)                      │    │
│  │                                                                     │    │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │    │
│  │  │  TradingGraph   │──│     7 Nodes     │──│   TradingState  │     │    │
│  │  │   (LangGraph)   │  │ (工作流节点)     │  │   (状态管理)    │     │    │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                     │                                        │
│                                     ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         Agent Layer (分析层)                         │    │
│  │                                                                     │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │    │
│  │  │ TA_Analyst  │ │ Fund_Analyst│ │Chain_Analyst│ │ Macro_Expert│  │    │
│  │  │  (技术分析) │ │  (资金流)   │ │ (链上数据)  │ │  (宏观)     │  │    │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                     │                                        │
│                                     ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                       Execution Layer (执行层)                       │    │
│  │                                                                     │    │
│  │  ┌──────────────────────────────────────────────────────────────┐  │    │
│  │  │                    ExecutorAgent                              │  │    │
│  │  │  ┌─────────────────────────────────────────────────────────┐ │  │    │
│  │  │  │ 7 Tools: open_long, open_short, close_position, hold,  │ │  │    │
│  │  │  │          add_to_long, add_to_short, reduce_position    │ │  │    │
│  │  │  └─────────────────────────────────────────────────────────┘ │  │    │
│  │  │  ┌─────────────────────────────────────────────────────────┐ │  │    │
│  │  │  │ Safety: _validate_stop_loss, _get_available_margin,    │ │  │    │
│  │  │  │         MIN_ADD_AMOUNT=10, SAFETY_BUFFER=50             │ │  │    │
│  │  │  └─────────────────────────────────────────────────────────┘ │  │    │
│  │  └──────────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                     │                                        │
│                                     ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Trading Layer (交易层)                        │    │
│  │                                                                     │    │
│  │  ┌──────────────────────────┐    ┌──────────────────────────┐      │    │
│  │  │      PaperTrader         │    │       OKX API            │      │    │
│  │  │   (模拟交易/回测)        │    │   (实盘/模拟盘)          │      │    │
│  │  └──────────────────────────┘    └──────────────────────────┘      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                     │                                        │
│                                     ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Memory Layer (记忆层)                         │    │
│  │                                                                     │    │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐    │    │
│  │  │ ReflectionMemory │ │  AgentWeights    │ │ TradingDecision  │    │    │
│  │  │    (Redis)       │ │    (Redis)       │ │  Store (Redis)   │    │    │
│  │  └──────────────────┘ └──────────────────┘ └──────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 目录结构

```
backend/services/report_orchestrator/app/core/trading/
├── __init__.py
├── trading_meeting.py          # 主入口 (兼容旧版 + LangGraph)
├── executor_agent.py           # ⭐ 执行器 Agent (7 工具 + 安全逻辑)
├── executor.py                 # 旧版 TradeExecutor
│
├── trigger/                    # ⭐ 触发器系统 (三层架构)
│   ├── __init__.py
│   ├── fast_monitor.py        # 🆕 Layer 1: 硬条件检测 (无 LLM)
│   ├── agent.py               # Layer 2: TriggerAgent (LLM 驱动)
│   ├── scheduler.py           # TriggerScheduler (定时检查)
│   ├── lock.py                # TriggerLock (状态机)
│   ├── news_crawler.py        # 新闻抓取
│   ├── ta_calculator.py       # 技术指标计算
│   ├── scorer.py              # 规则评分器 (备用)
│   └── prompts.py             # LLM 提示词
│
├── orchestration/             # ⭐ LangGraph 编排
│   ├── __init__.py
│   ├── graph.py               # TradingGraph 主入口
│   ├── nodes.py               # 7 个工作流节点
│   └── state.py               # TradingState 定义
│
├── domain/                    # 领域模型
│   ├── unified_position.py    # 统一仓位模型
│   └── account.py             # 账户信息
│
├── safety/                    # 安全控制
│   └── guards.py              # SafetyGuard
│
└── reflection/                # 反思学习
    └── engine.py              # ReflectionEngine
```

---

# 第二部分：核心系统

## 交易决策流程

### 整体流程图

```
市场变化 → TriggerAgent 判断 → 触发分析?
                                   │ YES
                                   ▼
        ┌─────────────────────────────────────────┐
        │         LangGraph Workflow               │
        │                                          │
        │  market_analysis_node                    │
        │         ↓                                │
        │  signal_generation_node (Agents 投票)   │
        │         ↓                                │
        │  risk_assessment_node (安全检查)         │
        │         ↓                                │
        │  consensus_node (达成共识)               │
        │         ↓                                │
        │  execution_node → ExecutorAgent         │
        │         ↓                                │
        │  reflection_node (记录反思)              │
        └─────────────────────────────────────────┘
                   ↓
            交易信号生成 → PaperTrader/OKX 执行
```

### Agent 投票机制

每个分析 Agent 返回投票结果：

```python
{
    "agent_id": "technical_analyst",
    "direction": "long",      # long/short/hold
    "confidence": 75,         # 0-100
    "key_factors": ["RSI oversold", "Golden cross"],
    "reasoning": "技术面看涨..."
}
```

共识计算规则：

- 加权平均各 Agent 投票
- 动态权重基于历史准确率
- 信心度低于阈值则 HOLD

---

## 触发器系统 (TriggerAgent)

### 设计目标

避免在无变化的市场中频繁调用 LLM 分析，节省 API 成本。

### 三层触发器架构

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                     三层触发器架构                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Layer 1: FastMonitor (每 5 分钟，无 LLM 调用)                          │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  硬条件检测 - 纯规则计算，零 API 成本                               │ │
│  │  - 价格急涨急跌 (1m/5m/15m)                                        │ │
│  │  - 成交量异常放大                                                  │ │
│  │  - 资金费率极端/突变                                               │ │
│  │  - 持仓量异常变化                                                  │ │
│  │  - RSI 极端超买/超卖                                               │ │
│  │  - EMA 价格偏离                                                    │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                            │ 任一条件触发                               │
│                            ▼                                            │
│  Layer 2: TriggerAgent (条件触发时，LLM 分析)                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  LLM 深度分析                                                      │ │
│  │  - 综合新闻 + 技术指标                                             │ │
│  │  - 考虑当前仓位状态                                                │ │
│  │  - 输出 should_trigger + confidence                                │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                            │ should_trigger=True && confidence>60       │
│                            ▼                                            │
│  Layer 3: Full Analysis (完整多 Agent 分析)                             │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  5 Agent 投票 → Leader 共识 → ExecutorAgent 执行                   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 组件说明

| 组件 | 职责 |
|------|------|
| `FastMonitor` | Layer 1: 硬条件检测，无 LLM 调用 |
| `TriggerAgent` | Layer 2: LLM 分析是否应该触发主分析 |
| `TriggerScheduler` | 每 5 分钟执行定时检查 |
| `TriggerLock` | 状态机，防止并发触发和主分析冲突 |
| `NewsCrawler` | 抓取加密货币相关新闻 |
| `TACalculator` | 计算 RSI、MACD、成交量等技术指标 |

### FastMonitor 硬条件指标 (6 类)

| 指标 | 阈值 | 紧急度 | OKX API |
|------|------|--------|---------|
| 价格急变 (1m) | ±1.5% | high | `/market/candles` |
| 价格急变 (5m) | ±2.5% | high | `/market/candles` |
| 价格急变 (15m) | ±4.0% | critical | `/market/candles` |
| 成交量异常 (1m) | >5x 均值 | high | `/market/candles` |
| 成交量异常 (5m) | >3x 均值 | medium | `/market/candles` |
| 资金费率极端 | >0.1% | high | `/public/funding-rate` |
| 资金费率突变 | >0.05% | medium | `/public/funding-rate` |
| 持仓量变化 | >3% (15min) | medium | `/public/open-interest` |
| RSI 超买 | >85 | medium | 计算自 K 线 |
| RSI 超卖 | <15 | medium | 计算自 K 线 |
| EMA 偏离 | >5% vs EMA20 | medium | 计算自 K 线 |

### 状态机 (TriggerLock)

```
                    ┌─────────┐
                    │  idle   │ ← 初始状态
                    └────┬────┘
                         │ acquire() 触发检查
                         ▼
                    ┌─────────┐
                    │checking │ ← TriggerAgent 运行中
                    └────┬────┘
                         │ release_check()
         ┌───────────────┼───────────────┐
         │               │               │
    should_trigger   not_trigger    error
         │               │               │
         ▼               ▼               ▼
    ┌─────────┐    ┌──────────┐    ┌─────────┐
    │analyzing│    │ cooldown │    │  idle   │
    └────┬────┘    └────┬─────┘    └─────────┘
         │              │ (5 分钟后过期)
         │              ▼
         │         ┌─────────┐
         └────────►│  idle   │
   release()       └─────────┘
```

### 仓位感知能力

TriggerAgent 可以感知当前仓位状态：

```python
# TriggerContext 新增字段
has_position: bool = False
position_direction: str = "none"
position_pnl_percent: float = 0.0
position_size_usd: float = 0.0
```

这使 TriggerAgent 可以做出仓位相关决策：

- 持仓浮亏 >10%? → 可能需要止损分析
- 持仓浮盈 >15%? → 考虑是否锁定利润

### 成本节省效果

| 场景 | 原架构 | 三层架构 |
|------|--------|----------|
| 市场平静 | 每次调用 LLM | 仅 FastMonitor (0 API 调用) |
| 轻微波动 | 调用 LLM | FastMonitor + TriggerAgent |
| 剧烈波动 | 调用完整分析 | 3 层全部执行 |
| 预估节省 | - | 60-80% LLM 调用 |

---

## 执行系统 (ExecutorAgent)

### 7 个交易工具

| 工具 | 用途 | 直接调用 |
|------|------|----------|
| `open_long` | 开多仓 (含反向逻辑) | ✅ paper_trader.open_long() |
| `open_short` | 开空仓 (含反向逻辑) | ✅ paper_trader.open_short() |
| `hold` | 观望不操作 | 无交易调用 |
| `close_position` | 完全平仓 | ✅ paper_trader.close_position() |
| `add_to_long` | 加多仓 | ✅ paper_trader.open_long() (小仓) |
| `add_to_short` | 加空仓 | ✅ paper_trader.open_short() (小仓) |
| `reduce_position` | 部分平仓 | ✅ paper_trader.close_position(partial) |

### 场景逻辑 (open_long 示例)

```
LLM 决定 LONG
     │
     ▼
当前仓位检查
     │
     ├─── 已持有 LONG ──→ 加仓或维持
     │
     ├─── 已持有 SHORT ──→ 先平空，再开多 (反向操作)
     │
     └─── 无仓位 ──→ 新开多仓
```

### 安全机制

```python
# 安全常量
MIN_ADD_AMOUNT = 10.0   # 最小加仓金额 (USDT)
SAFETY_BUFFER = 50.0    # 保证金安全缓冲 (USDT)

# 安全方法
_get_position_info()      # 获取当前仓位
_get_available_margin()   # 真实可用保证金 (含未实现盈亏)
_validate_stop_loss()     # 验证止损价格不低于爆仓价格
```

### 止损验证逻辑

```python
def _validate_stop_loss(direction, entry_price, sl_price, leverage, margin):
    """
    确保止损触发在爆仓之前
    爆仓条件: 亏损达到保证金的 80%
    """
    liquidation_loss = margin * 0.8
    size = (margin * leverage) / entry_price
    
    if direction == "long":
        liquidation_price = entry_price - (liquidation_loss / size)
        if sl_price <= liquidation_price:
            safe_sl = liquidation_price * 1.05  # 5% 安全边际
            return False, f"SL below liquidation", safe_sl
    # ...
```

---

## 资金费率感知系统 (Funding Fee System)

### 设计目标

传统交易系统往往忽视资金费率（Funding Fee）的影响，导致长期持仓成本过高。本系统引入完整的资金费率感知模块：

1. **规避高昂成本**: 自动识别并规避需要支付高额资金费的时段
2. **捕捉套利机会**: 识别负费率机会，通过持仓"躺赚"费率
3. **防止利润侵蚀**: 实时监控资金费对利润的侵蚀比例，必要时强制平仓

### 核心组件

| 组件 | 职责 |
|------|------|
| `FundingDataService` | 对接 OKX API，获取实时费率、下一次结算时间、历史平均值 |
| `FundingCostCalculator` | 计算持有成本、盈亏平衡点、交易可行性 |
| `EntryTimingController` | **入场时机优化**：建议"立即入场"还是"等待结算后入场" |
| `HoldingTimeManager` | **动态久期管理**：基于费率高低，动态计算建议的最大持仓时间 |
| `FundingImpactMonitor` | **实时监控与强平**：后台任务，监控资金费/利润占比，触发风控 |

### 关键策略逻辑

#### 1. 智能入场 (Entry Timing)

- **支付方 (Paying)**: 如果距离结算 < 30分钟，且费率较高，系统会建议 **延迟入场** (Delay)，等待结算完成后再开仓，节省一次费用
- **收取方 (Receiving)**: 如果距离结算 < 30分钟，系统会建议 **立即入场** (Enter Now)，以捕获即将到来的费率收入

#### 2. 动态持仓限制 (Dynamic Holding Limit)

系统不再使用固定的持仓时间限制，而是基于费率动态计算 `optimal_holding_hours`：

- **公式**: `最大持仓时间 = (预期利润 * 允许损耗比) / 单位时间费率成本`
- **效果**: 费率越高，允许持仓的时间越短，迫使 Agent 追求资本效率

#### 3. 利润保护与强平 (Force Close)

- **监控指标**: `费率影响比 (Impact %)` = `累计已付资金费` / `当前未实现利润`
- **阈值逻辑**:
  - **Impact > 30%**: 发出 WARNING 警告
  - **Impact > 50%**: 触发 **CRITICAL 强制平仓**

### Agent 整合

资金费率信息被直接注入到 `ExecutorAgent` 的 Prompt 中：

- **⚠️ CRITICAL 警告**: 明确告知当前是支付方还是收取方
- **成本预估表**: 展示持仓 8h/24h 的预计绝对成本
- **盈亏平衡点**: 告知价格需要跑赢多少才能覆盖费率
- **时机建议**: 明确建议 "Wait for settlement" 或 "Enter now"

---

## LangGraph 工作流

### 7 个节点

```python
workflow_nodes = [
    "market_analysis_node",    # 市场数据收集
    "signal_generation_node",  # Agent 投票
    "risk_assessment_node",    # 风险评估
    "consensus_node",          # 共识达成
    "execution_node",          # 执行交易 (ExecutorAgent)
    "reflection_node",         # 反思记录
    "react_fallback_node"      # 错误恢复
]
```

### 条件边

```python
# 是否执行交易
def should_execute_or_fallback(state):
    if state.get("error"):
        return "react_fallback"
    return "execution"

# 是否进行反思
def should_reflect(state):
    signal = state.get("final_signal", {})
    if signal.get("direction") in ["long", "short"]:
        return "reflection"
    return END
```

### TradingState 结构

```python
class TradingState(TypedDict):
    # 输入
    position_context: Dict[str, Any]
    market_snapshot: Dict[str, Any]
    
    # 中间状态
    agent_votes: List[Dict]
    leader_summary: str
    risk_assessment: Dict
    
    # 输出
    final_signal: Dict
    execution_success: bool
    
    # 元数据
    current_node: str
    completed_nodes: List[str]
    node_timings: Dict[str, float]
    error: Optional[str]
```

---

# 第三部分：交易模式

## 人在环路模式设计 (Human-in-the-Loop)

系统支持三种交易模式，满足不同用户的风险偏好和参与程度。

### 模式对比总览

| 特性 | 全自动 | 半自动 | 手动 |
|------|--------|--------|------|
| 自动开仓 | ✅ | ❌ 需确认 | ❌ |
| 自动平仓 | ✅ | ❌ 需确认 | ❌ |
| 分析报告 | ✅ | ✅ | ✅ |
| 交易建议 | ✅ 直接执行 | ✅ 待确认 | ✅ 仅供参考 |
| 风险等级 | 高 | 中 | 低 |
| 参与程度 | 无需参与 | 审批确认 | 完全参与 |
| 适合用户 | 量化交易者 | 有经验交易者 | 学习者/保守型 |

---

### 模式 1: 全自动模式 (Full Auto)

**特点**: 完全托管给系统，无需人工干预

| 功能 | 行为 |
|------|------|
| 触发分析 | ✅ 自动 (TriggerAgent) |
| 开仓决策 | ✅ 自动 (ExecutorAgent) |
| 仓位管理 | ✅ 自动 (加仓/减仓/止损) |
| 平仓执行 | ✅ 自动 (触发 TP/SL 或信号反转) |
| 用户干预 | ❌ 无需 |

**适用场景**: 高信任度用户、小资金试水、长期策略验证

```python
# 配置示例
TRADING_MODE = "full_auto"
REQUIRE_CONFIRMATION = False
AUTO_EXECUTE_TRADES = True
```

---

### 模式 2: 半自动模式 (Semi-Auto)

**特点**: 系统提供建议，用户确认或修改后执行

| 功能 | 行为 |
|------|------|
| 触发分析 | ✅ 自动 |
| 开仓决策 | ⚠️ 系统建议 → 用户确认/修改 |
| 仓位管理 | ⚠️ 系统建议 → 用户确认 |
| 平仓执行 | ⚠️ 系统建议 → 用户确认 |
| 用户干预 | ✅ 最终审批权 |

**交互流程**:

```
系统分析完成
     ↓
生成交易建议 (方向/杠杆/止盈止损)
     ↓
推送通知给用户 (Telegram/WebSocket/App)
     ↓
用户操作:
  ├── ✅ 确认执行 → 系统下单
  ├── ✏️ 修改参数 → 系统按修改后参数下单
  ├── ❌ 拒绝 → 不执行
  └── ⏰ 超时 (可配置) → 自动取消或自动执行
```

**配置选项**:

```python
TRADING_MODE = "semi_auto"
REQUIRE_CONFIRMATION = True
CONFIRMATION_TIMEOUT_SECONDS = 300  # 5分钟超时
TIMEOUT_ACTION = "cancel"  # cancel / auto_execute
NOTIFICATION_CHANNELS = ["telegram", "websocket"]
```

**UI 交互示例**:

```json
{
  "signal_id": "sig_20260103_001",
  "type": "trade_suggestion",
  "suggestion": {
    "direction": "long",
    "leverage": 5,
    "amount_percent": 20,
    "tp_percent": 8.0,
    "sl_percent": 3.0,
    "confidence": 78
  },
  "reasoning": "技术面RSI超卖+资金费率为负，看涨信号明确",
  "actions": ["confirm", "modify", "reject"],
  "expires_at": "2026-01-03T17:05:00Z"
}
```

---

### 模式 3: 手动模式 (Manual)

**特点**: 用户完全自主交易，系统仅提供分析和建议

| 功能 | 行为 |
|------|------|
| 触发分析 | ✅ 自动 (或用户手动触发) |
| 分析报告 | ✅ 自动生成并推送 |
| 开仓决策 | ❌ 用户自行操作 |
| 仓位管理 | ❌ 用户自行操作 |
| 平仓执行 | ❌ 用户自行操作 |
| 用户干预 | ✅ 完全控制 |

**系统提供**:

- 📊 实时市场分析报告
- 📈 技术指标和趋势预测
- 🗳️ 多 Agent 投票结果和共识
- ⚠️ 风险提示和建议止损位
- 📰 重大新闻和市场事件提醒

```python
TRADING_MODE = "manual"
AUTO_EXECUTE_TRADES = False
PUSH_ANALYSIS_REPORTS = True
ANALYSIS_PUSH_CHANNELS = ["telegram", "email", "websocket"]
```

---

### 实现架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Trading Mode Manager                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Signal Generation (通用)                │    │
│  │  TriggerAgent → LangGraph → Agent投票 → 共识建议     │    │
│  └─────────────────────────────────────────────────────┘    │
│                            │                                 │
│                            ▼                                 │
│  ┌────────────┬────────────┬────────────────────────────┐   │
│  │  Full Auto │ Semi-Auto  │         Manual             │   │
│  │            │            │                            │   │
│  │ ExecutorAgent           │                            │   │
│  │ 直接执行   │ 推送建议   │         推送报告           │   │
│  │            │     ↓      │                            │   │
│  │            │ 等待用户   │                            │   │
│  │            │ 确认/修改  │                            │   │
│  │            │     ↓      │                            │   │
│  │            │ 执行交易   │         用户自行交易       │   │
│  └────────────┴────────────┴────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

# 第四部分：开发与部署

## 快速开始指南

### 本地开发

```bash
# 1. 启动依赖服务
docker-compose up -d redis postgres llm_gateway

# 2. 运行交易服务
cd backend/services/report_orchestrator
uvicorn app.main:app --reload --port 8000

# 3. 启动前端 (可选)
cd frontend
npm run dev
```

### 配置文件

```bash
# .env 关键配置
OKX_API_KEY=xxx
OKX_SECRET_KEY=xxx
OKX_PASSPHRASE=xxx
OKX_IS_DEMO=true          # true=模拟盘, false=实盘

TRIGGER_CHECK_INTERVAL=300        # 触发器检查间隔 (秒)
TRIGGER_CONFIDENCE_THRESHOLD=60   # 触发器信心阈值

REDIS_HOST=localhost
LLM_GATEWAY_URL=http://localhost:8003
```

### API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/trading/status` | GET | 获取系统状态 |
| `/api/trading/start` | POST | 启动交易系统 |
| `/api/trading/stop` | POST | 停止交易系统 |
| `/api/trading/history` | GET | 获取交易历史 |
| `/ws/trading/{session_id}` | WS | 实时交易推送 |

---

## 生产环境部署指南

### 模拟盘 vs 实盘

| 模式 | OKX_DEMO_MODE | 说明 |
|------|---------------|------|
| 模拟盘 | `true` | 使用 OKX 模拟交易 API，无真实资金风险 |
| 实盘 | `false` | 使用 OKX 真实交易 API，真金白银 |

### 切换到正式环境

#### 1. 修改 `.env` 配置

```bash
# OKX 正式环境 API (⚠️ 使用正式 API Key，不是模拟盘的)
OKX_API_KEY=你的正式环境API_KEY
OKX_SECRET_KEY=你的正式环境SECRET_KEY
OKX_PASSPHRASE=你的正式环境PASSPHRASE

# ⚠️ 关键配置：必须设为 false
OKX_DEMO_MODE=false
```

#### 2. 重新构建并部署

```bash
cd trading-standalone
git pull origin dev
./stop.sh && docker compose up -d --build
```

#### 3. 验证正式环境

```bash
# 检查日志确认是 REAL 模式
docker logs trading-service 2>&1 | grep -E "REAL|demo"

# 应该看到:
# OKX REAL account balance: $XXXX.XX
```

### 多服务器部署

如果同时运行模拟盘和实盘，确保：

1. **使用不同的服务器或端口**
2. **每个服务器的 `.env` 配置独立**
3. **前端使用动态主机检测**（已在 `status.html` 中实现）

---

# 第五部分：演进与规划

## 重构变更记录

### v2.0 → v3.0 主要变更

| 变更项 | v2.0 (旧) | v3.0 (新) |
|--------|----------|----------|
| **编排方式** | trading_meeting.py 单文件 | LangGraph 工作流 |
| **执行器** | TradeExecutor (信号生成) | ExecutorAgent (直接交易) |
| **触发器** | 定时轮询 | TriggerAgent + LLM 分析 |
| **仓位管理** | open_long_tool 内部场景 | 7 个独立工具 |
| **代码行数** | ~4,000 行单文件 | 模块化分布 |

### 移除的能力

| 能力 | 原实现 | 状态 | 替代方案 |
|------|--------|------|----------|
| **Embedding 搜索** | Chroma 向量库 | ❌ 已移除 | 直接 API 搜索 |
| **RAG 知识库** | embedding + 检索 | ❌ 已移除 | 无 |
| **语义相似搜索** | 向量相似度 | ❌ 已移除 | 关键词匹配 |

### 保留的能力

| 能力 | 状态 | 说明 |
|------|------|------|
| 止损验证 | ✅ 完整 | `_validate_stop_loss()` |
| 保证金管理 | ✅ 完整 | `_get_available_margin()` 含未实现盈亏 |
| 反向操作 | ✅ 完整 | open_long/short 自动处理 |
| 加仓减仓 | ✅ 完整 | add_to_long/short, reduce_position |
| Agent 权重 | ✅ 完整 | 动态调整 |
| 反思学习 | ✅ 完整 | ReflectionEngine |

---

## 改进建议与未来规划

### ⚡ P0 优先级: Agent 并行执行 (下一阶段重点)

**当前问题**:

- `signal_generation_node` 使用占位符投票
- Agents 顺序执行，总时间 = Σ(各Agent时间)
- 实际并行注释: "In real implementation, call agents here"

**改进方案**:

```python
# 改进后的 signal_generation_node
async def signal_generation_node(state: TradingState) -> Dict[str, Any]:
    """并行执行所有分析 Agents"""
    agent_configs = [
        ("technical_analyst", TAConfig),
        ("fundamental_analyst", FundConfig),
        ("onchain_analyst", ChainConfig),
        ("macro_analyst", MacroConfig),
        ("sentiment_analyst", SentimentConfig),
    ]
    
    # 并行创建和执行所有 Agents
    tasks = []
    for agent_id, config in agent_configs:
        agent = create_agent(agent_id, config)
        tasks.append(agent.analyze(state.get("market_data")))
    
    # 等待所有 Agents 完成
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 收集有效投票
    votes = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Agent failed: {result}")
        else:
            votes.append(result)
    
    return {"agent_votes": votes}
```

**预期收益**:

- 5 个 Agents × 10s 每个 → 从 50s 降到 ~15s
- 更快的交易决策响应
- 更好的市场机会捕捉

**实现步骤**:

1. 将 Agent 初始化移到 LangGraph 外部
2. 在 `signal_generation_node` 使用 `asyncio.gather()`
3. 添加超时控制 (单 Agent timeout 30s)
4. 添加错误隔离 (单 Agent 失败不影响其他)

---

### 短期规划 (1-2 周)

| 任务 | 优先级 | 说明 |
|------|--------|------|
| **Agent 并行执行** | P0 | asyncio.gather 并发调用 |
| 集成测试 | P1 | 端到端测试 LangGraph 工作流 |
| 超时处理 | P1 | 单 Agent 超时不阻塞整体 |
| 日志增强 | P2 | 结构化日志 + 追踪 ID |

### 中期规划 (1-2 月)

| 任务 | 优先级 | 说明 |
|------|--------|------|
| ATR 动态止损 | P1 | 基于波动率调整止损距离 |
| 多时间框架分析 | P2 | 1h + 4h + 1d 综合判断 |
| 事件驱动触发 | P2 | 监听链上大额转账 |
| Agent 权重自学习 | P2 | 基于历史表现自动调整 |

### 长期规划 (3-6 月)

| 任务 | 优先级 | 说明 |
|------|--------|------|
| **人在环路模式** | P1 | 实现三种交易模式切换 |
| 策略框架 | P2 | 可配置的交易策略模板 |
| 风控仪表板 | P3 | 可视化监控面板 |

---

## 未实现与移除的能力

### 1. Embedding/RAG 搜索 (已移除)

**原因**: 维护成本高，效果不明显

**影响**:

- 无法进行语义相似搜索
- 历史分析报告无法作为知识库

**替代方案**:

- 使用 Perplexity API 实时搜索
- 关键词匹配历史记录

### 2. 多交易对支持 (未实现)

**当前**: 仅支持 BTC-USDT-SWAP

**扩展方向**:

- 添加 ETH-USDT-SWAP
- symbol 参数化

### 3. 自动止盈止损调整 (部分实现)

**当前**: 使用固定百分比 (TP 8%, SL 3%)

**改进方向**:

- 基于 ATR 动态计算
- 移动止损 (trailing stop)

---

# 第六部分：附录

## Bug 修复记录 (2026-01)

### 🔧 OKX Demo Mode 环境变量无效 (2026-01-06)

**问题**：设置 `OKX_DEMO_MODE=false` 后，系统仍然连接模拟盘。

**根因**：`okx_client.py` 中 `__init__` 的默认参数 `demo_mode=True` 导致环境变量被忽略。

```python
# 修复前 (Bug)
def __init__(self, demo_mode: bool = True):
    self.demo_mode = demo_mode or os.getenv("OKX_DEMO_MODE", "true")
    # demo_mode=True，所以 True or ... = True

# 修复后
def __init__(self, demo_mode: Optional[bool] = None):
    if demo_mode is None:
        self.demo_mode = os.getenv("OKX_DEMO_MODE", "true").lower() == "true"
    else:
        self.demo_mode = demo_mode
```

**相关文件**：`backend/services/report_orchestrator/app/core/trading/okx_client.py`

---

### 🔧 Insufficient Margin 误报 (2026-01-06)

**问题**：交易实际成功执行，但信号的 reasoning 显示 `[insufficient_margin]`。

**根因**：系统有**双重执行路径**：

1. `ExecutorAgent` 先执行，调用 `_get_available_margin()` 返回 0（因为使用了 paper_trader）
2. `trading_routes.py` 后执行，用 `OKXTrader` 成功开仓
3. 但 reasoning 来自 ExecutorAgent 的错误标签

**修复**：在 `trading_routes.py` 中，优先使用 OKX `order_id` 作为成功的确定性证据：

```python
# 如果有 OKX order_id，交易一定成功了
if order_id and trade_success:
    trade_actually_executed = True
    # 修复错误的 reasoning tag
    if signal and "[insufficient_margin]" in signal.reasoning:
        signal.reasoning = signal.reasoning.replace("[insufficient_margin]", "[new_long]")
```

**相关文件**：`backend/services/report_orchestrator/app/api/trading_routes.py`

---

### 🔧 前端 Dashboard 服务器 URL 硬编码 (2026-01-06)

**问题**：访问不同服务器的 Dashboard 时，数据都来自同一个服务器。

**根因**：`status.html` 中硬编码了服务器 IP：

```javascript
// 修复前 (Bug)
const SERVER = 'http://45.76.159.149:9000';

// 修复后
const SERVER = `http://${window.location.hostname}:9000`;
```

**相关文件**：`trading-standalone/status.html`

---

### 🔧 保证金计算使用错误数据源 (2026-01-05)

**问题**：`_get_available_margin()` 返回 0，导致所有交易被标记为 insufficient_margin。

**根因**：函数使用 `self.paper_trader.get_status()` 但 paper_trader 未正确配置。

**修复**：优先使用 OKX 的 `max_avail_size`：

```python
max_avail = status.get("max_avail_size", 0)  # OKX API 返回的真实可用保证金
if max_avail > 0:
    true_available = max_avail
else:
    true_available = available + max(unrealized_pnl, 0)
```

**相关文件**：`backend/services/report_orchestrator/app/core/trading/executor_agent.py`

---

## 常见问题排查

### Q1: 交易成功但状态显示 "failed"

**检查**：

1. 查看日志中的 `order_id`，如果存在说明交易成功
2. 检查 reasoning 是否有 `[insufficient_margin]` 等错误标签
3. 确认已部署最新代码

### Q2: OKX 连接失败

**检查**：

1. API Key 权限是否包含 Trade
2. IP 白名单是否配置正确
3. `OKX_DEMO_MODE` 与 API Key 类型是否匹配

```bash
# 测试 OKX 连接
docker exec trading-service python3 -c "
import asyncio
from app.core.trading.okx_client import OKXClient

async def test():
    client = OKXClient()
    await client.initialize()
    balance = await client.get_account_balance()
    print(f'Demo Mode: {client.demo_mode}')
    print(f'Balance: \${balance.total_equity:.2f}')
    await client.close()

asyncio.run(test())
"
```

### Q3: 前端显示其他服务器的数据

**解决**：

1. 强制刷新浏览器 (Cmd+Shift+R)
2. 确认访问的 URL 是正确的服务器 IP
3. 检查 `status.html` 是否使用了动态主机检测

### Q4: 日志中看不到 ExecutorAgent 信息

**检查**：

1. Docker 镜像是否重新构建 (`docker compose up -d --build`)
2. 检查容器内代码版本

```bash
docker exec trading-service cat /app/app/core/trading/executor_agent.py | head -20
```

---

## 附录：配置与规范

### A. 代码规范

- 所有交易相关代码使用 `async/await`
- 日志格式: `[ModuleName] emoji 消息`
- 错误处理: 捕获并记录，返回默认安全值

### B. 相关文档

- [ARCHITECTURE.md](/docs/refactoring/ARCHITECTURE.md) - 模块架构
- [DEPLOY.md](/docs/refactoring/DEPLOY.md) - 部署指南
- [REFACTORING_PLAN.md](/docs/refactoring/REFACTORING_PLAN.md) - 重构计划

### C. 环境变量完整列表

```bash
# OKX API 配置
OKX_API_KEY=                    # API Key
OKX_SECRET_KEY=                 # Secret Key
OKX_PASSPHRASE=                 # Passphrase
OKX_DEMO_MODE=true              # true=模拟盘, false=实盘

# 交易参数
DEFAULT_LEVERAGE=5              # 默认杠杆
MAX_LEVERAGE=20                 # 最大杠杆
DEFAULT_POSITION_PERCENT=20     # 默认仓位比例 (%)
MIN_POSITION_PERCENT=10         # 最小仓位比例 (%)
MAX_POSITION_PERCENT=30         # 最大仓位比例 (%)
DEFAULT_TP_PERCENT=8            # 默认止盈 (%)
DEFAULT_SL_PERCENT=3            # 默认止损 (%)

# 触发器配置
TRIGGER_INTERVAL_SECONDS=300    # 检查间隔 (秒)
TRIGGER_COOLDOWN_MINUTES=30     # 冷却时间 (分钟)
FAST_MONITOR_ENABLED=true       # 快速监控开关

# LLM 配置
GOOGLE_API_KEY=                 # Gemini API Key
DEEPSEEK_API_KEY=               # DeepSeek API Key

# 服务配置
REDIS_HOST=redis                # Redis 主机
LLM_GATEWAY_URL=http://llm_gateway:8003
```

### D. 联系方式

如有问题，请联系项目维护者或提交 Issue。

---

*最后更新: 2026-01-06 by Antigravity AI Assistant*
