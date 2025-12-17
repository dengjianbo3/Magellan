"""
Trading Interfaces Module

Abstract base classes defining contracts for trading system components.
These interfaces enable dependency injection and testability.
"""

from .trader import ITrader
from .llm_gateway import ILLMGateway
from .memory_store import IMemoryStore
from .tool import ITool, ToolResult

__all__ = [
    "ITrader",
    "ILLMGateway", 
    "IMemoryStore",
    "ITool",
    "ToolResult",
]
