"""
Telegram Notification Service

Sends trading alerts via Telegram Bot API.
Supports interactive confirmation buttons.
"""

import os
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

import httpx
import structlog

logger = structlog.get_logger(__name__)


class TelegramNotifier:
    """
    Sends trading notifications via Telegram Bot.
    
    Environment variables:
    - TELEGRAM_BOT_TOKEN: Bot API token from @BotFather
    - TELEGRAM_CHAT_ID: Target chat ID for notifications
    """
    
    BASE_URL = "https://api.telegram.org/bot{token}"
    
    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        self._http_client: Optional[httpx.AsyncClient] = None
    
    @property
    def is_configured(self) -> bool:
        """Check if Telegram is properly configured."""
        return bool(self.bot_token and self.chat_id)
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    async def send_pending_trade_alert(
        self,
        trade_id: str,
        direction: str,
        leverage: int,
        confidence: int,
        take_profit_percent: float,
        stop_loss_percent: float,
        reasoning: str,
        expires_in_seconds: int,
    ) -> bool:
        """
        Send pending trade notification to Telegram.
        
        Returns True if message was sent successfully.
        """
        if not self.is_configured:
            logger.warning("telegram_not_configured")
            return False
        
        # Format direction emoji
        direction_emoji = "📈" if direction.lower() == "long" else "📉"
        direction_text = direction.upper()
        
        # Calculate expiry time
        expires_in_minutes = expires_in_seconds // 60
        
        # Build message
        message = f"""🔔 *新交易建议* `{trade_id[:12]}`

{direction_emoji} *方向*: {direction_text} | 💰 *杠杆*: {leverage}x
🎯 *止盈*: {take_profit_percent:.1f}% | 🛡️ *止损*: {stop_loss_percent:.1f}%
💪 *信心*: {confidence}%
⏰ *有效期*: {expires_in_minutes} 分钟

📝 *分析*:
{reasoning[:300]}{"..." if len(reasoning) > 300 else ""}

---
确认: `/confirm_{trade_id}`
拒绝: `/reject_{trade_id}`
查看: [控制台](http://localhost:8000/api/trading/pending/{trade_id})"""

        return await self._send_message(message, parse_mode="Markdown")
    
    async def send_trade_confirmed(
        self,
        trade_id: str,
        direction: str,
        confirmed_by: str,
    ) -> bool:
        """Send notification when trade is confirmed."""
        if not self.is_configured:
            return False
        
        message = f"""✅ *交易已确认*

🆔 `{trade_id}`
📊 方向: {direction.upper()}
👤 确认人: {confirmed_by}
⏰ 时间: {datetime.now().strftime("%H:%M:%S")}"""

        return await self._send_message(message, parse_mode="Markdown")
    
    async def send_trade_rejected(
        self,
        trade_id: str,
        rejected_by: str,
        reason: str = "",
    ) -> bool:
        """Send notification when trade is rejected."""
        if not self.is_configured:
            return False
        
        message = f"""❌ *交易已拒绝*

🆔 `{trade_id}`
👤 拒绝人: {rejected_by}
📝 原因: {reason or "未提供"}"""

        return await self._send_message(message, parse_mode="Markdown")
    
    async def send_trade_expired(self, trade_id: str) -> bool:
        """Send notification when trade expires."""
        if not self.is_configured:
            return False
        
        message = f"""⏰ *交易已过期*

🆔 `{trade_id}`
交易建议已超时未确认，已自动取消。"""

        return await self._send_message(message, parse_mode="Markdown")
    
    async def send_trade_executed(
        self,
        trade_id: str,
        direction: str,
        entry_price: float,
        leverage: int,
    ) -> bool:
        """Send notification when trade is executed."""
        if not self.is_configured:
            return False
        
        emoji = "🟢" if direction.lower() == "long" else "🔴"
        
        message = f"""{emoji} *交易已执行*

🆔 `{trade_id}`
📊 方向: {direction.upper()}
💰 入场价: ${entry_price:,.2f}
📈 杠杆: {leverage}x
⏰ 时间: {datetime.now().strftime("%H:%M:%S")}"""

        return await self._send_message(message, parse_mode="Markdown")
    
    async def _send_message(
        self,
        text: str,
        parse_mode: str = "Markdown",
    ) -> bool:
        """Send message via Telegram API."""
        try:
            client = await self._get_client()
            url = f"{self.BASE_URL.format(token=self.bot_token)}/sendMessage"
            
            response = await client.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                }
            )
            
            if response.status_code == 200:
                logger.info("telegram_message_sent", chat_id=self.chat_id[:8] + "...")
                return True
            else:
                logger.warning(
                    "telegram_send_failed",
                    status=response.status_code,
                    error=response.text[:200]
                )
                return False
                
        except Exception as e:
            logger.error("telegram_send_error", error=str(e))
            return False
    
    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Singleton instance
_telegram_notifier: Optional[TelegramNotifier] = None


def get_telegram_notifier() -> TelegramNotifier:
    """Get singleton TelegramNotifier instance."""
    global _telegram_notifier
    if _telegram_notifier is None:
        _telegram_notifier = TelegramNotifier()
    return _telegram_notifier
