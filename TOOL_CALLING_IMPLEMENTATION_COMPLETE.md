# Tool Calling 实现完成报告

## ✅ 实施总结

已成功实现 LLM Gateway 的 Tool Calling 功能，解决了 Leader Agent 无法执行交易工具的问题。

**时间**: 2025-12-03
**状态**: ✅ 完成并测试通过
**影响范围**:
- ✅ 主项目 (Magellan)
- ✅ Trading-Standalone 项目

---

## 🎯 问题根因

**之前的问题**:
- Leader Agent 做出交易决策时输出 `[USE_TOOL: open_short(...)]` 纯文本
- LLM Gateway 不支持 Function Calling，导致工具无法被真正调用
- 结果：无法执行交易开仓

**根本原因**:
- LLM Gateway 的 `/chat` 端点只支持纯文本对话
- Agent 虽然有 `get_tools_schema()` 方法，但 `_call_llm()` 不传递工具参数
- LLM 返回的是文本而非结构化的 `tool_calls`

---

## 🔧 实施方案

### 阶段 1: LLM Gateway 添加 Tool Calling 支持

#### 修改文件
`/backend/services/llm_gateway/app/main.py`

#### 新增功能

**1. OpenAI 兼容的数据模型**
```python
class ChatCompletionMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    messages: List[ChatCompletionMessage]
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = "auto"
    temperature: Optional[float] = None
    provider: Optional[Literal["gemini", "kimi", "deepseek"]] = None

class ChatCompletionResponse(BaseModel):
    choices: List[Dict[str, Any]]
    model: str
    usage: Optional[Dict[str, Any]] = None
```

**2. 新端点 `/v1/chat/completions`**
```python
@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI 兼容的 Chat Completions API (支持 Tool Calling)"""
    provider = request.provider or current_provider

    if request.tools:
        print(f"[LLM Gateway] Tool calling enabled with {len(request.tools)} tools")

    if provider == "gemini":
        return await call_gemini_with_tools(request)
    elif provider == "deepseek":
        return await call_deepseek_with_tools(request)
    elif provider == "kimi":
        return await call_kimi_with_tools(request)
```

**3. 三个 LLM 提供商的 Tool Calling 实现**

##### Gemini Tool Calling
```python
async def call_gemini_with_tools(request: ChatCompletionRequest):
    # 转换 OpenAI tools → Gemini FunctionDeclaration
    function_declarations = convert_openai_to_gemini_tools(request.tools)

    # 转换 OpenAI messages → Gemini Content
    contents = convert_openai_to_gemini_messages(request.messages)

    # 调用 Gemini with function_declarations
    config = types.GenerateContentConfig(
        tools=[types.Tool(function_declarations=function_declarations)],
        temperature=request.temperature
    )

    response = gemini_client.models.generate_content(
        model=settings.GEMINI_MODEL_NAME,
        contents=contents,
        config=config
    )

    # 转换 Gemini function_call → OpenAI tool_calls
    return convert_gemini_to_openai_response(response, settings.GEMINI_MODEL_NAME)
```

##### DeepSeek Tool Calling
```python
async def call_deepseek_with_tools(request: ChatCompletionRequest):
    # DeepSeek 使用 OpenAI SDK，原生支持
    messages = [msg.dict(exclude_none=True) for msg in request.messages]

    response = await loop.run_in_executor(
        None,
        lambda: deepseek_client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL_NAME,
            messages=messages,
            tools=request.tools,
            tool_choice=request.tool_choice,
            temperature=request.temperature
        )
    )

    return response.model_dump()  # 已是 OpenAI 格式
```

##### Kimi Tool Calling
```python
async def call_kimi_with_tools(request: ChatCompletionRequest):
    # Kimi 使用 OpenAI SDK，原生支持
    messages = [msg.dict(exclude_none=True) for msg in request.messages]

    response = await loop.run_in_executor(
        None,
        lambda: kimi_client.chat.completions.create(
            model=settings.KIMI_MODEL_NAME,
            messages=messages,
            tools=request.tools,
            tool_choice=request.tool_choice,
            temperature=request.temperature or 0.6
        )
    )

    return response.model_dump()  # 已是 OpenAI 格式
```

**4. 格式转换函数**

```python
def convert_openai_to_gemini_tools(openai_tools):
    """将 OpenAI tools 格式转为 Gemini FunctionDeclaration"""
    function_declarations = []
    for tool in openai_tools:
        func = tool.get("function", {})
        function_declarations.append(
            types.FunctionDeclaration(
                name=func.get("name"),
                description=func.get("description", ""),
                parameters=func.get("parameters", {})
            )
        )
    return function_declarations

def convert_gemini_to_openai_response(gemini_response, model_name):
    """将 Gemini function_call 转为 OpenAI tool_calls 格式"""
    candidate = gemini_response.candidates[0]
    content_parts = candidate.content.parts

    message = {"role": "assistant"}
    tool_calls = []
    text_parts = []

    for part in content_parts:
        if hasattr(part, 'function_call') and part.function_call:
            fc = part.function_call
            tool_calls.append({
                "id": f"call_{len(tool_calls)}",
                "type": "function",
                "function": {
                    "name": fc.name,
                    "arguments": json.dumps(dict(fc.args))
                }
            })
        elif hasattr(part, 'text') and part.text:
            text_parts.append(part.text)

    if tool_calls:
        message["tool_calls"] = tool_calls
        message["content"] = None
    else:
        message["content"] = "".join(text_parts)

    return {
        "choices": [{
            "message": message,
            "finish_reason": "tool_calls" if tool_calls else "stop"
        }],
        "model": model_name
    }
```

### 阶段 2: Agent 支持 Tool Calling

#### 修改文件
`/backend/services/report_orchestrator/app/core/roundtable/agent.py`

#### 核心修改

**1. `_call_llm()` 方法 (第239-381行)**

```python
async def _call_llm(self, messages: List[Dict[str, str]], max_retries: int = 3):
    """调用LLM网关进行推理（带重试机制，支持 Tool Calling）"""
    has_tools = len(self.tools) > 0

    if has_tools:
        # 使用 OpenAI 兼容的 /v1/chat/completions 端点
        tools_schema = self.get_tools_schema()

        request_data = {
            "messages": messages,  # OpenAI 格式
            "tools": tools_schema,
            "tool_choice": "auto",
            "temperature": self.temperature
        }

        print(f"[Agent:{self.name}] Using Tool Calling with {len(tools_schema)} tools")

        response = await client.post(
            f"{self.llm_gateway_url}/v1/chat/completions",
            json=request_data
        )
        result = response.json()
        return result  # 已是 OpenAI 格式

    else:
        # 向后兼容：使用旧的 /chat 端点
        # ... 原有逻辑
```

**2. `_parse_llm_response()` 方法 (第383-550行)**

```python
async def _parse_llm_response(self, llm_response: Dict[str, Any]):
    """解析LLM的响应并生成消息（支持原生 Tool Calling）"""
    choice = llm_response["choices"][0]
    message = choice["message"]

    # 优先检查原生 tool_calls (OpenAI 格式)
    if message.get("tool_calls") and self.tools:
        self.status = "tool_using"
        tool_results = []

        for tool_call in message["tool_calls"]:
            tool_name = tool_call["function"]["name"]
            tool_args_str = tool_call["function"]["arguments"]

            if tool_name in self.tools:
                print(f"[Agent:{self.name}] Native Tool Calling: {tool_name}")

                # 解析 JSON 参数
                tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                print(f"[Agent:{self.name}] Tool arguments: {tool_args}")

                # 执行工具
                tool_result = await self.tools[tool_name].execute(**tool_args)
                print(f"[Agent:{self.name}] Tool {tool_name} result: {tool_result}")

                # 收集结果
                if isinstance(tool_result, dict) and "summary" in tool_result:
                    tool_results.append(f"\n[{tool_name}结果]: {tool_result['summary']}")
                else:
                    tool_results.append(f"\n[{tool_name}结果]: {str(tool_result)[:500]}")

        if tool_results:
            combined_result = "".join(tool_results)
            messages_to_send.append(Message(
                agent_name=self.name,
                content=combined_result,
                message_type=MessageType.INFORMATION
            ))

        self.status = "idle"
        return messages_to_send

    # 向后兼容：检测自定义格式 [USE_TOOL: ...]
    # ... 原有逻辑
```

---

## ✅ 验证结果

### 主项目测试

**测试命令**:
```bash
curl -X POST http://localhost:8000/api/trading/trigger
```

**测试结果**:
```
Found executed decision tool: open_long with params: {
    'leverage': '15',
    'amount_usdt': '3000',
    'take_profit_percentage': '6.0',
    'stop_loss_percentage': '2.8',
    'reason': "全员强共识看多：SEC撤诉重大利好叠加技术突破($92k)，且市场处于'恐慌中上涨'的健康状态，量化显示现货驱动。信心度90%，采用15倍杠杆顶格仓位博弈加速上涨。"
}
```

✅ **成功**：Leader Agent 通过 Tool Calling 成功调用 `open_long` 工具

### 支持的 LLM 提供商

| 提供商 | 状态 | 实现方式 | 测试 |
|-------|------|---------|------|
| **Gemini** | ✅ 支持 | Gemini native Function Calling API | ✅ 已测试 |
| **DeepSeek** | ✅ 支持 | OpenAI SDK (原生支持) | ✅ 已测试 |
| **Kimi** | ✅ 支持 | OpenAI SDK (原生支持) | ✅ 已测试 |

### Trading-Standalone 同步状态

**状态**: ✅ **自动同步**

Trading-Standalone 项目通过 docker-compose.yml 的 `context` 配置使用主项目的代码：

```yaml
# trading-standalone/docker-compose.yml
llm_gateway:
  build:
    context: ../backend/services/llm_gateway  # 使用主项目代码

trading_service:
  build:
    context: ../backend/services/report_orchestrator  # 使用主项目代码
```

**结论**: 无需单独修改，trading-standalone 自动获得 Tool Calling 功能

---

## 🔄 工作流程对比

### 修复前
```
Agent → LLM Gateway /chat (纯文本) → Gemini/DeepSeek → 纯文本响应
Leader 输出: "[USE_TOOL: open_short(...)]" (仅文本，需手动解析)
结果: 无法执行工具，无交易记录
```

### 修复后
```
Agent (with tools) → LLM Gateway /v1/chat/completions →
  → LLM (Function Calling) →
  → 结构化 tool_calls 响应 →
  → Agent 解析并执行工具 →
  → 成功开仓，记录到 Paper Trader
```

---

## 📋 关键日志

### LLM Gateway 日志
```
[LLM Gateway] Chat completions request using provider: deepseek
[LLM Gateway] Tool calling enabled with 3 tools
[DeepSeek Tool Calling] Configured 3 tools
```

### Agent 日志
```
[Agent:Leader] Using Tool Calling with 3 tools
[Agent:Leader] Native Tool Calling: open_long
[Agent:Leader] Tool arguments: {'leverage': '15', 'amount_usdt': '3000', ...}
[Agent:Leader] Tool open_long result: {...}
```

### Trading 日志
```
Found executed decision tool: open_long with params: {...}
[BROADCAST] type=agent_message, clients=1, agent=Leader
```

---

## 🎯 向后兼容性

### 保留功能
- ✅ 旧的 `/chat` 端点仍然可用
- ✅ 无工具的 Agent 自动使用旧端点
- ✅ 自定义格式 `[USE_TOOL: ...]` 仍然支持（降级模式）

### 自动切换逻辑
```python
if has_tools:
    # 使用新的 Tool Calling 端点
    endpoint = "/v1/chat/completions"
else:
    # 使用旧的文本端点
    endpoint = "/chat"
```

---

## 📊 技术细节

### OpenAI 工具格式
```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "open_short",
        "description": "开空仓（做空）",
        "parameters": {
          "type": "object",
          "properties": {
            "leverage": {"type": "integer"},
            "amount_usdt": {"type": "number"},
            "tp_percent": {"type": "number"},
            "sl_percent": {"type": "number"}
          },
          "required": ["leverage", "amount_usdt", "tp_percent", "sl_percent"]
        }
      }
    }
  ]
}
```

### Gemini 工具格式
```python
FunctionDeclaration(
    name="open_short",
    description="开空仓（做空）",
    parameters={
        "type": "object",
        "properties": {
            "leverage": {"type": "integer"},
            "amount_usdt": {"type": "number"},
            "tp_percent": {"type": "number"},
            "sl_percent": {"type": "number"}
        },
        "required": ["leverage", "amount_usdt", "tp_percent", "sl_percent"]
    }
)
```

### tool_calls 响应格式
```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_0",
            "type": "function",
            "function": {
              "name": "open_short",
              "arguments": "{\"leverage\": 15, \"amount_usdt\": 2000, ...}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ],
  "model": "gemini-2.5-flash"
}
```

---

## ✅ 验证清单

- [x] LLM Gateway 添加 `/v1/chat/completions` 端点
- [x] 实现 Gemini Tool Calling (FunctionDeclaration 转换)
- [x] 实现 DeepSeek Tool Calling (OpenAI SDK)
- [x] 实现 Kimi Tool Calling (OpenAI SDK)
- [x] Agent `_call_llm()` 传递 tools 参数
- [x] Agent `_parse_llm_response()` 处理 tool_calls
- [x] 主项目测试通过（Leader 成功执行 open_long）
- [x] Trading-Standalone 自动同步
- [x] 向后兼容性验证（无工具的 Agent 正常工作）
- [x] 三个 LLM 提供商全部支持

---

## 🚀 后续建议

### 可选优化

1. **添加工具执行日志到数据库**
   - 记录每次工具调用的参数和结果
   - 便于审计和调试

2. **支持异步工具执行**
   - 对于长时间运行的工具，支持异步执行
   - 避免阻塞 Agent 响应

3. **工具调用重试机制**
   - 对失败的工具调用自动重试
   - 设置最大重试次数和延迟

4. **工具权限控制**
   - 不同 Agent 可以访问不同的工具集
   - 避免误用高风险工具

### 监控指标

建议监控以下指标：
- Tool Calling 成功率
- 工具执行时间
- 工具调用频率
- LLM 提供商响应时间

---

## 📝 总结

✅ **成功实现** LLM Gateway 的原生 Tool Calling 支持

✅ **解决问题**: Leader Agent 现在能够成功执行交易工具

✅ **全面兼容**: 支持 Gemini、DeepSeek、Kimi 三个 LLM 提供商

✅ **自动同步**: Trading-Standalone 无需额外配置即可使用

✅ **向后兼容**: 不影响现有无工具的 Agent

**修复效果**: 从"无法执行交易"到"成功调用工具并开仓" 🎉

---

**实施日期**: 2025-12-03
**实施人员**: Claude Code
**版本**: v1.0.0
