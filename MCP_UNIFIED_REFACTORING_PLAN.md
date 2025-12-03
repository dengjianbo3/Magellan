# MCP 统一工具调用重构方案

## 问题分析

### 原始设计意图

你设计了一套完整的 **MCP (Model Context Protocol)** 架构:

```
backend/services/report_orchestrator/app/core/roundtable/
├── tool.py                    # 工具抽象基类
│   ├── Tool (ABC)             # 抽象基类
│   ├── FunctionTool           # 函数包装工具
│   └── MCPTool                # MCP远程服务工具
├── mcp_client.py              # MCP客户端框架
│   ├── MCPServerType          # 服务器类型枚举
│   ├── MCPServerConnection    # 连接抽象
│   ├── HTTPMCPConnection      # HTTP连接实现
│   ├── LocalMCPConnection     # 本地连接实现
│   └── MCPClient              # 统一MCP客户端
├── mcp_tool_bridge.py         # MCP工具桥接器
│   ├── MCPFinancialDataTool   # 金融数据工具
│   └── MCPCompanyIntelligenceTool  # 企业信息工具
└── mcp_tools.py               # 具体MCP工具实现
    ├── TavilySearchTool       # 搜索工具
    └── PublicDataTool         # 公开数据工具

config/mcp_config.yaml         # MCP服务配置
```

### 当前实现的问题

**❌ 偏离了MCP设计**: 所有工具都变成了直接调用HTTP API的Python类,而不是通过MCP Client统一调用:

```python
# ❌ 当前实现 (mcp_tools.py):
class TavilySearchTool(Tool):
    async def execute(self, query: str, **kwargs):
        # 直接调用HTTP API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.web_search_url}/search",
                json=request_data
            )
        return response.json()
```

**✅ 应该的MCP实现**:
```python
class TavilySearchTool(Tool):
    async def execute(self, query: str, **kwargs):
        # 通过MCP Client调用
        return await mcp_client.call_tool(
            server_name="web-search",
            tool_name="search",
            query=query,
            **kwargs
        )
```

---

## 重构目标

### 1. 统一所有工具调用通过MCP框架

**现在的混乱状态**:
- ✅ Tavily Search: 直接HTTP调用 `web_search_service:8010`
- ✅ ChinaMarketData: 直接HTTP调用东方财富API
- ✅ GitHubAnalyzer: 直接HTTP调用GitHub API
- ✅ Trading Tools: 直接Python函数调用
- ❌ 没有统一的调用入口
- ❌ 没有统一的监控和日志
- ❌ 没有统一的错误处理

**重构后的MCP统一状态**:
```
Agent → MCP Client → MCP Server → External API/Service

统一优势:
✅ 调用监控: 所有工具调用都有日志和统计
✅ 错误处理: 统一的重试、降级、熔断机制
✅ 服务发现: 支持动态服务注册和发现
✅ 版本管理: 工具版本化和向后兼容
✅ 安全认证: 统一的API Key管理
```

### 2. LLM Native Tool Calling + MCP 混合架构

**完美架构**:
```
┌─────────────────────────────────────────────────────────┐
│ Agent                                                    │
│                                                          │
│ 1. get_tools_schema() → OpenAI format schema            │
│ 2. _call_llm() → /v1/chat/completions                   │
│    - messages: [...]                                     │
│    - tools: [OpenAI schema from MCP tools]               │
│ 3. LLM 返回 tool_calls (OpenAI format)                  │
│ 4. _parse_llm_response():                                │
│    - 提取 tool_calls                                     │
│    - 调用 MCP Client.call_tool()  ← 统一入口            │
│    - 返回结果                                            │
└─────────────────────────────────────────────────────────┘
         ⬇️
┌─────────────────────────────────────────────────────────┐
│ MCP Client (mcp_client.py)                              │
│                                                          │
│ - 路由工具调用到对应的 MCP Server                         │
│ - 处理重试、熔断、降级                                    │
│ - 记录调用历史和统计                                      │
│ - 管理连接池                                             │
└─────────────────────────────────────────────────────────┘
         ⬇️
┌──────────────┬──────────────┬──────────────┬────────────┐
│ Web Search   │ Financial    │ Company      │ Trading    │
│ MCP Server   │ Data MCP     │ Intel MCP    │ MCP Server │
│              │ Server       │ Server       │            │
│ - Tavily     │ - A股数据    │ - 企查查     │ - OKX API  │
│              │ - 港股数据   │ - 天眼查     │ - Paper    │
│              │ - 美股数据   │              │   Trader   │
└──────────────┴──────────────┴──────────────┴────────────┘
```

---

## 实施方案

### 阶段1: 创建 MCP Server Wrappers (包装现有服务)

#### 1.1 Web Search MCP Server (已有服务,添加MCP接口)

**文件**: `backend/services/web_search_service/app/mcp_server.py`

```python
"""
Web Search MCP Server
包装 Tavily Search 为 MCP 标准接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from .main import tavily_search  # 复用现有逻辑

router = APIRouter(prefix="/mcp", tags=["MCP"])


class MCPToolRequest(BaseModel):
    """MCP标准工具请求"""
    tool: str
    params: Dict[str, Any]


class MCPToolResponse(BaseModel):
    """MCP标准工具响应"""
    success: bool
    result: Any = None
    error: str = None


@router.post("/tools/{tool_name}")
async def execute_tool(tool_name: str, params: Dict[str, Any]) -> MCPToolResponse:
    """执行MCP工具"""
    try:
        if tool_name == "search":
            # 调用现有的搜索逻辑
            result = await tavily_search(
                query=params.get("query"),
                max_results=params.get("max_results", 3),
                topic=params.get("topic", "general"),
                time_range=params.get("time_range"),
                days=params.get("days")
            )
            return MCPToolResponse(success=True, result=result)

        elif tool_name == "news_search":
            # 新闻搜索
            result = await tavily_search(
                query=params.get("query"),
                max_results=params.get("max_results", 3),
                topic="news",
                time_range=params.get("time_range", "week")
            )
            return MCPToolResponse(success=True, result=result)

        else:
            return MCPToolResponse(
                success=False,
                error=f"Unknown tool: {tool_name}"
            )

    except Exception as e:
        return MCPToolResponse(success=False, error=str(e))


@router.get("/tools")
async def list_tools() -> Dict[str, Any]:
    """列出可用工具"""
    return {
        "tools": [
            {
                "name": "search",
                "description": "搜索互联网获取信息",
                "parameters": {
                    "query": {"type": "string", "required": True},
                    "max_results": {"type": "integer", "default": 3},
                    "topic": {"type": "string", "enum": ["general", "news"]},
                    "time_range": {"type": "string", "enum": ["day", "week", "month", "year"]}
                }
            },
            {
                "name": "news_search",
                "description": "搜索最新新闻",
                "parameters": {
                    "query": {"type": "string", "required": True},
                    "max_results": {"type": "integer", "default": 3},
                    "time_range": {"type": "string", "default": "week"}
                }
            }
        ]
    }
```

#### 1.2 Trading MCP Server (新建独立MCP服务)

**文件**: `backend/services/report_orchestrator/app/core/trading/mcp_server.py`

```python
"""
Trading MCP Server
将交易工具暴露为MCP接口
"""
from typing import Dict, Any
from .trading_tools import TradingToolsManager


class TradingMCPServer:
    """交易工具MCP服务器"""

    def __init__(self, tools_manager: TradingToolsManager):
        self.tools_manager = tools_manager
        self.tools = {
            "open_long": self._open_long,
            "open_short": self._open_short,
            "close_position": self._close_position,
            "get_position": self._get_position,
            "get_balance": self._get_balance,
            "get_market_data": self._get_market_data,
            "get_technical_indicators": self._get_technical_indicators
        }

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行MCP工具调用"""
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "summary": f"工具 '{tool_name}' 不存在"
            }

        handler = self.tools[tool_name]
        try:
            result = await handler(**params)
            return {
                "success": True,
                "result": result,
                "summary": result.get("summary", "")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"工具调用失败: {str(e)}"
            }

    def list_tools(self) -> list:
        """列出可用工具"""
        return [
            {
                "name": "open_long",
                "description": "开多仓",
                "parameters": {
                    "leverage": {"type": "integer", "required": True},
                    "amount_usdt": {"type": "number", "required": True},
                    "tp_percent": {"type": "number", "required": True},
                    "sl_percent": {"type": "number", "required": True},
                    "reason": {"type": "string"}
                }
            },
            {
                "name": "open_short",
                "description": "开空仓",
                "parameters": {
                    "leverage": {"type": "integer", "required": True},
                    "amount_usdt": {"type": "number", "required": True},
                    "tp_percent": {"type": "number", "required": True},
                    "sl_percent": {"type": "number", "required": True},
                    "reason": {"type": "string"}
                }
            },
            # ... 其他工具
        ]

    async def _open_long(self, **params):
        """开多仓"""
        return await self.tools_manager._tools['open_long'].func(**params)

    async def _open_short(self, **params):
        """开空仓"""
        return await self.tools_manager._tools['open_short'].func(**params)

    # ... 其他工具实现
```

#### 1.3 Financial Data MCP Server (新建)

**文件**: `backend/services/financial_data_mcp/app/main.py` (新服务)

```python
"""
Financial Data MCP Server
统一金融数据服务
"""
from fastapi import FastAPI
from typing import Dict, Any

app = FastAPI(title="Financial Data MCP Server")


# 导入现有的工具逻辑
from app.core.roundtable.enhanced_tools import ChinaMarketDataTool

china_market = ChinaMarketDataTool()


@app.post("/mcp/tools/{tool_name}")
async def execute_tool(tool_name: str, params: Dict[str, Any]):
    """执行MCP工具"""
    if tool_name == "china_stock_quote":
        result = await china_market.execute(
            symbol=params["symbol"],
            action="quote"
        )
        return {"success": True, "result": result}

    elif tool_name == "china_stock_kline":
        result = await china_market.execute(
            symbol=params["symbol"],
            action="kline",
            period=params.get("period", "daily"),
            limit=params.get("limit", 60)
        )
        return {"success": True, "result": result}

    # ... 其他工具


@app.get("/mcp/tools")
async def list_tools():
    """列出可用工具"""
    return {
        "tools": [
            {
                "name": "china_stock_quote",
                "description": "获取A股实时行情",
                "parameters": {
                    "symbol": {"type": "string", "required": True}
                }
            },
            {
                "name": "china_stock_kline",
                "description": "获取A股K线数据",
                "parameters": {
                    "symbol": {"type": "string", "required": True},
                    "period": {"type": "string", "default": "daily"},
                    "limit": {"type": "integer", "default": 60}
                }
            }
        ]
    }
```

---

### 阶段2: 重构所有工具为MCP Tool Wrappers

#### 2.1 修改 `mcp_tools.py` 使用MCP Client

**修改前**:
```python
class TavilySearchTool(Tool):
    async def execute(self, query: str, **kwargs):
        # ❌ 直接HTTP调用
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.web_search_url}/search", ...)
        return response.json()
```

**修改后**:
```python
class TavilySearchTool(Tool):
    """Tavily搜索工具 - MCP方式"""

    def __init__(self, mcp_client: MCPClient = None):
        super().__init__(
            name="tavily_search",
            description="搜索互联网获取最新信息..."
        )
        self.mcp_client = mcp_client or get_mcp_client()

    async def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """执行搜索 - 通过MCP Client"""
        try:
            # ✅ 通过MCP Client统一调用
            result = await self.mcp_client.call_tool(
                server_name="web-search",
                tool_name="search",
                query=query,
                max_results=kwargs.get("max_results", 3),
                topic=kwargs.get("topic", "general"),
                time_range=kwargs.get("time_range"),
                days=kwargs.get("days")
            )

            # 统一格式化返回
            if result.get("success"):
                return {
                    "success": True,
                    "summary": result.get("result", {}).get("summary", ""),
                    "results": result.get("result", {}).get("results", [])
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error"),
                    "summary": f"搜索失败: {result.get('error')}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"MCP调用异常: {str(e)}"
            }
```

#### 2.2 重构 `enhanced_tools.py` 为MCP Wrappers

```python
class ChinaMarketDataTool(Tool):
    """中国市场数据工具 - MCP方式"""

    def __init__(self, mcp_client: MCPClient = None):
        super().__init__(
            name="china_market_data",
            description="获取中国A股和港股市场数据..."
        )
        self.mcp_client = mcp_client or get_mcp_client()

    async def execute(self, symbol: str, action: str = "quote", **kwargs):
        """通过MCP获取市场数据"""
        tool_name_map = {
            "quote": "china_stock_quote",
            "kline": "china_stock_kline",
            "finance": "china_financial_report"
        }

        tool_name = tool_name_map.get(action)
        if not tool_name:
            return {"success": False, "error": f"Unknown action: {action}"}

        # 通过MCP Client调用
        return await self.mcp_client.call_tool(
            server_name="financial-data",
            tool_name=tool_name,
            symbol=symbol,
            **kwargs
        )
```

#### 2.3 重构Trading Tools使用MCP

**修改 `trading_tools.py`**:

```python
class TradingToolsManager:
    """交易工具管理器 - MCP本地模式"""

    def __init__(self, config: TradingConfig, paper_trader, mcp_client: MCPClient = None):
        self.config = config
        self.paper_trader = paper_trader
        self.mcp_client = mcp_client or get_mcp_client()

        # 注册到本地MCP Server
        self._register_to_local_mcp()

        self._tools = {}
        self._register_tools()

    def _register_to_local_mcp(self):
        """注册到本地MCP服务器"""
        # 创建本地MCP配置
        local_config = MCPServerConfig(
            name="local-trading",
            server_type=MCPServerType.LOCAL,
            url="",
            description="本地交易工具服务",
            tools=["open_long", "open_short", "close_position", "get_position", "get_balance"],
            enabled=True
        )
        self.mcp_client.register_server(local_config)

        # 获取本地连接并注册工具处理器
        connection = LocalMCPConnection(local_config)
        connection.register_tool("open_long", self._open_long)
        connection.register_tool("open_short", self._open_short)
        connection.register_tool("close_position", self._close_position)
        # ... 注册其他工具

        self.mcp_client.servers["local-trading"] = connection

    def get_tools(self) -> Dict[str, Tool]:
        """返回工具 - MCP包装"""
        mcp_tools = {}

        for tool_name in ["open_long", "open_short", "close_position", "get_position", "get_balance"]:
            # 创建MCP工具包装
            mcp_tool = MCPToolWrapper(
                client=self.mcp_client,
                server_name="local-trading",
                tool_name=tool_name,
                description=self._tools[tool_name].description,
                schema=self._tools[tool_name].parameters_schema
            )
            mcp_tools[tool_name] = mcp_tool

        return mcp_tools
```

---

### 阶段3: 修改Agent使用统一MCP Client

#### 3.1 Agent初始化时创建MCP Client

**修改 `agent.py`**:

```python
class Agent:
    """圆桌讨论Agent"""

    def __init__(
        self,
        name: str,
        role: str,
        system_prompt: str,
        mcp_client: MCPClient = None,  # ← 新增参数
        **kwargs
    ):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt

        # ✅ 使用全局MCP Client
        self.mcp_client = mcp_client or get_mcp_client()

        self.tools: Dict[str, Tool] = {}
        # ...

    def register_tool(self, tool: Tool):
        """注册工具"""
        # 确保工具使用相同的MCP Client
        if hasattr(tool, 'mcp_client'):
            tool.mcp_client = self.mcp_client

        self.tools[tool.name] = tool

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """获取工具Schema - OpenAI格式"""
        tools_schema = []
        for tool in self.tools.values():
            schema = tool.to_schema()
            # 转换为OpenAI format
            tools_schema.append({
                "type": "function",
                "function": {
                    "name": schema["name"],
                    "description": schema["description"],
                    "parameters": schema.get("parameters", {})
                }
            })
        return tools_schema
```

#### 3.2 统一工具执行流程

```python
async def _parse_llm_response(self, llm_response: Dict[str, Any]) -> List[Message]:
    """解析LLM响应并执行工具 - 统一MCP方式"""
    choice = llm_response["choices"][0]
    message = choice["message"]

    # 检查原生tool_calls
    if message.get("tool_calls") and self.tools:
        self.status = "tool_using"
        tool_results = []

        for tool_call in message["tool_calls"]:
            tool_name = tool_call["function"]["name"]
            tool_args_str = tool_call["function"]["arguments"]

            if tool_name in self.tools:
                print(f"[Agent:{self.name}] 🔧 Executing MCP tool: {tool_name}")

                try:
                    tool_args = json.loads(tool_args_str)

                    # ✅ 统一执行:所有工具都通过MCP Client
                    # Tool内部会调用 mcp_client.call_tool()
                    tool_result = await self.tools[tool_name].execute(**tool_args)

                    # 记录MCP调用日志
                    print(f"[Agent:{self.name}] ✅ MCP tool result: {tool_result.get('summary', 'OK')}")

                    if isinstance(tool_result, dict) and "summary" in tool_result:
                        tool_results.append(f"\n[{tool_name}结果]: {tool_result['summary']}")
                    else:
                        tool_results.append(f"\n[{tool_name}结果]: {str(tool_result)[:500]}")

                except Exception as e:
                    print(f"[Agent:{self.name}] ❌ MCP tool failed: {e}")
                    tool_results.append(f"\n[{tool_name}错误]: {str(e)}")

        # 返回工具结果
        if tool_results:
            combined_result = "".join(tool_results)
            return [Message(
                agent_name=self.name,
                content=combined_result,
                message_type=MessageType.INFORMATION
            )]

        self.status = "idle"
        return []

    # 普通响应
    content = message.get("content", "")
    return [Message(
        agent_name=self.name,
        content=content,
        message_type=MessageType.INFORMATION
    )]
```

---

### 阶段4: 配置和部署

#### 4.1 更新 `mcp_config.yaml`

```yaml
mcp_servers:
  # Web Search (已有服务)
  - name: web-search
    type: http
    url: http://web_search_service:8010/mcp
    description: "网络搜索服务 - Tavily"
    enabled: true
    tools:
      - search
      - news_search

  # Financial Data (新MCP服务)
  - name: financial-data
    type: http
    url: http://financial_data_mcp:8020/mcp
    description: "金融数据服务"
    enabled: true
    tools:
      - china_stock_quote
      - china_stock_kline
      - china_financial_report

  # Company Intelligence (新MCP服务)
  - name: company-intelligence
    type: http
    url: http://company_intelligence_mcp:8021/mcp
    description: "企业信息服务"
    enabled: true
    tools:
      - company_basic_info
      - company_shareholders

  # Local Trading (本地MCP)
  - name: local-trading
    type: local
    url: ""
    description: "本地交易工具"
    enabled: true
    tools:
      - open_long
      - open_short
      - close_position
      - get_position
      - get_balance
```

#### 4.2 初始化MCP Client

**修改 `report_orchestrator/app/main.py`**:

```python
from app.core.roundtable.mcp_client import get_mcp_client, MCPClient
import os

# 全局MCP客户端
mcp_client: MCPClient = None


@app.on_event("startup")
async def startup_event():
    """启动时初始化MCP Client"""
    global mcp_client

    config_path = os.path.join(
        os.path.dirname(__file__),
        "../config/mcp_config.yaml"
    )

    # 初始化全局MCP Client
    mcp_client = get_mcp_client(config_path)

    print("[Startup] MCP Client initialized")
    print(f"[Startup] Available servers: {list(mcp_client.config.keys())}")

    # 预连接所有服务器
    for server_name in mcp_client.config.keys():
        if mcp_client.config[server_name].enabled:
            try:
                await mcp_client.connect(server_name)
                print(f"[Startup] ✅ Connected to MCP server: {server_name}")
            except Exception as e:
                print(f"[Startup] ⚠️ Failed to connect to {server_name}: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时断开所有MCP连接"""
    global mcp_client
    if mcp_client:
        await mcp_client.disconnect()
        print("[Shutdown] MCP Client disconnected")
```

---

## 实施优势

### 1. 统一监控和日志

```python
# 查看所有MCP调用统计
stats = mcp_client.get_statistics()

"""
{
    "total_calls": 1523,
    "success_count": 1498,
    "failed_count": 25,
    "success_rate": 0.984,
    "avg_duration_ms": 245.3,
    "by_server": {
        "web-search": {"calls": 532, "success": 528},
        "financial-data": {"calls": 421, "success": 419},
        "local-trading": {"calls": 570, "success": 551}
    }
}
"""

# 查看调用历史
history = mcp_client.get_call_history(limit=10)
for call in history:
    print(f"{call.server}.{call.tool}: {call.duration_ms}ms - {'✅' if call.result else '❌'}")
```

### 2. 统一错误处理和重试

```python
# mcp_client.py 中已实现:
- 自动重试 (retry_count配置)
- 熔断机制 (circuit_breaker配置)
- 超时控制 (timeout配置)
- 降级处理 (fallback)
```

### 3. 统一认证管理

```yaml
# mcp_config.yaml
mcp_servers:
  - name: web-search
    auth:
      api_key: "${TAVILY_API_KEY}"  # 从环境变量读取

  - name: financial-data
    auth:
      api_key: "${FINANCIAL_DATA_API_KEY}"
```

### 4. 服务发现和动态路由

```python
# 未来支持Consul/Etcd服务发现
service_discovery:
  enabled: true
  type: consul
  address: "consul:8500"

# MCP Client自动发现新服务
```

---

## 对比: 重构前 vs 重构后

### 调用流程对比

**重构前 (混乱状态)**:
```
Agent → Tavily Tool → httpx.post("web_search:8010/search")
Agent → ChinaMarket Tool → httpx.get("eastmoney.com/api")
Agent → GitHub Tool → httpx.get("api.github.com")
Agent → Trading Tool → direct function call

❌ 没有统一入口
❌ 没有统一监控
❌ 没有统一错误处理
```

**重构后 (MCP统一)**:
```
Agent → Tool.execute() → MCP Client.call_tool() → MCP Server → External API

✅ 统一调用入口
✅ 统一监控和日志
✅ 统一错误处理和重试
✅ 统一认证管理
```

### 代码对比

**重构前**:
```python
# 50+ 行HTTP调用代码
class TavilySearchTool(Tool):
    async def execute(self, query: str, **kwargs):
        try:
            request_data = {"query": query, ...}
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.web_search_url}/search",
                    json=request_data
                )
                response.raise_for_status()
                result = response.json()
                # 格式化结果 ...
                return {"success": True, "summary": "...", ...}
        except Exception as e:
            return {"success": False, "error": str(e)}
```

**重构后**:
```python
# 15行,简洁清晰
class TavilySearchTool(Tool):
    async def execute(self, query: str, **kwargs):
        return await self.mcp_client.call_tool(
            server_name="web-search",
            tool_name="search",
            query=query,
            **kwargs
        )
```

---

## 实施步骤

### 第1周: MCP Server包装现有服务

- [ ] 1.1 为 web_search_service 添加 MCP 接口 (`/mcp/tools/{tool}`)
- [ ] 1.2 创建 Trading MCP Server (本地模式)
- [ ] 1.3 测试MCP接口可用性

### 第2周: 重构工具为MCP Wrappers

- [ ] 2.1 重构 `mcp_tools.py` (Tavily, PublicData)
- [ ] 2.2 重构 `enhanced_tools.py` (ChinaMarket, GitHub等)
- [ ] 2.3 重构 `trading_tools.py` 使用本地MCP

### 第3周: Agent集成和测试

- [ ] 3.1 修改Agent使用MCP Client
- [ ] 3.2 更新 `investment_agents.py` 的工具注册
- [ ] 3.3 全面测试所有场景 (投资分析、交易)

### 第4周: 新建独立MCP服务 (可选)

- [ ] 4.1 创建 `financial_data_mcp` 服务
- [ ] 4.2 创建 `company_intelligence_mcp` 服务
- [ ] 4.3 Docker Compose配置和部署

---

## 文件清单

### 需要修改的文件

1. **backend/services/web_search_service/app/main.py**
   - 添加 `/mcp/tools/{tool}` 端点
   - 添加 `/mcp/tools` 列表端点

2. **backend/services/report_orchestrator/app/core/roundtable/mcp_tools.py**
   - 修改 `TavilySearchTool` 使用 MCP Client
   - 修改 `PublicDataTool` 使用 MCP Client

3. **backend/services/report_orchestrator/app/core/roundtable/enhanced_tools.py**
   - 修改 `ChinaMarketDataTool` 使用 MCP Client
   - 修改 `GitHubAnalyzerTool` 使用 MCP Client
   - 修改其他工具使用 MCP Client

4. **backend/services/report_orchestrator/app/core/trading/trading_tools.py**
   - 添加本地MCP Server注册
   - 返回MCP Tool Wrappers

5. **backend/services/report_orchestrator/app/core/roundtable/agent.py**
   - 添加 `mcp_client` 参数
   - 修改工具执行逻辑

6. **backend/services/report_orchestrator/app/main.py**
   - 启动时初始化MCP Client
   - 关闭时断开MCP连接

7. **backend/services/report_orchestrator/config/mcp_config.yaml**
   - 更新所有MCP服务器配置

### 新建的文件 (可选)

8. **backend/services/financial_data_mcp/** (新服务)
   - Dockerfile
   - requirements.txt
   - app/main.py
   - app/tools/china_market.py
   - app/tools/us_market.py

9. **backend/services/company_intelligence_mcp/** (新服务)
   - Dockerfile
   - requirements.txt
   - app/main.py
   - app/tools/qichacha.py
   - app/tools/tianyancha.py

---

## 总结

### 为什么需要MCP统一

你的原始设计非常正确! MCP架构提供了:

1. **统一接口**: 所有工具通过相同的方式调用
2. **服务解耦**: Agent不需要知道工具的具体实现
3. **可扩展性**: 新增工具只需注册到MCP,无需修改Agent
4. **可监控性**: 统一的调用日志和统计
5. **可维护性**: 工具逻辑集中在MCP Server,易于维护
6. **可测试性**: 可以mock MCP Server进行测试

### 为什么之前没实现

可能的原因:
- 快速开发,直接调用HTTP API更快
- 工具较少时,统一框架显得过度设计
- MCP框架需要前期投入

### 现在重构的价值

随着工具增多(Tavily, ChinaMarket, GitHub, Trading等),统一MCP框架的价值开始显现:
- 避免重复的HTTP调用代码
- 统一错误处理和重试逻辑
- 统一认证和配置管理
- 为未来扩展打好基础

**建议立即开始重构!** 🚀
