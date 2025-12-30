"""
Safety Guards for Trading Execution

Centralized safety controls to prevent unintended trades.
Consolidates all safety checks from across the codebase.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Any
from enum import Enum

logger = logging.getLogger(__name__)


class BlockReason(Enum):
    """Reasons for blocking trade execution."""
    STARTUP_PROTECTION = "startup_protection"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    COOLDOWN_ACTIVE = "cooldown_active"
    INVALID_PARAMS = "invalid_params"
    CONCURRENT_EXECUTION = "concurrent_execution"
    OKX_HEDGE_MODE = "okx_hedge_mode"
    LOW_CONFIDENCE = "low_confidence"
    SEARCH_SERVICE_DOWN = "search_service_down"
    NO_POSITION_TO_CLOSE = "no_position_to_close"
    ALREADY_HAS_POSITION = "already_has_position"


@dataclass
class SafetyCheckResult:
    """Result of a safety check."""
    allowed: bool
    reason: Optional[BlockReason] = None
    message: str = ""
    details: Optional[dict] = None
    
    def __bool__(self) -> bool:
        return self.allowed
    
    @classmethod
    def allow(cls) -> "SafetyCheckResult":
        return cls(allowed=True)
    
    @classmethod
    def block(cls, reason: BlockReason, message: str, details: dict = None) -> "SafetyCheckResult":
        return cls(allowed=False, reason=reason, message=message, details=details)


class SafetyGuard:
    """
    Centralized safety guard for trading execution.
    
    Consolidates safety checks from:
    - trading_routes.py (startup protection)
    - okx_trader.py (daily loss limit, hedge mode)
    - scheduler.py (cooldown)
    - trading_meeting.py (execution guards)
    
    Usage:
        guard = SafetyGuard(trader, cooldown_manager, config)
        result = await guard.pre_execution_check(votes, position_context, trigger_reason)
        if not result:
            logger.warning(f"Trade blocked: {result.message}")
            return
    """
    
    def __init__(
        self,
        trader: Any,
        cooldown_manager: Any = None,
        config: Any = None,
        min_confidence: int = 60
    ):
        self.trader = trader
        self.cooldown = cooldown_manager
        self.config = config
        self.min_confidence = min_confidence
        self._execution_lock = asyncio.Lock()
        self._startup_completed = False
        self._startup_time: Optional[datetime] = None
    
    def mark_startup_complete(self):
        """Mark that startup phase has completed."""
        self._startup_completed = True
        self._startup_time = datetime.now()
        logger.info("[SAFETY] Startup protection phase completed")
    
    @property
    def is_startup_phase(self) -> bool:
        """Check if still in startup protection window (first 5 minutes)."""
        if self._startup_completed and self._startup_time:
            elapsed = (datetime.now() - self._startup_time).total_seconds()
            return elapsed < 300  # 5 minute startup window
        return not self._startup_completed
    
    async def pre_execution_check(
        self,
        votes: List[Any],
        position_context: dict,
        trigger_reason: str = None,
        confidence: int = None
    ) -> SafetyCheckResult:
        """
        Perform all pre-execution safety checks.
        
        Args:
            votes: List of agent votes
            position_context: Current position state
            trigger_reason: Why the analysis was triggered
            confidence: Overall decision confidence
            
        Returns:
            SafetyCheckResult indicating if execution should proceed
        """
        # 1. Concurrent execution check
        if self._execution_lock.locked():
            return SafetyCheckResult.block(
                reason=BlockReason.CONCURRENT_EXECUTION,
                message="Another execution is already in progress"
            )
        
        # 2. Startup protection - block auto-reverse during startup
        if trigger_reason == "startup" and position_context.get("has_position"):
            proposed_direction = self._get_proposed_direction(votes)
            current_direction = position_context.get("direction")
            
            if proposed_direction and proposed_direction != current_direction:
                logger.warning(
                    f"[SAFETY] BLOCKED: Auto-reverse from {current_direction} to "
                    f"{proposed_direction} during startup"
                )
                return SafetyCheckResult.block(
                    reason=BlockReason.STARTUP_PROTECTION,
                    message=f"Cannot auto-reverse position from {current_direction} to {proposed_direction} during startup",
                    details={
                        "current_direction": current_direction,
                        "proposed_direction": proposed_direction,
                        "trigger_reason": trigger_reason
                    }
                )
        
        # 3. Daily loss limit check
        if hasattr(self.trader, '_check_daily_loss_limit'):
            is_allowed, message = self.trader._check_daily_loss_limit()
            if not is_allowed:
                logger.warning(f"[SAFETY] BLOCKED: Daily loss limit - {message}")
                return SafetyCheckResult.block(
                    reason=BlockReason.DAILY_LOSS_LIMIT,
                    message=message
                )
        
        # 4. Cooldown check
        if self.cooldown and not self.cooldown.check_cooldown():
            return SafetyCheckResult.block(
                reason=BlockReason.COOLDOWN_ACTIVE,
                message="System is in cooldown after consecutive losses"
            )
        
        # 5. OKX Hedge Mode check - block auto-close of existing position
        if hasattr(self.trader, 'is_hedge_mode') and self.trader.is_hedge_mode:
            if position_context.get("has_position"):
                proposed_direction = self._get_proposed_direction(votes)
                current_direction = position_context.get("direction")
                
                if proposed_direction and proposed_direction != current_direction:
                    return SafetyCheckResult.block(
                        reason=BlockReason.OKX_HEDGE_MODE,
                        message="OKX hedge mode: Cannot auto-close existing position for reverse",
                        details={
                            "current_direction": current_direction,
                            "proposed_direction": proposed_direction
                        }
                    )
        
        # 6. Minimum confidence check
        if confidence is not None and confidence < self.min_confidence:
            return SafetyCheckResult.block(
                reason=BlockReason.LOW_CONFIDENCE,
                message=f"Confidence {confidence}% below minimum {self.min_confidence}%"
            )
        
        return SafetyCheckResult.allow()
    
    async def validate_trade_params(
        self,
        direction: str,
        leverage: int,
        amount_usdt: float,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None,
        current_price: Optional[float] = None
    ) -> SafetyCheckResult:
        """
        Validate trade parameters before execution.
        
        Args:
            direction: "long" or "short"
            leverage: Leverage multiplier
            amount_usdt: Trade amount in USDT
            tp_price: Take profit price
            sl_price: Stop loss price
            current_price: Current market price
        """
        max_leverage = getattr(self.config, 'max_leverage', 20) if self.config else 20
        max_position_percent = getattr(self.config, 'max_position_percent', 0.3) if self.config else 0.3
        
        # Leverage validation
        if leverage < 1 or leverage > max_leverage:
            return SafetyCheckResult.block(
                reason=BlockReason.INVALID_PARAMS,
                message=f"Leverage {leverage} must be between 1 and {max_leverage}"
            )
        
        # Amount validation
        if amount_usdt <= 0:
            return SafetyCheckResult.block(
                reason=BlockReason.INVALID_PARAMS,
                message="Amount must be positive"
            )
        
        # Check against available balance
        if hasattr(self.trader, 'get_account'):
            try:
                account = await self.trader.get_account()
                available = account.get('available_balance', 0)
                max_amount = available * max_position_percent
                
                if amount_usdt > max_amount:
                    return SafetyCheckResult.block(
                        reason=BlockReason.INVALID_PARAMS,
                        message=f"Amount ${amount_usdt:.2f} exceeds max ${max_amount:.2f} ({max_position_percent*100:.0f}% of available)"
                    )
            except Exception as e:
                logger.warning(f"Could not validate amount against balance: {e}")
        
        # TP/SL validation
        if current_price and current_price > 0:
            if direction == "long":
                if tp_price is not None and tp_price <= current_price:
                    return SafetyCheckResult.block(
                        reason=BlockReason.INVALID_PARAMS,
                        message=f"TP price ${tp_price} must be above current price ${current_price} for long"
                    )
                if sl_price is not None and sl_price >= current_price:
                    return SafetyCheckResult.block(
                        reason=BlockReason.INVALID_PARAMS,
                        message=f"SL price ${sl_price} must be below current price ${current_price} for long"
                    )
            else:  # short
                if tp_price is not None and tp_price >= current_price:
                    return SafetyCheckResult.block(
                        reason=BlockReason.INVALID_PARAMS,
                        message=f"TP price ${tp_price} must be below current price ${current_price} for short"
                    )
                if sl_price is not None and sl_price <= current_price:
                    return SafetyCheckResult.block(
                        reason=BlockReason.INVALID_PARAMS,
                        message=f"SL price ${sl_price} must be above current price ${current_price} for short"
                    )
        
        return SafetyCheckResult.allow()
    
    def _get_proposed_direction(self, votes: List[Any]) -> Optional[str]:
        """Extract proposed direction from votes."""
        if not votes:
            return None
        
        # Count votes
        long_count = 0
        short_count = 0
        
        for vote in votes:
            direction = None
            if hasattr(vote, 'direction'):
                direction = vote.direction
                if hasattr(direction, 'value'):
                    direction = direction.value
            elif isinstance(vote, dict):
                direction = vote.get('direction')
            
            if direction:
                if direction.lower() in ("long", "buy", "add_long"):
                    long_count += 1
                elif direction.lower() in ("short", "sell", "add_short"):
                    short_count += 1
        
        if long_count > short_count:
            return "long"
        elif short_count > long_count:
            return "short"
        return None
    
    async def acquire_execution_lock(self, timeout: float = 30.0) -> bool:
        """
        Acquire execution lock for trade execution.
        
        Args:
            timeout: Maximum time to wait for lock
            
        Returns:
            True if lock acquired, False if timeout
        """
        try:
            await asyncio.wait_for(self._execution_lock.acquire(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            logger.warning(f"[SAFETY] Could not acquire execution lock within {timeout}s")
            return False
    
    def release_execution_lock(self):
        """Release execution lock."""
        if self._execution_lock.locked():
            self._execution_lock.release()
