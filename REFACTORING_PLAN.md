# Magellan 系统重构计划

## 完成状态 (2025-11-27 更新)

| 阶段 | 状态 | 完成内容 |
|------|------|----------|
| Phase 0 | ✅ 完成 | 清理 11 个 .bak 备份文件 |
| Phase 1 | ✅ 完成 | 统一 Agent 架构：AgentRegistry + 9 个原子 Agent |
| Phase 2 | ✅ 完成 | Kafka 基础设施：Zookeeper + Kafka + Kafka UI |
| Phase 3 | ✅ 完成 | 消息服务：LLMMessageService + AgentMessageService + SessionEventPublisher |
| Phase 4 | ✅ 完成 | 代码清理 + 路由模块 + 存储服务层 + 配置集中化 |

### 新增组件

**Agent 系统**
- `app/core/agents/` - 统一 Agent 注册和工厂

**消息系统**
- `app/messaging/` - Kafka 消息队列封装
- `app/messaging/services/` - LLM/Agent/Session 消息服务适配器

**API 路由模块**
- `app/api/routers/` - API 路由拆分
  - `health.py` - 健康检查端点
  - `reports.py` - 报告管理端点
  - `dashboard.py` - 仪表板端点
  - `knowledge.py`, `roundtable.py`, `files.py`, `analysis.py` - 占位符

**存储服务层**
- `app/services/storage/` - 统一存储接口
  - `report_storage.py` - 报告存储（Redis + 内存回退）
  - `session_storage.py` - 会话存储（Redis + 内存回退）

**配置管理**
- `app/core/settings.py` - 集中配置管理（使用 pydantic-settings）

---

## 重构目标

1. **统一原子 Agent 架构** - 所有 Agent 唯一定义，不同场景通过组合实现
2. **Kafka 消息队列通信** - 替换 API 调用，实现消息持久化和系统解耦
3. **代码清理和拆分** - 提升可维护性，不影响功能

---

## 第一部分：当前架构分析

### 现有 Agent 系统（两套并存）

```
┌─────────────────────────────────────────────────────────────────┐
│                    当前混乱的架构                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  app/agents/ (旧系统 - 9个文件)          DEPRECATED BUT USED    │
│  ├── MarketAnalysisAgent                                        │
│  ├── FinancialExpertAgent                                       │
│  ├── TeamAnalysisAgent                                          │
│  ├── RiskAgent                                                  │
│  ├── ReportSynthesizerAgent  ←── Orchestrators 仍在使用         │
│  └── ...                                                        │
│                                                                 │
│  app/core/roundtable/ (新系统 - 14+文件)  ACTIVE BUT ISOLATED   │
│  ├── create_market_analyst()                                    │
│  ├── create_financial_expert()                                  │
│  ├── create_team_evaluator()                                    │
│  ├── create_risk_assessor()                                     │
│  ├── create_tech_specialist()                                   │
│  ├── create_legal_advisor()                                     │
│  ├── create_technical_analyst()                                 │
│  └── create_leader()                                            │
│                                                                 │
│  config/agents.yaml (配置定义)            CORRECT DESIGN        │
│  ├── 7个原子Agent + 2个特殊Agent                                │
│  └── 但未被完整实现                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 当前通信方式

```
┌─────────────┐     HTTP/REST      ┌─────────────┐
│   Frontend  │ ──────────────────→│ Orchestrator│
└─────────────┘                    └──────┬──────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
                    ▼                     ▼                     ▼
            ┌───────────┐         ┌───────────┐         ┌───────────┐
            │LLM Gateway│         │Web Search │         │   Redis   │
            │  (HTTP)   │         │  (HTTP)   │         │  (TCP)    │
            └───────────┘         └───────────┘         └───────────┘

问题:
- 同步调用，阻塞等待
- 无消息持久化
- 难以追踪/重放
- 服务间强耦合
```

---

## 第二部分：目标架构设计

### 2.1 统一原子 Agent 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    目标 Agent 架构                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  core/agents/                                                   │
│  ├── base/                                                      │
│  │   ├── agent.py          # Agent 基类                         │
│  │   ├── rewoo_agent.py    # ReWOO 架构实现                     │
│  │   └── interfaces.py     # 输入输出接口定义                    │
│  │                                                              │
│  ├── atomic/               # 7个原子 Agent (唯一实现)            │
│  │   ├── team_evaluator.py                                      │
│  │   ├── market_analyst.py                                      │
│  │   ├── financial_expert.py                                    │
│  │   ├── risk_assessor.py                                       │
│  │   ├── tech_specialist.py                                     │
│  │   ├── legal_advisor.py                                       │
│  │   └── technical_analyst.py                                   │
│  │                                                              │
│  ├── special/              # 2个特殊 Agent                       │
│  │   ├── leader.py         # 仅用于圆桌会议                      │
│  │   └── synthesizer.py    # 仅用于分析报告生成                  │
│  │                                                              │
│  ├── tools/                # Agent 工具集                        │
│  │   ├── search_tools.py                                        │
│  │   ├── data_tools.py                                          │
│  │   ├── analysis_tools.py                                      │
│  │   └── mcp_tools.py                                           │
│  │                                                              │
│  └── registry.py           # 统一的 Agent 注册中心               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

关键原则:
1. 每个原子 Agent 只有一个实现文件
2. 所有场景（分析/圆桌）复用同一套 Agent
3. 通过配置 (agents.yaml) 控制 Agent 行为
4. 通过 Workflow 编排 Agent 组合
```

### 2.2 Kafka 消息队列架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Kafka 消息架构                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                      Kafka Cluster                       │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │  Topics:                                         │    │   │
│  │  │                                                  │    │   │
│  │  │  magellan.agent.request    # Agent 执行请求      │    │   │
│  │  │  magellan.agent.response   # Agent 执行结果      │    │   │
│  │  │  magellan.llm.request      # LLM 调用请求        │    │   │
│  │  │  magellan.llm.response     # LLM 调用响应        │    │   │
│  │  │  magellan.tool.request     # 工具调用请求        │    │   │
│  │  │  magellan.tool.response    # 工具调用结果        │    │   │
│  │  │  magellan.session.events   # 会话事件流          │    │   │
│  │  │  magellan.audit.log        # 审计日志            │    │   │
│  │  │                                                  │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│                              │                                  │
│              ┌───────────────┼───────────────┐                 │
│              │               │               │                  │
│              ▼               ▼               ▼                  │
│     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│     │ Orchestrator│  │ LLM Gateway │  │ Web Search  │          │
│     │  (Consumer/ │  │  (Consumer/ │  │  (Consumer/ │          │
│     │   Producer) │  │   Producer) │  │   Producer) │          │
│     └─────────────┘  └─────────────┘  └─────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

优势:
1. 消息持久化 - 可追溯、可重放
2. 异步解耦 - 服务独立扩展
3. 负载均衡 - 多 Consumer 并行处理
4. 故障恢复 - 消息不丢失
5. 审计追踪 - 完整的消息历史
```

### 2.3 消息格式设计

```python
# 标准消息格式
class MagellanMessage(BaseModel):
    # 消息元数据
    message_id: str              # UUID
    correlation_id: str          # 关联ID (追踪整个请求链)
    timestamp: datetime
    version: str = "1.0"

    # 消息路由
    source: str                  # 发送方服务
    destination: str             # 目标服务/Agent
    reply_to: Optional[str]      # 回复 Topic

    # 消息内容
    message_type: MessageType    # REQUEST/RESPONSE/EVENT/ERROR
    payload: Dict[str, Any]      # 实际内容

    # 追踪信息
    session_id: Optional[str]
    user_id: Optional[str]
    trace_id: str                # 分布式追踪ID

# Agent 请求消息
class AgentRequest(MagellanMessage):
    agent_id: str
    action: str                  # analyze/synthesize/...
    inputs: Dict[str, Any]
    config: AgentConfig

# Agent 响应消息
class AgentResponse(MagellanMessage):
    agent_id: str
    status: str                  # success/error/partial
    outputs: Dict[str, Any]
    metrics: ExecutionMetrics    # 执行时间、token消耗等
```

---

## 第三部分：分阶段实施计划

### Phase 0: 准备工作 (1天)

```
任务:
├── 0.1 清理备份文件 (.bak)
├── 0.2 删除未使用的代码和导入
├── 0.3 统一代码风格
└── 0.4 创建分支 refactor/unified-architecture
```

### Phase 1: 统一 Agent 架构 (3-5天)

```
任务:
├── 1.1 创建新的 agents 目录结构
│   └── core/agents/{base,atomic,special,tools}/
│
├── 1.2 迁移原子 Agent 实现
│   ├── 从 roundtable/investment_agents.py 提取
│   ├── 每个 Agent 独立文件
│   └── 保持 ReWOO 架构
│
├── 1.3 统一 Agent 接口
│   ├── 定义 AgentInput/AgentOutput 接口
│   ├── 所有 Agent 实现统一接口
│   └── 输入输出可序列化
│
├── 1.4 更新 AgentRegistry
│   ├── 从 agents.yaml 加载配置
│   ├── 动态创建 Agent 实例
│   └── 支持 quick_mode 参数
│
├── 1.5 迁移 Orchestrators
│   ├── 使用新的 AgentRegistry
│   ├── 删除对旧 app/agents/ 的依赖
│   └── 提取公共逻辑到 BaseOrchestrator
│
└── 1.6 测试验证
    ├── 所有5个场景的测试
    └── 圆桌会议功能测试
```

### Phase 2: Kafka 基础设施 (2-3天)

```
任务:
├── 2.1 添加 Kafka 容器
│   ├── docker-compose.yml 添加 Kafka + Zookeeper
│   ├── 配置 Topics 自动创建
│   └── 配置数据持久化卷
│
├── 2.2 创建消息基础库
│   ├── 消息模型定义 (MagellanMessage)
│   ├── Kafka Producer/Consumer 封装
│   ├── 序列化/反序列化
│   └── 错误处理和重试
│
├── 2.3 消息路由层
│   ├── Topic 路由规则
│   ├── 消息过滤器
│   └── 死信队列处理
│
└── 2.4 监控和管理
    ├── Kafka UI (Kafdrop/AKHQ)
    ├── 消息追踪
    └── 健康检查
```

### Phase 3: 服务消息化改造 (5-7天)

```
任务:
├── 3.1 LLM Gateway 消息化
│   ├── 添加 Kafka Consumer (llm.request)
│   ├── 添加 Kafka Producer (llm.response)
│   ├── 保留 HTTP 接口 (兼容)
│   └── 消息去重和幂等
│
├── 3.2 Web Search Service 消息化
│   ├── Kafka 集成
│   └── 异步搜索支持
│
├── 3.3 Agent 执行消息化
│   ├── Agent 请求队列
│   ├── Agent 响应队列
│   ├── 并行执行支持
│   └── 超时和取消
│
├── 3.4 Session 事件流
│   ├── 会话状态事件
│   ├── 进度更新事件
│   └── 前端 WebSocket 集成
│
└── 3.5 审计日志
    ├── 所有消息归档
    ├── 查询和重放API
    └── 数据保留策略
```

### Phase 4: 代码清理和优化 (2-3天)

```
任务:
├── 4.1 拆分 main.py
│   ├── api/v2/analysis.py
│   ├── api/v2/websocket.py
│   ├── api/health.py
│   └── main.py (<300行)
│
├── 4.2 提取 Orchestrator 公共逻辑
│   ├── 消息映射提取
│   ├── 合成逻辑提取
│   └── 减少 ~1000 行重复代码
│
├── 4.3 删除废弃代码
│   ├── 删除 app/agents/ (旧系统)
│   ├── 删除 V1 WebSocket 端点
│   └── 清理未使用的导入
│
├── 4.4 配置集中化
│   ├── 创建 config/settings.py
│   ├── 环境变量统一管理
│   └── .env.example
│
└── 4.5 文档更新
    ├── 更新 SYSTEM_ARCHITECTURE.md
    ├── API 文档
    └── 开发者指南
```

---

## 第四部分：技术细节

### 4.1 Kafka 配置

```yaml
# docker-compose.yml 新增
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
    volumes:
      - zookeeper_data:/var/lib/zookeeper/data

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_LOG_RETENTION_HOURS: 168  # 7天
      KAFKA_LOG_RETENTION_BYTES: 10737418240  # 10GB
    volumes:
      - kafka_data:/var/lib/kafka/data

  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    ports:
      - "8080:8080"
    environment:
      KAFKA_CLUSTERS_0_NAME: magellan
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:29092
```

### 4.2 统一 Agent 接口

```python
# core/agents/base/interfaces.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel

class AgentInput(BaseModel):
    """Agent 标准输入"""
    session_id: str
    agent_id: str
    target: Dict[str, Any]      # 分析目标
    context: Dict[str, Any]     # 上下文（前序 Agent 结果）
    config: Dict[str, Any]      # 配置（quick_mode 等）

class AgentOutput(BaseModel):
    """Agent 标准输出"""
    agent_id: str
    status: str                 # success/error
    score: Optional[float]      # 0-100 评分
    analysis: Dict[str, Any]    # 分析结果
    key_findings: List[str]     # 关键发现
    risks: List[str]            # 风险点
    recommendations: List[str]  # 建议
    metadata: Dict[str, Any]    # 元数据（耗时、token等）

class AtomicAgent(ABC):
    """原子 Agent 基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.quick_mode = config.get('quick_mode', False)

    @abstractmethod
    async def analyze(self, input: AgentInput) -> AgentOutput:
        """执行分析 - 所有 Agent 实现此方法"""
        pass

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Agent 唯一标识"""
        pass
```

### 4.3 消息处理流程

```
用户发起分析请求
        │
        ▼
┌───────────────────┐
│   API Gateway     │
│   (HTTP/WS)       │
└────────┬──────────┘
         │
         │ Publish: magellan.session.events
         ▼
┌───────────────────┐
│      Kafka        │◄──────────────────────────────────┐
│                   │                                    │
│ Topics:           │                                    │
│ - agent.request   │                                    │
│ - agent.response  │                                    │
│ - llm.request     │                                    │
│ - llm.response    │                                    │
│ - tool.request    │                                    │
│ - tool.response   │                                    │
│ - audit.log       │                                    │
└────────┬──────────┘                                    │
         │                                               │
         │ Subscribe: agent.request                      │
         ▼                                               │
┌───────────────────┐     Publish: llm.request     ┌────┴──────────┐
│   Orchestrator    │─────────────────────────────→│  LLM Gateway  │
│   (Agent 编排)    │                              │               │
│                   │◄─────────────────────────────│  (Gemini/Kimi)│
└────────┬──────────┘     Subscribe: llm.response  └───────────────┘
         │
         │ Publish: agent.response
         │ Publish: audit.log (归档)
         ▼
┌───────────────────┐
│   Session Store   │
│   (状态管理)      │
└───────────────────┘
```

---

## 第五部分：风险和缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Kafka 增加系统复杂度 | 中 | 保留 HTTP 降级路径；完善监控 |
| 消息乱序 | 中 | 使用 partition key 保证顺序 |
| 重构期间功能中断 | 高 | 分阶段实施；每阶段完整测试 |
| Agent 迁移兼容性 | 中 | 保持接口向后兼容；渐进式迁移 |

---

## 第六部分：里程碑

| 阶段 | 目标 | 验收标准 |
|------|------|----------|
| Phase 0 | 代码清理 | 无 .bak 文件；lint 通过 |
| Phase 1 | Agent 统一 | 所有场景使用新 Agent；测试通过 |
| Phase 2 | Kafka 基础 | Kafka 容器运行；消息可收发 |
| Phase 3 | 消息化改造 | 核心流程走消息队列 |
| Phase 4 | 代码优化 | main.py < 300行；无废弃代码 |

---

## 附录：文件变更清单

### 新增文件

```
backend/services/report_orchestrator/
├── app/core/agents/
│   ├── __init__.py
│   ├── base/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── rewoo_agent.py
│   │   └── interfaces.py
│   ├── atomic/
│   │   ├── __init__.py
│   │   ├── team_evaluator.py
│   │   ├── market_analyst.py
│   │   ├── financial_expert.py
│   │   ├── risk_assessor.py
│   │   ├── tech_specialist.py
│   │   ├── legal_advisor.py
│   │   └── technical_analyst.py
│   ├── special/
│   │   ├── __init__.py
│   │   ├── leader.py
│   │   └── synthesizer.py
│   └── tools/
│       └── (迁移自 roundtable/*)
│
├── app/messaging/
│   ├── __init__.py
│   ├── kafka_client.py
│   ├── messages.py
│   ├── producer.py
│   ├── consumer.py
│   └── topics.py
│
├── app/api/
│   ├── __init__.py
│   ├── v2/
│   │   ├── analysis.py
│   │   └── websocket.py
│   ├── knowledge.py
│   └── health.py
│
└── config/
    └── settings.py
```

### 删除文件

```
backend/services/report_orchestrator/
├── app/agents/                    # 整个目录 (旧系统)
│   ├── market_analysis_agent.py
│   ├── financial_expert_agent.py
│   ├── team_analysis_agent.py
│   ├── risk_agent.py
│   ├── valuation_agent.py
│   ├── exit_agent.py
│   ├── preference_match_agent.py
│   └── crypto_analyst_agent.py    # 合并到 technical_analyst
│
├── app/core/roundtable/
│   ├── investment_agents.py.bak*  # 所有备份文件
│   └── (部分文件迁移到 core/agents/)
│
└── *.bak                          # 所有备份文件
```

---

*文档版本: 1.0*
*创建日期: 2025-11-27*
*作者: Claude & User*
