"""
Vote Calculator

Functions for calculating confidence, leverage, and position size
based on expert voting results.

Enhanced with dynamic agent weights based on historical performance.
"""

import os
import logging
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ============================================
# Dynamic Agent Weight Configuration
# ============================================

@dataclass
class WeightConfig:
    """Configuration for dynamic agent weights"""
    enabled: bool = True
    base_weight: float = 1.0
    accuracy_factor: float = 0.5      # How much historical accuracy matters
    recency_factor: float = 0.3       # How much recent performance matters
    min_weight: float = 0.5           # Minimum weight
    max_weight: float = 2.0           # Maximum weight
    min_trades_for_weight: int = 5    # Minimum trades before applying weights
    
    @classmethod
    def from_env(cls) -> 'WeightConfig':
        """Load configuration from environment variables"""
        return cls(
            enabled=os.getenv('AGENT_WEIGHT_ENABLED', 'true').lower() == 'true',
            base_weight=float(os.getenv('AGENT_WEIGHT_BASE', '1.0')),
            accuracy_factor=float(os.getenv('AGENT_WEIGHT_ACCURACY_FACTOR', '0.5')),
            recency_factor=float(os.getenv('AGENT_WEIGHT_RECENCY_FACTOR', '0.3')),
            min_weight=float(os.getenv('AGENT_WEIGHT_MIN', '0.5')),
            max_weight=float(os.getenv('AGENT_WEIGHT_MAX', '2.0')),
            min_trades_for_weight=int(os.getenv('AGENT_WEIGHT_MIN_TRADES', '5')),
        )


class DynamicWeightCalculator:
    """
    Calculate dynamic agent weights based on historical performance.
    
    Weight formula:
        weight = base + (overall_accuracy - 0.5) * accuracy_factor
                     + (recent_accuracy - 0.5) * recency_factor
    
    Example:
        - Agent with 70% win rate, 80% recent: weight = 1.0 + 0.2*0.5 + 0.3*0.3 = 1.19
        - Agent with 40% win rate, 30% recent: weight = 1.0 - 0.1*0.5 - 0.2*0.3 = 0.89
    """
    
    def __init__(self, config: Optional[WeightConfig] = None):
        self.config = config or WeightConfig.from_env()
        self._weights_cache: Dict[str, float] = {}
    
    def calculate_weight(
        self,
        agent_id: str,
        overall_win_rate: float,
        recent_win_rate: float,
        total_trades: int
    ) -> float:
        """
        Calculate weight for an agent based on performance.
        
        Args:
            agent_id: Agent identifier
            overall_win_rate: Overall win rate (0.0 - 1.0)
            recent_win_rate: Recent N trades win rate (0.0 - 1.0)
            total_trades: Total number of trades
            
        Returns:
            Weight multiplier (min_weight to max_weight)
        """
        if not self.config.enabled:
            return 1.0
        
        # Not enough trades, use base weight
        if total_trades < self.config.min_trades_for_weight:
            logger.debug(f"[Weight] {agent_id}: trades={total_trades} < min={self.config.min_trades_for_weight}, using base weight")
            return self.config.base_weight
        
        # Calculate weight adjustments
        accuracy_bonus = (overall_win_rate - 0.5) * self.config.accuracy_factor
        recency_bonus = (recent_win_rate - 0.5) * self.config.recency_factor
        
        weight = self.config.base_weight + accuracy_bonus + recency_bonus
        
        # Clamp to min/max
        weight = max(self.config.min_weight, min(self.config.max_weight, weight))
        
        logger.info(
            f"[Weight] {agent_id}: overall={overall_win_rate:.1%}, recent={recent_win_rate:.1%} "
            f"-> weight={weight:.2f}"
        )
        
        self._weights_cache[agent_id] = weight
        return weight
    
    def get_cached_weight(self, agent_id: str) -> float:
        """Get cached weight for an agent"""
        return self._weights_cache.get(agent_id, 1.0)


def calculate_confidence_from_votes(
    votes: Dict[str, str],
    direction: str = None,
    weights: Dict[str, float] = None
) -> int:
    """
    Calculate confidence based on expert votes with optional weights.

    Calculation rules:
    - Sum weighted votes for each direction
    - Calculate consensus strength based on weighted majority

    Args:
        votes: Expert vote dict {"agent_name": "long/short/hold"}
        direction: Target direction, if None use majority direction
        weights: Optional weight dict {"agent_name": weight}, default 1.0

    Returns:
        int: Confidence 0-100
    """
    if not votes:
        logger.warning("[Confidence] No vote data, using minimum confidence 30%")
        return 30

    # FIX: Ensure votes is dict type
    if isinstance(votes, list):
        logger.warning("[Confidence] votes is list type, converting to dict")
        try:
            votes = {v.agent_name: v.direction for v in votes if hasattr(v, 'agent_name') and hasattr(v, 'direction')}
        except Exception as e:
            logger.error(f"[Confidence] Unable to convert votes: {e}")
            return 30

    # Default weights
    if weights is None:
        weights = {}

    # Count weighted votes by direction
    long_weight = sum(weights.get(name, 1.0) for name, v in votes.items() if v == 'long')
    short_weight = sum(weights.get(name, 1.0) for name, v in votes.items() if v == 'short')
    hold_weight = sum(weights.get(name, 1.0) for name, v in votes.items() if v == 'hold')
    total_weight = long_weight + short_weight + hold_weight

    # Also count raw votes for logging
    long_count = sum(1 for v in votes.values() if v == 'long')
    short_count = sum(1 for v in votes.values() if v == 'short')
    hold_count = sum(1 for v in votes.values() if v == 'hold')

    # Determine target direction weight
    if direction:
        if direction == 'long':
            target_weight = long_weight
        elif direction == 'short':
            target_weight = short_weight
        else:
            target_weight = hold_weight
    else:
        target_weight = max(long_weight, short_weight, hold_weight)

    # Calculate consensus ratio (0.0 - 1.0)
    consensus_ratio = target_weight / total_weight if total_weight > 0 else 0

    # Map consensus ratio to confidence
    # 1.0 (unanimous) -> 90%
    # 0.75 -> 75%
    # 0.5 (split) -> 50%
    # <0.5 -> 30%
    if consensus_ratio >= 0.9:
        confidence = 90
    elif consensus_ratio >= 0.75:
        confidence = 75 + int((consensus_ratio - 0.75) * 60)  # 75-90
    elif consensus_ratio >= 0.5:
        confidence = 50 + int((consensus_ratio - 0.5) * 100)  # 50-75
    else:
        confidence = 30

    logger.info(
        f"[Confidence] Votes: long={long_count}({long_weight:.1f}w), "
        f"short={short_count}({short_weight:.1f}w), hold={hold_count}({hold_weight:.1f}w) "
        f"-> consensus={consensus_ratio:.1%} -> confidence={confidence}%"
    )
    return confidence


def calculate_leverage_from_confidence(confidence: int, max_leverage: int = 20) -> int:
    """
    Calculate appropriate leverage based on confidence.

    Rules:
    - confidence >= 85: 10x (high confidence)
    - confidence >= 75: 8x
    - confidence >= 65: 6x
    - confidence >= 55: 5x
    - confidence >= 45: 3x
    - confidence < 45: 2x (low confidence)

    Args:
        confidence: Confidence 0-100
        max_leverage: Maximum allowed leverage

    Returns:
        int: Recommended leverage multiplier
    """
    if confidence >= 85:
        leverage = 10
    elif confidence >= 75:
        leverage = 8
    elif confidence >= 65:
        leverage = 6
    elif confidence >= 55:
        leverage = 5
    elif confidence >= 45:
        leverage = 3
    else:
        leverage = 2

    # Cap at max_leverage
    leverage = min(leverage, max_leverage)

    logger.info(f"[Leverage] confidence={confidence}% -> recommended leverage={leverage}x (max={max_leverage}x)")
    return leverage


def calculate_amount_from_confidence(confidence: int) -> float:
    """
    Calculate appropriate position size based on confidence.

    Rules:
    - confidence >= 85: 60% (high confidence)
    - confidence >= 75: 50%
    - confidence >= 65: 40%
    - confidence >= 55: 30%
    - confidence < 55: 20% (low confidence)

    Args:
        confidence: Confidence 0-100

    Returns:
        float: Position ratio 0.0-1.0
    """
    if confidence >= 85:
        amount = 0.60
    elif confidence >= 75:
        amount = 0.50
    elif confidence >= 65:
        amount = 0.40
    elif confidence >= 55:
        amount = 0.30
    else:
        amount = 0.20

    logger.info(f"[Amount] confidence={confidence}% -> recommended position={amount*100:.0f}%")
    return amount
