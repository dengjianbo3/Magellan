"""
ITool Interface

Abstract base class for all trading system tools.
Tools are functions that agents can call to interact with external systems.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import json


class ToolCategory(Enum):
    """Categories of tools for organization."""
    MARKET = "market"  # Market data tools
    TRADING = "trading"  # Trade execution tools
    SEARCH = "search"  # Web search tools
    ACCOUNT = "account"  # Account info tools
    ANALYSIS = "analysis"  # Analysis tools


@dataclass
class ToolResult:
    """Result from tool execution."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    tool_name: str = ""
    execution_time_ms: float = 0.0
    
    def to_string(self) -> str:
        """Convert result to string for agent consumption."""
        if self.success:
            return json.dumps(self.data, ensure_ascii=False, indent=2)
        return f"Error: {self.error}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "tool_name": self.tool_name
        }


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    type: str  # "string", "integer", "number", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None


class ITool(ABC):
    """
    Abstract base class for all tools.
    
    Tools provide agents with the ability to interact with
    external systems (market data, trading, search, etc.).
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description for LLM."""
        pass
    
    @property
    @abstractmethod
    def category(self) -> ToolCategory:
        """Tool category for organization."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """List of parameters this tool accepts."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult with execution outcome
        """
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get OpenAI function calling schema.
        
        Returns:
            Schema dict in OpenAI format
        """
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
                
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
    
    def validate_params(self, **kwargs) -> Optional[str]:
        """
        Validate parameters before execution.
        
        Returns:
            Error message if validation fails, None if valid
        """
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                return f"Missing required parameter: {param.name}"
        return None
