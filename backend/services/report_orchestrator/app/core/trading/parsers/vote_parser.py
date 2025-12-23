"""
Vote Parser

Parses agent responses into Vote objects.
Handles JSON, text inference, and various edge cases.
"""

import json
import re
import logging
from dataclasses import dataclass
from typing import Optional

from ..domain.vote import Vote, VoteDirection
from .direction_normalizer import DirectionNormalizer
from .text_inferrer import TextInferrer

logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    """Result of parsing attempt."""
    success: bool
    vote: Optional[Vote] = None
    method: str = ""  # "json", "json_in_code_block", "text_inference", "fallback"
    error: Optional[str] = None
    raw_response: str = ""


class VoteParser:
    """
    Parses LLM responses into Vote objects.
    
    Tries multiple parsing strategies:
    1. Direct JSON parsing
    2. JSON in code block (```json ... ```)
    3. JSON in response text
    4. Text inference from keywords
    5. Fallback to HOLD
    """
    
    # Required fields for valid vote JSON
    REQUIRED_FIELDS = ["direction"]
    
    # Optional fields with defaults
    OPTIONAL_FIELDS = {
        "confidence": 50,
        "leverage": 3,
        "take_profit_percent": 5.0,
        "stop_loss_percent": 2.0,
        "reasoning": ""
    }
    
    def parse(self, response: str) -> ParseResult:
        """
        Parse response into Vote.
        
        Tries multiple strategies in order of preference.
        
        Args:
            response: Raw LLM response text
            
        Returns:
            ParseResult with vote and metadata
        """
        if not response or not response.strip():
            return ParseResult(
                success=False,
                vote=self._fallback_vote(),
                method="fallback",
                error="Empty response",
                raw_response=response or ""
            )
        
        # Strategy 1: Try direct JSON
        result = self._try_direct_json(response)
        if result.success:
            return result
        
        # Strategy 2: Try JSON in code block
        result = self._try_code_block_json(response)
        if result.success:
            return result
        
        # Strategy 3: Try to find JSON in text
        result = self._try_embedded_json(response)
        if result.success:
            return result
        
        # Strategy 4: Text inference
        result = self._try_text_inference(response)
        if result.success:
            return result
        
        # Strategy 5: Fallback
        return ParseResult(
            success=True,
            vote=self._fallback_vote(),
            method="fallback",
            raw_response=response
        )
    
    def _try_direct_json(self, response: str) -> ParseResult:
        """Try to parse response as direct JSON."""
        try:
            data = json.loads(response.strip())
            vote = self._json_to_vote(data)
            return ParseResult(
                success=True,
                vote=vote,
                method="json",
                raw_response=response
            )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            return ParseResult(
                success=False,
                error=str(e),
                raw_response=response
            )
    
    def _try_code_block_json(self, response: str) -> ParseResult:
        """Try to extract JSON from code block."""
        patterns = [
            r'```json\s*\n?(.*?)\n?```',
            r'```\s*\n?(.*?)\n?```',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                json_str = match.group(1).strip()
                try:
                    data = json.loads(json_str)
                    vote = self._json_to_vote(data)
                    return ParseResult(
                        success=True,
                        vote=vote,
                        method="json_in_code_block",
                        raw_response=response
                    )
                except (json.JSONDecodeError, ValueError, KeyError):
                    continue
        
        return ParseResult(success=False, raw_response=response)
    
    def _try_embedded_json(self, response: str) -> ParseResult:
        """Try to find JSON object embedded in text."""
        # Look for JSON object pattern
        patterns = [
            r'\{[^{}]*"direction"[^{}]*\}',
            r'\{[^{}]*"vote"[^{}]*\}',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                json_str = match.group(0)
                try:
                    data = json.loads(json_str)
                    vote = self._json_to_vote(data)
                    return ParseResult(
                        success=True,
                        vote=vote,
                        method="embedded_json",
                        raw_response=response
                    )
                except (json.JSONDecodeError, ValueError, KeyError):
                    continue
        
        return ParseResult(success=False, raw_response=response)
    
    def _try_text_inference(self, response: str) -> ParseResult:
        """Infer vote from text content."""
        try:
            vote = TextInferrer.infer(response)
            return ParseResult(
                success=True,
                vote=vote,
                method="text_inference",
                raw_response=response
            )
        except Exception as e:
            logger.warning(f"Text inference failed: {e}")
            return ParseResult(
                success=False,
                error=str(e),
                raw_response=response
            )
    
    def _json_to_vote(self, data: dict) -> Vote:
        """Convert JSON dict to Vote object."""
        # Handle nested "vote" key
        if "vote" in data and isinstance(data["vote"], dict):
            data = data["vote"]
        
        # Get direction (required)
        direction_raw = data.get("direction", "")
        if not direction_raw:
            raise ValueError("Missing required field: direction")
        
        direction = DirectionNormalizer.normalize(str(direction_raw))
        
        # Get optional fields with defaults
        confidence = self._safe_int(data.get("confidence"), 50, 0, 100)
        leverage = self._safe_int(data.get("leverage"), 3, 1, 125)
        
        tp_percent = self._safe_float(
            data.get("take_profit_percent") or data.get("tp_percent") or data.get("tp"),
            5.0, 0.5, 50.0
        )
        sl_percent = self._safe_float(
            data.get("stop_loss_percent") or data.get("sl_percent") or data.get("sl"),
            2.0, 0.5, 20.0
        )
        
        reasoning = str(data.get("reasoning", "") or data.get("reason", ""))
        
        return Vote(
            direction=direction,
            confidence=confidence,
            leverage=leverage,
            take_profit_percent=tp_percent,
            stop_loss_percent=sl_percent,
            reasoning=reasoning
        )
    
    def _fallback_vote(self) -> Vote:
        """Create fallback HOLD vote."""
        return Vote(
            direction=VoteDirection.HOLD,
            confidence=30,
            leverage=1,
            take_profit_percent=5.0,
            stop_loss_percent=2.0,
            reasoning="Fallback: could not parse response"
        )
    
    @staticmethod
    def _safe_int(value, default: int, min_val: int, max_val: int) -> int:
        """Safely convert to int with bounds."""
        try:
            result = int(value) if value is not None else default
            return max(min_val, min(max_val, result))
        except (TypeError, ValueError):
            return default
    
    @staticmethod
    def _safe_float(value, default: float, min_val: float, max_val: float) -> float:
        """Safely convert to float with bounds."""
        try:
            result = float(value) if value is not None else default
            return max(min_val, min(max_val, result))
        except (TypeError, ValueError):
            return default
