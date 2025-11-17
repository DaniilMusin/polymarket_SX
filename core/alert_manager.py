"""
Enhanced alert system for sending notifications about critical events.

Supports:
- Telegram bot notifications
- Discord webhook notifications
"""

import logging
import os
import asyncio
from typing import Optional
import aiohttp


class AlertManager:
    """Manages alerts to various channels."""

    def __init__(self):
        """Initialize alert manager."""
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('TELEGRAM_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')

        self.telegram_enabled = bool(self.telegram_token and self.telegram_chat_id)
        self.discord_enabled = bool(self.discord_webhook)

        if not self.telegram_enabled and not self.discord_enabled:
            logging.warning(
                "⚠️  No alert channels configured! "
                "Set TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID or DISCORD_WEBHOOK_URL"
            )

    async def send_critical_alert(
        self,
        title: str,
        message: str,
        details: Optional[dict] = None
    ):
        """
        Send critical alert to all configured channels.

        Args:
            title: Alert title
            message: Alert message
            details: Optional dict with additional details
        """
        # Format message
        full_message = f"🚨 **CRITICAL: {title}**\n\n{message}"

        if details:
            full_message += "\n\n**Details:**\n"
            for key, value in details.items():
                full_message += f"• {key}: {value}\n"

        # Send to all channels
        tasks = []
        if self.telegram_enabled:
            tasks.append(self._send_telegram(full_message))
        if self.discord_enabled:
            tasks.append(self._send_discord(full_message, "CRITICAL"))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Log to console if no alerts configured
            logging.error("🚨 CRITICAL ALERT (no channels configured):")
            logging.error(full_message)

    async def send_warning_alert(
        self,
        title: str,
        message: str,
        details: Optional[dict] = None
    ):
        """Send warning alert."""
        full_message = f"⚠️  **WARNING: {title}**\n\n{message}"

        if details:
            full_message += "\n\n**Details:**\n"
            for key, value in details.items():
                full_message += f"• {key}: {value}\n"

        tasks = []
        if self.telegram_enabled:
            tasks.append(self._send_telegram(full_message))
        if self.discord_enabled:
            tasks.append(self._send_discord(full_message, "WARNING"))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def send_info_alert(
        self,
        title: str,
        message: str,
        details: Optional[dict] = None
    ):
        """Send info alert."""
        full_message = f"ℹ️  **{title}**\n\n{message}"

        if details:
            full_message += "\n\n**Details:**\n"
            for key, value in details.items():
                full_message += f"• {key}: {value}\n"

        tasks = []
        if self.telegram_enabled:
            tasks.append(self._send_telegram(full_message))
        if self.discord_enabled:
            tasks.append(self._send_discord(full_message, "INFO"))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_telegram(self, message: str):
        """Send message via Telegram bot."""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown',
            }

            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=10.0)
                async with session.post(url, json=payload, timeout=timeout) as resp:
                    if resp.status == 200:
                        logging.info("✅ Telegram alert sent")
                    else:
                        error = await resp.text()
                        logging.error("Failed to send Telegram alert: %s", error)

        except Exception as exc:
            logging.error("Error sending Telegram alert: %s", exc)

    async def _send_discord(self, message: str, level: str):
        """Send message via Discord webhook."""
        try:
            # Color based on level
            colors = {
                'CRITICAL': 0xFF0000,  # Red
                'WARNING': 0xFFA500,   # Orange
                'INFO': 0x0000FF,      # Blue
            }

            payload = {
                'embeds': [{
                    'description': message,
                    'color': colors.get(level, 0x0000FF),
                }]
            }

            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=10.0)
                async with session.post(
                    self.discord_webhook,
                    json=payload,
                    timeout=timeout
                ) as resp:
                    if resp.status in [200, 204]:
                        logging.info("✅ Discord alert sent")
                    else:
                        error = await resp.text()
                        logging.error("Failed to send Discord alert: %s", error)

        except Exception as exc:
            logging.error("Error sending Discord alert: %s", exc)


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get global alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


async def send_critical_alert(title: str, message: str, details: Optional[dict] = None):
    """Send critical alert (convenience function)."""
    manager = get_alert_manager()
    await manager.send_critical_alert(title, message, details)


async def send_warning_alert(title: str, message: str, details: Optional[dict] = None):
    """Send warning alert (convenience function)."""
    manager = get_alert_manager()
    await manager.send_warning_alert(title, message, details)


async def send_info_alert(title: str, message: str, details: Optional[dict] = None):
    """Send info alert (convenience function)."""
    manager = get_alert_manager()
    await manager.send_info_alert(title, message, details)
