"""
Trading Mode Manager - HITL (Human-in-the-Loop) Core

This project now uses a single execution mode:
- SEMI_AUTO (HITL): Always require user confirmation before execution.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List
import uuid
import json

import redis.asyncio as redis
import logging

try:
    import structlog
except Exception:  # Optional in some local/dev test setups
    structlog = None

from .trading_config import get_infra_config
from app.core.auth import get_current_user_id

logger = structlog.get_logger(__name__) if structlog is not None else logging.getLogger(__name__)


class TradingMode(Enum):
    """Trading execution modes."""
    SEMI_AUTO = "semi_auto"  # Wait for user confirmation (HITL-only)


class ExecutionAction(Enum):
    """Possible execution actions."""
    EXECUTE = "execute"          # Proceed with trade
    WAIT_CONFIRMATION = "wait"   # Wait for user confirmation
    SKIP = "skip"                # Do not execute


@dataclass
class ExecutionDecision:
    """Result of execution decision logic."""
    action: ExecutionAction
    reason: str
    pending_trade_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    
    @property
    def should_execute(self) -> bool:
        return self.action == ExecutionAction.EXECUTE
    
    @property
    def requires_confirmation(self) -> bool:
        return self.action == ExecutionAction.WAIT_CONFIRMATION


@dataclass
class PendingTrade:
    """A trade awaiting user confirmation (SEMI_AUTO mode)."""
    id: str
    signal: Dict[str, Any]
    created_at: datetime
    expires_at: datetime
    status: str = "pending"  # pending, confirmed, rejected, expired
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "signal": self.signal,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "status": self.status,
            "confirmed_by": self.confirmed_by,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PendingTrade":
        return cls(
            id=data["id"],
            signal=data["signal"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            status=data.get("status", "pending"),
            confirmed_by=data.get("confirmed_by"),
            confirmed_at=datetime.fromisoformat(data["confirmed_at"]) if data.get("confirmed_at") else None,
        )
    
    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at


@dataclass
class PendingTradeResponse:
    """Response from add_pending_trade with trade_id for frontend access."""
    trade_id: str
    pending_trade: PendingTrade


class TradingModeManager:
    """
    Manages trading execution mode and pending-trade confirmation flow.

    Stores mode in Redis but normalizes to SEMI_AUTO (HITL-only).
    """
    
    REDIS_KEY_MODE_PREFIX = "trading:mode"
    REDIS_KEY_PENDING_PREFIX_BASE = "trading:pending"
    REDIS_KEY_PENDING_LIST_PREFIX = "trading:pending_list"
    PENDING_TRADE_TTL_SECONDS = 900  # 15 minutes
    DEFAULT_MODE = TradingMode.SEMI_AUTO  # Default mode when key doesn't exist in Redis

    def __init__(self, user_id: Optional[str] = None, redis_client: Optional[redis.Redis] = None):
        self.user_id = get_current_user_id(user_id)
        self.redis = redis_client
        self._mode_lock = asyncio.Lock()
        self._execution_lock = asyncio.Lock()

    @property
    def redis_key_mode(self) -> str:
        return f"{self.REDIS_KEY_MODE_PREFIX}:{self.user_id}"

    @property
    def redis_key_pending_prefix(self) -> str:
        return f"{self.REDIS_KEY_PENDING_PREFIX_BASE}:{self.user_id}:"

    @property
    def redis_key_pending_list(self) -> str:
        return f"{self.REDIS_KEY_PENDING_LIST_PREFIX}:{self.user_id}"

    async def _ensure_redis(self) -> Optional[redis.Redis]:
        """Ensure Redis connection exists."""
        if self.redis is None:
            # Use centralized config for Redis URL
            redis_url = get_infra_config().redis_url
            try:
                self.redis = redis.from_url(redis_url, decode_responses=True)
                await self.redis.ping()
            except Exception as e:
                logger.warning("trading_mode_redis_connect_failed", error=str(e))
                return None
        return self.redis

    async def get_mode(self) -> TradingMode:
        """
        Get current trading mode.

        Always returns SEMI_AUTO.
        If Redis contains an obsolete value (e.g. "full_auto"/"manual"), it is normalized to "semi_auto".
        """
        try:
            redis_client = await self._ensure_redis()
            if redis_client:
                mode_value = await redis_client.get(self.redis_key_mode)
                normalized = self.DEFAULT_MODE

                if mode_value == self.DEFAULT_MODE.value:
                    normalized = self.DEFAULT_MODE
                elif mode_value:
                    # Legacy/unknown mode: normalize
                    logger.info(
                        "trading_mode_normalized",
                        previous_mode=mode_value,
                        new_mode=self.DEFAULT_MODE.value,
                    )
                else:
                    logger.info(
                        "trading_mode_not_set_initializing",
                        default_mode=self.DEFAULT_MODE.value,
                    )

                # Ensure Redis is consistent (both unset and legacy values)
                if mode_value != self.DEFAULT_MODE.value:
                    await redis_client.set(self.redis_key_mode, self.DEFAULT_MODE.value)

                return normalized
        except Exception as e:
            logger.warning("trading_mode_get_failed", error=str(e))

        # Fail-safe: HITL-only, never auto-execute.
        return self.DEFAULT_MODE
    
    async def set_mode(self, mode: TradingMode, user_id: Optional[str] = None) -> bool:
        """
        Set trading mode.
        
        Args:
            mode: The new trading mode
            user_id: Optional user ID for audit logging
            
        Returns:
            True if mode was set successfully
        """
        async with self._mode_lock:
            try:
                # HITL-only: only SEMI_AUTO is supported.
                mode = self.DEFAULT_MODE
                redis_client = await self._ensure_redis()
                if redis_client:
                    await redis_client.set(self.redis_key_mode, mode.value)
                    logger.info(
                        "trading_mode_changed",
                        new_mode=mode.value,
                        user_id=user_id
                    )
                    return True
            except Exception as e:
                logger.error("trading_mode_set_failed", error=str(e))
            return False
    
    async def should_execute(self, signal: Dict[str, Any]) -> ExecutionDecision:
        """
        Determine whether to execute a trade based on current mode.

        HITL-only: always create a pending trade and wait for user confirmation.
        
        Args:
            signal: The trading signal to evaluate
            
        Returns:
            ExecutionDecision with action, reason, and optional pending trade ID
        """
        pending_trade = await self._create_pending_trade(signal)
        return ExecutionDecision(
            action=ExecutionAction.WAIT_CONFIRMATION,
            reason="HITL-only: awaiting user confirmation",
            pending_trade_id=pending_trade.id,
            expires_at=pending_trade.expires_at,
        )
    
    async def _create_pending_trade(self, signal: Dict[str, Any]) -> PendingTrade:
        """Create a pending trade entry in Redis and send notifications."""
        trade_id = f"trade_{uuid.uuid4().hex[:12]}"
        now = datetime.now()
        expires_at = now + timedelta(seconds=self.PENDING_TRADE_TTL_SECONDS)
        
        pending = PendingTrade(
            id=trade_id,
            signal=signal,
            created_at=now,
            expires_at=expires_at,
        )
        
        try:
            redis_client = await self._ensure_redis()
            if redis_client:
                # Store pending trade
                key = f"{self.redis_key_pending_prefix}{trade_id}"
                await redis_client.setex(
                    key,
                    self.PENDING_TRADE_TTL_SECONDS,
                    json.dumps(pending.to_dict())
                )
                # Add to pending list
                await redis_client.lpush(self.redis_key_pending_list, trade_id)
                
                logger.info(
                    "pending_trade_created",
                    trade_id=trade_id,
                    expires_at=expires_at.isoformat()
                )
                
                # 🆕 Phase 2.1: Send notifications
                try:
                    from app.core.notifications import get_notification_service
                    notification_service = get_notification_service()
                    await notification_service.notify_pending_trade(
                        trade_id=trade_id,
                        signal=signal,
                        expires_at=expires_at,
                    )
                except Exception as notify_error:
                    logger.warning("pending_trade_notification_failed", error=str(notify_error))
                
        except Exception as e:
            logger.error("pending_trade_create_failed", error=str(e))
        
        return pending
    
    async def add_pending_trade(
        self,
        direction: str,
        leverage: int,
        entry_price: float,
        take_profit: float,
        stop_loss: float,
        confidence: int,
        reasoning: str,
        amount_percent: float = 0.5,
        symbol: str = "BTC-USDT-SWAP"
    ) -> "PendingTradeResponse":
        """
        Public method to add a pending trade for SEMI_AUTO mode.
        
        Creates a pending trade entry in Redis for user confirmation.
        
        Args:
            direction: Trade direction ('long' or 'short')
            leverage: Leverage multiplier
            entry_price: Entry price
            take_profit: Take profit price
            stop_loss: Stop loss price
            confidence: Confidence percentage (0-100)
            reasoning: Trade reasoning/analysis
            amount_percent: Position size as percentage of balance
            symbol: Trading symbol
            
        Returns:
            PendingTradeResponse with trade_id
        """
        # Construct signal dict
        signal = {
            "direction": direction,
            "leverage": leverage,
            "entry_price": entry_price,
            "take_profit_price": take_profit,
            "stop_loss_price": stop_loss,
            "confidence": confidence,
            "reasoning": reasoning,
            "amount_percent": amount_percent,
            "symbol": symbol,
        }
        
        # Create pending trade using internal method
        pending = await self._create_pending_trade(signal)
        
        # Return response with trade_id attribute
        return PendingTradeResponse(trade_id=pending.id, pending_trade=pending)
    
    async def get_pending_trade(self, trade_id: str) -> Optional[PendingTrade]:
        """Get a specific pending trade by ID."""
        try:
            redis_client = await self._ensure_redis()
            if redis_client:
                key = f"{self.redis_key_pending_prefix}{trade_id}"
                data = await redis_client.get(key)
                if data:
                    return PendingTrade.from_dict(json.loads(data))
        except Exception as e:
            logger.error("pending_trade_get_failed", trade_id=trade_id, error=str(e))
        return None
    
    async def get_pending_trades(self) -> List[PendingTrade]:
        """Get all pending trades. Also cleans up expired/processed entries from Redis list."""
        trades = []
        stale_ids = []
        try:
            redis_client = await self._ensure_redis()
            if redis_client:
                trade_ids = await redis_client.lrange(self.redis_key_pending_list, 0, -1)
                for trade_id in trade_ids:
                    trade = await self.get_pending_trade(trade_id)
                    if trade and not trade.is_expired and trade.status == "pending":
                        trades.append(trade)
                    else:
                        # Trade expired, processed, or deleted from Redis — mark for cleanup
                        stale_ids.append(trade_id)

                # Clean up stale entries from the list
                if stale_ids:
                    for stale_id in stale_ids:
                        await redis_client.lrem(self.redis_key_pending_list, 0, stale_id)
                    logger.info(
                        "pending_trades_cleanup",
                        removed_count=len(stale_ids),
                        remaining_count=len(trades)
                    )
        except Exception as e:
            logger.error("pending_trades_list_failed", error=str(e))
        return trades
    
    async def confirm_trade(
        self, 
        trade_id: str, 
        user_id: str,
        modifications: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Confirm a pending trade for execution.
        
        Args:
            trade_id: The pending trade ID
            user_id: User confirming the trade
            modifications: Optional modifications to the trade (leverage, TP/SL)
            
        Returns:
            The final signal to execute, or None if confirmation failed
        """
        async with self._execution_lock:
            trade = await self.get_pending_trade(trade_id)
            
            if not trade:
                logger.warning("pending_trade_not_found", trade_id=trade_id)
                return None
            
            if trade.is_expired:
                logger.warning("pending_trade_expired", trade_id=trade_id)
                return None
            
            if trade.status != "pending":
                logger.warning(
                    "pending_trade_already_processed",
                    trade_id=trade_id,
                    status=trade.status
                )
                return None
            
            # Apply modifications if provided
            signal = trade.signal.copy()
            if modifications:
                signal.update(modifications)
            
            # Update trade status
            trade.status = "confirmed"
            trade.confirmed_by = user_id
            trade.confirmed_at = datetime.now()
            
            try:
                redis_client = await self._ensure_redis()
                if redis_client:
                    key = f"{self.redis_key_pending_prefix}{trade_id}"
                    await redis_client.setex(
                        key,
                        60,  # Keep for 1 minute after confirmation
                        json.dumps(trade.to_dict())
                    )
                    
                logger.info(
                    "pending_trade_confirmed",
                    trade_id=trade_id,
                    user_id=user_id,
                    has_modifications=modifications is not None
                )
            except Exception as e:
                logger.error("pending_trade_confirm_failed", error=str(e))
            
            return signal
    
    async def reject_trade(self, trade_id: str, user_id: str, reason: str = "") -> bool:
        """Reject a pending trade."""
        trade = await self.get_pending_trade(trade_id)
        
        if not trade or trade.status != "pending":
            return False
        
        trade.status = "rejected"
        trade.confirmed_by = user_id
        trade.confirmed_at = datetime.now()
        
        try:
            redis_client = await self._ensure_redis()
            if redis_client:
                key = f"{self.redis_key_pending_prefix}{trade_id}"
                await redis_client.setex(key, 60, json.dumps(trade.to_dict()))
                
            logger.info(
                "pending_trade_rejected",
                trade_id=trade_id,
                user_id=user_id,
                reason=reason
            )
            return True
        except Exception as e:
            logger.error("pending_trade_reject_failed", error=str(e))
            return False


# Singleton instances by user scope
_mode_managers: Dict[str, TradingModeManager] = {}


def get_mode_manager(user_id: Optional[str] = None) -> TradingModeManager:
    """Get the TradingModeManager instance scoped by user."""
    scope = get_current_user_id(user_id)
    manager = _mode_managers.get(scope)
    if manager is None:
        manager = TradingModeManager(user_id=scope)
        _mode_managers[scope] = manager
    return manager


async def get_current_mode() -> TradingMode:
    """Convenience function to get current trading mode."""
    return await get_mode_manager().get_mode()


async def set_trading_mode(mode: TradingMode, user_id: Optional[str] = None) -> bool:
    """Convenience function to set trading mode."""
    return await get_mode_manager(user_id).set_mode(mode, user_id)
