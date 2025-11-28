# MAIA: Multi-Agent Interaction Architecture

## 概述

MAIA (Multi-Agent Interaction Architecture) 是 Magellan 的多智能体圆桌讨论模块，基于 Crypilot 的圆桌会议设计哲学实现。

该模块允许多个具有不同专业背景和能力的 AI Agent 协作讨论投资决策问题，通过观点碰撞和知识共享得出更全面、更深入的分析结论。

## 设计哲学

基于以下三个核心原则（来自 MAIA 框架）:

1. **Agent Autonomy（智能体自主性）**
   - 每个 Agent 是独立的实体，自主决策
   - Agent 自己决定说什么、对谁说、用什么工具
   - 基于角色定位和能力进行推理

2. **Peer-to-Peer Communication（对等通信）**
   - Agent 之间可以直接通信
   - 支持广播、一对一、私聊等多种通信模式
   - 无需中央控制器干预，实现有机互动

3. **Tool-Based Capabilities（基于工具的能力）**
   - Agent 不限于文本生成
   - 可装备"工具带"（Tool Belt）
   - 通过 MCP (Model Context Protocol) 集成外部能力

## 架构组件

### 1. Message（消息）

`message.py` - 通信的基本单位

```python
from roundtable import Message, MessageType

msg = Message(
    sender="MarketAnalyst",
    recipient="FinancialExpert",
    content="我认为市场估值偏高...",
    message_type=MessageType.DISAGREEMENT
)
```

**消息类型**:
- `BROADCAST`: 广播给所有人
- `DIRECT`: 一对一消息
- `PRIVATE`: 私聊（不公开）
- `QUESTION`: 提问
- `RESPONSE`: 回复
- `AGREEMENT`: 赞同
- `DISAGREEMENT`: 反对
- `THINKING`: 思考过程分享

### 2. Tool（工具）

`tool.py` - Agent 可使用的非 LLM 能力

**基于函数的工具**:
```python
from roundtable import FunctionTool

async def search_market(query: str) -> dict:
    # 实现搜索逻辑
    return {"results": "..."}

tool = FunctionTool(
    name="search_market_data",
    description="搜索市场数据和行业报告",
    func=search_market,
    parameters_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"}
        }
    }
)
```

**基于 MCP 的工具**:
```python
from roundtable import MCPTool

tool = MCPTool(
    name="query_database",
    description="查询内部投资数据库",
    mcp_server_url="http://mcp-server:8080",
    mcp_method="query",
    parameters_schema={...}
)
```

### 3. Agent（智能体）

`agent.py` - 系统中的自主行动者

```python
from roundtable import Agent

agent = Agent(
    name="MarketAnalyst",
    role_prompt="你是市场分析专家，专注于...",
    model="gpt-4",
    temperature=0.7
)

# 注册工具
agent.register_tool(market_search_tool)

# Agent 自主思考和行动
messages = await agent.think_and_act()
```

**Agent 的核心方法**:
- `think_and_act()`: 主循环 - 处理消息、推理、生成响应
- `register_tool()`: 注册工具到 Agent
- `get_tools_schema()`: 获取工具的 JSON Schema（用于 LLM function calling）

### 4. MessageBus（消息总线）

`message_bus.py` - 通信骨干

```python
from roundtable import MessageBus

bus = MessageBus()

# 注册 Agent
bus.register_agent("MarketAnalyst")
bus.register_agent("FinancialExpert")

# 发送消息
await bus.send(message)

# 获取待处理消息
messages = bus.get_messages("MarketAnalyst")

# 查看对话历史
history = bus.get_conversation_history()
```

**功能**:
- Agent 注册/注销
- 消息路由（广播、点对点）
- 消息历史记录
- 实时监听器（用于 WebSocket 推送）

### 5. Meeting（会议编排器）

`meeting.py` - 管理整个讨论流程

```python
from roundtable import Meeting
from roundtable.investment_agents import create_all_agents

# 创建专家团队
agents = create_all_agents()

# 创建 Meeting
meeting = Meeting(
    agents=agents,
    agent_event_bus=event_bus,
    max_turns=15,
    max_duration_seconds=180
)

# 启动讨论
initial_msg = Message(
    sender="User",
    recipient="ALL",
    content="请分析特斯拉的投资价值"
)

result = await meeting.run(initial_message=initial_msg)
```

**Meeting 功能**:
- 初始化 Agents 和 MessageBus
- 管理 turn-based 执行流程
- 通过 AgentEventBus 实时推送状态
- 生成讨论摘要

## 预定义专家团队

`investment_agents.py` - 投资分析专家

### 1. Leader（领导者）
- **职责**: 主持讨论、综合判断、总结提炼
- **工具**: 决策支持系统
- **特点**: 全局视角、战略思维

### 2. MarketAnalyst（市场分析师）
- **职责**: 市场趋势、竞争格局、行业洞察
- **工具**: `search_market_data` - 搜索市场数据
- **特点**: 数据驱动、量化分析

### 3. FinancialExpert（财务专家）
- **职责**: 财务报表分析、估值、财务健康度
- **工具**: `analyze_financials` - 分析财务指标
- **特点**: 审慎态度、关注异常信号

### 4. TeamEvaluator（团队评估专家）
- **职责**: 管理团队评估、组织文化、执行能力
- **工具**: `search_team_info` - 搜索团队信息
- **特点**: 人本视角、"投资就是投人"

### 5. RiskAssessor（风险评估专家）
- **职责**: 风险识别、风险评估、缓解建议
- **工具**: `assess_risks` - 风险评估
- **特点**: 系统性思维、审慎原则

### 6. TechSpecialist（技术专家）[可选]
- **职责**: 技术架构、创新性、技术壁垒
- **工具**: `search_tech_info` - 搜索技术信息
- **特点**: 技术视角、长期可持续性

## 使用示例

### 基本使用

```python
from app.core.roundtable import Meeting, Message
from app.core.roundtable.investment_agents import create_all_agents
from app.core.agent_event_bus import get_event_bus

# 创建事件总线
event_bus = get_event_bus()

# 创建专家团队
agents = create_all_agents()

# 创建会议
meeting = Meeting(
    agents=agents,
    agent_event_bus=event_bus,
    max_turns=15,
    max_duration_seconds=180
)

# 启动讨论
initial_message = Message(
    sender="User",
    recipient="ALL",
    content="请分析特斯拉 2024Q4 的投资价值"
)

# 运行讨论
summary = await meeting.run(initial_message=initial_message)

print(f"讨论轮次: {summary['total_turns']}")
print(f"总消息数: {summary['total_messages']}")
print(f"参与专家: {summary['participating_agents']}")
```

### 自定义 Agent

```python
from app.core.roundtable import Agent, FunctionTool

# 创建自定义工具
async def analyze_sentiment(text: str) -> dict:
    # 实现情绪分析
    return {"sentiment": "positive", "score": 0.85}

sentiment_tool = FunctionTool(
    name="analyze_sentiment",
    description="分析市场情绪",
    func=analyze_sentiment,
    parameters_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"}
        }
    }
)

# 创建自定义 Agent
sentiment_agent = Agent(
    name="SentimentAnalyst",
    role_prompt="你是市场情绪分析专家...",
    model="gpt-4",
    temperature=0.6
)
sentiment_agent.register_tool(sentiment_tool)

# 添加到会议
agents = create_all_agents()
agents.append(sentiment_agent)
```

### WebSocket 实时推送

```python
from fastapi import WebSocket
from app.core.agent_event_bus import get_event_bus

@app.websocket("/ws/roundtable")
async def roundtable_ws(websocket: WebSocket):
    await websocket.accept()

    # 订阅事件
    event_bus = get_event_bus()
    await event_bus.subscribe(websocket)

    try:
        # 启动圆桌讨论
        meeting = create_investment_analysis_meeting(
            topic="Tesla Investment Analysis",
            company_name="Tesla",
            agent_event_bus=event_bus
        )

        initial_msg = Message(
            sender="User",
            recipient="ALL",
            content="请分析特斯拉的投资价值"
        )

        result = await meeting.run(initial_message=initial_msg)

        # 发送最终结果
        await websocket.send_json({
            "type": "discussion_complete",
            "summary": result
        })

    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        await event_bus.unsubscribe(websocket)
        await websocket.close()
```

## 与前端集成

### 前端接收的事件格式

```typescript
interface AgentEvent {
  agent_name: string
  event_type: "started" | "thinking" | "searching" | "analyzing" | "message" | "completed" | "error"
  message: string
  progress?: number  // 0-1
  data?: {
    recipient?: string
    message_type?: string
    timestamp?: string
    message_id?: string
    // ... 其他数据
  }
  timestamp: string
}
```

### 前端示例代码

```javascript
const ws = new WebSocket('ws://localhost:8002/ws/roundtable')

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)

  if (data.type === 'agent_event') {
    const agentEvent = data.event

    // 更新 UI
    switch (agentEvent.event_type) {
      case 'thinking':
        showAgentThinking(agentEvent.agent_name)
        break
      case 'message':
        addMessageToChat(agentEvent)
        break
      case 'completed':
        showDiscussionComplete()
        break
    }
  }
}

// 启动讨论
ws.send(JSON.stringify({
  action: 'start_discussion',
  topic: 'Tesla Investment Analysis',
  company: 'Tesla'
}))
```

## 扩展和定制

### 添加新的 Agent

1. 在 `investment_agents.py` 中定义新的 create 函数
2. 定义 Agent 的 role_prompt
3. 创建和注册专用工具
4. 在 `create_all_agents()` 中添加

### 添加新的工具

1. 实现工具函数
2. 创建 FunctionTool 或 MCPTool
3. 注册到对应的 Agent

### 自定义终止条件

```python
def custom_termination(turn: int, history: List[Message]) -> bool:
    # 当达成共识时终止
    agreement_count = sum(
        1 for msg in history[-5:]
        if msg.message_type == MessageType.AGREEMENT
    )
    return agreement_count >= 3

result = await meeting.run(
    initial_message=initial_msg,
    termination_condition=custom_termination
)
```

## 调试和监控

### 查看消息历史

```python
# 获取完整对话历史
history = meeting.get_conversation_history()
for msg in history:
    print(f"{msg['sender']} -> {msg['recipient']}: {msg['content']}")
```

### 查看 Agent 状态

```python
# 获取特定 Agent 的上下文
context = meeting.get_agent_context("MarketAnalyst")
```

### 查看 MessageBus 统计

```python
stats = meeting.message_bus.get_stats()
print(f"总 Agent 数: {stats['total_agents']}")
print(f"总消息数: {stats['total_messages']}")
print(f"待处理消息: {stats['pending_messages']}")
```

## 性能优化

### 并发执行

Meeting 支持两种执行策略:

1. **顺序执行**（默认，更可控）
2. **并发执行**（更快，需启用）

修改 `meeting.py` 中的 `_execute_turn()` 方法切换策略。

### 限制消息历史

```python
# 在 Agent._build_llm_prompt() 中
# 只保留最近 N 条消息
messages.extend(self.message_history[-10:])
```

### 使用更快的模型

```python
agent = Agent(
    name="QuickAnalyst",
    role_prompt="...",
    model="gpt-3.5-turbo",  # 更快但略不精确
    temperature=0.7
)
```

## 故障排查

### Agent 不响应

检查:
1. MessageBus 是否正确连接
2. Agent 是否有待处理消息
3. LLM Gateway 是否可访问

### 工具调用失败

检查:
1. 工具函数是否正确实现
2. 参数 schema 是否正确
3. LLM 是否正确解析工具

### WebSocket 断开

检查:
1. 事件总线订阅状态
2. WebSocket 连接状态
3. 异常处理是否完善

## 未来扩展

- [ ] 支持 Agent 动态加入/退出
- [ ] 支持投票机制
- [ ] 支持子讨论（小组讨论）
- [ ] 支持讨论记录导出
- [ ] 支持讨论回放
- [ ] 支持多语言（中英文切换）
- [ ] 集成更多 MCP 工具
- [ ] 支持 Agent 学习和优化

## 参考资料

- [MAIA Framework Design](https://github.com/example/maia)
- [Crypilot Roundtable](https://github.com/example/crypilot)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Model Context Protocol](https://modelcontextprotocol.io/)

## 许可证

[MIT License](LICENSE)
