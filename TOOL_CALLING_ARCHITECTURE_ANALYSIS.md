# Tool Calling 架构分析报告

## 问题1: Trading-Standalone 为什么会自动获得更新?

### 答案: Docker Build Context 配置

查看 `trading-standalone/docker-compose.yml` 第 33-72 行:

```yaml
# ========== LLM Gateway ==========
llm_gateway:
  build:
    context: ../backend/services/llm_gateway  # 👈 指向主项目源码
    dockerfile: Dockerfile

# ========== Trading Service ==========
trading_service:
  build:
    context: ../backend/services/report_orchestrator  # 👈 指向主项目源码
    dockerfile: Dockerfile
```

### 工作原理

1. **Build Context 是什么?**
   - `context` 指定 Docker 构建时的工作目录
   - Docker 会将该目录的全部内容发送给 Docker daemon
   - Dockerfile 中的 `COPY` 和 `ADD` 指令都相对于这个 context

2. **Trading-Standalone 的构建流程**:
   ```
   trading-standalone/
   ├── docker-compose.yml  (配置文件)
   └── (其他配置)

   当运行 docker-compose build 时:
   ├── llm_gateway: 使用 ../backend/services/llm_gateway 作为 context
   │   └── 这会复制主项目的 llm_gateway 全部代码
   └── trading_service: 使用 ../backend/services/report_orchestrator 作为 context
       └── 这会复制主项目的 report_orchestrator 全部代码
   ```

3. **自动更新的机制**:
   ```bash
   # 当你在主项目修改了代码后
   cd /Users/dengjianbo/Documents/Magellan/backend/services/llm_gateway/app
   # 编辑了 main.py

   # 然后在 trading-standalone 中重新构建
   cd /Users/dengjianbo/Documents/Magellan/trading-standalone
   docker-compose build trading_service

   # Docker 会:
   # 1. 读取 ../backend/services/report_orchestrator 的最新代码
   # 2. 重新构建镜像
   # 3. 自动包含最新的代码变更
   ```

### 代码共享的优点

✅ **单一代码源 (Single Source of Truth)**:
- 所有服务使用同一份代码
- 避免了代码重复和同步问题
- 主项目的 bug 修复自动应用到 trading-standalone

✅ **简化维护**:
- 不需要在多个地方维护相同的代码
- 修改一次,所有环境生效

⚠️ **需要重新构建**:
- 代码修改后需要运行 `docker-compose build` 才能生效
- 不是"热更新",而是"构建时同步"

---

## 问题2: 为什么之前其他 Agent (Tavily) 可以工作,但交易工具失效了?

### 关键发现: 都是硬解析!

通过分析代码,我发现了一个**重要真相**:

**之前所有的工具(包括 Tavily)都没有使用原生 Tool Calling!**

### 证据1: Tavily 工具的实现方式

查看 `mcp_tools.py` 第 11-127 行:

```python
class TavilySearchTool(Tool):
    """Tavily 网络搜索工具 (MCP方式)"""

    async def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """执行网络搜索"""
        try:
            # 直接调用 HTTP API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.web_search_url}/search",
                    json=request_data
                )
                # 返回结果
                return {
                    "success": True,
                    "summary": "...",
                    "results": results
                }
```

**关键点**: Tavily 工具的 `execute()` 方法是直接在 Python 中调用的,**不依赖 LLM 的 Tool Calling**!

### 证据2: Agent 如何使用工具 (修复前)

查看 `agent.py` 的 `_parse_llm_response()` 方法(第 474-550行,修复前的逻辑):

```python
# 修复前: 硬解析文本格式 [USE_TOOL: tool_name(args)]
pattern = r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'
matches = re.findall(pattern, content)

if matches:
    for tool_name, args_str in matches:
        if tool_name in self.tools:
            # 手动解析参数
            args = self._parse_tool_args(args_str)
            # 直接调用工具的 execute 方法
            result = await self.tools[tool_name].execute(**args)
```

### 为什么 Tavily 工作,但交易工具失效?

#### Tavily 工具可以工作的原因:

1. **Agent 的 Prompt 中有明确的使用格式**:
   ```
   你可以使用以下工具:
   - tavily_search: 搜索网络信息

   使用格式: [USE_TOOL: tavily_search(query="比特币最新价格")]
   ```

2. **LLM 被训练成输出这种格式**:
   ```
   Agent: 让我搜索一下比特币价格
   LLM 输出: [USE_TOOL: tavily_search(query="Bitcoin price today")]
   ```

3. **Agent 解析文本并执行**:
   ```python
   # 正则匹配到 [USE_TOOL: tavily_search(query="Bitcoin price today")]
   tool_name = "tavily_search"
   args = {"query": "Bitcoin price today"}
   result = await self.tools["tavily_search"].execute(**args)
   ```

#### 交易工具失效的原因:

查看日志中的 Leader 输出:
```
Leader: 全员强共识看多，建议开多仓
杠杆15倍，金额3000USDT，止盈6%，止损2.8%
[USE_TOOL: open_long(leverage=15, amount_usdt=3000, tp_percent=6.0, sl_percent=2.8)]
```

**问题所在**:

1. ❌ **文本解析不可靠**:
   - LLM 可能改变格式: `open_long(...)` vs `[USE_TOOL: open_long(...)]`
   - 参数可能用中文: `杠杆=15` vs `leverage=15`
   - JSON 格式不稳定: `{"leverage": 15}` vs `leverage=15`

2. ❌ **执行时机不明确**:
   ```python
   # Agent 输出了文本后
   content = "[USE_TOOL: open_long(...)]"

   # 但这只是字符串,不是实际的函数调用!
   # Agent 需要再次调用 _parse_llm_response 才能执行
   ```

3. ❌ **交易工具需要立即执行**:
   - Tavily 搜索: 可以延迟,不影响结果
   - 开仓交易: 价格瞬息万变,延迟可能导致滑点或错过时机

### 对比: 修复后的原生 Tool Calling

```python
# 修复后: LLM 直接返回结构化的 tool_calls
response = {
    "choices": [{
        "message": {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_0",
                    "type": "function",
                    "function": {
                        "name": "open_long",
                        "arguments": '{"leverage": 15, "amount_usdt": 3000, ...}'
                    }
                }
            ]
        }
    }]
}

# Agent 解析并立即执行
tool_name = "open_long"
tool_args = json.loads('{"leverage": 15, ...}')  # 标准 JSON
result = await self.tools[tool_name].execute(**tool_args)
```

### 其他 Agent 的工具实现方式

查看 `enhanced_tools.py`:

1. **ChinaMarketDataTool** (第 22-484 行):
   ```python
   async def execute(self, symbol: str, action: str = "quote", **kwargs):
       # 直接调用东方财富 API
       async with httpx.AsyncClient() as client:
           response = await client.get(self.eastmoney_quote_url, ...)
   ```
   - ❌ 也是硬解析 `[USE_TOOL: china_market_data(...)]`

2. **GitHubAnalyzerTool** (第 603-976 行):
   ```python
   async def execute(self, repo: str, action: str = "repo_info", **kwargs):
       # 直接调用 GitHub API
       async with httpx.AsyncClient() as client:
           response = await client.get(f"{self.api_base}/repos/{repo}", ...)
   ```
   - ❌ 也是硬解析

3. **PatentSearchTool** (第 981-1132 行):
   ```python
   async def execute(self, query: str, search_type: str = "keyword", **kwargs):
       # 实际上还是调用 TavilySearchTool
       from .mcp_tools import TavilySearchTool
       tavily = TavilySearchTool()
       result = await tavily.execute(query=search_query, ...)
   ```
   - ❌ 也是硬解析,内部再调用 Tavily

### 为什么硬解析对交易工具不可靠?

对比不同工具的容错性:

| 工具类型 | 容错性 | 原因 |
|---------|-------|------|
| **Tavily Search** | 🟢 高 | - 搜索结果不需要精确参数<br>- 延迟几秒不影响结果<br>- 失败可以重试 |
| **GitHub Analyzer** | 🟢 高 | - 仓库信息是静态的<br>- 数据不会突变<br>- 失败可以重试 |
| **China Market Data** | 🟡 中 | - 股价会变化,但波动较小<br>- 有盘中/盘后区分<br>- 可以接受几秒延迟 |
| **Trading Tools** | 🔴 极低 | - ❌ 价格每秒都在变<br>- ❌ 滑点影响收益<br>- ❌ 不能重试(可能重复开仓)<br>- ❌ 参数必须精确(杠杆/金额/止盈止损) |

### 硬解析的具体问题

#### 问题1: 格式不稳定

LLM 可能输出:
```python
# 格式1: 标准格式
"[USE_TOOL: open_long(leverage=15, amount_usdt=3000, tp_percent=6.0, sl_percent=2.8)]"

# 格式2: 中文参数名
"[使用工具: 开多仓(杠杆=15, 金额=3000, 止盈=6%, 止损=2.8%)]"

# 格式3: JSON 格式
'[USE_TOOL: open_long({"leverage": 15, "amount_usdt": 3000, "tp_percent": 6.0})]'

# 格式4: 自然语言
"我建议使用15倍杠杆开多仓,金额3000USDT,止盈6%,止损2.8%"
```

正则表达式 `r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'` **只能匹配格式1**!

#### 问题2: 参数解析失败

```python
def _parse_tool_args(self, args_str: str) -> dict:
    # 尝试解析 "leverage=15, amount_usdt=3000, tp_percent=6.0"

    # 失败场景1: 带引号的字符串
    args_str = 'leverage=15, reason="SEC撤诉,利好"'  # 逗号在引号内!

    # 失败场景2: 嵌套对象
    args_str = 'params={"tp": 6.0, "sl": 2.8}'  # 无法解析嵌套

    # 失败场景3: 布尔值和None
    args_str = 'auto=True, reason=None'  # 需要特殊处理
```

#### 问题3: 执行时机延迟

```python
# 时间线:
T0: Leader 开始思考
T1: LLM 返回 "[USE_TOOL: open_long(...)]"  (纯文本)
T2: Agent 解析文本,提取工具调用
T3: Agent 调用 execute()
T4: 交易所执行开仓

# 问题: T1 → T4 可能间隔 1-3 秒
# 在这期间,比特币价格可能从 $92,000 涨到 $92,300
# 导致:
# - 预期止盈位: $92,000 * 1.06 = $97,520
# - 实际开仓价: $92,300
# - 实际止盈位: $92,300 * 1.06 = $97,838  (偏差 $318!)
```

### 原生 Tool Calling 的优势

```python
# OpenAI/Gemini/DeepSeek 原生 Tool Calling:

# 1. LLM 直接返回结构化调用
{
    "tool_calls": [
        {
            "function": {
                "name": "open_long",
                "arguments": '{"leverage": 15, "amount_usdt": 3000, "tp_percent": 6.0, "sl_percent": 2.8, "reason": "SEC撤诉利好"}'
            }
        }
    ]
}

# 优点:
# ✅ 格式固定: 永远是 JSON
# ✅ 参数准确: LLM 会严格按照 schema 生成
# ✅ 立即执行: 不需要二次解析
# ✅ 错误处理: 参数验证失败会直接报错
# ✅ 可追踪: 有 tool_call_id 可以追踪执行状态
```

---

## 总结

### 问题1答案: Trading-Standalone 自动更新机制

**通过 Docker Build Context 实现代码共享**:
- `docker-compose.yml` 中的 `context: ../backend/services/xxx` 指向主项目
- 重新构建时自动使用主项目的最新代码
- 不是运行时同步,而是构建时同步

### 问题2答案: 其他工具为什么能工作

**所有工具(包括 Tavily)都是硬解析**:
- 之前没有原生 Tool Calling,都用 `[USE_TOOL: tool_name(...)]` 格式
- Tavily 等工具能工作是因为:
  1. 容错性高(搜索/查询类操作)
  2. 不需要精确时机
  3. 失败可以重试

**交易工具失效的原因**:
- 硬解析对交易场景**极不可靠**:
  1. 格式可能变化
  2. 参数解析可能失败
  3. 执行延迟导致滑点
  4. 不能重试(避免重复开仓)

**修复方案(已完成)**:
- 实现原生 Tool Calling (OpenAI 兼容)
- LLM 直接返回结构化 `tool_calls`
- Agent 立即解析并执行
- 支持 Gemini, DeepSeek, Kimi 三个提供商

---

## 架构对比图

### 修复前: 硬解析架构
```
┌─────────────────────────────────────────────────────────┐
│ Agent (with tools)                                      │
│                                                         │
│ 1. Prompt: "你可以使用 [USE_TOOL: xxx(...)] 调用工具"  │
│ 2. _call_llm() → /chat (纯文本)                         │
│ 3. LLM 返回: "根据分析...[USE_TOOL: open_long(...)]"    │
│ 4. _parse_llm_response():                               │
│    - 正则匹配 r'\[USE_TOOL:\s*(\w+)\((.*?)\)\]'         │
│    - 手动解析参数字符串                                  │
│    - 调用 tool.execute()                                │
└─────────────────────────────────────────────────────────┘
         ⬇️
    ❌ 问题:
    - 格式不稳定
    - 解析可能失败
    - 执行延迟
```

### 修复后: 原生 Tool Calling
```
┌─────────────────────────────────────────────────────────┐
│ Agent (with tools)                                      │
│                                                         │
│ 1. tools_schema = get_tools_schema()  (OpenAI 格式)    │
│ 2. _call_llm() → /v1/chat/completions                  │
│    - messages: [...]                                    │
│    - tools: [{type:"function", function:{...}}]         │
│ 3. LLM 返回:                                            │
│    {                                                    │
│      "choices": [{                                      │
│        "message": {                                     │
│          "tool_calls": [{                               │
│            "function": {                                │
│              "name": "open_long",                       │
│              "arguments": '{"leverage":15,...}'         │
│            }                                            │
│          }]                                             │
│        }                                                │
│      }]                                                 │
│    }                                                    │
│ 4. _parse_llm_response():                               │
│    - 检测 message.tool_calls                            │
│    - JSON.parse(arguments)                              │
│    - 立即调用 tool.execute()                            │
└─────────────────────────────────────────────────────────┘
         ⬇️
    ✅ 优势:
    - 格式标准化 (OpenAI)
    - 参数 JSON 格式
    - 立即执行
    - 全 LLM 提供商支持
```

---

## 技术细节

### LLM Gateway 的双端点设计

```python
# 旧端点 (向后兼容,用于非工具场景)
@app.post("/chat")
async def chat(request: ChatRequest):
    # 纯文本对话
    return {"response": "..."}

# 新端点 (支持 Tool Calling)
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    if request.tools:
        # 原生 Tool Calling
        if provider == "gemini":
            return await call_gemini_with_tools(request)
        elif provider == "deepseek":
            return await call_deepseek_with_tools(request)
    else:
        # 普通对话
        return await call_without_tools(request)
```

### Agent 的智能路由

```python
async def _call_llm(self, messages, max_retries=3):
    has_tools = len(self.tools) > 0

    if has_tools:
        # 使用新端点,支持 Tool Calling
        endpoint = "/v1/chat/completions"
        request_data = {
            "messages": messages,
            "tools": self.get_tools_schema(),
            "tool_choice": "auto"
        }
    else:
        # 使用旧端点,普通对话
        endpoint = "/chat"
        request_data = {
            "messages": messages
        }

    response = await client.post(f"{gateway_url}{endpoint}", json=request_data)
    return response.json()
```

---

## 验证结果

### 修复前:
```
Leader: 建议开多仓,杠杆15倍...
[USE_TOOL: open_long(leverage=15, amount_usdt=3000, tp_percent=6.0, sl_percent=2.8)]

❌ 结果: 无交易执行
❌ 原因: 文本解析失败或格式不匹配
```

### 修复后:
```
[Agent:Leader] Using Tool Calling with 7 tools
[Agent:Leader] Native Tool Calling: open_long
[Agent:Leader] Tool arguments: {'leverage': 15, 'amount_usdt': 3000, ...}
[Agent:Leader] Tool open_long result: {...}

✅ 结果: 成功开仓
✅ 原因: 原生 Tool Calling,结构化执行
```

---

## 文件位置参考

1. **Trading-Standalone 配置**:
   - `/Users/dengjianbo/Documents/Magellan/trading-standalone/docker-compose.yml:36` (llm_gateway context)
   - `/Users/dengjianbo/Documents/Magellan/trading-standalone/docker-compose.yml:71` (trading_service context)

2. **LLM Gateway 实现**:
   - `/Users/dengjianbo/Documents/Magellan/backend/services/llm_gateway/app/main.py:34-52` (OpenAI 模型)
   - `/Users/dengjianbo/Documents/Magellan/backend/services/llm_gateway/app/main.py:349-481` (格式转换)
   - `/Users/dengjianbo/Documents/Magellan/backend/services/llm_gateway/app/main.py:667-689` (Tool Calling 端点)

3. **Agent 实现**:
   - `/Users/dengjianbo/Documents/Magellan/backend/services/report_orchestrator/app/core/roundtable/agent.py:239-381` (_call_llm)
   - `/Users/dengjianbo/Documents/Magellan/backend/services/report_orchestrator/app/core/roundtable/agent.py:383-550` (_parse_llm_response)

4. **工具实现示例**:
   - `/Users/dengjianbo/Documents/Magellan/backend/services/report_orchestrator/app/core/roundtable/mcp_tools.py:11-127` (TavilySearchTool)
   - `/Users/dengjianbo/Documents/Magellan/backend/services/report_orchestrator/app/core/roundtable/enhanced_tools.py` (各种增强工具)
