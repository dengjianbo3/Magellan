"""
MCP (Model Context Protocol) 客户端框架
为圆桌讨论Agent提供统一的MCP服务访问接口
"""
import os
import yaml
import asyncio
import httpx
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class MCPServerType(Enum):
    """MCP服务器类型"""
    HTTP = "http"           # HTTP API服务
    WEBSOCKET = "websocket" # WebSocket服务
    GRPC = "grpc"           # gRPC服务
    LOCAL = "local"         # 本地函数调用


@dataclass
class MCPServerConfig:
    """MCP服务器配置"""
    name: str
    server_type: MCPServerType
    url: str
    description: str = ""
    tools: List[str] = field(default_factory=list)
    auth: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    retry_count: int = 3
    enabled: bool = True


@dataclass
class MCPToolCall:
    """MCP工具调用记录"""
    server: str
    tool: str
    params: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: float = 0


class MCPServerConnection(ABC):
    """MCP服务器连接抽象基类"""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.connected = False

    @abstractmethod
    async def connect(self) -> bool:
        """建立连接"""
        pass

    @abstractmethod
    async def disconnect(self):
        """断开连接"""
        pass

    @abstractmethod
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        pass

    @abstractmethod
    async def list_tools(self) -> List[Dict[str, Any]]:
        """列出可用工具"""
        pass


class HTTPMCPConnection(MCPServerConnection):
    """HTTP MCP服务器连接"""

    def __init__(self, config: MCPServerConfig):
        super().__init__(config)
        self.client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        """建立HTTP连接"""
        try:
            self.client = httpx.AsyncClient(
                base_url=self.config.url,
                timeout=self.config.timeout,
                headers=self._get_auth_headers()
            )
            # 尝试健康检查
            try:
                response = await self.client.get("/health")
                self.connected = response.status_code == 200
            except:
                # 即使没有health端点，也认为连接成功
                self.connected = True
            return self.connected
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {self.config.name}: {e}")
            return False

    async def disconnect(self):
        """断开HTTP连接"""
        if self.client:
            await self.client.aclose()
            self.client = None
            self.connected = False

    def _get_auth_headers(self) -> Dict[str, str]:
        """获取认证头"""
        headers = {}
        if "api_key" in self.config.auth:
            headers["Authorization"] = f"Bearer {self.config.auth['api_key']}"
        if "x_api_key" in self.config.auth:
            headers["X-API-Key"] = self.config.auth["x_api_key"]
        return headers

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """调用HTTP工具"""
        if not self.client:
            await self.connect()

        try:
            # 标准MCP调用格式
            response = await self.client.post(
                f"/tools/{tool_name}",
                json=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # 尝试备用端点格式
            try:
                response = await self.client.post(
                    f"/{tool_name}",
                    json=params
                )
                response.raise_for_status()
                return response.json()
            except:
                return {
                    "success": False,
                    "error": f"HTTP error: {e.response.status_code}",
                    "summary": f"MCP调用失败: {str(e)}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"MCP调用异常: {str(e)}"
            }

    async def list_tools(self) -> List[Dict[str, Any]]:
        """列出HTTP服务器可用工具"""
        if not self.client:
            await self.connect()

        try:
            response = await self.client.get("/tools")
            response.raise_for_status()
            return response.json().get("tools", [])
        except:
            # 返回配置中定义的工具
            return [{"name": t} for t in self.config.tools]


class LocalMCPConnection(MCPServerConnection):
    """本地MCP连接（直接函数调用）"""

    def __init__(self, config: MCPServerConfig, tool_registry: Dict[str, Callable] = None):
        super().__init__(config)
        self.tool_registry = tool_registry or {}

    async def connect(self) -> bool:
        self.connected = True
        return True

    async def disconnect(self):
        self.connected = False

    def register_tool(self, name: str, handler: Callable):
        """注册本地工具"""
        self.tool_registry[name] = handler

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """调用本地工具"""
        if tool_name not in self.tool_registry:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found",
                "summary": f"工具 '{tool_name}' 未注册"
            }

        handler = self.tool_registry[tool_name]
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**params)
            else:
                result = handler(**params)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"本地工具调用失败: {str(e)}"
            }

    async def list_tools(self) -> List[Dict[str, Any]]:
        return [{"name": name} for name in self.tool_registry.keys()]


class MCPClient:
    """
    MCP客户端

    提供统一的接口访问多个MCP服务器
    """

    def __init__(self, config_path: str = None):
        """
        初始化MCP客户端

        Args:
            config_path: MCP配置文件路径（YAML格式）
        """
        self.servers: Dict[str, MCPServerConnection] = {}
        self.config: Dict[str, MCPServerConfig] = {}
        self.call_history: List[MCPToolCall] = []

        if config_path and os.path.exists(config_path):
            self._load_config(config_path)

    def _load_config(self, config_path: str):
        """加载MCP配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)

            for server_config in config_data.get("mcp_servers", []):
                name = server_config["name"]
                self.config[name] = MCPServerConfig(
                    name=name,
                    server_type=MCPServerType(server_config.get("type", "http")),
                    url=server_config.get("url", ""),
                    description=server_config.get("description", ""),
                    tools=server_config.get("tools", []),
                    auth=self._resolve_auth(server_config.get("auth", {})),
                    timeout=server_config.get("timeout", 30),
                    retry_count=server_config.get("retry_count", 3),
                    enabled=server_config.get("enabled", True)
                )
        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")

    def _resolve_auth(self, auth_config: Dict[str, str]) -> Dict[str, str]:
        """解析认证配置（支持环境变量）"""
        resolved = {}
        for key, value in auth_config.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                resolved[key] = os.environ.get(env_var, "")
            else:
                resolved[key] = value
        return resolved

    def register_server(self, config: MCPServerConfig):
        """注册MCP服务器"""
        self.config[config.name] = config

    async def connect(self, server_name: str) -> MCPServerConnection:
        """连接到指定MCP服务器"""
        if server_name in self.servers and self.servers[server_name].connected:
            return self.servers[server_name]

        if server_name not in self.config:
            raise ValueError(f"Unknown MCP server: {server_name}")

        config = self.config[server_name]

        if not config.enabled:
            raise ValueError(f"MCP server '{server_name}' is disabled")

        # 根据服务器类型创建连接
        if config.server_type == MCPServerType.HTTP:
            connection = HTTPMCPConnection(config)
        elif config.server_type == MCPServerType.LOCAL:
            connection = LocalMCPConnection(config)
        else:
            raise ValueError(f"Unsupported server type: {config.server_type}")

        if await connection.connect():
            self.servers[server_name] = connection
            return connection
        else:
            raise ConnectionError(f"Failed to connect to MCP server: {server_name}")

    async def disconnect(self, server_name: str = None):
        """断开MCP服务器连接"""
        if server_name:
            if server_name in self.servers:
                await self.servers[server_name].disconnect()
                del self.servers[server_name]
        else:
            for name, server in list(self.servers.items()):
                await server.disconnect()
            self.servers.clear()

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        **params
    ) -> Dict[str, Any]:
        """
        调用MCP工具

        Args:
            server_name: MCP服务器名称
            tool_name: 工具名称
            **params: 工具参数

        Returns:
            工具执行结果
        """
        import time
        start_time = time.time()

        call_record = MCPToolCall(
            server=server_name,
            tool=tool_name,
            params=params
        )

        try:
            connection = await self.connect(server_name)
            result = await connection.call_tool(tool_name, params)
            call_record.result = result
        except Exception as e:
            call_record.error = str(e)
            result = {
                "success": False,
                "error": str(e),
                "summary": f"MCP调用失败: {str(e)}"
            }

        call_record.duration_ms = (time.time() - start_time) * 1000
        self.call_history.append(call_record)

        return result

    async def list_tools(self, server_name: str = None) -> Dict[str, List[Dict]]:
        """
        列出可用工具

        Args:
            server_name: 指定服务器名称，None表示所有服务器

        Returns:
            {server_name: [tool_info, ...]}
        """
        result = {}

        servers_to_check = [server_name] if server_name else list(self.config.keys())

        for name in servers_to_check:
            if name not in self.config or not self.config[name].enabled:
                continue
            try:
                connection = await self.connect(name)
                tools = await connection.list_tools()
                result[name] = tools
            except Exception as e:
                logger.warning(f"Failed to list tools from {name}: {e}")
                result[name] = []

        return result

    def get_call_history(self, limit: int = 100) -> List[MCPToolCall]:
        """获取调用历史"""
        return self.call_history[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """获取调用统计"""
        if not self.call_history:
            return {"total_calls": 0}

        total = len(self.call_history)
        success = sum(1 for c in self.call_history if c.result and c.result.get("success"))
        failed = total - success
        avg_duration = sum(c.duration_ms for c in self.call_history) / total

        # 按服务器统计
        by_server = {}
        for call in self.call_history:
            if call.server not in by_server:
                by_server[call.server] = {"calls": 0, "success": 0}
            by_server[call.server]["calls"] += 1
            if call.result and call.result.get("success"):
                by_server[call.server]["success"] += 1

        return {
            "total_calls": total,
            "success_count": success,
            "failed_count": failed,
            "success_rate": success / total if total > 0 else 0,
            "avg_duration_ms": avg_duration,
            "by_server": by_server
        }


class MCPToolWrapper:
    """
    MCP工具包装器

    将MCP服务包装为Tool接口，便于Agent使用
    """

    def __init__(
        self,
        client: MCPClient,
        server_name: str,
        tool_name: str,
        description: str = "",
        schema: Dict[str, Any] = None
    ):
        self.client = client
        self.server_name = server_name
        self.tool_name = tool_name
        self.description = description
        self._schema = schema or {}

    @property
    def name(self) -> str:
        return f"{self.server_name}_{self.tool_name}"

    async def execute(self, **params) -> Dict[str, Any]:
        """执行工具"""
        return await self.client.call_tool(
            self.server_name,
            self.tool_name,
            **params
        )

    def to_schema(self) -> Dict[str, Any]:
        """返回工具Schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self._schema.get("parameters", {
                "type": "object",
                "properties": {},
                "required": []
            })
        }


# 全局MCP客户端实例
_global_mcp_client: Optional[MCPClient] = None


def get_mcp_client(config_path: str = None) -> MCPClient:
    """获取全局MCP客户端"""
    global _global_mcp_client
    if _global_mcp_client is None:
        _global_mcp_client = MCPClient(config_path)
    return _global_mcp_client


def reset_mcp_client():
    """重置全局MCP客户端"""
    global _global_mcp_client
    if _global_mcp_client:
        asyncio.create_task(_global_mcp_client.disconnect())
    _global_mcp_client = None
