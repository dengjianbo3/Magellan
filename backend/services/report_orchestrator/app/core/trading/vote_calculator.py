"""
Vote Calculator

Functions for calculating confidence, leverage, and position size
based on expert voting results.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


def calculate_confidence_from_votes(votes: Dict[str, str], direction: str = None) -> int:
    """
    Calculate confidence based on expert votes.

    Calculation rules:
    - 5 unanimous votes: 90%
    - 4 unanimous votes: 80%
    - 3 unanimous votes: 65%
    - 2 unanimous votes: 50%
    - 1 or fewer votes: 30%

    Args:
        votes: Expert vote dict {"agent_name": "long/short/hold"}
        direction: Target direction, if None use majority direction

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

    # Count votes by direction
    long_count = sum(1 for v in votes.values() if v == 'long')
    short_count = sum(1 for v in votes.values() if v == 'short')
    hold_count = sum(1 for v in votes.values() if v == 'hold')
    total = len(votes)

    # Determine target direction and vote count
    if direction:
        if direction == 'long':
            target_count = long_count
        elif direction == 'short':
            target_count = short_count
        else:
            target_count = hold_count
    else:
        target_count = max(long_count, short_count, hold_count)

    # Confidence calculation based on vote count
    if target_count >= 5:
        confidence = 90
    elif target_count >= 4:
        confidence = 80
    elif target_count >= 3:
        confidence = 65
    elif target_count >= 2:
        confidence = 50
    else:
        confidence = 30

    logger.info(f"[Confidence] Votes: long={long_count}, short={short_count}, hold={hold_count} -> confidence={confidence}%")
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
