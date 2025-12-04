# Magellan Trading Standalone - 技术文档

> 完整的自动交易系统技术文档，为后续开发者提供全面的项目理解

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [核心组件详解](#3-核心组件详解)
4. [多Agent交易系统](#4-多agent交易系统)
5. [交易流程](#5-交易流程)
6. [API接口](#6-api接口)
7. [配置系统](#7-配置系统)
8. [部署指南](#8-部署指南)
9. [监控与日志](#9-监控与日志)
10. [已知问题与解决方案](#10-已知问题与解决方案)
11. [开发指南](#11-开发指南)
12. [代码文件索引](#12-代码文件索引)

---

## 1. 项目概述

### 1.1 项目定位

Magellan Trading Standalone 是一个轻量级的自动交易部署项目，从主项目 Magellan 中提取交易相关功能，专为服务器后台运行设计。

**核心特点：**
- 多Agent协作的AI交易决策系统
- 支持模拟交易(Paper Trading)和实盘交易(OKX)
- 完全基于Docker部署，资源占用约1.5GB
- 定时自动分析 + 手动触发分析
- Web Dashboard实时监控

### 1.2 项目结构

```
trading-standalone/
├── docker-compose.yml      # Docker服务编排
├── config.yaml             # 交易配置文件
├── .env                    # 环境变量(API Keys)
├── status.html             # Web Dashboard前端
├── start.sh                # 启动脚本
├── stop.sh                 # 停止脚本
├── status.sh               # 状态查询脚本
├── logs.sh                 # 日志查看脚本
├── view-agents.sh          # Agent讨论查看器(推荐)
├── view-logs.sh            # 完整日志查看器
├── test_api.sh             # API测试脚本
├── deploy_dashboard.sh     # Dashboard部署脚本
└── README.md               # 快速入门指南
```

### 1.3 与主项目的关系

Trading Standalone 是 Magellan 主项目的子集部署：

- **代码复用**: 使用主项目 `backend/services/report_orchestrator` 镜像
- **配置独立**: 通过 `config.yaml` 和环境变量覆盖默认配置
- **功能精简**: 仅启用交易相关API，其他功能(DD分析、报告生成)不激活

```
Magellan (主项目)
└── backend/services/
    ├── report_orchestrator/    <- Trading Standalone 使用这个服务
    │   └── app/core/trading/   <- 交易核心代码
    ├── llm_gateway/            <- LLM统一网关
    └── web_search_service/     <- MCP搜索服务
```

---

## 2. 系统架构

### 2.1 服务架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Trading Standalone System                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────┐   ┌──────────────────────────┐           │
│  │   Web Dashboard (8888)   │   │      Redis (6379)        │           │
│  │   ├─ status.html         │   │   ├─ 账户状态存储        │           │
│  │   ├─ 实时状态监控        │   │   ├─ 持仓信息            │           │
│  │   └─ 交易历史展示        │   │   ├─ 交易历史            │           │
│  └───────────┬──────────────┘   │   └─ 净值曲线            │           │
│              │                  └────────────┬─────────────┘           │
│              │                               │                         │
│              ▼                               ▼                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                  Trading Service (8000)                         │   │
│  │   report_orchestrator镜像，运行在STANDALONE_MODE=true模式       │   │
│  │                                                                 │   │
│  │  ┌──────────────────────────────────────────────────────────┐  │   │
│  │  │                    Trading Meeting                        │  │   │
│  │  │         (app/core/trading/trading_meeting.py)             │  │   │
│  │  │                                                           │  │   │
│  │  │   Phase 1: Market Analysis                                │  │   │
│  │  │   ┌──────────┐ ┌──────────┐ ┌──────────┐                 │  │   │
│  │  │   │Technical │ │Macro     │ │Sentiment │                 │  │   │
│  │  │   │Analyst   │ │Economist │ │Analyst   │                 │  │   │
│  │  │   └────┬─────┘ └────┬─────┘ └────┬─────┘                 │  │   │
│  │  │        │            │            │                        │  │   │
│  │  │   Phase 2: Signal Generation (投票)                       │  │   │
│  │  │        │            │            │                        │  │   │
│  │  │        ▼            ▼            ▼                        │  │   │
│  │  │   ┌──────────┐ ┌──────────┐ ┌──────────┐                 │  │   │
│  │  │   │Quant     │ │上述3个   │ │          │                 │  │   │
│  │  │   │Strategist│ │Agent     │ │          │                 │  │   │
│  │  │   └────┬─────┘ └────┬─────┘ └──────────┘                 │  │   │
│  │  │        │            │                                     │  │   │
│  │  │   Phase 3: Risk Assessment                                │  │   │
│  │  │        └─────┬──────┘                                     │  │   │
│  │  │              ▼                                            │  │   │
│  │  │   ┌──────────────────┐                                   │  │   │
│  │  │   │  RiskAssessor    │                                   │  │   │
│  │  │   │  风险评估/审批    │                                   │  │   │
│  │  │   └────────┬─────────┘                                   │  │   │
│  │  │            │                                              │  │   │
│  │  │   Phase 4: Consensus & Execution                          │  │   │
│  │  │            ▼                                              │  │   │
│  │  │   ┌──────────────────┐                                   │  │   │
│  │  │   │     Leader       │ ─────▶ [USE_TOOL: open_long(...)] │  │   │
│  │  │   │  综合决策/执行    │ ─────▶ [USE_TOOL: open_short(...)]│  │   │
│  │  │   │                  │ ─────▶ [USE_TOOL: hold(...)]      │  │   │
│  │  │   └──────────────────┘                                   │  │   │
│  │  └──────────────────────────────────────────────────────────┘  │   │
│  │                                                                 │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │   │
│  │  │  TradingScheduler│  │   PaperTrader   │  │  CooldownManager│ │   │
│  │  │  定时触发分析    │  │  模拟交易执行   │  │   连续亏损冷却  │ │   │
│  │  │  (默认4小时)     │  │  TP/SL监控      │  │   (3亏→24h暂停) │ │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│              │                         │                               │
│              ▼                         ▼                               │
│  ┌──────────────────────────┐   ┌──────────────────────────┐          │
│  │   LLM Gateway (8003)     │   │ Web Search Service (8010)│          │
│  │   ├─ DeepSeek (默认)     │   │   ├─ Tavily搜索          │          │
│  │   ├─ Gemini              │   │   └─ MCP协议             │          │
│  │   └─ Kimi (Moonshot)     │   │                          │          │
│  └──────────────────────────┘   └──────────────────────────┘          │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘

外部数据源:
├─ Binance API     <- 实时价格、K线、技术指标计算
├─ CoinGecko API   <- 价格备用源
├─ Alternative.me  <- Fear & Greed Index
├─ Binance Futures <- Funding Rate
└─ OKX API         <- 实盘交易执行(可选)
```

### 2.2 Docker服务配置

| 服务 | 容器名 | 端口 | 内存限制 | 功能 |
|------|--------|------|----------|------|
| redis | trading-redis | 6379 | 300MB | 状态存储 |
| llm_gateway | trading-llm-gateway | 8003 | 512MB | LLM统一网关 |
| web_search_service | trading-web-search | 8010 | 256MB | Tavily搜索 |
| trading_service | trading-service | 8000 | 768MB | 交易核心服务 |
| web_dashboard | trading-dashboard | 8888 | 50MB | Web监控面板 |

**总计**: ~1.9GB内存限制，实际使用约1.5GB

### 2.3 数据流

```
1. 触发分析 (定时/手动)
   │
   ▼
2. TradingMeeting.run() 启动交易会议
   │
   ├─▶ Phase 1: 各Agent使用工具获取实时数据
   │    └─ [USE_TOOL: get_market_price/get_klines/tavily_search...]
   │
   ├─▶ Phase 2: 各Agent基于数据给出投票
   │    └─ 方向 + 信心度 + 建议杠杆 + TP/SL
   │
   ├─▶ Phase 3: RiskAssessor评估风险
   │
   └─▶ Phase 4: Leader综合决策并调用执行工具
        └─ [USE_TOOL: open_long/open_short/hold]
             │
             ▼
3. PaperTrader执行模拟交易
   │
   ├─▶ 检查余额/持仓
   ├─▶ 开仓/平仓
   ├─▶ 设置TP/SL
   └─▶ 保存状态到Redis
        │
        ▼
4. 持续监控 (后台任务)
   │
   ├─▶ 定期检查TP/SL触发
   └─▶ 价格更新
```

---

## 3. 核心组件详解

### 3.1 TradingMeeting (交易会议)

**文件**: `backend/services/report_orchestrator/app/core/trading/trading_meeting.py`

交易会议是整个系统的核心，继承自Roundtable Meeting框架。

#### 关键类

```python
@dataclass
class TradingMeetingConfig:
    """从环境变量读取配置"""
    symbol: str = "BTC-USDT-SWAP"
    max_leverage: int = 20
    max_position_percent: float = 0.30  # 30%
    min_position_percent: float = 0.10  # 10%
    min_confidence: int = 60
    default_tp_percent: float = 5.0
    default_sl_percent: float = 2.0
```

#### 5个阶段

| 阶段 | 方法 | 说明 |
|------|------|------|
| 1. Market Analysis | `_run_market_analysis_phase()` | TechnicalAnalyst, MacroEconomist, SentimentAnalyst获取数据分析 |
| 2. Signal Generation | `_run_signal_generation_phase()` | 4个Agent投票(含QuantStrategist) |
| 3. Risk Assessment | `_run_risk_assessment_phase()` | RiskAssessor评估交易风险 |
| 4. Consensus Building | `_run_consensus_phase()` | Leader综合意见形成决策 |
| 5. Execution | `_run_execution_phase()` | 确认执行结果 |

#### 工具调用机制

Agent使用特殊格式调用工具:
```
[USE_TOOL: tool_name(param1="value1", param2="value2")]
```

系统使用正则解析并执行:
```python
tool_pattern = r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'
tool_matches = re.findall(tool_pattern, content)
```

#### 决策工具去重机制

防止Leader在单次响应中重复调用交易工具:
```python
decision_tools = {'open_long', 'open_short', 'hold'}
seen_decision_tool = False
for tool_name, params_str in tool_matches:
    if tool_name in decision_tools:
        if not seen_decision_tool:
            filtered_matches.append((tool_name, params_str))
            seen_decision_tool = True
        else:
            logger.warning(f"Skipping duplicate decision tool: {tool_name}")
```

### 3.2 PaperTrader (模拟交易器)

**文件**: `backend/services/report_orchestrator/app/core/trading/paper_trader.py`

完全本地的模拟交易系统，无需连接真实交易所。

#### 核心数据结构

```python
@dataclass
class PaperPosition:
    id: str
    symbol: str
    direction: str  # "long" or "short"
    size: float     # BTC数量
    entry_price: float
    leverage: int
    margin: float   # 保证金
    take_profit_price: Optional[float]
    stop_loss_price: Optional[float]
    opened_at: datetime

@dataclass
class PaperAccount:
    initial_balance: float = 10000.0
    balance: float = 10000.0          # 可用余额
    total_equity: float = 10000.0     # 总权益
    used_margin: float = 0.0          # 已用保证金
    unrealized_pnl: float = 0.0       # 未实现盈亏
    realized_pnl: float = 0.0         # 已实现盈亏
```

#### 关键方法

| 方法 | 功能 |
|------|------|
| `open_long()` | 开多仓，验证余额和保证金 |
| `open_short()` | 开空仓 |
| `close_position()` | 平仓，计算PnL |
| `check_tp_sl()` | 检查止盈止损是否触发 |
| `get_current_price()` | 获取当前价格(CoinGecko/Binance) |

#### 状态持久化

所有状态保存到Redis:
- `paper_trader:account` - 账户信息
- `paper_trader:position` - 当前持仓
- `paper_trader:trades` - 交易历史(最近100条)
- `paper_trader:equity_history` - 净值曲线(最近1000条)

### 3.3 TradingScheduler (调度器)

**文件**: `backend/services/report_orchestrator/app/core/trading/scheduler.py`

#### 状态机

```python
class SchedulerState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    ANALYZING = "analyzing"
    EXECUTING = "executing"
    PAUSED = "paused"
    STOPPED = "stopped"
```

#### 关键特性

- **默认间隔**: 4小时 (`SCHEDULER_INTERVAL_HOURS`)
- **首次分析**: 启动后立即执行一次
- **超时保护**: 单次分析最长25分钟
- **手动触发**: `trigger_now(reason="manual")` 支持立即分析

### 3.4 CooldownManager (冷却管理)

**文件**: `backend/services/report_orchestrator/app/core/trading/scheduler.py`

防止连续亏损时继续交易:

```python
class CooldownManager:
    max_consecutive_losses: int = 3   # 连续亏损次数触发冷却
    cooldown_hours: int = 24          # 冷却时间

    def record_trade_result(self, pnl: float) -> bool:
        """记录交易结果，返回是否允许继续交易"""
        if pnl < 0:
            self._consecutive_losses += 1
            if self._consecutive_losses >= self.max_consecutive_losses:
                self._trigger_cooldown()
                return False
        else:
            self._consecutive_losses = 0  # 盈利重置计数
        return True
```

### 3.5 TradingToolkit (交易工具集)

**文件**: `backend/services/report_orchestrator/app/core/trading/trading_tools.py`

为Agent提供的工具集，分为分析工具和执行工具。

#### 分析工具

| 工具名 | 功能 | 数据源 |
|--------|------|--------|
| `get_market_price` | 获取当前价格和24h行情 | Binance API |
| `get_klines` | 获取K线数据 | Binance API |
| `calculate_technical_indicators` | 计算RSI/MACD/BB/EMA | 基于Binance K线计算 |
| `get_account_balance` | 获取账户余额 | PaperTrader |
| `get_current_position` | 获取当前持仓 | PaperTrader |
| `get_fear_greed_index` | 恐慌贪婪指数 | Alternative.me API |
| `get_funding_rate` | 资金费率 | Binance Futures API |
| `get_trade_history` | 交易历史 | PaperTrader |
| `tavily_search` | 网络搜索 | MCP Web Search Service |

#### 执行工具 (仅Leader可用)

| 工具名 | 功能 |
|--------|------|
| `open_long` | 开多仓 |
| `open_short` | 开空仓 |
| `close_position` | 平仓 |
| `hold` | 观望决策 |

#### 数据源优先级

价格获取采用多级降级策略:
```
Binance API -> CoinGecko API -> Paper Trader缓存价格
```

---

## 4. 多Agent交易系统

### 4.1 Agent概览

**文件**: `backend/services/report_orchestrator/app/core/trading/trading_agents.py`

系统使用6个专业Agent协作分析:

| Agent | ID | 角色 | 工具 |
|-------|-----|------|------|
| 技术分析师 | TechnicalAnalyst | K线形态、技术指标分析 | 分析工具 |
| 宏观经济分析师 | MacroEconomist | 宏观经济、货币政策分析 | 分析工具 + tavily_search |
| 情绪分析师 | SentimentAnalyst | 市场情绪、恐慌贪婪指数 | 分析工具 |
| 量化策略师 | QuantStrategist | 统计分析、量化信号 | 分析工具 |
| 风险评估师 | RiskAssessor | 风险评估、审批建议 | 分析工具 |
| 主持人 | Leader | 综合决策、执行交易 | 执行工具 |

### 4.2 Agent加载机制

从AgentRegistry加载原子Agent:
```python
def create_trading_agents(toolkit=None):
    registry = get_registry()
    agents = []

    analysis_agent_ids = [
        "technical_analyst",
        "macro_economist",
        "sentiment_analyst",
        "risk_assessor",
        "quant_strategist",
    ]

    for agent_id in analysis_agent_ids:
        agent = registry.create_agent(agent_id, language='zh')
        agents.append(agent)

    leader = create_leader(language='zh')
    agents.append(leader)
```

### 4.3 投票机制

每个分析Agent在Signal Generation阶段提供投票:

```python
@dataclass
class AgentVote:
    agent_id: str
    agent_name: str
    direction: str           # "long", "short", "hold"
    confidence: int          # 0-100
    reasoning: str
    suggested_leverage: int
    suggested_tp_percent: float
    suggested_sl_percent: float
```

### 4.4 杠杆-信心度对应规则

系统强制执行杠杆与信心度的对应关系:

| 信心度 | 杠杆范围 (max_leverage=20) |
|--------|---------------------------|
| >80% (高) | 10-20倍 |
| 60-80% (中) | 5-10倍 |
| <60% (低) | 1-5倍或观望 |

---

## 5. 交易流程

### 5.1 完整分析周期

```
[触发] ─────────────────────────────────────────────────────▶
   │
   ├─ 定时触发 (TradingScheduler, 默认4小时)
   │
   └─ 手动触发 (POST /api/trading/trigger)
         │
         ▼
[Phase 1: Market Analysis] ─────────────────────────────────▶
   │
   ├─ TechnicalAnalyst
   │   └─ [USE_TOOL: get_market_price(...)]
   │   └─ [USE_TOOL: get_klines(...)]
   │   └─ [USE_TOOL: calculate_technical_indicators(...)]
   │
   ├─ MacroEconomist
   │   └─ [USE_TOOL: tavily_search("Bitcoin BTC market news")]
   │
   └─ SentimentAnalyst
       └─ [USE_TOOL: get_fear_greed_index()]
       └─ [USE_TOOL: get_funding_rate(...)]
         │
         ▼
[Phase 2: Signal Generation] ───────────────────────────────▶
   │
   └─ 4个Agent投票: TechnicalAnalyst, MacroEconomist,
                    SentimentAnalyst, QuantStrategist
       │
       └─ 每个Agent返回:
          - 方向: 做多/做空/观望
          - 信心度: 0-100%
          - 建议杠杆: 1-20x
          - 建议止盈: X%
          - 建议止损: X%
          - 理由
         │
         ▼
[Phase 3: Risk Assessment] ─────────────────────────────────▶
   │
   └─ RiskAssessor评估
       ├─ 审查各Agent投票
       ├─ 评估风险等级
       └─ 给出批准/否决建议
         │
         ▼
[Phase 4: Consensus & Execution] ───────────────────────────▶
   │
   └─ Leader综合决策
       │
       ├─ 分析各专家意见
       ├─ 评估综合信心度
       ├─ 确定交易参数
       │
       └─ 调用执行工具 (必须三选一)
           ├─ [USE_TOOL: open_long(leverage="5", amount_usdt="2000")]
           ├─ [USE_TOOL: open_short(leverage="3", amount_usdt="1500")]
           └─ [USE_TOOL: hold(reason="市场不明朗")]
                │
                ▼
[执行] ─────────────────────────────────────────────────────▶
   │
   └─ PaperTrader执行
       │
       ├─ 验证余额
       ├─ 计算持仓大小
       ├─ 设置TP/SL
       ├─ 保存到Redis
       │
       └─ 返回执行结果
```

### 5.2 持仓监控

后台持续运行TP/SL监控:

```python
async def check_tp_sl(self):
    """检查止盈止损是否触发"""
    if not self._position:
        return None

    current_price = await self.get_current_price()

    if self._position.direction == "long":
        # 多仓: 价格 >= TP 或 价格 <= SL
        if current_price >= self._position.take_profit_price:
            await self.close_position(reason="tp")
            return "tp"
        if current_price <= self._position.stop_loss_price:
            await self.close_position(reason="sl")
            return "sl"
    else:  # short
        # 空仓: 价格 <= TP 或 价格 >= SL
        if current_price <= self._position.take_profit_price:
            await self.close_position(reason="tp")
            return "tp"
        if current_price >= self._position.stop_loss_price:
            await self.close_position(reason="sl")
            return "sl"
```

---

## 6. API接口

### 6.1 接口概览

**Base URL**: `http://localhost:8000/api/trading`

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/status` | 获取系统状态 |
| GET | `/account` | 获取账户信息 |
| GET | `/position` | 获取当前持仓 |
| GET | `/history` | 获取交易/信号历史 |
| POST | `/start` | 启动交易系统 |
| POST | `/stop` | 停止交易系统 |
| POST | `/trigger` | 手动触发分析 |
| POST | `/close` | 手动平仓 |

### 6.2 响应示例

#### GET /status
```json
{
  "enabled": true,
  "demo_mode": true,
  "symbol": "BTC-USDT-SWAP",
  "scheduler": {
    "state": "running",
    "interval_hours": 4,
    "next_run": "2024-12-04T16:00:00",
    "last_run": "2024-12-04T12:00:00",
    "run_count": 5
  },
  "cooldown": {
    "in_cooldown": false,
    "consecutive_losses": 1,
    "max_consecutive_losses": 3
  }
}
```

#### GET /account
```json
{
  "total_equity": 10256.78,
  "available_balance": 9000.00,
  "true_available_margin": 9256.78,
  "used_margin": 1000.00,
  "unrealized_pnl": 256.78,
  "realized_pnl": 0.00,
  "total_trades": 3,
  "win_rate": 0.667,
  "currency": "USDT"
}
```

#### GET /position
```json
{
  "has_position": true,
  "symbol": "BTC-USDT-SWAP",
  "direction": "long",
  "size": 0.01,
  "entry_price": 95000.00,
  "current_price": 97567.80,
  "leverage": 10,
  "margin": 1000.00,
  "unrealized_pnl": 256.78,
  "unrealized_pnl_percent": 25.68,
  "take_profit_price": 99750.00,
  "stop_loss_price": 93100.00,
  "liquidation_price": 87400.00
}
```

#### GET /history?limit=5
```json
{
  "signals": [
    {
      "timestamp": "2024-12-04T12:00:00",
      "signal": {
        "direction": "long",
        "confidence": 75,
        "leverage": 10,
        "reasoning": "技术面看涨..."
      },
      "status": "executed"
    }
  ],
  "trades": [
    {
      "id": "abc123",
      "direction": "long",
      "entry_price": 94000.00,
      "exit_price": 95500.00,
      "pnl": 150.00,
      "pnl_percent": 15.00,
      "close_reason": "tp"
    }
  ]
}
```

---

## 7. 配置系统

### 7.1 config.yaml

```yaml
# 交易参数
trading:
  symbol: "BTC-USDT-SWAP"
  demo_mode: true  # true=模拟盘, false=实盘

# 风险控制
risk:
  max_leverage: 20          # 最大杠杆
  max_position_percent: 30  # 最大仓位百分比
  min_position_percent: 10  # 最小仓位百分比
  default_position_percent: 20
  min_confidence: 60        # 最低信心度
  default_tp_percent: 5.0   # 默认止盈
  default_sl_percent: 2.0   # 默认止损

# 调度
scheduler:
  interval_hours: 4         # 分析间隔
  cooldown_hours: 24        # 冷却时间
  max_consecutive_losses: 3 # 触发冷却的连续亏损次数

# LLM配置
llm:
  provider: "deepseek"      # 默认提供商
```

### 7.2 环境变量 (.env)

```bash
# LLM API Keys
GOOGLE_API_KEY=your_gemini_key
DEEPSEEK_API_KEY=your_deepseek_key
KIMI_API_KEY=your_kimi_key

# Web Search
TAVILY_API_KEY=your_tavily_key

# OKX交易所 (实盘时需要)
OKX_API_KEY=your_okx_key
OKX_SECRET_KEY=your_okx_secret
OKX_PASSPHRASE=your_okx_passphrase
OKX_DEMO_MODE=true

# 覆盖配置
DEFAULT_LLM_PROVIDER=deepseek
SCHEDULER_INTERVAL_HOURS=4
MAX_LEVERAGE=20
```

### 7.3 配置优先级

```
环境变量 > config.yaml > 代码默认值
```

---

## 8. 部署指南

### 8.1 本地部署

```bash
# 1. 配置
cp .env.example .env
# 编辑 .env 填入 API Keys

# 2. 启动
./start.sh

# 3. 查看状态
./status.sh

# 4. 查看Agent讨论
./view-agents.sh
```

### 8.2 远程服务器部署

```bash
# 1. 克隆代码到服务器
git clone <repo> /root/trading-standalone
cd /root/trading-standalone

# 2. 配置环境变量
cp .env.example .env
vim .env

# 3. 启动
docker compose up -d

# 4. 部署Dashboard
docker compose up -d web_dashboard

# 5. 访问
# API: http://server:8000/api/trading/status
# Dashboard: http://server:8888/
```

### 8.3 推荐服务器配置

| 项目 | 最低 | 推荐 |
|------|------|------|
| 内存 | 2GB | 4GB |
| CPU | 1核 | 2核 |
| 存储 | 10GB | 20GB |
| 地区 | - | 香港/新加坡 (访问外部API) |

---

## 9. 监控与日志

### 9.1 日志查看工具

| 命令 | 用途 |
|------|------|
| `./view-agents.sh` | **推荐**: 只显示Agent讨论和工具调用 |
| `./view-logs.sh` | 完整日志，包含所有细节 |
| `./logs.sh` | 简化日志 |
| `./logs.sh trading -f` | 实时跟踪 |

### 9.2 Web Dashboard

访问 `http://server:8888/` 查看:
- 系统状态 (运行中/已停止)
- 账户信息 (余额、权益)
- 当前持仓 (方向、PnL)
- 最近信号
- 历史交易

### 9.3 API监控

```bash
# 测试所有API端点
./test_api.sh

# 快速状态检查
curl http://localhost:8000/api/trading/status | python3 -m json.tool
```

---

## 10. 已知问题与解决方案

### 10.1 重复交易执行问题

**问题**: Leader可能在单次响应中多次调用`open_long/open_short`

**解决方案** (已实现):
```python
# trading_meeting.py:718-735
decision_tools = {'open_long', 'open_short', 'hold'}
seen_decision_tool = False
for tool_name, params_str in tool_matches:
    if tool_name in decision_tools:
        if not seen_decision_tool:
            filtered_matches.append((tool_name, params_str))
            seen_decision_tool = True
        else:
            logger.warning(f"Skipping duplicate decision tool: {tool_name}")
```

### 10.2 Gemini内容安全过滤

**问题**: Gemini有时会因内容安全过滤阻止响应

**解决方案** (已实现):
- 每个Agent有fallback响应
- 宏观经济分析避免敏感话题
- 搜索查询聚焦投资/市场数据

```python
def _get_fallback_response(self, agent_id: str, agent_name: str) -> str:
    """当响应被阻止时返回保守的中性回复"""
    ...
```

### 10.3 价格数据获取失败

**问题**: 单一价格源不可用

**解决方案** (已实现):
- 多级降级: Binance -> CoinGecko -> 缓存价格
- 所有工具都有error处理和fallback

### 10.4 Dashboard显示问题

**问题**: Balance显示$0.00或N/A

**可能原因**:
1. 浏览器缓存 - Ctrl+Shift+R强制刷新
2. API连接失败 - 检查CORS和网络
3. 服务未启动 - `docker ps`确认服务运行

### 10.5 LLM响应不稳定

**问题**: Agent不遵循工具调用格式

**解决方案**:
- Prompt中明确格式要求和示例
- 在Prompt中添加"禁止"说明
- 使用正则宽松匹配

---

## 11. 开发指南

### 11.1 添加新Agent

1. 在`config/agents.yaml`中定义Agent:
```yaml
new_agent:
  name:
    en: "New Agent"
    zh: "新Agent"
  role_prompt:
    en: "You are..."
    zh: "你是..."
```

2. 在`trading_agents.py`中添加到列表:
```python
analysis_agent_ids = [
    ...
    "new_agent",
]
```

### 11.2 添加新工具

在`trading_tools.py`的`_build_tools()`方法中:

```python
self._tools['new_tool'] = FunctionTool(
    name="new_tool",
    description="工具描述",
    parameters_schema={
        "type": "object",
        "properties": {
            "param1": {"type": "string"}
        }
    },
    func=self._new_tool_impl
)

async def _new_tool_impl(self, param1: str) -> str:
    # 实现
    return json.dumps({"result": "..."})
```

### 11.3 修改交易逻辑

关键文件:
- `trading_meeting.py` - 会议流程
- `paper_trader.py` - 交易执行
- `trading_tools.py` - 工具实现

### 11.4 调试技巧

```bash
# 查看实时日志
docker compose logs -f trading_service

# 只看Agent相关
docker compose logs trading_service 2>&1 | grep -E "Agent|tool|decision"

# 手动触发测试
curl -X POST http://localhost:8000/api/trading/trigger

# 检查Redis状态
docker exec -it trading-redis redis-cli
> GET paper_trader:account
> GET paper_trader:position
```

---

## 12. 代码文件索引

### 12.1 核心交易代码

| 文件 | 路径 | 行数 | 功能 |
|------|------|------|------|
| trading_meeting.py | app/core/trading/ | ~1210 | 交易会议核心逻辑 |
| paper_trader.py | app/core/trading/ | ~760 | 模拟交易器 |
| scheduler.py | app/core/trading/ | ~346 | 调度器和冷却管理 |
| trading_tools.py | app/core/trading/ | ~1250 | Agent工具集 |
| trading_agents.py | app/core/trading/ | ~181 | Agent加载和配置 |
| price_service.py | app/core/trading/ | ~200 | 价格服务 |
| retry_handler.py | app/core/trading/ | ~150 | 重试和熔断 |
| agent_memory.py | app/core/trading/ | ~100 | Agent记忆系统 |

### 12.2 配置文件

| 文件 | 路径 | 功能 |
|------|------|------|
| docker-compose.yml | trading-standalone/ | Docker服务编排 |
| config.yaml | trading-standalone/ | 交易配置 |
| .env | trading-standalone/ | API Keys |
| agents.yaml | config/ | Agent定义 |

### 12.3 脚本文件

| 文件 | 功能 |
|------|------|
| start.sh | 启动服务 |
| stop.sh | 停止服务 |
| status.sh | 状态查询 |
| logs.sh | 日志查看 |
| view-agents.sh | Agent讨论查看器 |
| test_api.sh | API测试 |
| deploy_dashboard.sh | Dashboard部署 |

---

## 附录

### A. 常用命令速查

```bash
# 启动/停止
./start.sh && ./status.sh
./stop.sh

# 日志
./view-agents.sh              # 推荐
docker compose logs -f trading_service

# API测试
./test_api.sh
curl http://localhost:8000/api/trading/status

# 手动触发
curl -X POST http://localhost:8000/api/trading/trigger

# Redis调试
docker exec -it trading-redis redis-cli KEYS "paper*"
```

### B. 环境变量完整列表

| 变量 | 默认值 | 说明 |
|------|--------|------|
| TRADING_SYMBOL | BTC-USDT-SWAP | 交易对 |
| MAX_LEVERAGE | 20 | 最大杠杆 |
| MAX_POSITION_PERCENT | 30 | 最大仓位% |
| MIN_POSITION_PERCENT | 10 | 最小仓位% |
| DEFAULT_POSITION_PERCENT | 20 | 默认仓位% |
| MIN_CONFIDENCE | 60 | 最低信心度 |
| DEFAULT_TP_PERCENT | 5.0 | 默认止盈% |
| DEFAULT_SL_PERCENT | 2.0 | 默认止损% |
| SCHEDULER_INTERVAL_HOURS | 4 | 分析间隔(小时) |
| COOLDOWN_HOURS | 24 | 冷却时间(小时) |
| MAX_CONSECUTIVE_LOSSES | 3 | 触发冷却的连亏次数 |
| DEFAULT_LLM_PROVIDER | deepseek | LLM提供商 |
| OKX_DEMO_MODE | true | OKX模拟盘模式 |
| STANDALONE_MODE | true | 独立部署模式 |

---

*文档最后更新: 2024-12-04*
*基于代码版本: dev分支最新提交*
