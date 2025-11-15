# 圆桌讨论功能集成指南

## 概述

圆桌讨论功能已成功集成到 Magellan 后端系统中。该功能基于 MAIA (Multi-Agent Interaction Architecture) 框架实现，支持多个具有不同专业背景的 AI Agent 协作讨论投资决策问题。

## 已完成的工作

### 1. 核心框架实现

在 `/backend/services/report_orchestrator/app/core/roundtable/` 目录下实现了完整的 MAIA 框架：

- **Message** (`message.py`) - 消息通信基本单位
  - 支持 8 种消息类型：广播、直接、私聊、提问、回复、赞同、反对、思考
  - 包含发送者、接收者、内容、时间戳等完整信息

- **Tool** (`tool.py`) - Agent 可使用的工具
  - 基于函数的工具 (FunctionTool)
  - 基于 MCP 的工具 (MCPTool)

- **MessageBus** (`message_bus.py`) - 消息路由中心
  - Agent 注册/注销
  - 消息路由（广播、点对点）
  - 消息历史记录
  - 实时监听器（用于 WebSocket 推送）

- **Agent** (`agent.py`) - 自主智能体基类
  - `think_and_act()` 主循环
  - 工具注册和调用
  - 消息处理和生成

- **Meeting** (`meeting.py`) - 讨论编排器
  - 管理 turn-based 执行流程
  - 通过 AgentEventBus 实时推送状态
  - 生成讨论摘要

### 2. 预定义专家团队

在 `investment_agents.py` 中创建了 5 位投资分析专家：

1. **Leader (领导者)**
   - 角色：讨论主持人
   - 职责：引导讨论、综合观点、推动共识
   - 风格：客观中立、善于综合、注重大局

2. **Market Analyst (市场分析师)**
   - 角色：市场专家
   - 职责：分析市场趋势、竞争格局、行业机会
   - 风格：数据驱动、关注宏观、乐观积极

3. **Financial Expert (财务专家)**
   - 角色：财务分析专家
   - 职责：分析财务报表、估值、盈利能力
   - 风格：谨慎保守、关注风险、注重数据

4. **Team Evaluator (团队评估专家)**
   - 角色：人才与组织专家
   - 职责：评估管理团队、组织文化、执行能力
   - 风格：人本视角、"投资就是投人"

5. **Risk Assessor (风险评估师)**
   - 角色：风险管理专家
   - 职责：识别风险、评估影响、提出预警
   - 风格：审慎怀疑、关注负面、防范风险

### 3. WebSocket API 集成

在 `main.py` 中添加了新的 WebSocket 端点：

**端点**: `ws://localhost:8002/ws/roundtable`

**请求格式**:
```json
{
    "action": "start_discussion",
    "topic": "2024Q4投资价值分析",
    "company_name": "特斯拉",
    "context": {
        "summary": "公司概况...",
        "financial_data": {...},
        "market_data": {...}
    }
}
```

**响应格式**:
```json
{
    "type": "agents_ready",
    "session_id": "roundtable_特斯拉_abc123",
    "agents": ["领导者", "市场分析师", "财务专家", "团队评估专家", "风险评估师"],
    "message": "圆桌讨论准备就绪，共5位专家参与"
}
```

```json
{
    "type": "agent_event",
    "event": {
        "agent_name": "市场分析师",
        "event_type": "thinking",
        "message": "正在思考...",
        "progress": 0.2
    }
}
```

```json
{
    "type": "agent_event",
    "event": {
        "agent_name": "市场分析师",
        "event_type": "message",
        "message": "从市场趋势来看，该公司...",
        "data": {
            "recipient": "ALL",
            "message_type": "broadcast",
            "timestamp": "2025-01-15T10:30:00"
        }
    }
}
```

```json
{
    "type": "discussion_complete",
    "session_id": "roundtable_特斯拉_abc123",
    "summary": {
        "total_turns": 5,
        "total_messages": 21,
        "total_duration_seconds": 340.5,
        "agent_stats": {...},
        "message_type_stats": {...},
        "conversation_history": [...]
    }
}
```

## 测试方法

### 方法 1: 使用命令行测试脚本

```bash
cd /Users/dengjianbo/Documents/Magellan/backend/services/report_orchestrator

# 运行完整圆桌讨论（默认讨论特斯拉）
python3 test_roundtable.py

# 运行简单测试（单个 Agent）
python3 test_roundtable.py simple
```

**预期输出**:
- 4 位专家参与讨论
- 多轮对话，每轮约 4-5 分钟
- 专家从不同角度分析，互相质疑和补充
- 最终生成讨论摘要

### 方法 2: 使用 WebSocket 测试页面

1. 启动后端服务:
```bash
cd /Users/dengjianbo/Documents/Magellan/backend/services/report_orchestrator
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

2. 打开测试页面:
```bash
open test_roundtable_websocket.html
```

3. 在页面中:
   - 确认 WebSocket URL: `ws://localhost:8002/ws/roundtable`
   - 输入公司名称（例如：特斯拉）
   - 输入讨论主题（例如：2024Q4投资价值分析）
   - 可选：提供上下文 JSON
   - 点击"连接并开始讨论"

4. 观察实时讨论:
   - 看到专家团队列表
   - 实时显示每位专家的思考和发言
   - 查看不同消息类型（广播、提问、赞同、反对）
   - 讨论完成后查看统计摘要

### 方法 3: 使用 WebSocket 客户端（如 wscat）

```bash
# 安装 wscat
npm install -g wscat

# 连接到 WebSocket
wscat -c ws://localhost:8002/ws/roundtable

# 发送请求
{"action": "start_discussion", "company_name": "特斯拉", "topic": "2024Q4投资价值分析"}

# 观察实时消息流
```

## 实际测试结果

在测试中，5 位专家围绕"特斯拉 2024Q4 投资价值"进行了深入讨论：

**讨论主题演变**:
1. **第 1 轮**: 框架设定 - 是汽车公司还是 AI 公司？
2. **第 2 轮**: 乘数效应 vs 致命捆绑 - 汽车业务与 AI 业务的关系
3. **第 3 轮**: 战略分析 - 价格战是"歼灭战"还是"消耗战"？
4. **第 4 轮**: 财务建模 - 成本优势能持续多久？
5. **第 5 轮**: 风险评估 - 战后利润率修复可能性

**关键特点**:
- ✅ 专家各持立场：市场分析师乐观、财务专家谨慎、风险评估师警惕
- ✅ 观点互相碰撞：从不同角度质疑和补充
- ✅ 讨论逐层深入：从表面估值到结构性分析
- ✅ 自然对话流程：无需人工干预即可持续讨论

**统计数据**:
- 总轮次: 5 轮
- 总消息: 21 条
- 持续时间: 340.5 秒（约 5.7 分钟）
- 每位专家: 5 条消息

## 前端集成建议

### 1. 创建圆桌讨论视图组件

```vue
<!-- RoundtableView.vue -->
<template>
  <div class="roundtable-container">
    <!-- 专家列表 -->
    <div class="experts-panel">
      <div v-for="agent in agents" :key="agent" class="expert-card">
        <div class="expert-avatar">{{ agent }}</div>
        <div class="expert-status">{{ agentStatus[agent] }}</div>
      </div>
    </div>

    <!-- 讨论区域 -->
    <div class="discussion-area">
      <div v-for="msg in messages" :key="msg.id" class="message-bubble">
        <div class="message-header">
          <span class="sender">{{ msg.sender }}</span>
          <span class="timestamp">{{ msg.timestamp }}</span>
        </div>
        <div class="message-content">{{ msg.content }}</div>
      </div>
    </div>

    <!-- 控制面板 -->
    <div class="control-panel">
      <button @click="startDiscussion" :disabled="isDiscussing">
        开始讨论
      </button>
      <button @click="pauseDiscussion" v-if="isDiscussing">
        暂停
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const ws = ref(null)
const agents = ref([])
const messages = ref([])
const agentStatus = ref({})
const isDiscussing = ref(false)

const connectWebSocket = () => {
  ws.value = new WebSocket('ws://localhost:8002/ws/roundtable')

  ws.value.onmessage = (event) => {
    const data = JSON.parse(event.data)
    handleMessage(data)
  }
}

const handleMessage = (data) => {
  if (data.type === 'agents_ready') {
    agents.value = data.agents
    agents.value.forEach(agent => {
      agentStatus.value[agent] = '待命中'
    })
  }
  else if (data.type === 'agent_event') {
    const event = data.event

    if (event.event_type === 'thinking') {
      agentStatus.value[event.agent_name] = '思考中'
    }
    else if (event.event_type === 'message') {
      agentStatus.value[event.agent_name] = '发言'
      messages.value.push({
        id: Date.now(),
        sender: event.agent_name,
        content: event.message,
        timestamp: new Date().toLocaleTimeString()
      })
    }
  }
  else if (data.type === 'discussion_complete') {
    isDiscussing.value = false
    agents.value.forEach(agent => {
      agentStatus.value[agent] = '讨论完成'
    })
  }
}

const startDiscussion = () => {
  if (!ws.value) connectWebSocket()

  ws.value.send(JSON.stringify({
    action: 'start_discussion',
    company_name: '特斯拉',
    topic: '2024Q4投资价值分析'
  }))

  isDiscussing.value = true
}

onMounted(() => {
  // 可以在这里自动连接
})

onUnmounted(() => {
  if (ws.value) {
    ws.value.close()
  }
})
</script>
```

### 2. 集成到现有工作流

建议在 DD 分析完成后，提供"启动圆桌讨论"选项：

```typescript
// 在 DD 分析完成后
if (analysisCompleted) {
  showRoundtableOption({
    company_name: companyName,
    context: {
      summary: ddResult.summary,
      financial_data: ddResult.financials,
      market_data: ddResult.market
    }
  })
}
```

## 未来扩展方向

### 1. MCP 工具集成
- 为每个 Agent 配置专属的 MCP 工具
- 市场分析师：市场数据查询工具
- 财务专家：财务计算工具
- 风险评估师：风险模型工具

### 2. 动态 Agent 配置
- 允许用户选择参与讨论的专家
- 支持自定义 Agent 角色和提示词

### 3. 讨论控制功能
- 暂停/恢复讨论
- 人工介入提问
- 导出讨论记录

### 4. 多语言支持
- 中英文切换
- 其他语言支持

## 文档和参考

- **核心实现**: `/backend/services/report_orchestrator/app/core/roundtable/`
- **详细文档**: `/backend/services/report_orchestrator/app/core/roundtable/README.md`
- **测试脚本**: `/backend/services/report_orchestrator/test_roundtable.py`
- **WebSocket 测试页面**: `/backend/services/report_orchestrator/test_roundtable_websocket.html`
- **总结文档**: `/ROUNDTABLE_IMPLEMENTATION_SUMMARY.md`

## 注意事项

1. **性能考虑**: 每轮讨论需要调用多次 LLM，时间较长（5-6 分钟）
2. **API 配额**: 频繁调用可能遇到 Gemini API 限流
3. **错误处理**: 已实现完善的错误处理和重试机制
4. **实时推送**: 通过 AgentEventBus 实现 WebSocket 实时更新

## 支持

如有问题，请查看：
- 后端日志: `docker logs magellan-report_orchestrator-1`
- LLM Gateway 日志: `docker logs magellan-llm_gateway-1`
- 前端控制台输出

---

**版本**: V4.0
**日期**: 2025-01-15
**状态**: ✅ 已完成并测试通过
