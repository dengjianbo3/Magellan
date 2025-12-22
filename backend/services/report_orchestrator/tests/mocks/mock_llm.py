"""
Mock LLM Gateway

Mock implementation for testing without real LLM calls.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class MockLLMResponse:
    """Mock LLM response."""
    content: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: Dict[str, int] = field(default_factory=lambda: {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150
    })


class MockLLMGateway:
    """
    Mock LLM Gateway for testing.
    
    Allows configuration of responses for testing without real API calls.
    """
    
    def __init__(self):
        """Initialize mock gateway."""
        self.call_history: List[Dict[str, Any]] = []
        self.responses: List[MockLLMResponse] = []
        self._response_index = 0
        self._response_generator: Optional[Callable] = None
    
    def set_responses(self, responses: List[str]) -> None:
        """
        Set list of responses to return in order.
        
        Args:
            responses: List of response strings
        """
        self.responses = [MockLLMResponse(content=r) for r in responses]
        self._response_index = 0
    
    def set_response_generator(self, generator: Callable[[str], str]) -> None:
        """
        Set a function that generates responses based on input.
        
        Args:
            generator: Function that takes prompt and returns response
        """
        self._response_generator = generator
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
        temperature: float = 0.7,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> MockLLMResponse:
        """
        Mock chat completion call.
        
        Args:
            messages: Chat messages
            model: Model name (ignored in mock)
            temperature: Temperature (ignored in mock)
            tools: Tool definitions (ignored in mock)
            
        Returns:
            MockLLMResponse
        """
        # Record the call
        self.call_history.append({
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "tools": tools
        })
        
        # Get last user message for context
        last_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "")
                break
        
        # Use generator if available
        if self._response_generator:
            content = self._response_generator(last_message)
            return MockLLMResponse(content=content)
        
        # Use preset responses
        if self.responses and self._response_index < len(self.responses):
            response = self.responses[self._response_index]
            self._response_index += 1
            return response
        
        # Default response
        return MockLLMResponse(content="Mock LLM response - no preset response")
    
    def reset(self) -> None:
        """Reset state for new test."""
        self.call_history = []
        self._response_index = 0
    
    def get_call_count(self) -> int:
        """Get number of calls made."""
        return len(self.call_history)
    
    def get_last_call(self) -> Optional[Dict[str, Any]]:
        """Get last call made."""
        return self.call_history[-1] if self.call_history else None


class VoteResponseGenerator:
    """
    Generator for realistic vote responses.
    
    Useful for testing vote parsing.
    """
    
    @staticmethod
    def long_vote(confidence: int = 75, leverage: int = 3) -> str:
        """Generate a long vote response."""
        return json.dumps({
            "direction": "long",
            "confidence": confidence,
            "leverage": leverage,
            "take_profit_percent": 5.0,
            "stop_loss_percent": 2.0,
            "reasoning": "Bullish technical signals indicate upward momentum"
        })
    
    @staticmethod
    def short_vote(confidence: int = 70, leverage: int = 3) -> str:
        """Generate a short vote response."""
        return json.dumps({
            "direction": "short",
            "confidence": confidence,
            "leverage": leverage,
            "take_profit_percent": 5.0,
            "stop_loss_percent": 2.0,
            "reasoning": "Bearish divergence and resistance rejection"
        })
    
    @staticmethod
    def hold_vote() -> str:
        """Generate a hold vote response."""
        return json.dumps({
            "direction": "hold",
            "confidence": 50,
            "leverage": 1,
            "take_profit_percent": 0,
            "stop_loss_percent": 0,
            "reasoning": "Market conditions unclear, waiting for clarity"
        })
    
    @staticmethod
    def vote_in_markdown(direction: str = "long", confidence: int = 75) -> str:
        """Generate vote wrapped in markdown code block."""
        vote = {
            "direction": direction,
            "confidence": confidence,
            "leverage": 3,
            "take_profit_percent": 5.0,
            "stop_loss_percent": 2.0,
            "reasoning": "Test vote with markdown wrapper"
        }
        return f"""Based on my analysis, here is my trading recommendation:

```json
{json.dumps(vote, indent=2)}
```

This vote is based on technical indicators showing clear signals."""
