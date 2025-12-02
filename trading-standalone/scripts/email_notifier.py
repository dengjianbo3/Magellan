#!/usr/bin/env python3
"""
Email Notification Service for Trading Decisions

Sends email notifications when trading decisions are made.
Can be run standalone or imported as a module.
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class EmailNotifier:
    """
    Email notification service for trading events.

    Supports:
    - Trading decision notifications
    - TP/SL trigger alerts
    - Error notifications
    - Daily summary reports
    """

    def __init__(
        self,
        smtp_server: str = None,
        smtp_port: int = 587,
        smtp_user: str = None,
        smtp_password: str = None,
        from_address: str = None,
        to_addresses: List[str] = None,
        enabled: bool = True
    ):
        self.smtp_server = smtp_server or os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER", "")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD", "")
        self.from_address = from_address or os.getenv("EMAIL_FROM", self.smtp_user)

        to_env = os.getenv("EMAIL_TO", "")
        self.to_addresses = to_addresses or [a.strip() for a in to_env.split(",") if a.strip()]

        self.enabled = enabled and bool(self.smtp_user and self.smtp_password and self.to_addresses)

        if not self.enabled:
            logger.warning("Email notifications disabled: missing configuration")

    def _send_email(self, subject: str, body: str, html: bool = True) -> bool:
        """Send an email."""
        if not self.enabled:
            logger.debug("Email disabled, skipping send")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[Magellan Trading] {subject}"
            msg["From"] = self.from_address
            msg["To"] = ", ".join(self.to_addresses)

            if html:
                msg.attach(MIMEText(body, "html"))
            else:
                msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_address, self.to_addresses, msg.as_string())

            logger.info(f"Email sent: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def notify_decision(
        self,
        decision: str,
        symbol: str,
        confidence: float,
        reasoning: str,
        market_data: Dict[str, Any] = None,
        timestamp: datetime = None
    ) -> bool:
        """
        Send notification for trading decision.

        Args:
            decision: LONG, SHORT, HOLD, CLOSE
            symbol: Trading symbol
            confidence: Decision confidence (0-1)
            reasoning: Decision reasoning
            market_data: Optional market data
            timestamp: Decision timestamp
        """
        ts = timestamp or datetime.now()

        # Color based on decision
        colors = {
            "LONG": "#22c55e",   # Green
            "SHORT": "#ef4444",  # Red
            "HOLD": "#f59e0b",   # Orange
            "CLOSE": "#6366f1"   # Purple
        }
        color = colors.get(decision, "#6b7280")

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: {color}; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">📊 Trading Decision: {decision}</h1>
            </div>

            <div style="padding: 20px; background: #f3f4f6;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Symbol</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{symbol}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Confidence</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{confidence:.1%}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Time (UTC)</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{ts.strftime('%Y-%m-%d %H:%M:%S')}</td>
                    </tr>
        """

        if market_data:
            if "price" in market_data:
                html += f"""
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Current Price</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">${market_data['price']:,.2f}</td>
                    </tr>
                """

        html += f"""
                </table>

                <div style="margin-top: 20px; padding: 15px; background: white; border-radius: 8px;">
                    <h3 style="margin-top: 0; color: #374151;">Analysis Summary</h3>
                    <p style="color: #6b7280; line-height: 1.6;">{reasoning}</p>
                </div>
            </div>

            <div style="padding: 15px; background: #1f2937; color: #9ca3af; text-align: center; font-size: 12px;">
                Magellan Auto Trading System | Demo Mode
            </div>
        </body>
        </html>
        """

        return self._send_email(f"{decision} - {symbol}", html)

    def notify_execution(
        self,
        action: str,
        symbol: str,
        side: str,
        size: float,
        price: float,
        order_id: str = None,
        timestamp: datetime = None
    ) -> bool:
        """Send notification for trade execution."""
        ts = timestamp or datetime.now()

        color = "#22c55e" if side.upper() == "BUY" else "#ef4444"

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: {color}; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">⚡ Trade Executed: {side.upper()}</h1>
            </div>

            <div style="padding: 20px; background: #f3f4f6;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Symbol</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{symbol}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Action</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{action}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Size</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{size} USDT</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Price</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">${price:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Time (UTC)</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{ts.strftime('%Y-%m-%d %H:%M:%S')}</td>
                    </tr>
                </table>
            </div>

            <div style="padding: 15px; background: #1f2937; color: #9ca3af; text-align: center; font-size: 12px;">
                Order ID: {order_id or 'N/A'}
            </div>
        </body>
        </html>
        """

        return self._send_email(f"Executed {side.upper()} {symbol}", html)

    def notify_tp_sl(
        self,
        trigger_type: str,  # "TP" or "SL"
        symbol: str,
        pnl: float,
        pnl_percent: float,
        entry_price: float,
        exit_price: float,
        timestamp: datetime = None
    ) -> bool:
        """Send notification for TP/SL trigger."""
        ts = timestamp or datetime.now()

        is_profit = trigger_type == "TP"
        emoji = "🎯" if is_profit else "🛑"
        color = "#22c55e" if is_profit else "#ef4444"
        title = "Take Profit Hit!" if is_profit else "Stop Loss Triggered"

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: {color}; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">{emoji} {title}</h1>
            </div>

            <div style="padding: 20px; background: #f3f4f6;">
                <div style="text-align: center; padding: 20px;">
                    <div style="font-size: 36px; font-weight: bold; color: {color};">
                        {'+' if pnl >= 0 else ''}{pnl:.2f} USDT
                    </div>
                    <div style="font-size: 18px; color: #6b7280;">
                        ({'+' if pnl_percent >= 0 else ''}{pnl_percent:.2f}%)
                    </div>
                </div>

                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Symbol</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{symbol}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Entry Price</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">${entry_price:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Exit Price</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">${exit_price:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Time (UTC)</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{ts.strftime('%Y-%m-%d %H:%M:%S')}</td>
                    </tr>
                </table>
            </div>

            <div style="padding: 15px; background: #1f2937; color: #9ca3af; text-align: center; font-size: 12px;">
                Magellan Auto Trading System
            </div>
        </body>
        </html>
        """

        return self._send_email(f"{trigger_type} Triggered - {symbol}", html)

    def notify_error(
        self,
        error_type: str,
        message: str,
        details: str = None,
        timestamp: datetime = None
    ) -> bool:
        """Send notification for system errors."""
        ts = timestamp or datetime.now()

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #dc2626; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">⚠️ System Error</h1>
            </div>

            <div style="padding: 20px; background: #fef2f2;">
                <h3 style="color: #dc2626; margin-top: 0;">{error_type}</h3>
                <p style="color: #374151;">{message}</p>

                {f'<pre style="background: #fee2e2; padding: 15px; border-radius: 8px; overflow-x: auto; font-size: 12px;">{details}</pre>' if details else ''}

                <p style="color: #6b7280; font-size: 12px;">
                    Time: {ts.strftime('%Y-%m-%d %H:%M:%S')} UTC
                </p>
            </div>

            <div style="padding: 15px; background: #1f2937; color: #9ca3af; text-align: center; font-size: 12px;">
                Please check the trading service logs for more details.
            </div>
        </body>
        </html>
        """

        return self._send_email(f"ERROR: {error_type}", html)

    def notify_daily_summary(
        self,
        date: datetime,
        total_trades: int,
        winning_trades: int,
        total_pnl: float,
        total_pnl_percent: float,
        trades: List[Dict] = None
    ) -> bool:
        """Send daily trading summary."""
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        pnl_color = "#22c55e" if total_pnl >= 0 else "#ef4444"

        trades_html = ""
        if trades:
            trades_html = """
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                <tr style="background: #e5e7eb;">
                    <th style="padding: 10px; text-align: left;">Time</th>
                    <th style="padding: 10px; text-align: left;">Action</th>
                    <th style="padding: 10px; text-align: right;">PnL</th>
                </tr>
            """
            for trade in trades[-10:]:  # Last 10 trades
                trade_color = "#22c55e" if trade.get("pnl", 0) >= 0 else "#ef4444"
                trades_html += f"""
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{trade.get('time', 'N/A')}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{trade.get('action', 'N/A')}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: right; color: {trade_color};">
                        {trade.get('pnl', 0):+.2f} USDT
                    </td>
                </tr>
                """
            trades_html += "</table>"

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #3b82f6; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">📈 Daily Trading Summary</h1>
                <p style="margin: 10px 0 0 0;">{date.strftime('%Y-%m-%d')}</p>
            </div>

            <div style="padding: 20px; background: #f3f4f6;">
                <div style="text-align: center; padding: 20px;">
                    <div style="font-size: 36px; font-weight: bold; color: {pnl_color};">
                        {'+' if total_pnl >= 0 else ''}{total_pnl:.2f} USDT
                    </div>
                    <div style="font-size: 18px; color: #6b7280;">
                        ({'+' if total_pnl_percent >= 0 else ''}{total_pnl_percent:.2f}%)
                    </div>
                </div>

                <div style="display: flex; justify-content: space-around; margin: 20px 0;">
                    <div style="text-align: center;">
                        <div style="font-size: 24px; font-weight: bold; color: #374151;">{total_trades}</div>
                        <div style="color: #6b7280;">Total Trades</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 24px; font-weight: bold; color: #22c55e;">{winning_trades}</div>
                        <div style="color: #6b7280;">Winning</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 24px; font-weight: bold; color: #3b82f6;">{win_rate:.1f}%</div>
                        <div style="color: #6b7280;">Win Rate</div>
                    </div>
                </div>

                {trades_html}
            </div>

            <div style="padding: 15px; background: #1f2937; color: #9ca3af; text-align: center; font-size: 12px;">
                Magellan Auto Trading System | Daily Report
            </div>
        </body>
        </html>
        """

        return self._send_email(f"Daily Summary - {date.strftime('%Y-%m-%d')}", html)


# Singleton instance
_notifier: Optional[EmailNotifier] = None


def get_notifier() -> EmailNotifier:
    """Get or create the email notifier singleton."""
    global _notifier
    if _notifier is None:
        _notifier = EmailNotifier()
    return _notifier


def send_decision_notification(
    decision: str,
    symbol: str,
    confidence: float,
    reasoning: str,
    **kwargs
) -> bool:
    """Convenience function to send decision notification."""
    return get_notifier().notify_decision(decision, symbol, confidence, reasoning, **kwargs)


def send_execution_notification(
    action: str,
    symbol: str,
    side: str,
    size: float,
    price: float,
    **kwargs
) -> bool:
    """Convenience function to send execution notification."""
    return get_notifier().notify_execution(action, symbol, side, size, price, **kwargs)


def send_tp_sl_notification(
    trigger_type: str,
    symbol: str,
    pnl: float,
    pnl_percent: float,
    entry_price: float,
    exit_price: float,
    **kwargs
) -> bool:
    """Convenience function to send TP/SL notification."""
    return get_notifier().notify_tp_sl(trigger_type, symbol, pnl, pnl_percent, entry_price, exit_price, **kwargs)


def send_error_notification(error_type: str, message: str, **kwargs) -> bool:
    """Convenience function to send error notification."""
    return get_notifier().notify_error(error_type, message, **kwargs)


if __name__ == "__main__":
    # Test the email notifier
    import sys

    logging.basicConfig(level=logging.INFO)

    notifier = EmailNotifier()

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("Sending test email...")
        success = notifier.notify_decision(
            decision="LONG",
            symbol="BTC-USDT-SWAP",
            confidence=0.85,
            reasoning="Strong bullish momentum detected. RSI showing oversold conditions with positive divergence. Volume increasing on upward moves.",
            market_data={"price": 95000.00}
        )
        print(f"Email sent: {success}")
    else:
        print("Email Notifier Configuration:")
        print(f"  Enabled: {notifier.enabled}")
        print(f"  SMTP Server: {notifier.smtp_server}:{notifier.smtp_port}")
        print(f"  From: {notifier.from_address}")
        print(f"  To: {notifier.to_addresses}")
        print("\nRun with 'test' argument to send a test email:")
        print("  python email_notifier.py test")
