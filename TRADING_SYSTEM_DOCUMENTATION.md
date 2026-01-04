# Magellan Trading System - 完整架构与能力文档 v3.0

> **文档更新日期**: 2026-01-03
> **适用版本**: dev 分支 (LangGraph + ExecutorAgent 增强版)

## 📋 目录

1. [系统概述](#系统概述)
2. [技术架构](#技术架构)
3. [交易系统详解](#交易系统详解)
4. [触发器系统 (TriggerAgent)](#触发器系统-triggeragent)
5. [执行系统 (ExecutorAgent)](#执行系统-executoragent)
6. [LangGraph 工作流](#langgraph-工作流)
7. [重构变更记录](#重构变更记录)
8. [未实现与移除的能力](#未实现与移除的能力)
9. [改进建议与未来规划](#改进建议与未来规划)
10. [快速开始指南](#快速开始指南)

---

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

---

## 技术架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Magellan Trading System v3.0                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                       Trigger Layer (触发层)                         │    │
│  │                                                                     │    │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │    │
│  │  │TriggerScheduler│ │ TriggerAgent │ │ NewsCrawler │ │TACalculator│ │    │
│  │  │  (定时检查)   │ │  (LLM分析)   │ │  (新闻抓取) │ │ (技术指标) │ │    │
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

### 目录结构

```
backend/services/report_orchestrator/app/core/trading/
├── __init__.py
├── trading_meeting.py          # 主入口 (兼容旧版 + LangGraph)
├── executor_agent.py           # ⭐ 执行器 Agent (7 工具 + 安全逻辑)
├── executor.py                 # 旧版 TradeExecutor
│
├── trigger/                    # ⭐ 触发器系统 (新增)
│   ├── __init__.py
│   ├── agent.py               # TriggerAgent (LLM 驱动)
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

## 交易系统详解

### 交易决策流程

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

### 组件说明

| 组件 | 职责 |
|------|------|
| `TriggerScheduler` | 每 5 分钟执行定时检查 |
| `TriggerAgent` | 使用 LLM 分析是否应该触发主分析 |
| `TriggerLock` | 状态机，防止并发触发和主分析冲突 |
| `NewsCrawler` | 抓取加密货币相关新闻 |
| `TACalculator` | 计算 RSI、MACD、成交量等技术指标 |

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

TriggerAgent 现在可以感知当前仓位状态：

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

## 改进建议与未来规划

### ⚡ 优先级 P0: Agent 并行执行 (下一阶段重点)

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

### 短期 (1-2 周)

| 任务 | 优先级 | 说明 |
|------|--------|------|
| **Agent 并行执行** | P0 | asyncio.gather 并发调用 |
| 集成测试 | P1 | 端到端测试 LangGraph 工作流 |
| 超时处理 | P1 | 单 Agent 超时不阻塞整体 |
| 日志增强 | P2 | 结构化日志 + 追踪 ID |

### 中期 (1-2 月)

| 任务 | 优先级 | 说明 |
|------|--------|------|
| ATR 动态止损 | P1 | 基于波动率调整止损距离 |
| 多时间框架分析 | P2 | 1h + 4h + 1d 综合判断 |
| 事件驱动触发 | P2 | 监听链上大额转账 |
| Agent 权重自学习 | P2 | 基于历史表现自动调整 |

### 🎛️ 人在环路 (Human-in-the-Loop) 模式设计

系统支持三种交易模式，满足不同用户的风险偏好和参与程度：

#### 模式 1: 全自动模式 (Full Auto)

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

#### 模式 2: 半自动模式 (Semi-Auto)

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
# 配置示例
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

#### 模式 3: 手动模式 (Manual)

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
# 配置示例
TRADING_MODE = "manual"
AUTO_EXECUTE_TRADES = False
PUSH_ANALYSIS_REPORTS = True
ANALYSIS_PUSH_CHANNELS = ["telegram", "email", "websocket"]
```

---

#### 模式对比

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

#### 实现架构

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

### 长期 (3-6 月)

| 任务 | 优先级 | 说明 |
|------|--------|------|
| 多交易对支持 | P1 | ETH, BNB 等主流币 |
| 策略框架 | P2 | 可配置的交易策略模板 |
| 回测系统 | P2 | 历史数据回测验证 |
| 风控仪表板 | P3 | 可视化监控面板 |
| **人在环路模式** | P1 | 实现三种交易模式切换 |

---

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

## 附录

### A. 代码规范

- 所有交易相关代码使用 `async/await`
- 日志格式: `[ModuleName] emoji 消息`
- 错误处理: 捕获并记录，返回默认安全值

### B. 相关文档

- [ARCHITECTURE.md](/docs/refactoring/ARCHITECTURE.md) - 模块架构
- [DEPLOY.md](/docs/refactoring/DEPLOY.md) - 部署指南
- [REFACTORING_PLAN.md](/docs/refactoring/REFACTORING_PLAN.md) - 重构计划

### C. 联系方式

如有问题，请联系项目维护者或提交 Issue。

---

*最后更新: 2026-01-03 by Antigravity AI Assistant*
