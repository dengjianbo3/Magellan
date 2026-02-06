"""
Notifications Package

Provides multi-channel notification support for trading events.
- WebSocket: Real-time frontend notifications
- Telegram: Mobile push notifications
"""

from .service import NotificationService, get_notification_service
from .telegram import TelegramNotifier

__all__ = [
    "NotificationService",
    "get_notification_service",
    "TelegramNotifier",
]
