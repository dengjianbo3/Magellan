# Magellan Trading System - 未来改进路线图 v2.0

> **创建日期**: 2026-01-07 | **架构审核**: 2026-01-08
> **目标**: 以人在环路 (HITL) 为核心，构建可观测、可恢复、可渐进发布的交易系统

---

## 🏛️ 架构愿景

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      Magellan Architecture Vision v2.0                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                     🛡️ CROSS-CUTTING CONCERNS                              │  │
│  │  Observability │ Circuit Breaker │ Feature Flags │ Config Management     │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                    │
│  │   FULL AUTO    │  │   SEMI-AUTO    │  │     MANUAL     │                    │
│  │   全自动托管    │  │  半自动确认    │  │   手动+监控    │                    │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘                    │
│          │                   │                   │                              │
│          ▼                   ▼                   ▼                              │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                    Shared Intelligence Layer                               │  │
│  │  Multi-Agent │ Risk Assessment │ Market Signals │ Reflection Memory       │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                    🔧 INFRASTRUCTURE LAYER                                 │  │
│  │  Redis (State) │ LangGraph (Orchestration) │ OKX API │ LLM Gateway        │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 模式定义

| 模式 | 用户参与度 | 系统职责 | 目标用户 |
|------|-----------|---------|---------|
| **Full Auto** | 0% - 完全托管 | 分析+决策+执行+风控 | 量化交易者、信任系统的用户 |
| **Semi-Auto** | 30% - 审批确认 | 分析+建议，等待确认后执行 | 有经验的交易者 |
| **Manual** | 100% - 自主交易 | 仅提供监控、分析和建议 | 学习者、保守型用户 |

---

## 🗺️ 总体路线图 (v2.0)

```
Timeline: 2026 Q1 - Q3
═══════════════════════════════════════════════════════════════════════════════

Phase 0: 可观测性基础 (Week 1-2) ✅ COMPLETED
├── ✅ 结构化日志 + Trace ID                    ██████████ P0
├── ✅ 关键指标采集                             ██████████ P0
└── ✅ Circuit Breaker 基础                     ██████████ P1

Phase 1: 并行与模式 (Week 3-6) ✅ COMPLETED
├── ✅ Agent 并行执行 + 限流                    ██████████ P0
├── ✅ HITL 基础框架                            ██████████ P0
├── ✅ Feature Flags 基础                       ██████████ P1
└── ✅ 集成测试                                 ██████████ P1

Phase 2: 模式完善 (Week 7-10) ✅ COMPLETED
├── ✅ Semi-Auto 通知系统                       ██████████ P0
├── ⏳ Manual 监控仪表板                        ██████░░░░ P1  (deferred)
├── ✅ ATR 动态止损                             ██████████ P1
└── ✅ 优雅降级策略                             ██████████ P2

Phase 3: 智能增强 (Week 11-16) ✅ COMPLETED
├── ✅ 多时间框架分析                            ██████████ P1
├── ✅ Agent 权重自学习                          ██████████ P1
└── ✅ 用户偏好学习                              ██████████ P2

Phase 4: 扩展能力 (Week 17-24)
├── 策略框架                                      ██████░░░░ P2
└── 移动端适配                                    ████░░░░░░ P3
```

---

## 🆕 Phase 0: 可观测性基础 (Week 1-2)

> **架构决策 (ADR-001)**: 在开发新功能之前，先建立可观测性基础设施，确保所有后续开发都能被有效监控和调试。

### 0.1 结构化日志 + Trace ID (P0) 📊

**目标**: 所有请求可追踪，日志可机器解析

```python
# core/observability/logging.py
import structlog
from contextvars import ContextVar

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")

def configure_logging():
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            add_trace_id,  # 注入 trace_id
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.BoundLogger,
    )

def add_trace_id(logger, method_name, event_dict):
    trace_id = trace_id_var.get()
    if trace_id:
        event_dict["trace_id"] = trace_id
    return event_dict
```

**日志输出示例**:

```json
{
  "timestamp": "2026-01-08T10:30:00Z",
  "level": "info",
  "trace_id": "abc123-def456",
  "event": "trade_signal_generated",
  "direction": "long",
  "confidence": 0.78
}
```

**验收标准**:

- [ ] 所有日志为 JSON 格式
- [ ] 每个交易周期有唯一 trace_id
- [ ] 错误日志包含完整 stack trace

---

### 0.2 关键指标采集 (P0) 📈

**核心指标 (基于 RED 方法)**:

| 指标类型 | 指标名 | 描述 |
|---------|-------|------|
| **Rate** | `trading.signals.generated` | 信号生成速率 |
| **Errors** | `trading.executions.failed` | 交易执行失败数 |
| **Duration** | `trading.agent.latency` | Agent 分析延迟 |
| **Custom** | `trading.mode.current` | 当前交易模式 |

```python
# core/observability/metrics.py
from prometheus_client import Counter, Histogram, Gauge

signals_generated = Counter(
    'trading_signals_generated_total',
    'Total trading signals generated',
    ['direction', 'mode']
)

agent_latency = Histogram(
    'trading_agent_latency_seconds',
    'Agent analysis latency',
    ['agent_name'],
    buckets=[1, 2, 5, 10, 20, 30, 60]
)
```

---

### 0.3 Circuit Breaker 基础 (P1) 🔌

**目标**: 外部 API 故障时快速失败，避免级联崩溃

```python
# core/resilience/circuit_breaker.py
from pycircuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=30)
async def call_okx_api(endpoint: str, params: dict):
    """OKX API 调用 (带熔断)"""
    return await okx_client.request(endpoint, params)
```

**熔断配置**:

| API | 失败阈值 | 恢复超时 |
|-----|---------|---------|
| OKX API | 5 次 | 30 秒 |
| LLM Gateway | 3 次 | 60 秒 |
| Tavily Search | 3 次 | 120 秒 |

**熔断状态机**:

```
CLOSED ──failure_threshold──▶ OPEN ──recovery_timeout──▶ HALF_OPEN
   ▲                                                         │
   └──────────────────── success ────────────────────────────┘
```

---

## 🔧 Phase 1: 并行与模式 (Week 3-6)

### 1.1 Agent 并行执行 + 限流 (P0) ⚡

> **架构决策 (ADR-002)**: 采用信号量+分层并行方案，避免 API 速率限制。

**API 限制**:

| API | 限制 | 风险 |
|-----|------|------|
| Tavily | 5 req/s (免费) / 20 req/s (付费) | ⚠️ 高 |
| Gemini | 15 RPM (免费) / 1000 RPM (付费) | 中等 |
| DeepSeek | 较宽松 | 低 |

**解决方案**: 信号量限流 + 分层并行

```python
# 限流配置
RATE_LIMIT_CONFIG = {
    "max_concurrent_agents": 2,      # 最多 2 个 Agent 同时运行
    "tavily_requests_per_second": 3, # Tavily 限速
    "batch_delay_seconds": 0.3,      # 批次间延迟
}

async def signal_generation_node(state: TradingState):
    # 第一批: 无外部 API (仅 OKX)
    batch_1 = [TechnicalAnalyst()]
    
    # 第二批: Tavily 搜索
    batch_2 = [FundamentalAnalyst(), MacroAnalyst()]
    
    # 第三批: 其他 LLM
    batch_3 = [SentimentAnalyst(), OnchainAnalyst()]
    
    for batch in [batch_1, batch_2, batch_3]:
        results = await execute_with_rate_limit(batch, state)
        await asyncio.sleep(RATE_LIMIT_CONFIG["batch_delay_seconds"])
```

**验收标准**:

- [ ] 5 Agent 执行完成时间 < 25s
- [ ] 不触发 API 速率限制
- [ ] 失败 Agent 使用 fallback vote

---

### 1.2 Feature Flags 基础 (P1) 🚩

> **架构决策 (ADR-003)**: 所有新功能通过 Feature Flag 控制，支持渐进发布和紧急回滚。

```python
# core/feature_flags.py
class FeatureFlag(Enum):
    PARALLEL_AGENTS = "parallel_agents"
    SEMI_AUTO_MODE = "semi_auto_mode"
    ATR_STOP_LOSS = "atr_stop_loss"

class FeatureFlagManager:
    async def is_enabled(self, flag: FeatureFlag, user_id: str = None) -> bool:
        # 1. 检查全局开关
        # 2. 检查用户级开关 (灰度发布)
        # 3. 返回默认值
        pass
    
    async def set_flag(self, flag: FeatureFlag, enabled: bool):
        """紧急回滚用"""
        pass
```

**发布策略**:

1. Feature 开发完成 → Flag 默认 OFF
2. 内部测试 → Flag 对测试用户 ON
3. 灰度发布 → Flag 对 10% 用户 ON
4. 全量发布 → Flag 全局 ON
5. 稳定后 → 移除 Flag

---

### 1.3 HITL 基础框架 (P0) 🎛️

**核心组件**: TradingModeManager

```python
class TradingMode(Enum):
    FULL_AUTO = "full_auto"
    SEMI_AUTO = "semi_auto"
    MANUAL = "manual"

class TradingModeManager:
    async def get_mode(self) -> TradingMode: ...
    async def set_mode(self, mode: TradingMode, user_id: str): ...
    async def should_execute_trade(self, signal) -> ExecutionDecision: ...
```

**❗ 潜在问题与缓解**:

| 问题 | 风险 | 缓解措施 |
|------|------|----------|
| Redis 并发竞态 | 多客户端同时修改 | WATCH/MULTI/EXEC 事务 |
| 服务重启状态丢失 | 模式重置 | Redis AOF 持久化 |
| 模式切换时交易进行中 | 状态不一致 | 等待当前交易完成 + 状态锁 |

---

## 📱 Phase 2: 模式完善 (Week 7-10)

### 2.1 Semi-Auto 通知系统 (P0) 📲

**多渠道通知**: Telegram + WebSocket + Email (可选)

**Telegram Bot 交互**:

```
🔔 新交易建议

📊 方向: LONG | 💰 杠杆: 5x | 📈 仓位: 20%
🎯 止盈: 8% | 🛡️ 止损: 3% | 💪 信心: 78%
⏰ 有效期: 5分钟

[✅ 确认] [✏️ 修改] [❌ 拒绝]
```

**❗ 潜在问题与缓解**:

| 问题 | 缓解措施 |
|------|----------|
| Telegram 通知延迟 | 多渠道冗余 |
| WebSocket 断连 | Exponential Backoff 重连 |
| 重复确认 | confirmation_id 幂等性检查 |

---

### 2.2 ATR 动态止损 (P1) 📏

```python
class ATRStopLossCalculator:
    atr_period = 14
    atr_multiplier = 1.5
    
    async def calculate_sl(self, direction, entry_price) -> float:
        atr = await self._get_atr()
        sl_distance = atr * self.atr_multiplier
        sl_price = entry_price - sl_distance if direction == "long" else entry_price + sl_distance
        return await self._ensure_above_liquidation(sl_price)
```

**❗ 潜在问题与缓解**:

| 问题 | 缓解措施 |
|------|----------|
| ATR 过大导致止损太宽 | 设置最大止损上限 (5%) |
| Whipsaw 频繁触发 | 使用较高 multiplier (2x-3x) |

---

### 2.3 优雅降级策略 (P2) 🛡️

> **架构决策 (ADR-004)**: 当外部依赖不可用时，系统应能继续提供有限功能。

| 降级级别 | 触发条件 | Agent 分析 | 交易执行 |
|---------|---------|-----------|---------|
| FULL | 所有服务正常 | ✅ 完整 | ✅ 所有操作 |
| REDUCED | 1个熔断 | ⚠️ 使用缓存 | ✅ 所有操作 |
| MINIMAL | 2+熔断 | ❌ 暂停 | ⚠️ 仅平仓 |
| OFFLINE | 全部熔断 | ❌ | ❌ |

---

## 🧠 Phase 3: 智能增强 (Week 11-16)

### 3.1 多时间框架分析 (P1) ⏱️

```python
TIMEFRAMES = ["15m", "1H", "4H", "1D"]
WEIGHTS = {"15m": 0.1, "1H": 0.3, "4H": 0.4, "1D": 0.2}
```

**决策规则**:

- 多周期一致 → 高信心
- 短期与长期背离 → 降低信心或 HOLD

### 3.2 Agent 权重自学习 (P1) 🎓

从交易结果学习，自动调整 Agent 权重 (范围: 0.5 - 2.0)

---

## Phase 4: 扩展能力 (Week 17-24)

### 4.1 策略框架 (P2) 📋

支持可配置的交易策略模板

### 4.2 移动端适配 (P3) 📱

PWA / Telegram Mini App

---

## 📊 成功指标

| 指标 | 当前值 | Phase 0 | Phase 2 | Phase 4 |
|------|--------|---------|---------|---------|
| Agent 执行时间 | 50s | < 25s | < 20s | < 15s |
| 日志结构化 | ❌ | ✅ JSON | ✅ | ✅ |
| Trace 覆盖率 | 0% | > 90% | > 95% | > 99% |
| 熔断器可用 | ❌ | ✅ | ✅ | ✅ |
| Feature Flag | ❌ | ✅ | ✅ | ✅ |
| 降级策略 | ❌ | ❌ | ✅ | ✅ |

---

## 📝 架构决策记录 (ADR)

| ADR | 标题 | 状态 |
|-----|------|------|
| ADR-001 | 先建可观测性，后开发功能 | ✅ 已采纳 |
| ADR-002 | 信号量+分层并行避免 API 限流 | ✅ 已采纳 |
| ADR-003 | Feature Flag 控制所有新功能 | ✅ 已采纳 |
| ADR-004 | 熔断触发优雅降级 | ✅ 已采纳 |
| ADR-005 | Redis AOF 持久化模式状态 | ✅ 已采纳 |

---

## ⚠️ 风险与缓解 (v2.0)

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 外部 API 故障 | 系统不可用 | Circuit Breaker + 优雅降级 |
| 新功能引入 Bug | 影响生产 | Feature Flag 渐进发布 |
| 调试困难 | 问题定位慢 | 结构化日志 + Trace ID |
| 性能退化 | 用户体验差 | 指标监控 + 告警 |
| Redis 故障 | 状态丢失 | AOF 持久化 + 哨兵 |

---

## 🎯 下一步行动

### Phase 0 (本周开始)

1. **配置 structlog** - 替换现有日志
2. **添加 Prometheus 指标** - 关键业务指标
3. **集成 pycircuitbreaker** - OKX/LLM/Tavily

### Phase 1 (Week 3-4)

1. **实现 FeatureFlagManager** - Redis 存储
2. **重构 signal_generation_node** - 并行+限流
3. **TradingModeManager** - 模式切换

---

*最后更新: 2026-01-08 (v2.0 架构审核版)*
