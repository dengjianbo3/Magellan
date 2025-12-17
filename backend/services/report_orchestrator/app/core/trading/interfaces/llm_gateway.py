"""
ILLMGateway Interface

Abstract base class for LLM gateway implementations.
Enables mocking LLM calls for testing.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class LLMMessage:
    """Represents a single message in a conversation."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: Optional[str] = None  # Agent or tool name
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None


@dataclass
class LLMResponse:
    """Response from LLM call."""
    content: str
    tool_calls: Optional[List[Dict]] = None
    finish_reason: str = "stop"
    usage: Dict[str, int] = field(default_factory=dict)
    model: str = ""
    
    @property
    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return self.tool_calls is not None and len(self.tool_calls) > 0


@dataclass 
class ToolSchema:
    """Schema for a tool that can be called by LLM."""
    name: str
    description: str
    parameters: Dict[str, Any]
    
    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class ILLMGateway(ABC):
    """
    Abstract LLM gateway interface.
    
    Provides a consistent interface for calling language models,
    enabling easy mocking for tests and swapping implementations.
    """
    
    @abstractmethod
    async def call(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[ToolSchema]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> LLMResponse:
        """
        Call the LLM with messages and optional tools.
        
        Args:
            messages: Conversation history
            tools: Available tools for function calling
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
            model: Override default model
            
        Returns:
            LLMResponse with model output
        """
        pass
    
    @abstractmethod
    async def call_with_retry(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[ToolSchema]] = None,
        temperature: float = 0.7,
        max_retries: int = 3
    ) -> LLMResponse:
        """
        Call LLM with automatic retry on transient failures.
        
        Args:
            messages: Conversation history
            tools: Available tools for function calling
            temperature: Sampling temperature
            max_retries: Maximum retry attempts
            
        Returns:
            LLMResponse with model output
        """
        pass
    
    @property
    @abstractmethod
    def default_model(self) -> str:
        """Get the default model name."""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the LLM service is available."""
        pass
