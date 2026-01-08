"""
Notification Service

Unified service for multi-channel trading notifications.
Coordinates WebSocket and Telegram notifications.
"""

import asyncio
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from dataclasses import dataclass, field

import structlog

from .telegram import TelegramNotifier, get_telegram_notifier

logger = structlog.get_logger(__name__)


@dataclass
class NotificationEvent:
    """Base notification event."""
    event_type: str
    trade_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)


class NotificationService:
    """
    Unified notification service for trading events.
    
    Supports:
    - WebSocket broadcasts (for frontend)
    - Telegram notifications (for mobile)
    """
    
    def __init__(
        self,
        telegram_notifier: Optional[TelegramNotifier] = None,
    ):
        self.telegram = telegram_notifier or get_telegram_notifier()
        self._websocket_listeners: List[Callable] = []
    
    def register_websocket_listener(self, callback: Callable):
        """Register a WebSocket broadcast callback."""
        self._websocket_listeners.append(callback)
    
    def unregister_websocket_listener(self, callback: Callable):
        """Remove a WebSocket listener."""
        if callback in self._websocket_listeners:
            self._websocket_listeners.remove(callback)
    
    async def notify_pending_trade(
        self,
        trade_id: str,
        signal: Dict[str, Any],
        expires_at: datetime,
    ) -> None:
        """
        Notify about a new pending trade requiring confirmation.
        
        Sends notifications via:
        1. WebSocket (immediate)
        2. Telegram (if configured)
        """
        now = datetime.now()
        expires_in_seconds = int((expires_at - now).total_seconds())
        
        # Extract signal details
        direction = signal.get("direction", "hold")
        leverage = signal.get("leverage", 1)
        confidence = signal.get("confidence", 0)
        take_profit = signal.get("take_profit_percent", 0)
        stop_loss = signal.get("stop_loss_percent", 0)
        reasoning = signal.get("reasoning", "")
        
        # Build notification payload
        payload = {
            "event": "pending_trade",
            "trade_id": trade_id,
            "direction": direction,
            "leverage": leverage,
            "confidence": confidence,
            "take_profit_percent": take_profit,
            "stop_loss_percent": stop_loss,
            "reasoning": reasoning[:500],
            "expires_at": expires_at.isoformat(),
            "expires_in_seconds": expires_in_seconds,
            "created_at": now.isoformat(),
        }
        
        logger.info(
            "notification_pending_trade",
            trade_id=trade_id,
            direction=direction
        )
        
        # 1. WebSocket broadcast
        await self._broadcast_websocket(payload)
        
        # 2. Telegram notification
        if self.telegram.is_configured:
            asyncio.create_task(
                self.telegram.send_pending_trade_alert(
                    trade_id=trade_id,
                    direction=direction,
                    leverage=leverage,
                    confidence=confidence,
                    take_profit_percent=take_profit,
                    stop_loss_percent=stop_loss,
                    reasoning=reasoning,
                    expires_in_seconds=expires_in_seconds,
                )
            )
    
    async def notify_trade_confirmed(
        self,
        trade_id: str,
        confirmed_by: str,
        signal: Dict[str, Any],
    ) -> None:
        """Notify when a pending trade is confirmed."""
        direction = signal.get("direction", "hold")
        
        payload = {
            "event": "trade_confirmed",
            "trade_id": trade_id,
            "direction": direction,
            "confirmed_by": confirmed_by,
            "confirmed_at": datetime.now().isoformat(),
        }
        
        logger.info(
            "notification_trade_confirmed",
            trade_id=trade_id,
            confirmed_by=confirmed_by
        )
        
        await self._broadcast_websocket(payload)
        
        if self.telegram.is_configured:
            asyncio.create_task(
                self.telegram.send_trade_confirmed(
                    trade_id=trade_id,
                    direction=direction,
                    confirmed_by=confirmed_by,
                )
            )
    
    async def notify_trade_rejected(
        self,
        trade_id: str,
        rejected_by: str,
        reason: str = "",
    ) -> None:
        """Notify when a pending trade is rejected."""
        payload = {
            "event": "trade_rejected",
            "trade_id": trade_id,
            "rejected_by": rejected_by,
            "reason": reason,
            "rejected_at": datetime.now().isoformat(),
        }
        
        logger.info(
            "notification_trade_rejected",
            trade_id=trade_id,
            rejected_by=rejected_by
        )
        
        await self._broadcast_websocket(payload)
        
        if self.telegram.is_configured:
            asyncio.create_task(
                self.telegram.send_trade_rejected(
                    trade_id=trade_id,
                    rejected_by=rejected_by,
                    reason=reason,
                )
            )
    
    async def notify_trade_expired(self, trade_id: str) -> None:
        """Notify when a pending trade expires."""
        payload = {
            "event": "trade_expired",
            "trade_id": trade_id,
            "expired_at": datetime.now().isoformat(),
        }
        
        logger.info("notification_trade_expired", trade_id=trade_id)
        
        await self._broadcast_websocket(payload)
        
        if self.telegram.is_configured:
            asyncio.create_task(
                self.telegram.send_trade_expired(trade_id)
            )
    
    async def notify_trade_executed(
        self,
        trade_id: str,
        direction: str,
        entry_price: float,
        leverage: int,
    ) -> None:
        """Notify when trade is executed."""
        payload = {
            "event": "trade_executed",
            "trade_id": trade_id,
            "direction": direction,
            "entry_price": entry_price,
            "leverage": leverage,
            "executed_at": datetime.now().isoformat(),
        }
        
        logger.info(
            "notification_trade_executed",
            trade_id=trade_id,
            direction=direction
        )
        
        await self._broadcast_websocket(payload)
        
        if self.telegram.is_configured:
            asyncio.create_task(
                self.telegram.send_trade_executed(
                    trade_id=trade_id,
                    direction=direction,
                    entry_price=entry_price,
                    leverage=leverage,
                )
            )
    
    async def _broadcast_websocket(self, payload: Dict[str, Any]) -> None:
        """Broadcast to all registered WebSocket listeners."""
        for listener in self._websocket_listeners:
            try:
                await listener(payload)
            except Exception as e:
                logger.warning("websocket_broadcast_error", error=str(e))


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get singleton NotificationService instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
