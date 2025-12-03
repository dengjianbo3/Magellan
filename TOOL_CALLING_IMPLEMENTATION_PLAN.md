# Tool Calling 实施计划

## 问题总结

**根因**: LLM Gateway 不支持 Tool Calling，导致 Leader Agent 无法执行交易工具。

**当前流程**:
```
Agent → LLM Gateway /chat (纯文本) → Gemini/DeepSeek → 纯文本响应
```

**期望流程**:
```
Agent (with tools) → LLM Gateway /v1/chat/completions → Gemini/DeepSeek (Function Calling) → 结构化 tool_calls 响应
```

---

## 实施方案

### 阶段1: LLM Gateway 添加 Tool Calling 支持

#### 1.1 新增 Pydantic 模型 (main.py)

```python
# OpenAI 兼容的请求/响应模型
class ChatCompletionMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None  # OpenAI tool_calls 格式
    tool_call_id: Optional[str] = None  # For tool role messages

class ChatCompletionRequest(BaseModel):
    messages: List[ChatCompletionMessage]
    tools: Optional[List[Dict]] = None  # OpenAI tools schema
    tool_choice: Optional[Union[str, Dict]] = "auto"  # auto, none, or specific tool
    temperature: Optional[float] = None
    provider: Optional[Literal["gemini", "kimi", "deepseek"]] = None

class ChatCompletionResponse(BaseModel):
    choices: List[Dict]  # [{"message": {"role", "content", "tool_calls"}}]
    model: str
    usage: Optional[Dict] = None
```

#### 1.2 新端点 `/v1/chat/completions` (兼容 OpenAI)

```python
@app.post("/v1/chat/completions", tags=["AI Generation"])
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI 兼容的 Chat Completions API (支持 Tool Calling)
    """
    provider = request.provider or current_provider

    if provider == "gemini":
        return await call_gemini_with_tools(request)
    elif provider == "deepseek":
        return await call_deepseek_with_tools(request)
    elif provider == "kimi":
        return await call_kimi_with_tools(request)
```

#### 1.3 Gemini Tool Calling 实现

```python
async def call_gemini_with_tools(request: ChatCompletionRequest):
    from google.genai import types

    # 转换 OpenAI messages → Gemini Content
    contents = convert_openai_to_gemini_messages(request.messages)

    # 转换 OpenAI tools → Gemini function declarations
    function_declarations = None
    if request.tools:
        function_declarations = convert_openai_to_gemini_tools(request.tools)

    # 调用 Gemini with tools
    config = types.GenerateContentConfig(
        tools=[types.Tool(function_declarations=function_declarations)] if function_declarations else None,
        temperature=request.temperature
    )

    response = gemini_client.models.generate_content(
        model=settings.GEMINI_MODEL_NAME,
        contents=contents,
        config=config
    )

    # 转换 Gemini response → OpenAI format
    return convert_gemini_to_openai_response(response)
```

**关键转换函数**:
- `convert_openai_to_gemini_tools()`:
  - OpenAI: `{"type": "function", "function": {"name", "description", "parameters"}}`
  - Gemini: `FunctionDeclaration(name, description, parameters)`

- `convert_gemini_to_openai_response()`:
  - Gemini: `response.candidates[0].content.parts[0].function_call`
  - OpenAI: `{"tool_calls": [{"id", "type": "function", "function": {"name", "arguments"}}]}`

#### 1.4 DeepSeek Tool Calling 实现

DeepSeek 使用 OpenAI SDK，原生支持：

```python
async def call_deepseek_with_tools(request: ChatCompletionRequest):
    # DeepSeek 使用 OpenAI 兼容接口，直接传递
    response = await loop.run_in_executor(
        None,
        lambda: deepseek_client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL_NAME,
            messages=[msg.dict() for msg in request.messages],
            tools=request.tools if request.tools else None,
            tool_choice=request.tool_choice if request.tools else None,
            temperature=request.temperature
        )
    )

    # 直接返回 OpenAI 格式响应
    return response.model_dump()
```

#### 1.5 Kimi Tool Calling 实现

Kimi 同样使用 OpenAI SDK：

```python
async def call_kimi_with_tools(request: ChatCompletionRequest):
    # Kimi 使用 OpenAI 兼容接口
    response = await loop.run_in_executor(
        None,
        lambda: kimi_client.chat.completions.create(
            model=settings.KIMI_MODEL_NAME,
            messages=[msg.dict() for msg in request.messages],
            tools=request.tools if request.tools else None,
            tool_choice=request.tool_choice if request.tools else None,
            temperature=request.temperature or 0.6
        )
    )

    return response.model_dump()
```

---

### 阶段2: Agent 调用 Tool Calling 接口

#### 2.1 修改 `agent.py` 的 `_call_llm` 方法

```python
async def _call_llm(self, messages: List[Dict[str, str]], max_retries: int = 3) -> Dict[str, Any]:
    """
    调用LLM网关进行推理（支持 Tool Calling）
    """
    # 获取工具schema
    tools = None
    if self.tools:
        tools = self.get_tools_schema()

    request_data = {
        "messages": messages,  # 直接使用 OpenAI 格式
        "temperature": self.temperature
    }

    # 如果有工具，添加 tools 参数
    if tools:
        request_data["tools"] = tools
        request_data["tool_choice"] = "auto"

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                # 调用新的 Tool Calling 端点
                response = await client.post(
                    f"{self.llm_gateway_url}/v1/chat/completions",
                    json=request_data
                )
                response.raise_for_status()
                result = response.json()

                # 返回标准 OpenAI 格式响应
                return result
        except Exception as e:
            # ... 重试逻辑
```

#### 2.2 修改 `_parse_llm_response` 处理 tool_calls

```python
async def _parse_llm_response(self, llm_response: Dict[str, Any]) -> List[Message]:
    """
    解析LLM的响应（支持 tool_calls）
    """
    choice = llm_response["choices"][0]
    message = choice["message"]

    # 检查是否有 tool_calls
    if message.get("tool_calls"):
        # 执行工具调用
        tool_messages = []
        for tool_call in message["tool_calls"]:
            tool_name = tool_call["function"]["name"]
            tool_args = json.loads(tool_call["function"]["arguments"])

            # 执行工具
            tool_result = await self.tools[tool_name].execute(**tool_args)

            tool_messages.append(Message(
                agent_name=self.name,
                content=f"[Tool: {tool_name}] {tool_result}",
                message_type="tool_result"
            ))

        return tool_messages
    else:
        # 普通文本响应
        content = message.get("content", "")
        return [Message(
            agent_name=self.name,
            content=content,
            message_type="response"
        )]
```

---

### 阶段3: 测试计划

#### 3.1 单元测试 - LLM Gateway

```bash
# 测试 Gemini Tool Calling
curl -X POST http://localhost:8003/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "北京今天天气如何？"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "获取天气信息",
        "parameters": {
          "type": "object",
          "properties": {
            "city": {"type": "string"}
          }
        }
      }
    }],
    "provider": "gemini"
  }'
```

#### 3.2 集成测试 - Trading Meeting

```bash
# 启动主项目
docker-compose up -d

# 触发交易分析
curl -X POST http://localhost:8000/api/trading/trigger

# 查看日志，确认 tool_calls 被执行
docker-compose logs --tail=100 report_orchestrator | grep -E "tool_call|open_short|Trading"
```

#### 3.3 E2E 测试 - Trading Standalone

```bash
# 启动 standalone
cd trading-standalone
./start.sh

# 查看是否成功调用工具开仓
./logs.sh trading | grep -E "tool_call|open_short|Trade"
```

---

## 实施步骤

1. ✅ 分析现有架构
2. ⏳ 实现 LLM Gateway Tool Calling (main.py)
3. ⏳ 修改 Agent._call_llm 传递 tools
4. ⏳ 测试 Gemini Tool Calling
5. ⏳ 测试 DeepSeek Tool Calling
6. ⏳ 集成测试主项目
7. ⏳ 集成测试 standalone
8. ✅ 提交代码

---

## 预期效果

**修复前**:
- Leader 输出: `[USE_TOOL: open_short(...)]` (纯文本)
- 结果: 无交易执行

**修复后**:
- Leader 使用 tool_calls: `{"tool_calls": [{"function": {"name": "open_short", "arguments": "{...}"}}]}`
- 结果: 成功开仓，记录到 paper_trader

---

## 注意事项

1. **向后兼容**: 保留 `/chat` 端点，不影响现有非工具调用场景
2. **错误处理**: Tool Calling 失败时，应该降级到文本提示方式
3. **日志增强**: 添加详细的 tool_call 执行日志
4. **测试覆盖**: 确保三个 LLM 提供商都支持 Tool Calling
