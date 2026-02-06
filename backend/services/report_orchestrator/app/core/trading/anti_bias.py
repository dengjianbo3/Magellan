"""
Anti-Bias System - Systematic Solutions for LONG Bias Prevention

This module provides two systematic solutions:
1. Direction Neutralization: Agents output bullish_score/bearish_score instead of direction
2. Echo Chamber Detector: Auto-intervention when consensus exceeds threshold

Design Philosophy:
- Eliminate directional words (long/short) from Agent prompts to prevent linguistic bias
- Detect and mitigate groupthink before it affects trading decisions
- Maintain transparency through logging and warnings
"""

import logging
import random
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class BiasCheckStatus(Enum):
    """Status of bias detection checks."""
    PASSED = "passed"
    ECHO_CHAMBER_DETECTED = "echo_chamber_detected"
    NEUTRALIZED = "neutralized"


@dataclass
class NeutralVote:
    """
    Direction-Neutral Vote Structure
    
    Instead of agents outputting "direction: long/short",
    they output bullish_score and bearish_score separately.
    The system then calculates the direction based on score difference.
    """
    agent_id: str
    agent_name: str
    bullish_score: int  # 0-100: How strong are the bullish arguments
    bearish_score: int  # 0-100: How strong are the bearish arguments
    confidence: int     # 0-100: Overall analysis confidence
    leverage: int
    take_profit_percent: float
    stop_loss_percent: float
    reasoning: str
    
    @property
    def direction(self) -> str:
        """Calculate direction from scores."""
        return DirectionNeutralizer.calculate_direction(
            self.bullish_score, 
            self.bearish_score
        )
    
    @property
    def score_difference(self) -> int:
        """Get the difference between bullish and bearish scores."""
        return self.bullish_score - self.bearish_score
    
    def to_legacy_vote(self) -> Dict[str, Any]:
        """Convert to legacy vote format for backward compatibility."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "direction": self.direction,
            "confidence": self.confidence,
            "leverage": self.leverage,
            "take_profit_percent": self.take_profit_percent,
            "stop_loss_percent": self.stop_loss_percent,
            "reasoning": self.reasoning,
            # New fields for transparency
            "bullish_score": self.bullish_score,
            "bearish_score": self.bearish_score,
            "score_difference": self.score_difference
        }


class DirectionNeutralizer:
    """
    Converts bullish_score/bearish_score to direction decisions.
    
    The key innovation: Agents never see or output "long" or "short".
    They only rate the strength of bullish and bearish arguments.
    The system applies consistent, unbiased logic to determine direction.
    """
    
    # Default threshold for direction decision
    DEFAULT_THRESHOLD = 15  # Difference needed to trigger a trade
    
    @staticmethod
    def calculate_direction(
        bullish_score: int, 
        bearish_score: int,
        threshold: int = None
    ) -> str:
        """
        Calculate trading direction from scores.
        
        Args:
            bullish_score: 0-100, strength of bullish arguments
            bearish_score: 0-100, strength of bearish arguments
            threshold: Minimum score difference to trigger a trade
            
        Returns:
            "long", "short", or "hold"
        """
        threshold = threshold or DirectionNeutralizer.DEFAULT_THRESHOLD
        diff = bullish_score - bearish_score
        
        if diff >= threshold:
            return "long"
        elif diff <= -threshold:
            return "short"
        else:
            return "hold"
    
    @staticmethod
    def aggregate_neutral_votes(
        votes: List[NeutralVote],
        weights: Dict[str, float] = None
    ) -> Tuple[str, int, Dict[str, Any]]:
        """
        Aggregate neutral votes into a final direction.
        
        Args:
            votes: List of NeutralVote objects
            weights: Optional agent weight multipliers
            
        Returns:
            Tuple of (direction, confidence, metadata)
        """
        if not votes:
            return "hold", 0, {"reason": "no_votes"}
        
        weights = weights or {}
        
        # Calculate weighted average scores
        total_bullish = 0.0
        total_bearish = 0.0
        total_weight = 0.0
        
        for vote in votes:
            weight = weights.get(vote.agent_id, 1.0)
            total_bullish += vote.bullish_score * weight
            total_bearish += vote.bearish_score * weight
            total_weight += weight
        
        avg_bullish = total_bullish / total_weight if total_weight > 0 else 50
        avg_bearish = total_bearish / total_weight if total_weight > 0 else 50
        
        direction = DirectionNeutralizer.calculate_direction(
            int(avg_bullish), 
            int(avg_bearish)
        )
        
        # Confidence based on score clarity
        score_diff = abs(avg_bullish - avg_bearish)
        confidence = min(int(score_diff + 50), 100)  # Convert diff to confidence
        
        metadata = {
            "avg_bullish_score": round(avg_bullish, 1),
            "avg_bearish_score": round(avg_bearish, 1),
            "score_difference": round(avg_bullish - avg_bearish, 1),
            "vote_count": len(votes),
            "method": "direction_neutralization"
        }
        
        logger.info(
            f"[DirectionNeutralizer] Aggregated {len(votes)} votes: "
            f"Bullish={avg_bullish:.1f}, Bearish={avg_bearish:.1f} → {direction.upper()}"
        )
        
        return direction, confidence, metadata
    
    @staticmethod
    def get_neutral_vote_prompt() -> str:
        """
        Get the prompt instruction for neutral voting.
        
        Key innovation: No mention of "long" or "short" in the output format.
        """
        return '''
**Output your analysis as JSON** at the END of your response:

```json
{
  "bullish_score": 65,
  "bearish_score": 45,
  "confidence": 70,
  "leverage": 5,
  "take_profit_percent": 8.0,
  "stop_loss_percent": 3.0,
  "reasoning": "Your balanced analysis covering both bullish and bearish factors"
}
```

**Scoring Guide**:
- `bullish_score` (0-100): How strong are the arguments FOR price going UP?
- `bearish_score` (0-100): How strong are the arguments FOR price going DOWN?
- You MUST seriously evaluate BOTH directions, not just favor one.
- A balanced market might have both scores around 50-60.
- An extremely bullish market might be 85 bullish / 25 bearish.
- An extremely bearish market might be 25 bullish / 85 bearish.
'''


@dataclass
class EchoChamberCheckResult:
    """Result of echo chamber detection."""
    status: BiasCheckStatus
    consensus_ratio: float
    dominant_direction: Optional[str]
    confidence_penalty: float
    warning_message: str
    should_force_review: bool


class EchoChamberDetector:
    """
    Detects and mitigates groupthink in trading decisions.
    
    When too many agents agree on the same direction, it may indicate:
    1. Genuine strong market signal (valid)
    2. Agents reinforcing each other's biases (dangerous)
    
    This detector applies automatic interventions when consensus is suspiciously high.
    """
    
    # Configuration
    ECHO_THRESHOLD = 0.80       # 80%+ agreement triggers detection
    STRONG_ECHO_THRESHOLD = 0.95  # 95%+ triggers severe penalty
    CONFIDENCE_PENALTY_MILD = 0.15  # 15% reduction for mild echo
    CONFIDENCE_PENALTY_SEVERE = 0.30  # 30% reduction for severe echo
    
    def __init__(self, threshold: float = None, penalty: float = None):
        """
        Initialize the detector.
        
        Args:
            threshold: Custom consensus threshold (default 0.80)
            penalty: Custom confidence penalty (default 0.15)
        """
        self.threshold = threshold or self.ECHO_THRESHOLD
        self.penalty = penalty or self.CONFIDENCE_PENALTY_MILD
        self._detection_count = 0
    
    def check(self, votes: List[Dict[str, Any]]) -> EchoChamberCheckResult:
        """
        Check for echo chamber conditions.
        
        Args:
            votes: List of vote dictionaries with 'direction' field
            
        Returns:
            EchoChamberCheckResult with detection status and recommendations
        """
        if not votes:
            return EchoChamberCheckResult(
                status=BiasCheckStatus.PASSED,
                consensus_ratio=0.0,
                dominant_direction=None,
                confidence_penalty=0.0,
                warning_message="",
                should_force_review=False
            )
        
        # Count directions (handle both legacy and neutral votes)
        direction_counts = {"long": 0, "short": 0, "hold": 0}
        
        for vote in votes:
            if isinstance(vote, NeutralVote):
                direction = vote.direction
            elif isinstance(vote, dict):
                direction = vote.get("direction", "hold")
                if hasattr(direction, 'value'):
                    direction = direction.value
            else:
                direction = "hold"
            
            direction = direction.lower() if isinstance(direction, str) else "hold"
            if direction in direction_counts:
                direction_counts[direction] += 1
        
        total = sum(direction_counts.values())
        if total == 0:
            return EchoChamberCheckResult(
                status=BiasCheckStatus.PASSED,
                consensus_ratio=0.0,
                dominant_direction=None,
                confidence_penalty=0.0,
                warning_message="",
                should_force_review=False
            )
        
        # Find dominant direction and ratio
        max_count = max(direction_counts.values())
        dominant_direction = None
        for d, count in direction_counts.items():
            if count == max_count:
                dominant_direction = d
                break
        
        consensus_ratio = max_count / total
        
        # Check thresholds
        if consensus_ratio >= self.STRONG_ECHO_THRESHOLD:
            # Severe echo chamber
            self._detection_count += 1
            return EchoChamberCheckResult(
                status=BiasCheckStatus.ECHO_CHAMBER_DETECTED,
                consensus_ratio=consensus_ratio,
                dominant_direction=dominant_direction,
                confidence_penalty=self.CONFIDENCE_PENALTY_SEVERE,
                warning_message=(
                    f"⚠️ SEVERE ECHO CHAMBER: {consensus_ratio*100:.0f}% consensus on {dominant_direction.upper()}. "
                    f"Confidence reduced by {self.CONFIDENCE_PENALTY_SEVERE*100:.0f}%. "
                    f"Consider opposing viewpoints before proceeding."
                ),
                should_force_review=True
            )
        elif consensus_ratio >= self.threshold:
            # Mild echo chamber
            self._detection_count += 1
            return EchoChamberCheckResult(
                status=BiasCheckStatus.ECHO_CHAMBER_DETECTED,
                consensus_ratio=consensus_ratio,
                dominant_direction=dominant_direction,
                confidence_penalty=self.penalty,
                warning_message=(
                    f"⚠️ ECHO CHAMBER DETECTED: {consensus_ratio*100:.0f}% consensus on {dominant_direction.upper()}. "
                    f"Confidence reduced by {self.penalty*100:.0f}%. "
                    f"High agreement may indicate groupthink."
                ),
                should_force_review=False
            )
        
        return EchoChamberCheckResult(
            status=BiasCheckStatus.PASSED,
            consensus_ratio=consensus_ratio,
            dominant_direction=dominant_direction,
            confidence_penalty=0.0,
            warning_message="",
            should_force_review=False
        )
    
    def apply_penalty(self, confidence: int, check_result: EchoChamberCheckResult) -> int:
        """
        Apply confidence penalty based on echo chamber check.
        
        Args:
            confidence: Original confidence score (0-100)
            check_result: Result from check() method
            
        Returns:
            Adjusted confidence score
        """
        if check_result.confidence_penalty > 0:
            penalty_amount = int(confidence * check_result.confidence_penalty)
            adjusted = max(0, confidence - penalty_amount)
            logger.warning(
                f"[EchoChamberDetector] Applied {check_result.confidence_penalty*100:.0f}% penalty: "
                f"{confidence}% → {adjusted}%"
            )
            return adjusted
        return confidence
    
    @property
    def detection_count(self) -> int:
        """Get the number of echo chambers detected in this session."""
        return self._detection_count


# Singleton instances for easy access
_echo_detector = None

def get_echo_chamber_detector() -> EchoChamberDetector:
    """Get or create the singleton echo chamber detector."""
    global _echo_detector
    if _echo_detector is None:
        _echo_detector = EchoChamberDetector()
    return _echo_detector


def parse_neutral_vote(
    agent_id: str,
    agent_name: str,
    response: str
) -> Optional[NeutralVote]:
    """
    Parse a neutral vote from LLM response.
    
    Args:
        agent_id: Agent identifier
        agent_name: Agent display name
        response: Raw LLM response text
        
    Returns:
        NeutralVote object or None if parsing fails
    """
    import json
    import re
    
    # Try to extract JSON from response
    json_patterns = [
        r'```json\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
        r'\{[\s\S]*"bullish_score"[\s\S]*\}'
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        for match in matches:
            try:
                if isinstance(match, str):
                    data = json.loads(match.strip())
                else:
                    data = json.loads(match)
                
                # Validate required fields
                if "bullish_score" in data and "bearish_score" in data:
                    return NeutralVote(
                        agent_id=agent_id,
                        agent_name=agent_name,
                        bullish_score=int(data.get("bullish_score", 50)),
                        bearish_score=int(data.get("bearish_score", 50)),
                        confidence=int(data.get("confidence", 50)),
                        leverage=int(data.get("leverage", 1)),
                        take_profit_percent=float(data.get("take_profit_percent", 8.0)),
                        stop_loss_percent=float(data.get("stop_loss_percent", 3.0)),
                        reasoning=data.get("reasoning", "")
                    )
            except (json.JSONDecodeError, ValueError):
                continue
    
    logger.warning(f"[parse_neutral_vote] Failed to parse neutral vote from {agent_name}")
    return None
