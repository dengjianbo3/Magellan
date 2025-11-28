# Magellan 系统架构文档

## 📋 目录

1. [项目概述](#项目概述)
2. [技术栈](#技术栈)
3. [系统架构](#系统架构)
4. [后端架构](#后端架构)
5. [前端架构](#前端架构)
6. [产品功能](#产品功能)
7. [前后端对接](#前后端对接)
8. [部署架构](#部署架构)
9. [开发指南](#开发指南)
10. [常见问题](#常见问题)

---

## 项目概述

### 项目名称
**Magellan AI Investment Analysis Platform**（麦哲伦AI投资分析平台）

### 项目定位
面向投资机构的AI驱动尽调分析平台，支持5种投资场景的智能分析和报告生成。

### 核心价值
- **智能化**：多Agent协同工作，自动化完成复杂的投资分析
- **场景化**：针对不同投资阶段定制分析流程
- **实时性**：WebSocket实时反馈分析进度
- **专业性**：基于行业最佳实践的分析框架

### 支持的投资场景
1. **Early Stage Investment** (早期投资尽调)
2. **Growth Investment** (成长期投资尽调)
3. **Public Market Investment** (二级市场投资分析)
4. **Alternative Investment** (另类投资尽调)
5. **Industry Research** (行业研究)

---

## 技术栈

### 前端技术栈
```
核心框架：
- Vue 3 (Composition API)
- Vue Router 4
- Vite 4

UI框架：
- TailwindCSS 3
- Material Symbols Icons

状态管理：
- Composables (useLanguage, useToast)
- SessionManager (localStorage)

通信：
- WebSocket (原生)
- Fetch API
```

### 后端技术栈
```
核心框架：
- FastAPI (Python 3.11+)
- Uvicorn (ASGI服务器)

Agent框架：
- ReWOO Architecture
- Custom Agent Registry

外部服务：
- LLM Gateway (LLM调用统一网关)
- SEC Edgar API (上市公司数据)
- Perplexity API (实时搜索)

数据库：
- PostgreSQL (持久化存储)
- Redis (缓存和会话)

消息队列：
- Kafka (服务间通信、消息持久化)
- Zookeeper (Kafka 协调)
- Kafka UI (消息监控) - http://localhost:8080
```

### 基础设施
```
容器化：
- Docker
- Docker Compose

反向代理：
- Nginx

监控：
- Prometheus
- Grafana
```

---

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                         用户浏览器                            │
│                     (Vue 3 + TailwindCSS)                    │
└─────────────────────────────────────────────────────────────┘
                            ↕ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────┐
│                         Nginx (8080)                         │
│                    (反向代理 + 静态资源)                       │
└─────────────────────────────────────────────────────────────┘
                            ↕
        ┌──────────────────────────────────────┐
        │                                      │
        ↓                                      ↓
┌─────────────────┐                  ┌─────────────────┐
│  Frontend Dev   │                  │  Backend API    │
│  Vite Server    │                  │  FastAPI:8000   │
│  (开发模式)      │                  │                 │
└─────────────────┘                  └─────────────────┘
                                              ↕
                  ┌──────────────────────────────────────────┐
                  │                                          │
                  ↓                                          ↓
        ┌─────────────────┐                      ┌─────────────────┐
        │  LLM Gateway    │                      │  External APIs  │
        │  (OpenAI/Claude)│                      │  - SEC Edgar    │
        │                 │                      │  - Perplexity   │
        └─────────────────┘                      └─────────────────┘
                  ↕                                          ↕
        ┌─────────────────┐                      ┌─────────────────┐
        │   PostgreSQL    │                      │      Redis      │
        │   (数据持久化)   │                      │    (会话缓存)    │
        └─────────────────┘                      └─────────────────┘
```

### 核心流程

```
用户操作 → 场景选择 → 配置分析 → 启动分析
                                    ↓
                            创建Session & WebSocket连接
                                    ↓
                            Orchestrator协调Agents
                                    ↓
                    ┌──────────────┴──────────────┐
                    ↓                             ↓
            Agents并行/串行执行              实时推送进度
                    ↓                             ↓
            调用LLM & External APIs          前端更新UI
                    ↓                             ↓
                生成分析结果                   显示Agent状态
                    ↓                             ↓
                汇总最终报告   ←──────────────   完成通知
                    ↓
                保存 & 返回
```

---

## 后端架构

### 目录结构

```
backend/
├── services/
│   └── report_orchestrator/
│       └── app/
│           ├── main.py                      # FastAPI应用入口
│           ├── api/
│           │   ├── v1/                      # API V1 (已废弃)
│           │   └── v2/                      # API V2 (当前版本)
│           │       ├── analysis.py          # 分析接口
│           │       └── websocket.py         # WebSocket接口
│           ├── core/
│           │   ├── agent_registry.py        # Agent注册中心 ⭐
│           │   ├── agent_event_bus.py       # Agent事件总线
│           │   ├── intent_recognizer.py     # 意图识别
│           │   ├── dd_state_machine.py      # 状态机
│           │   ├── orchestrators/           # 场景编排器
│           │   │   ├── base_orchestrator.py
│           │   │   ├── early_stage_orchestrator.py
│           │   │   ├── growth_investment_orchestrator.py
│           │   │   ├── public_market_orchestrator.py
│           │   │   ├── alternative_investment_orchestrator.py
│           │   │   └── industry_research_orchestrator.py
│           │   └── roundtable/              # Agent实现
│           │       ├── agent.py             # 基础Agent类 ⭐
│           │       ├── market_analysis_agent.py
│           │       ├── team_analysis_agent.py
│           │       └── ...
│           ├── agents/                      # 旧版Agent (逐步废弃)
│           ├── models/
│           │   ├── analysis_models.py       # 数据模型
│           │   └── report_models.py
│           └── utils/
│               ├── llm_client.py
│               └── data_fetcher.py
└── test_*.py                                # 测试脚本
```

### 核心模块详解

#### 1. Agent Registry（Agent注册中心）⭐

**文件**：`app/core/agent_registry.py`

**职责**：
- 统一管理所有Agent的创建和配置
- 提供Agent查询和实例化接口
- 支持动态Agent注册

**核心接口**：
```python
class AgentRegistry:
    @classmethod
    def register_agent(cls, agent_id: str, agent_class, config: dict)

    @classmethod
    def get_agent(cls, agent_id: str, session_id: str, **kwargs) -> Agent

    @classmethod
    def list_agents(cls) -> List[str]
```

**已注册的Agents**：
```python
AGENTS = {
    "market_analyst": MarketAnalysisAgent,
    "team_analyst": TeamAnalysisAgent,
    "financial_expert": FinancialAnalysisAgent,
    "risk_analyst": RiskAnalysisAgent,
    "tech_specialist": TechAnalysisAgent,
    "industry_researcher": IndustryResearchAgent,
    # ... 更多
}
```

#### 2. Agent基类（ReWOO架构）⭐

**文件**：`app/core/roundtable/agent.py`

**架构**：基于ReWOO (Reasoning WithOut Observation) 模式

**核心方法**：
```python
class Agent:
    async def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行分析的主方法"""
        # 1. 构建提示词
        # 2. 调用LLM
        # 3. 解析工具调用
        # 4. 执行工具
        # 5. 返回结果

    async def _call_llm(self, messages: List[Dict]) -> Dict:
        """调用LLM Gateway"""

    def _execute_tool(self, tool_name: str, params: str) -> str:
        """执行工具调用"""
```

**工具系统**：
```python
tools = {
    "search_company_info": "搜索公司信息",
    "get_financial_data": "获取财务数据",
    "analyze_market_trend": "分析市场趋势",
    # ...
}
```

**LLM调用格式**：
```python
# 请求格式
{
    "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
    ],
    "model": "gpt-4",
    "temperature": 0.7
}

# 响应格式（支持两种）
# 格式1: Dict
{
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "分析结果..."
            }
        }
    ]
}

# 格式2: String
"分析结果..."
```

#### 3. Orchestrator（场景编排器）

**文件**：`app/core/orchestrators/base_orchestrator.py`

**职责**：
- 定义分析场景的workflow
- 协调多个Agent的执行顺序
- 管理分析状态和进度
- 发送WebSocket消息

**基类方法**：
```python
class BaseOrchestrator:
    async def execute(self) -> Dict[str, Any]:
        """执行分析主流程"""
        # 1. 验证目标
        await self._validate_target()

        # 2. 获取workflow
        workflow = self._get_workflow()

        # 3. 执行步骤
        for step in workflow:
            await self._execute_step(step)
            await self._send_progress()

        # 4. 生成报告
        report = await self._synthesize_report()
        return report
```

**Workflow定义**：
```python
def _get_workflow(self) -> List[Dict]:
    if self.depth == AnalysisDepth.QUICK:
        return [
            {
                "id": "market_check",
                "name": "市场规模检查",
                "agent": "market_analyst",
                "estimated_duration": 60
            },
            # ...
        ]
```

**具体Orchestrator示例**：

1. **EarlyStageOrchestrator** - 早期投资
   - 重点：团队评估、产品验证、市场机会
   - Agents: team_analyst, product_analyst, market_analyst

2. **IndustryResearchOrchestrator** - 行业研究
   - 重点：市场规模、竞争格局、趋势分析
   - Agents: market_analyst, industry_researcher, tech_specialist

#### 4. WebSocket通信

**文件**：`app/api/v2/websocket.py`

**连接流程**：
```python
@router.websocket("/ws/v2/analysis/{session_id}")
async def analysis_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()

    # 注册连接
    connection_manager.register(session_id, websocket)

    try:
        # 接收初始请求
        request_data = await websocket.receive_json()

        # 创建并执行Orchestrator
        orchestrator = create_orchestrator(request_data, websocket)
        result = await orchestrator.execute()

        # 发送完成消息
        await websocket.send_json({
            "type": "complete",
            "data": result
        })
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        connection_manager.disconnect(session_id)
```

**消息类型**：
```python
MESSAGE_TYPES = {
    "workflow_start": "工作流开始",
    "step_start": "步骤开始",
    "step_progress": "步骤进度",
    "step_complete": "步骤完成",
    "agent_event": "Agent事件",
    "status_update": "状态更新",
    "error": "错误",
    "complete": "分析完成",
    "ping": "心跳请求",
    "pong": "心跳响应"
}
```

---

## 前端架构

### 目录结构

```
frontend/
├── src/
│   ├── App.vue                          # 根组件
│   ├── main.js                          # 应用入口
│   ├── router/
│   │   └── index.js                     # 路由配置
│   ├── views/                           # 页面级组件
│   │   ├── DashboardView.vue            # 仪表板
│   │   ├── AnalysisWizardView.vue       # 分析向导 ⭐
│   │   ├── AgentsView.vue               # Agent管理
│   │   ├── ReportsView.vue              # 报告列表
│   │   └── SettingsView.vue             # 设置
│   ├── components/                      # 组件库
│   │   ├── layout/                      # 布局组件
│   │   │   ├── MainLayout.vue
│   │   │   ├── Sidebar.vue
│   │   │   └── Navbar.vue
│   │   ├── dashboard/                   # 仪表板组件
│   │   │   ├── StatCard.vue
│   │   │   └── RecentSessions.vue
│   │   └── analysis/                    # 分析相关组件 ⭐
│   │       ├── ScenarioSelection.vue    # 场景选择
│   │       ├── UnifiedAnalysisForm.vue  # 统一分析表单
│   │       ├── AnalysisProgress.vue     # 分析进度 ⭐
│   │       └── StepResultCard.vue       # 步骤结果卡片
│   ├── composables/                     # 组合式函数
│   │   ├── useLanguage.js               # 国际化
│   │   └── useToast.js                  # 提示消息
│   ├── services/                        # 服务层 ⭐
│   │   ├── analysisServiceV2.js         # 分析服务V2 ⭐
│   │   └── sessionManager.js            # 会话管理
│   └── i18n/                            # 国际化资源
│       ├── zh.js
│       └── en.js
├── public/
├── index.html
├── vite.config.js
├── tailwind.config.js
└── package.json
```

### 核心模块详解

#### 1. 分析向导流程 ⭐

**文件**：`src/views/AnalysisWizardView.vue`

**三步流程**：
```
Step 0: 场景选择 (ScenarioSelection)
   ↓
Step 1: 配置分析 (UnifiedAnalysisForm)
   ↓
Step 2: 分析进度 (AnalysisProgress)
```

**状态管理**：
```javascript
const currentStep = ref(0)           // 当前步骤
const selectedScenario = ref(null)   // 选中的场景
const targetConfig = ref({})         // 目标配置
const analysisConfig = ref({         // 分析配置
  depth: 'quick',
  timeframe: '1Y',
  focus_areas: [],
  language: 'zh'
})
const sessionId = ref(null)          // 会话ID
```

**关键逻辑**：
```javascript
async function handleAnalysisStart(data) {
  // 1. 先移到进度页（重要！）
  currentStep.value = 2

  // 2. 等待组件mount
  await new Promise(resolve => setTimeout(resolve, 100))

  // 3. 调用API启动分析
  const result = await analysisServiceV2.startAnalysis(request)
  sessionId.value = result.sessionId

  // 4. 保存会话
  sessionManager.saveSession({...})
}
```

**为什么要先移到进度页？**
- AnalysisProgress组件需要先mount
- mount时会注册WebSocket消息监听器
- 避免错过早期的workflow_start消息

#### 2. 分析进度组件 ⭐

**文件**：`src/components/analysis/AnalysisProgress.vue`

**布局结构**：
```
┌─────────────────────────────────────────┐
│          Header (项目名 + 取消)          │
├─────────────────────────────────────────┤
│        Overall Progress Bar (总进度)     │
├─────────────────────────────────────────┤
│   Stats (剩余时间 | 活跃Agents | 开始时间) │
├──────────────────┬──────────────────────┤
│  AI Agent Status │  Analysis Results    │
│  (左侧面板)       │  (右侧面板)           │
│                  │                      │
│  ┌─────────┐    │  ┌─────────────┐    │
│  │ Agent 1 │    │  │ Step 1      │    │
│  │ Agent 2 │    │  │  - Result   │    │
│  │ Agent 3 │    │  │ Step 2      │    │
│  └─────────┘    │  │  - Running  │    │
│                  │  └─────────────┘    │
└──────────────────┴──────────────────────┘
```

**核心状态**：
```javascript
const workflow = ref([])              // 工作流步骤
const agents = computed(() => {...})  // Agent状态（从workflow计算）
const overallProgress = ref(0)        // 总进度
const analysisStatus = ref('running') // 分析状态
```

**WebSocket消息处理**：
```javascript
onMounted(() => {
  // 1. 刷新消息缓冲区（重要！）
  analysisServiceV2.flushMessageBuffer()

  // 2. 注册消息监听
  analysisServiceV2.on('workflow_start', handleWorkflowStart)
  analysisServiceV2.on('step_start', handleStepStart)
  analysisServiceV2.on('step_complete', handleStepComplete)
  analysisServiceV2.on('agent_event', handleAgentEvent)
  analysisServiceV2.on('complete', handleComplete)
  analysisServiceV2.on('error', handleError)
})

onUnmounted(() => {
  // 清理监听器
  analysisServiceV2.off('workflow_start', handleWorkflowStart)
  // ...
})
```

**消息处理函数**：
```javascript
function handleWorkflowStart(message) {
  // 初始化workflow
  workflow.value = message.data.steps.map((s, index) => {
    // 检测并翻译i18n key
    let displayName = s.name
    if (displayName && displayName.includes('.')) {
      displayName = t(displayName)
    }

    return {
      id: s.id,
      name: displayName,
      agent: s.agent,
      status: 'pending',
      progress: 0
    }
  })
}

function handleStepComplete(message) {
  // 更新步骤状态
  const step = workflow.value.find(s => s.id === message.data.step_id)
  if (step) {
    step.status = 'success'
    step.result = message.data.result
  }

  // 更新总进度
  const completed = workflow.value.filter(s => s.status === 'success').length
  overallProgress.value = Math.round((completed / workflow.value.length) * 100)
}
```

#### 3. 分析服务V2 ⭐

**文件**：`src/services/analysisServiceV2.js`

**核心功能**：
1. 启动分析（REST API）
2. WebSocket连接管理
3. 消息缓冲和重放
4. 心跳机制
5. 自动重连

**关键实现**：

```javascript
class AnalysisServiceV2 {
  constructor() {
    this.ws = null
    this.sessionId = null
    this.messageHandlers = new Map()
    this.messageBuffer = []           // 消息缓冲区 ⭐
    this.isBuffering = true           // 缓冲开关
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 10
    this.connectionState = 'disconnected'
  }

  // 启动分析
  async startAnalysis(request) {
    // 1. 调用REST API
    const response = await fetch(`${API_BASE}/api/v2/analysis/start`, {
      method: 'POST',
      body: JSON.stringify(request)
    })
    const data = await response.json()
    this.sessionId = data.session_id

    // 2. 连接WebSocket
    await this._connectWebSocket(request)

    return {
      sessionId: data.session_id,
      estimatedDuration: data.estimated_duration
    }
  }

  // WebSocket连接
  async _connectWebSocket(request) {
    const wsUrl = `ws://localhost:8000/ws/v2/analysis/${this.sessionId}`
    this.ws = new WebSocket(wsUrl)

    this.ws.onopen = () => {
      this._setConnectionState('connected')
      this._startHeartbeat()
      this.ws.send(JSON.stringify(request))
    }

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data)
      this._handleMessage(message)
    }

    this.ws.onclose = (event) => {
      this._stopHeartbeat()
      if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
        // 指数退避重连
        const backoffDelay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 16000)
        setTimeout(() => this._connectWebSocket(request), backoffDelay)
      }
    }
  }

  // 消息处理 ⭐
  _handleMessage(message) {
    // 1. 处理心跳
    if (message.type === 'pong') {
      this.lastHeartbeat = Date.now()
      return
    }

    // 2. 如果正在缓冲，存储重要消息
    if (this.isBuffering && this._isImportantMessage(message.type)) {
      this.messageBuffer.push(message)
      return
    }

    // 3. 分发消息给handlers
    this._dispatchMessage(message)
  }

  // 重要消息判断
  _isImportantMessage(type) {
    return [
      'workflow_start',
      'step_start',
      'step_complete',
      'agent_event',
      'status_update',
      'error',
      'complete'
    ].includes(type)
  }

  // 刷新消息缓冲区 ⭐
  flushMessageBuffer() {
    this.isBuffering = false
    const messages = [...this.messageBuffer]
    this.messageBuffer = []

    messages.forEach(message => {
      this._dispatchMessage(message)
    })
  }

  // 心跳机制
  _startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, 10000) // 每10秒一次
  }
}
```

**为什么需要消息缓冲？**

问题场景：
```
时间线 ────────────────────────────────────►
        │        │         │         │
    startAnalysis  →  workflow_start arrives
                   组件未mount，监听器未注册
                   ❌ 消息丢失！
```

解决方案：
```
时间线 ────────────────────────────────────►
        │        │         │         │
    startAnalysis  →  workflow_start  →  组件mount
                   存入buffer           刷新buffer
                   ✅ 消息保留！        ✅ 重放消息！
```

#### 4. 会话管理

**文件**：`src/services/sessionManager.js`

**功能**：
- 保存分析会话到localStorage
- 加载历史会话
- 支持会话恢复

```javascript
class SessionManager {
  saveSession(session) {
    const sessions = this.getSessions()
    sessions[session.sessionId] = {
      ...session,
      savedAt: Date.now()
    }
    localStorage.setItem('analysis_sessions', JSON.stringify(sessions))
  }

  getSession(sessionId) {
    const sessions = this.getSessions()
    return sessions[sessionId]
  }

  getSessions() {
    const data = localStorage.getItem('analysis_sessions')
    return data ? JSON.parse(data) : {}
  }
}
```

---

## 产品功能

### 5大投资场景

#### 1. 早期投资尽调 (Early Stage DD)

**适用对象**：
- 天使轮、Pre-A、A轮项目
- 创业公司（0-3年）

**分析重点**：
- 团队背景（40%）
- 产品验证（30%）
- 市场机会（20%）
- 风险扫描（10%）

**Quick模式Workflow**：
```python
[
    {"id": "team_check", "name": "团队背景检查", "agent": "team_evaluator"},
    {"id": "product_validation", "name": "产品验证", "agent": "tech_specialist"},
    {"id": "market_opportunity", "name": "市场机会", "agent": "market_analyst"},
    {"id": "red_flag_scan", "name": "红旗扫描", "agent": "risk_assessor"}
]
```

**输入字段**：
```json
{
  "company_name": "公司名称",
  "founders": ["创始人1", "创始人2"],
  "product_description": "产品描述",
  "target_market": "目标市场",
  "funding_round": "融资轮次",
  "valuation": "估值"
}
```

#### 2. 成长期投资尽调 (Growth Investment DD)

**适用对象**：
- B轮、C轮及以后
- 已有一定规模的公司

**分析重点**：
- 商业模式（30%）
- 财务健康（30%）
- 市场地位（25%）
- 增长潜力（15%）

**Quick模式Workflow**：
```python
[
    {"id": "business_model", "name": "商业模式分析"},
    {"id": "financial_health", "name": "财务健康检查"},
    {"id": "market_position", "name": "市场地位评估"},
    {"id": "growth_potential", "name": "增长潜力分析"}
]
```

#### 3. 二级市场投资分析 (Public Market Investment)

**适用对象**：
- 上市公司
- 二级市场股票

**分析重点**：
- 基本面分析（35%）
- 估值分析（30%）
- 市场情绪（20%）
- 技术面（15%）

**数据来源**：
- SEC Edgar API（财报、公告）
- Yahoo Finance（股价、财务数据）
- News API（新闻舆情）

#### 4. 另类投资尽调 (Alternative Investment DD)

**适用对象**：
- 房地产
- 私募股权
- 对冲基金
- 其他另类资产

**分析重点**：
- 资产质量（40%）
- 现金流（30%）
- 风险因素（20%）
- 退出路径（10%）

#### 5. 行业研究 (Industry Research)

**适用对象**：
- 行业趋势分析
- 细分赛道研究
- 竞争格局分析

**分析重点**：
- 市场规模与增长（30%）
- 竞争格局（25%）
- 技术趋势（25%）
- 投资机会（20%）

**输入字段**：
```json
{
  "industry_name": "行业名称",
  "sub_sector": "细分领域（可选）",
  "region": "地域范围（china/global/us）",
  "research_topic": "研究主题（可选，会自动生成）"
}
```

**自动生成research_topic逻辑**：
```python
topic_parts = [industry_name]
if sub_sector:
    topic_parts.append(sub_sector)
if region:
    region_name = {'china': '中国', 'global': '全球', 'us': '美国'}
    topic_parts.append(f"{region_name[region]}市场")
else:
    topic_parts.append("市场分析")

research_topic = " - ".join(topic_parts)
# 例如: "人工智能 - AI芯片 - 中国市场"
```

### 3种分析深度

#### Quick (快速判断)

**时长**：3-5分钟
**步骤**：4-5个核心步骤
**输出**：
- 投资建议（BUY/PASS/FURTHER_DD）
- 置信度评分
- 关键发现
- 红旗警告

#### Standard (标准分析)

**时长**：10-15分钟
**步骤**：8-10个详细步骤
**输出**：
- Quick的所有内容
- 详细分析报告
- 数据可视化
- 对比分析

#### Comprehensive (深度尽调)

**时长**：20-30分钟
**步骤**：15-20个全面步骤
**输出**：
- Standard的所有内容
- 外部数据验证
- 专家意见汇总
- 完整投资备忘录

---

## 前后端对接

### API接口规范

#### 1. 启动分析

**接口**：`POST /api/v2/analysis/start`

**请求**：
```json
{
  "project_name": "项目名称",
  "scenario": "early_stage_dd",
  "target": {
    "company_name": "公司名",
    "founders": ["创始人"],
    ...
  },
  "config": {
    "depth": "quick",
    "timeframe": "1Y",
    "focus_areas": [],
    "language": "zh"
  }
}
```

**响应**：
```json
{
  "session_id": "uuid-xxx-xxx",
  "scenario": "early_stage_dd",
  "depth": "quick",
  "estimated_duration": 300,
  "status": "created"
}
```

#### 2. 获取分析状态

**接口**：`GET /api/v2/analysis/{session_id}/status`

**响应**：
```json
{
  "session_id": "uuid-xxx-xxx",
  "status": "running",
  "progress": 45,
  "current_step": "financial_health",
  "steps_completed": 2,
  "steps_total": 5
}
```

### WebSocket消息格式

#### 连接

```javascript
ws://localhost:8000/ws/v2/analysis/{session_id}
```

#### 消息类型

##### 1. workflow_start

```json
{
  "type": "workflow_start",
  "data": {
    "steps": [
      {
        "id": "team_check",
        "name": "earlyStage.teamEvaluation",
        "agent": "earlyStage.teamAnalysisAgent",
        "estimated_duration": 60
      }
    ],
    "total_steps": 5
  }
}
```

**前端处理**：
- 初始化workflow数组
- 检测i18n key（包含"."）
- 翻译成中文显示

##### 2. step_start

```json
{
  "type": "step_start",
  "data": {
    "step_id": "team_check",
    "step_name": "团队背景检查",
    "agent": "team_analyst"
  }
}
```

##### 3. step_progress

```json
{
  "type": "step_progress",
  "data": {
    "step_id": "team_check",
    "progress": 50,
    "message": "正在分析创始人背景..."
  }
}
```

##### 4. step_complete

```json
{
  "type": "step_complete",
  "data": {
    "step_id": "team_check",
    "status": "success",
    "result": {
      "score": 0.85,
      "summary": "团队背景优秀，创始人有相关行业经验",
      "details": {
        "founders_experience": "10年+",
        "team_completeness": "完整",
        "key_strengths": ["技术背景强", "行业人脉广"]
      }
    },
    "duration": 58
  }
}
```

##### 5. agent_event

```json
{
  "type": "agent_event",
  "data": {
    "agent": "team_analyst",
    "event": "tool_call",
    "tool": "search_linkedin",
    "message": "正在搜索创始人LinkedIn信息..."
  }
}
```

##### 6. complete

```json
{
  "type": "complete",
  "data": {
    "session_id": "uuid-xxx",
    "status": "success",
    "report": {
      "recommendation": "BUY",
      "confidence": 0.82,
      "summary": {...},
      "sections": {...}
    },
    "duration": 285
  }
}
```

##### 7. error

```json
{
  "type": "error",
  "message": "Agent execution failed",
  "details": {
    "agent": "financial_expert",
    "error": "TypeError: string indices must be integers",
    "step_id": "financial_health"
  }
}
```

##### 8. ping/pong（心跳）

```json
// 客户端发送
{"type": "ping"}

// 服务器响应
{"type": "pong"}
```

### 数据流向图

```
┌─────────────┐
│   用户操作   │
│  选择场景   │
└──────┬──────┘
       │
       ↓
┌─────────────────────────────────┐
│  POST /api/v2/analysis/start    │
│  创建session，返回session_id     │
└──────┬──────────────────────────┘
       │
       ↓
┌─────────────────────────────────┐
│  WebSocket连接                   │
│  ws://.../ws/v2/analysis/{id}   │
└──────┬──────────────────────────┘
       │
       ↓
┌─────────────────────────────────┐
│  接收workflow_start消息          │
│  前端初始化workflow[]            │
└──────┬──────────────────────────┘
       │
       ↓
┌─────────────────────────────────┐
│  循环接收消息：                  │
│  - step_start                   │
│  - step_progress                │
│  - agent_event                  │
│  - step_complete                │
│  更新UI状态                      │
└──────┬──────────────────────────┘
       │
       ↓
┌─────────────────────────────────┐
│  接收complete消息                │
│  显示最终报告                    │
│  保存到localStorage              │
└─────────────────────────────────┘
```

---

## 部署架构

### Docker Compose配置

```yaml
version: '3.8'

services:
  # 后端API服务
  report_orchestrator:
    build: ./backend/services/report_orchestrator
    ports:
      - "8000:8000"
    environment:
      - LLM_GATEWAY_URL=http://llm_gateway:8001
      - DATABASE_URL=postgresql://user:pass@postgres:5432/magellan
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
      - llm_gateway
    volumes:
      - ./backend:/usr/src/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  # LLM Gateway
  llm_gateway:
    build: ./backend/services/llm_gateway
    ports:
      - "8001:8001"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

  # 前端开发服务器
  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev

  # PostgreSQL数据库
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=magellan
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=magellan
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # Redis缓存
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # Nginx (生产环境)
  nginx:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./frontend/dist:/usr/share/nginx/html
    depends_on:
      - report_orchestrator

volumes:
  postgres_data:
```

### 启动命令

```bash
# 开发环境
docker-compose up -d

# 查看日志
docker-compose logs -f report_orchestrator

# 重启服务
docker-compose restart report_orchestrator

# 停止所有服务
docker-compose down

# 重新构建
docker-compose build --no-cache
```

---

## 开发指南

### 新人上手步骤

#### 1. 环境准备

```bash
# 克隆代码
git clone <repository-url>
cd Magellan

# 安装后端依赖（可选，使用Docker则不需要）
cd backend/services/report_orchestrator
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 安装前端依赖
cd ../../../frontend
npm install

# 配置环境变量
cp .env.example .env
# 编辑.env，填入API密钥
```

#### 2. 启动服务

```bash
# 方式1：使用Docker Compose（推荐）
docker-compose up -d

# 方式2：手动启动
# 终端1 - 后端
cd backend/services/report_orchestrator
uvicorn app.main:app --reload --port 8000

# 终端2 - 前端
cd frontend
npm run dev

# 终端3 - LLM Gateway
cd backend/services/llm_gateway
uvicorn app.main:app --reload --port 8001
```

#### 3. 验证部署

访问：
- 前端：http://localhost:5173
- 后端API文档：http://localhost:8000/docs
- LLM Gateway：http://localhost:8001/docs

#### 4. 开发流程

**添加新Agent**：

1. 创建Agent类
```python
# backend/services/report_orchestrator/app/core/roundtable/my_agent.py
from .agent import Agent

class MyAgent(Agent):
    def __init__(self, session_id: str, **kwargs):
        super().__init__(
            name="MyAgent",
            session_id=session_id,
            system_prompt="你是一个...",
            tools=["search_data", "analyze_trend"]
        )

    async def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # 实现分析逻辑
        return await super().analyze(context)
```

2. 注册Agent
```python
# backend/services/report_orchestrator/app/core/agent_registry.py
from .roundtable.my_agent import MyAgent

class AgentRegistry:
    AGENTS = {
        # ...
        "my_agent": MyAgent,
    }
```

3. 在Orchestrator中使用
```python
def _get_workflow(self):
    return [
        {
            "id": "my_step",
            "name": "我的分析步骤",
            "agent": "my_agent",
            "estimated_duration": 60
        }
    ]
```

**添加新场景**：

1. 创建Orchestrator
```python
# app/core/orchestrators/my_scenario_orchestrator.py
from .base_orchestrator import BaseOrchestrator

class MyScenarioOrchestrator(BaseOrchestrator):
    def __init__(self, session_id, request, websocket):
        super().__init__(
            scenario=InvestmentScenario.MY_SCENARIO,
            session_id=session_id,
            request=request,
            websocket=websocket
        )
```

2. 注册路由
```python
# app/api/v2/analysis.py
SCENARIO_ORCHESTRATORS = {
    # ...
    "my_scenario": MyScenarioOrchestrator
}
```

3. 添加前端场景
```javascript
// frontend/src/components/analysis/ScenarioSelection.vue
const scenarios = [
  // ...
  {
    id: 'my_scenario',
    name: '我的场景',
    description: '描述...',
    icon: 'analytics'
  }
]
```

**调试技巧**：

```bash
# 查看后端实时日志
docker-compose logs -f report_orchestrator

# 查看WebSocket消息
# 在浏览器Console中
window.ws = analysisServiceV2.ws
window.ws.addEventListener('message', (e) => {
  console.log('WS:', JSON.parse(e.data))
})

# 检查Agent输出
# 在agent.py中添加
print(f"[Agent:{self.name}] 🔍 DEBUG: {variable}")

# 前端查看缓冲消息
console.log(analysisServiceV2.messageBuffer)
```

### 代码规范

**后端**：
- 遵循PEP 8
- 类型注解（Type Hints）
- Docstring（Google风格）
- 异步优先（async/await）

**前端**：
- Vue 3 Composition API
- 组件命名：PascalCase
- 文件命名：kebab-case
- 使用Composables共享逻辑

### 测试

```bash
# 后端单元测试
cd backend/services/report_orchestrator
pytest

# E2E测试
python test_phase3_e2e.py

# 前端测试（待完善）
cd frontend
npm run test
```

---

## 常见问题

### Q1: WebSocket消息丢失怎么办？

**原因**：组件mount前消息已到达

**解决**：
1. 前端使用消息缓冲机制
2. 组件mount后调用`flushMessageBuffer()`
3. 确保重要消息类型在缓冲列表中

### Q2: Agent名称显示英文key而非中文？

**原因**：
1. 后端发送了i18n key
2. 前端未检测和翻译

**解决**：
```javascript
// 检测包含"."的字符串为i18n key
if (name && name.includes('.')) {
  name = t(name)
}
```

### Q3: 财务分析报TypeError？

**当前状态**：已添加详细日志，待收集数据

**临时解决**：
- 检查LLM Gateway响应格式
- 确保返回标准dict格式

### Q4: 浏览器缓存导致代码不更新？

**解决**：
```bash
# 方式1：硬刷新
Cmd/Ctrl + Shift + R

# 方式2：清除缓存
# 开发者工具 → Application → Clear storage

# 方式3：禁用缓存
# 开发者工具 → Network → Disable cache
```

### Q5: Docker容器代码不更新？

**解决**：
```bash
# 检查volume挂载
docker-compose config | grep volumes

# 重启容器
docker-compose restart report_orchestrator

# 重新构建
docker-compose build --no-cache report_orchestrator
docker-compose up -d
```

### Q6: 如何添加新的工具(Tool)？

**步骤**：
1. 在Agent类中定义工具
```python
self.tools = {
    "my_tool": "工具描述"
}
```

2. 实现工具方法
```python
def _execute_tool(self, tool_name: str, params: str):
    if tool_name == "my_tool":
        return self._my_tool_impl(params)
    return super()._execute_tool(tool_name, params)

def _my_tool_impl(self, params: str):
    # 实现逻辑
    return "结果"
```

3. LLM会自动调用工具
```
[USE_TOOL: my_tool(param1, param2)]
```

### Q7: 如何切换LLM模型？

**配置**：
```python
# app/core/roundtable/agent.py
llm_response = await self._call_llm(
    messages,
    model="gpt-4",  # 或 "claude-3-opus"
    temperature=0.7
)
```

---

## 附录

### 相关文档

- [当前问题记录](./CURRENT_ISSUES.md)
- [API文档](http://localhost:8000/docs)
- [前端国际化指南](./frontend/I18N_README.md)
- [语言切换指南](./frontend/LANGUAGE_SWITCH_GUIDE.md)

### 技术栈文档链接

- [Vue 3](https://vuejs.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [TailwindCSS](https://tailwindcss.com/)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

### 版本历史

- **V3**: 完整UI重构，shadcn/ui主题
- **V2**: 5场景支持，Agent Registry
- **V1**: MVP版本

---

**最后更新**：2025-11-20
**维护者**：开发团队
**联系方式**：[待填写]
