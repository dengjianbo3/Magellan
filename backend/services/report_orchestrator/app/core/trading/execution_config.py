"""
Execution Configuration

Configurable parameters for smart trade execution including:
- Capital tier thresholds
- Sliced execution settings
- Slippage limits
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Literal, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


def _get_env_int(key: str, default: int) -> int:
    """Get integer from environment variable"""
    val = os.getenv(key)
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return default


def _get_env_float(key: str, default: float) -> float:
    """Get float from environment variable"""
    val = os.getenv(key)
    if val:
        try:
            return float(val)
        except ValueError:
            pass
    return default


class CapitalTier(Enum):
    """Capital tier classification for execution strategy selection"""
    SMALL = "small"      # Direct execution
    MEDIUM = "medium"    # Check slippage, may one-shot
    LARGE = "large"      # Sliced execution
    XLARGE = "xlarge"    # TWAP/VWAP strategy


@dataclass
class ExecutionConfig:
    """
    Configuration for smart trade execution.
    
    All values are configurable via environment variables.
    
    Environment Variables:
        EXEC_CAPITAL_SMALL_MAX: Max amount for small tier (default: 1000)
        EXEC_CAPITAL_MEDIUM_MAX: Max amount for medium tier (default: 10000) 
        EXEC_CAPITAL_LARGE_MAX: Max amount for large tier (default: 50000)
        EXEC_SLICE_INTERVAL_SECONDS: Seconds between slices (default: 60)
        EXEC_SLICE_COUNT_DEFAULT: Default number of slices (default: 5)
        EXEC_MAX_SLIPPAGE_PERCENT: Max allowed slippage (default: 0.5)
        EXEC_ABORT_ON_VOLATILITY: Abort on volatility spike (default: true)
        EXEC_VOLATILITY_THRESHOLD: Volatility % to trigger abort (default: 2.0)
    """
    
    # Capital tier thresholds (USD)
    capital_small_max: float = field(default_factory=lambda: _get_env_float("EXEC_CAPITAL_SMALL_MAX", 1000.0))
    capital_medium_max: float = field(default_factory=lambda: _get_env_float("EXEC_CAPITAL_MEDIUM_MAX", 10000.0))
    capital_large_max: float = field(default_factory=lambda: _get_env_float("EXEC_CAPITAL_LARGE_MAX", 50000.0))
    
    # Sliced execution settings
    slice_interval_seconds: int = field(default_factory=lambda: _get_env_int("EXEC_SLICE_INTERVAL_SECONDS", 60))
    slice_count_default: int = field(default_factory=lambda: _get_env_int("EXEC_SLICE_COUNT_DEFAULT", 5))
    slice_count_min: int = field(default_factory=lambda: _get_env_int("EXEC_SLICE_COUNT_MIN", 3))
    slice_count_max: int = field(default_factory=lambda: _get_env_int("EXEC_SLICE_COUNT_MAX", 10))
    slice_variance_percent: float = field(default_factory=lambda: _get_env_float("EXEC_SLICE_VARIANCE_PERCENT", 10.0))
    
    # Slippage settings
    max_slippage_percent: float = field(default_factory=lambda: _get_env_float("EXEC_MAX_SLIPPAGE_PERCENT", 0.5))
    slippage_warning_percent: float = field(default_factory=lambda: _get_env_float("EXEC_SLIPPAGE_WARNING_PERCENT", 0.3))
    
    # Volatility protection
    abort_on_volatility: bool = field(default_factory=lambda: os.getenv("EXEC_ABORT_ON_VOLATILITY", "true").lower() == "true")
    volatility_threshold_percent: float = field(default_factory=lambda: _get_env_float("EXEC_VOLATILITY_THRESHOLD", 2.0))
    
    # Execution limits
    max_retry_per_slice: int = field(default_factory=lambda: _get_env_int("EXEC_MAX_RETRY_PER_SLICE", 3))
    retry_delay_seconds: int = field(default_factory=lambda: _get_env_int("EXEC_RETRY_DELAY_SECONDS", 5))
    
    # Adaptive pause settings (for volatility response)
    adaptive_pause_min_seconds: int = field(default_factory=lambda: _get_env_int("EXEC_ADAPTIVE_PAUSE_MIN", 30))
    adaptive_pause_max_seconds: int = field(default_factory=lambda: _get_env_int("EXEC_ADAPTIVE_PAUSE_MAX", 300))
    
    def get_capital_tier(self, amount_usdt: float) -> CapitalTier:
        """
        Determine capital tier based on order amount.
        
        Args:
            amount_usdt: Order amount in USDT
            
        Returns:
            CapitalTier enum value
        """
        if amount_usdt <= self.capital_small_max:
            return CapitalTier.SMALL
        elif amount_usdt <= self.capital_medium_max:
            return CapitalTier.MEDIUM
        elif amount_usdt <= self.capital_large_max:
            return CapitalTier.LARGE
        else:
            return CapitalTier.XLARGE
    
    def get_recommended_strategy(self, amount_usdt: float) -> str:
        """
        Get recommended execution strategy for given amount.
        
        Args:
            amount_usdt: Order amount in USDT
            
        Returns:
            Strategy name: "direct", "sliced", "twap"
        """
        tier = self.get_capital_tier(amount_usdt)
        
        if tier == CapitalTier.SMALL:
            return "direct"
        elif tier == CapitalTier.MEDIUM:
            return "direct"  # But with slippage check
        elif tier == CapitalTier.LARGE:
            return "sliced"
        else:
            return "twap"
    
    def get_recommended_slices(self, amount_usdt: float) -> int:
        """
        Calculate recommended number of slices for given amount.
        
        Args:
            amount_usdt: Order amount in USDT
            
        Returns:
            Number of slices (1 for direct execution)
        """
        tier = self.get_capital_tier(amount_usdt)
        
        if tier in [CapitalTier.SMALL, CapitalTier.MEDIUM]:
            return 1
        elif tier == CapitalTier.LARGE:
            # Scale slices based on amount: larger amounts = more slices
            ratio = amount_usdt / self.capital_medium_max
            slices = min(self.slice_count_max, max(self.slice_count_min, int(ratio * 2)))
            return slices
        else:
            return self.slice_count_max
    
    def log_config(self):
        """Log current configuration for debugging"""
        logger.info(f"[ExecutionConfig] Capital tiers: small<${self.capital_small_max}, medium<${self.capital_medium_max}, large<${self.capital_large_max}")
        logger.info(f"[ExecutionConfig] Slicing: {self.slice_count_default} slices, {self.slice_interval_seconds}s interval")
        logger.info(f"[ExecutionConfig] Slippage: max {self.max_slippage_percent}%, warning at {self.slippage_warning_percent}%")
        logger.info(f"[ExecutionConfig] Volatility abort: {self.abort_on_volatility} at {self.volatility_threshold_percent}%")


@dataclass
class ExecutionPlan:
    """
    Execution plan generated before trade execution.
    
    Contains the strategy and parameters for executing a trade.
    """
    strategy: Literal["direct", "sliced", "twap"]
    direction: Literal["long", "short"]
    total_amount_usdt: float
    
    # Slicing parameters
    slice_count: int = 1
    slice_interval_seconds: int = 60
    slice_amounts: List[float] = field(default_factory=list)
    
    # Risk parameters
    max_slippage_percent: float = 0.5
    abort_on_volatility: bool = True
    
    # Trade parameters (from Leader decision)
    leverage: int = 1
    tp_percent: float = 5.0
    sl_percent: float = 2.0
    
    # Pre-execution analysis
    estimated_slippage_percent: float = 0.0
    liquidity_rating: Literal["high", "medium", "low"] = "high"
    execution_risk: Literal["low", "medium", "high"] = "low"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "strategy": self.strategy,
            "direction": self.direction,
            "total_amount_usdt": self.total_amount_usdt,
            "slice_count": self.slice_count,
            "slice_interval_seconds": self.slice_interval_seconds,
            "slice_amounts": self.slice_amounts,
            "max_slippage_percent": self.max_slippage_percent,
            "leverage": self.leverage,
            "tp_percent": self.tp_percent,
            "sl_percent": self.sl_percent,
            "estimated_slippage_percent": self.estimated_slippage_percent,
            "liquidity_rating": self.liquidity_rating,
            "execution_risk": self.execution_risk
        }


@dataclass
class ExecutionResult:
    """
    Result of trade execution.
    
    Contains execution quality metrics and status.
    """
    plan: ExecutionPlan
    status: Literal["completed", "partial", "aborted", "failed"]
    
    # Execution metrics
    executed_slices: int = 0
    total_filled_usdt: float = 0.0
    average_entry_price: float = 0.0
    
    # Slippage analysis
    total_slippage_percent: float = 0.0
    max_slice_slippage_percent: float = 0.0
    
    # Timing
    execution_start_time: Optional[str] = None
    execution_end_time: Optional[str] = None
    execution_duration_seconds: float = 0.0
    
    # Errors
    error_message: Optional[str] = None
    abort_reason: Optional[str] = None
    
    # Per-slice details
    slice_results: List[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "status": self.status,
            "executed_slices": self.executed_slices,
            "total_filled_usdt": self.total_filled_usdt,
            "average_entry_price": self.average_entry_price,
            "total_slippage_percent": self.total_slippage_percent,
            "execution_duration_seconds": self.execution_duration_seconds,
            "error_message": self.error_message,
            "abort_reason": self.abort_reason
        }
    
    @property
    def is_success(self) -> bool:
        return self.status in ["completed", "partial"]
    
    @property
    def fill_rate(self) -> float:
        if self.plan.total_amount_usdt == 0:
            return 0.0
        return self.total_filled_usdt / self.plan.total_amount_usdt


# Global config instance (lazy initialization)
_execution_config: Optional[ExecutionConfig] = None


def get_execution_config() -> ExecutionConfig:
    """Get the global execution config instance"""
    global _execution_config
    if _execution_config is None:
        _execution_config = ExecutionConfig()
        _execution_config.log_config()
    return _execution_config
