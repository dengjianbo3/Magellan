"""
Tool: MCP-based capabilities that agents can use
工具: Agent可以使用的基于MCP的能力
"""
from typing import Any, Dict, Optional, Callable
from pydantic import BaseModel
from abc import ABC, abstractmethod


class Tool(ABC):
    """
    工具抽象基类

    代表Agent可以使用的非LLM能力（如API调用、数据库查询、代码执行等）
    设计遵循MCP(Model Context Protocol)理念
    """

    def __init__(self, name: str, description: str):
        """
        初始化工具

        Args:
            name: 工具的程序化名称（如"get_stock_price"）
            description: 工具的自然语言描述（供LLM理解何时使用）
        """
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        执行工具的实际功能

        Args:
            **kwargs: 工具所需的参数

        Returns:
            工具执行的结果
        """
        pass

    def to_schema(self) -> Dict[str, Any]:
        """
        将工具转换为LLM可理解的JSON Schema格式

        Returns:
            工具的Schema描述
        """
        return {
            "name": self.name,
            "description": self.description,
            # 子类可以扩展添加parameters等字段
        }


class FunctionTool(Tool):
    """
    基于函数的工具实现

    允许快速将Python函数包装为Tool
    """

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable,
        parameters_schema: Optional[Dict[str, Any]] = None
    ):
        """
        Args:
            name: 工具名称
            description: 工具描述
            func: 要执行的函数
            parameters_schema: 参数的JSON Schema（可选）
        """
        super().__init__(name, description)
        self.func = func
        self.parameters_schema = parameters_schema or {}

    async def execute(self, **kwargs) -> Any:
        """执行包装的函数"""
        import asyncio
        import inspect

        # 检查函数是否为协程
        if inspect.iscoroutinefunction(self.func):
            return await self.func(**kwargs)
        else:
            # 在线程池中执行同步函数
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: self.func(**kwargs))

    def to_schema(self) -> Dict[str, Any]:
        """返回包含参数的完整Schema"""
        schema = super().to_schema()
        if self.parameters_schema:
            schema["parameters"] = self.parameters_schema
        return schema


class MCPTool(Tool):
    """
    MCP (Model Context Protocol) 工具

    用于集成外部MCP服务的工具
    """

    def __init__(
        self,
        name: str,
        description: str,
        mcp_server_url: str,
        mcp_method: str,
        parameters_schema: Optional[Dict[str, Any]] = None
    ):
        """
        Args:
            name: 工具名称
            description: 工具描述
            mcp_server_url: MCP服务器URL
            mcp_method: 要调用的MCP方法名
            parameters_schema: 参数Schema
        """
        super().__init__(name, description)
        self.mcp_server_url = mcp_server_url
        self.mcp_method = mcp_method
        self.parameters_schema = parameters_schema or {}

    async def execute(self, **kwargs) -> Any:
        """通过MCP协议调用远程服务"""
        import httpx
        import json

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.mcp_server_url,
                json={
                    "method": self.mcp_method,
                    "params": kwargs
                },
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            return result.get("result", result)

    def to_schema(self) -> Dict[str, Any]:
        """返回包含MCP信息的Schema"""
        schema = super().to_schema()
        schema.update({
            "parameters": self.parameters_schema,
            "mcp_server": self.mcp_server_url,
            "mcp_method": self.mcp_method
        })
        return schema
