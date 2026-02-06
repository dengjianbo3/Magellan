"""
Confidence Validator

Validates confidence levels against minimum thresholds for trading decisions.
"""

from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class ConfidenceValidator:
    """Validates trading decisions against confidence thresholds."""
    
    # Default thresholds
    MIN_CONFIDENCE_OPEN = 65    # Minimum to open new position
    MIN_CONFIDENCE_CLOSE = 50   # Minimum to close position
    
    def __init__(
        self,
        min_open: int = None,
        min_close: int = None
    ):
        """
        Initialize validator with custom thresholds.
        
        Args:
            min_open: Minimum confidence to open position (default: 65)
            min_close: Minimum confidence to close position (default: 50)
        """
        self.min_open = min_open or self.MIN_CONFIDENCE_OPEN
        self.min_close = min_close or self.MIN_CONFIDENCE_CLOSE
        
        logger.info(
            f"[ConfidenceValidator] Initialized - "
            f"MIN_OPEN={self.min_open}, MIN_CLOSE={self.min_close}"
        )
    
    def validate(
        self,
        action: str,
        confidence: int
    ) -> Tuple[bool, str]:
        """
        Validate confidence meets minimum threshold for action.
        
        Args:
            action: Trading action (open_long, open_short, close_position, hold)
            confidence: Confidence level 0-100
            
        Returns:
            (is_valid, message) tuple
        """
        # Find threshold for action
        thresholds = {
            "open_long": self.min_open,
            "open_short": self.min_open,
            "close_position": self.min_close,
            "hold": 0  # No minimum for hold
        }
        
        min_required = thresholds.get(action, 0)
        
        if confidence < min_required:
            msg = (
                f"Confidence {confidence}% below minimum {min_required}% "
               f"required for {action}"
            )
            logger.warning(f"[SafetyGuard] {msg}")
            return False, msg
        
        return True, "OK"
    
    def should_block(
        self,
        action: str,
        confidence: int
    ) -> bool:
        """
        Check if action should be blocked due to low confidence.
        
        Args:
            action: Trading action
            confidence: Confidence level
            
        Returns:
            True if should block, False if allowed
        """
        valid, _ = self.validate(action, confidence)
        return not valid
