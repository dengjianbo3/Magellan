"""
Text Inferrer

Infers trading direction from free-form text when JSON parsing fails.
Uses keyword analysis and sentiment scoring.
"""

import re
from typing import Tuple
from ..domain.vote import Vote, VoteDirection


class TextInferrer:
    """
    Infers trading signals from unstructured text responses.
    
    Fallback mechanism when LLM doesn't provide structured JSON output.
    Uses balanced keyword analysis to avoid directional bias.
    """
    
    # Bullish keywords with weights
    BULLISH_KEYWORDS = {
        # Strong signals (weight 2)
        "strong buy": 2,
        "strongly bullish": 2,
        "definitely long": 2,
        "recommend long": 2,
        "go long": 2,
        "enter long": 2,
        "open long": 2,
        
        # Medium signals (weight 1)
        "bullish": 1,
        "long": 1,
        "buy": 1,
        "uptrend": 1,
        "upward": 1,
        "positive": 1,
        "support holding": 1,
        "breakout": 1,
        "rally": 1,
        "bounce": 1,
        
        # Chinese keywords
        "看涨": 1,
        "做多": 2,
        "开多": 2,
        "多头": 1,
        "上涨": 1,
        "突破": 1,
    }
    
    # Bearish keywords with weights
    BEARISH_KEYWORDS = {
        # Strong signals (weight 2)
        "strong sell": 2,
        "strongly bearish": 2,
        "definitely short": 2,
        "recommend short": 2,
        "go short": 2,
        "enter short": 2,
        "open short": 2,
        
        # Medium signals (weight 1)
        "bearish": 1,
        "short": 1,
        "sell": 1,
        "downtrend": 1,
        "downward": 1,
        "negative": 1,
        "breakdown": 1,
        "decline": 1,
        "drop": 1,
        "fall": 1,
        
        # Chinese keywords
        "看跌": 1,
        "做空": 2,
        "开空": 2,
        "空头": 1,
        "下跌": 1,
        "跌破": 1,
    }
    
    # Neutral/Hold keywords
    NEUTRAL_KEYWORDS = {
        "hold": 1,
        "wait": 1,
        "neutral": 1,
        "unclear": 1,
        "uncertain": 1,
        "sideways": 1,
        "consolidation": 1,
        "mixed signals": 1,
        "no clear": 1,
        "观望": 1,
        "等待": 1,
        "震荡": 1,
    }
    
    @classmethod
    def infer(cls, text: str) -> Vote:
        """
        Infer vote from text content.
        
        Uses balanced keyword scoring to determine direction.
        Defaults to HOLD when signals are mixed or unclear.
        
        Args:
            text: Free-form text response from agent
            
        Returns:
            Vote with inferred direction and estimated confidence
        """
        if not text:
            return Vote(
                direction=VoteDirection.HOLD,
                confidence=30,
                reasoning="Empty response"
            )
        
        text_lower = text.lower()
        
        # Calculate scores
        bullish_score = cls._calculate_score(text_lower, cls.BULLISH_KEYWORDS)
        bearish_score = cls._calculate_score(text_lower, cls.BEARISH_KEYWORDS)
        neutral_score = cls._calculate_score(text_lower, cls.NEUTRAL_KEYWORDS)
        
        # Determine direction based on scores
        direction, confidence = cls._determine_direction(
            bullish_score, bearish_score, neutral_score
        )
        
        # Extract any mentioned parameters
        leverage = cls._extract_leverage(text)
        tp_percent = cls._extract_take_profit(text)
        sl_percent = cls._extract_stop_loss(text)
        
        # Build reasoning
        reasoning = cls._build_reasoning(
            text, bullish_score, bearish_score, neutral_score
        )
        
        return Vote(
            direction=direction,
            confidence=confidence,
            leverage=leverage,
            take_profit_percent=tp_percent,
            stop_loss_percent=sl_percent,
            reasoning=reasoning
        )
    
    @classmethod
    def _calculate_score(cls, text: str, keywords: dict) -> int:
        """Calculate weighted score for keyword category."""
        score = 0
        for keyword, weight in keywords.items():
            if keyword in text:
                score += weight
        return score
    
    @classmethod
    def _determine_direction(
        cls,
        bullish: int,
        bearish: int,
        neutral: int
    ) -> Tuple[VoteDirection, int]:
        """
        Determine direction from scores.
        
        Uses balanced logic - requires clear signal difference.
        Defaults to HOLD to avoid false positives.
        """
        # If neutral is dominant, hold
        if neutral > bullish and neutral > bearish:
            return VoteDirection.HOLD, 50
        
        # Require significant difference for directional call
        diff = abs(bullish - bearish)
        total = bullish + bearish + neutral
        
        if total == 0:
            return VoteDirection.HOLD, 30
        
        # Need at least 2x difference for strong signal
        if bullish > bearish * 2 and bullish >= 2:
            confidence = min(85, 50 + diff * 5)
            return VoteDirection.LONG, confidence
        
        if bearish > bullish * 2 and bearish >= 2:
            confidence = min(85, 50 + diff * 5)
            return VoteDirection.SHORT, confidence
        
        # Slight preference but not strong enough
        if bullish > bearish:
            return VoteDirection.LONG, 45 + min(20, diff * 3)
        elif bearish > bullish:
            return VoteDirection.SHORT, 45 + min(20, diff * 3)
        
        # Equal or no clear signal
        return VoteDirection.HOLD, 40
    
    @classmethod
    def _extract_leverage(cls, text: str) -> int:
        """Extract leverage from text."""
        patterns = [
            r'leverage[:\s]+(\d+)',
            r'(\d+)x\s*leverage',
            r'(\d+)x',
            r'杠杆[:\s]*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                leverage = int(match.group(1))
                return max(1, min(125, leverage))
        
        return 3  # Default leverage
    
    @classmethod
    def _extract_take_profit(cls, text: str) -> float:
        """Extract take profit percentage from text."""
        patterns = [
            r'take[_\s]?profit[:\s]+(\d+\.?\d*)\s*%',
            r'tp[:\s]+(\d+\.?\d*)\s*%',
            r'止盈[:\s]*(\d+\.?\d*)\s*%',
            r'(\d+\.?\d*)\s*%\s*(?:take[_\s]?profit|tp)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                tp = float(match.group(1))
                return max(1.0, min(20.0, tp))
        
        return 5.0  # Default TP
    
    @classmethod
    def _extract_stop_loss(cls, text: str) -> float:
        """Extract stop loss percentage from text."""
        patterns = [
            r'stop[_\s]?loss[:\s]+(\d+\.?\d*)\s*%',
            r'sl[:\s]+(\d+\.?\d*)\s*%',
            r'止损[:\s]*(\d+\.?\d*)\s*%',
            r'(\d+\.?\d*)\s*%\s*(?:stop[_\s]?loss|sl)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                sl = float(match.group(1))
                return max(0.5, min(10.0, sl))
        
        return 2.0  # Default SL
    
    @classmethod
    def _build_reasoning(
        cls,
        text: str,
        bullish: int,
        bearish: int,
        neutral: int
    ) -> str:
        """Build reasoning summary from scores."""
        parts = []
        
        if bullish > 0:
            parts.append(f"bullish signals ({bullish})")
        if bearish > 0:
            parts.append(f"bearish signals ({bearish})")
        if neutral > 0:
            parts.append(f"neutral signals ({neutral})")
        
        if parts:
            return f"Text inference: {', '.join(parts)}"
        return "Text inference: no clear signals detected"
