"""
BaseTool and ToolResult

Abstract base class for all trading tools with common functionality.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
import json
import logging
import asyncio

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Categories of trading tools."""
    MARKET = "market"       # Market data tools (price, klines, indicators)
    EXECUTION = "execution"  # Trade execution tools (open, close, modify)
    SEARCH = "search"       # Web search and news tools
    ACCOUNT = "account"     # Account and position info tools
    ANALYSIS = "analysis"   # Technical/sentiment analysis tools


@dataclass
class ToolResult:
    """
    Standardized result from tool execution.
    """
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    tool_name: str = ""
    category: ToolCategory = ToolCategory.MARKET
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_string(self, pretty: bool = True) -> str:
        """Convert result to string for agent consumption."""
        if self.success:
            if pretty:
                return json.dumps(self.data, ensure_ascii=False, indent=2)
            return json.dumps(self.data, ensure_ascii=False)
        return f"Error executing {self.tool_name}: {self.error}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "tool_name": self.tool_name,
            "category": self.category.value,
            "execution_time_ms": self.execution_time_ms
        }
    
    @classmethod
    def success_result(cls, data: Dict[str, Any], tool_name: str = "") -> "ToolResult":
        """Create successful result."""
        return cls(success=True, data=data, tool_name=tool_name)
    
    @classmethod
    def error_result(cls, error: str, tool_name: str = "") -> "ToolResult":
        """Create error result."""
        return cls(success=False, error=error, tool_name=tool_name)


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    type: str  # "string", "integer", "number", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None


class BaseTool(ABC):
    """
    Abstract base class for all trading tools.
    
    All tools should inherit from this class and implement
    the required methods.
    """
    
    # Class-level attributes to be overridden
    name: str = "base_tool"
    description: str = "Base tool description"
    category: ToolCategory = ToolCategory.MARKET
    
    def __init__(self):
        """Initialize the tool."""
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        self._execution_count = 0
        self._total_time_ms = 0.0
    
    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """
        List of parameters this tool accepts.
        
        Returns:
            List of ToolParameter definitions
        """
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
    
    async def safe_execute(self, **kwargs) -> ToolResult:
        """
        Execute tool with error handling and timing.
        
        Wraps execute() with try/catch and performance tracking.
        """
        start = datetime.now()
        try:
            # Validate parameters
            validation_error = self.validate_params(**kwargs)
            if validation_error:
                return ToolResult.error_result(validation_error, self.name)
            
            # Execute
            result = await self.execute(**kwargs)
            
            # Track timing
            elapsed_ms = (datetime.now() - start).total_seconds() * 1000
            result.execution_time_ms = elapsed_ms
            result.tool_name = self.name
            result.category = self.category
            
            # Track stats
            self._execution_count += 1
            self._total_time_ms += elapsed_ms
            
            return result
            
        except asyncio.TimeoutError:
            return ToolResult.error_result(
                f"Tool execution timed out", 
                self.name
            )
        except Exception as e:
            self.logger.error(f"Tool execution error: {e}")
            return ToolResult.error_result(str(e), self.name)
    
    def validate_params(self, **kwargs) -> Optional[str]:
        """
        Validate parameters before execution.
        
        Returns:
            Error message if validation fails, None if valid
        """
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                # Check if there's a default
                if param.default is None:
                    return f"Missing required parameter: {param.name}"
        return None
    
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
            
            if param.required and param.default is None:
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
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        avg_time = (
            self._total_time_ms / self._execution_count 
            if self._execution_count > 0 else 0
        )
        return {
            "name": self.name,
            "category": self.category.value,
            "execution_count": self._execution_count,
            "total_time_ms": self._total_time_ms,
            "avg_time_ms": avg_time
        }
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} category={self.category.value}>"
