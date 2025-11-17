#!/usr/bin/env python3
"""
Test Telegram bot configuration.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.alert_manager import AlertManager


async def main():
    """Test Telegram alerts."""
    print("🔔 Testing Telegram Bot Configuration\n")

    # Load .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  python-dotenv not installed")

    # Check config
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('TELEGRAM_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

    print(f"TELEGRAM_BOT_TOKEN: {'✓ Set' if telegram_token else '✗ Not set'}")
    print(f"TELEGRAM_CHAT_ID: {'✓ Set' if telegram_chat_id else '✗ Not set'}")
    print()

    if not telegram_token or not telegram_chat_id:
        print("❌ Telegram not configured!")
        print("\nTo configure:")
        print("1. Create bot: https://t.me/BotFather")
        print("2. Get chat ID: https://t.me/userinfobot")
        print("3. Add to .env:")
        print("   TELEGRAM_BOT_TOKEN=<your-token>")
        print("   TELEGRAM_CHAT_ID=<your-chat-id>")
        return

    # Test sending message
    print("📤 Sending test message...")

    manager = AlertManager()

    try:
        await manager.send_info_alert(
            "Telegram Test",
            "This is a test message from your arbitrage bot.",
            details={
                "Status": "Configuration successful",
                "Time": "Just now",
            }
        )

        print("✅ Test message sent successfully!")
        print("\nCheck your Telegram to confirm you received the message.")
        print("If you didn't receive it, check your bot token and chat ID.")

    except Exception as exc:
        print(f"❌ Failed to send message: {exc}")


if __name__ == '__main__':
    asyncio.run(main())
