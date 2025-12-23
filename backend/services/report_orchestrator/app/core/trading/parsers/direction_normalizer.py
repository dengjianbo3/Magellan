"""
Direction Normalizer

Normalizes various direction expressions to standard enum values.
Handles English, Chinese, and various synonyms.
"""

from ..domain.vote import VoteDirection


class DirectionNormalizer:
    """
    Normalizes direction strings to VoteDirection enum.
    
    Handles various input formats:
    - English: "long", "buy", "bullish", "short", "sell", "bearish"
    - Chinese: "做多", "开多", "做空", "开空", "观望", "平仓"
    - Abbreviations: "L", "S", "H"
    """
    
    # Mapping of various expressions to standardized directions
    DIRECTION_MAP = {
        # Long variants (English)
        "long": VoteDirection.LONG,
        "buy": VoteDirection.LONG,
        "bullish": VoteDirection.LONG,
        "bull": VoteDirection.LONG,
        "up": VoteDirection.LONG,
        "upward": VoteDirection.LONG,
        "positive": VoteDirection.LONG,
        "l": VoteDirection.LONG,
        
        # Long variants (Chinese)
        "做多": VoteDirection.LONG,
        "开多": VoteDirection.LONG,
        "多": VoteDirection.LONG,
        "看多": VoteDirection.LONG,
        "看涨": VoteDirection.LONG,
        "买入": VoteDirection.LONG,
        
        # Short variants (English)
        "short": VoteDirection.SHORT,
        "sell": VoteDirection.SHORT,
        "bearish": VoteDirection.SHORT,
        "bear": VoteDirection.SHORT,
        "down": VoteDirection.SHORT,
        "downward": VoteDirection.SHORT,
        "negative": VoteDirection.SHORT,
        "s": VoteDirection.SHORT,
        
        # Short variants (Chinese)
        "做空": VoteDirection.SHORT,
        "开空": VoteDirection.SHORT,
        "空": VoteDirection.SHORT,
        "看空": VoteDirection.SHORT,
        "看跌": VoteDirection.SHORT,
        "卖出": VoteDirection.SHORT,
        
        # Hold variants (English)
        "hold": VoteDirection.HOLD,
        "wait": VoteDirection.HOLD,
        "neutral": VoteDirection.HOLD,
        "flat": VoteDirection.HOLD,
        "sideline": VoteDirection.HOLD,
        "no_action": VoteDirection.HOLD,
        "noaction": VoteDirection.HOLD,
        "h": VoteDirection.HOLD,
        
        # Hold variants (Chinese)
        "观望": VoteDirection.HOLD,
        "持有": VoteDirection.HOLD,
        "等待": VoteDirection.HOLD,
        "不操作": VoteDirection.HOLD,
        
        # Close variants (English)
        "close": VoteDirection.CLOSE,
        "exit": VoteDirection.CLOSE,
        "close_position": VoteDirection.CLOSE,
        "closeposition": VoteDirection.CLOSE,
        
        # Close variants (Chinese)
        "平仓": VoteDirection.CLOSE,
        "清仓": VoteDirection.CLOSE,
        "离场": VoteDirection.CLOSE,
        
        # Add position variants
        "add_long": VoteDirection.ADD_LONG,
        "addlong": VoteDirection.ADD_LONG,
        "add_short": VoteDirection.ADD_SHORT,
        "addshort": VoteDirection.ADD_SHORT,
        "加多": VoteDirection.ADD_LONG,
        "加仓做多": VoteDirection.ADD_LONG,
        "加空": VoteDirection.ADD_SHORT,
        "加仓做空": VoteDirection.ADD_SHORT,
    }
    
    @classmethod
    def normalize(cls, direction: str) -> VoteDirection:
        """
        Normalize direction string to VoteDirection.
        
        Args:
            direction: Raw direction string
            
        Returns:
            VoteDirection enum value (defaults to HOLD if unrecognized)
        """
        if not direction:
            return VoteDirection.HOLD
        
        # Clean and normalize input
        cleaned = direction.lower().strip()
        
        # Remove common prefixes/suffixes
        cleaned = cleaned.replace("direction:", "").strip()
        cleaned = cleaned.replace("decision:", "").strip()
        cleaned = cleaned.replace("recommendation:", "").strip()
        
        # Handle quoted strings
        cleaned = cleaned.strip('"\'')
        
        # Replace underscores and hyphens
        normalized = cleaned.replace("-", "_").replace(" ", "_")
        
        # Direct lookup
        if normalized in cls.DIRECTION_MAP:
            return cls.DIRECTION_MAP[normalized]
        
        # Try without underscores
        no_underscores = normalized.replace("_", "")
        if no_underscores in cls.DIRECTION_MAP:
            return cls.DIRECTION_MAP[no_underscores]
        
        # Partial match for complex strings
        for key, value in cls.DIRECTION_MAP.items():
            if key in normalized or normalized in key:
                return value
        
        return VoteDirection.HOLD
    
    @classmethod
    def is_valid_direction(cls, direction: str) -> bool:
        """Check if string is a recognized direction."""
        if not direction:
            return False
        cleaned = direction.lower().strip().replace("-", "_").replace(" ", "_")
        return cleaned in cls.DIRECTION_MAP
    
    @classmethod
    def get_all_long_keywords(cls) -> list:
        """Get all keywords that map to LONG."""
        return [k for k, v in cls.DIRECTION_MAP.items() if v == VoteDirection.LONG]
    
    @classmethod
    def get_all_short_keywords(cls) -> list:
        """Get all keywords that map to SHORT."""
        return [k for k, v in cls.DIRECTION_MAP.items() if v == VoteDirection.SHORT]
