"""
Meeting Configuration

Configuration dataclass for TradingMeeting.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


# ========== Environment helpers ==========
def _get_env_float(key: str, default: float) -> float:
    val = os.getenv(key)
    if val:
        try:
            return float(val)
        except ValueError:
            pass
    return default

def _get_env_int(key: str, default: int) -> int:
    val = os.getenv(key)
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return default


@dataclass
class MeetingConfig:
    """
    Configuration for trading meeting execution.
    
    Reads from environment variables for consistency with TradingMeetingConfig.
    """
    # Symbol to trade
    symbol: str = field(default_factory=lambda: os.getenv("TRADING_SYMBOL", "BTC-USDT-SWAP"))
    
    # Execution parameters - read from env
    max_leverage: int = field(default_factory=lambda: _get_env_int("MAX_LEVERAGE", 20))
    default_leverage: int = field(default_factory=lambda: _get_env_int(\"DEFAULT_LEVERAGE\", 5))
    min_position_percent: float = field(default_factory=lambda: _get_env_float("MIN_POSITION_PERCENT", 10) / 100)
    max_position_percent: float = field(default_factory=lambda: _get_env_float("MAX_POSITION_PERCENT", 30) / 100)
    
    # Risk parameters - read from env
    default_take_profit_percent: float = field(default_factory=lambda: _get_env_float("DEFAULT_TP_PERCENT", 5.0))
    default_stop_loss_percent: float = field(default_factory=lambda: _get_env_float("DEFAULT_SL_PERCENT", 2.0))
    min_stop_loss_percent: float = field(default_factory=lambda: _get_env_float("MIN_STOP_LOSS_PERCENT", 0.5))
    max_stop_loss_percent: float = field(default_factory=lambda: _get_env_float("MAX_STOP_LOSS_PERCENT", 10.0))
    
    # Consensus parameters - read from env
    min_consensus_votes: int = 2  # Minimum agreeing votes for action
    min_confidence: int = field(default_factory=lambda: _get_env_int("MIN_CONFIDENCE", 60))
    
    # Timeouts (seconds)
    phase_timeout: int = 180
    agent_timeout: int = 60
    tool_timeout: int = 30
    
    # LLM parameters
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    
    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    
    # Feature flags
    enable_position_adding: bool = True
    enable_memory_injection: bool = True
    enable_reflection: bool = True
    
    # Debug
    verbose: bool = False
    log_prompts: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "max_leverage": self.max_leverage,
            "default_leverage": self.default_leverage,
            "min_position_percent": self.min_position_percent,
            "max_position_percent": self.max_position_percent,
            "default_take_profit_percent": self.default_take_profit_percent,
            "default_stop_loss_percent": self.default_stop_loss_percent,
            "min_consensus_votes": self.min_consensus_votes,
            "min_confidence": self.min_confidence,
            "phase_timeout": self.phase_timeout,
            "enable_position_adding": self.enable_position_adding,
            "enable_memory_injection": self.enable_memory_injection,
            "enable_reflection": self.enable_reflection,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MeetingConfig":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
