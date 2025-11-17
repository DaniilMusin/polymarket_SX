#!/usr/bin/env python3
"""
Test Discord webhook configuration.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.alert_manager import AlertManager


async def main():
    """Test Discord alerts."""
    print("🔔 Testing Discord Webhook Configuration\n")

    # Load .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  python-dotenv not installed")

    # Check config
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')

    print(f"DISCORD_WEBHOOK_URL: {'✓ Set' if discord_webhook else '✗ Not set'}")
    print()

    if not discord_webhook:
        print("❌ Discord webhook not configured!")
        print("\nTo configure:")
        print("1. Go to Discord channel settings")
        print("2. Integrations → Webhooks")
        print("3. Create webhook")
        print("4. Copy webhook URL")
        print("5. Add to .env:")
        print("   DISCORD_WEBHOOK_URL=<your-webhook-url>")
        return

    # Test sending message
    print("📤 Sending test messages...")

    manager = AlertManager()

    try:
        # Test info message
        await manager.send_info_alert(
            "Discord Test - INFO",
            "This is a test INFO message from your arbitrage bot.",
            details={
                "Status": "Configuration successful",
                "Type": "INFO",
            }
        )
        print("✅ INFO message sent")

        # Wait a bit
        await asyncio.sleep(1)

        # Test warning message
        await manager.send_warning_alert(
            "Discord Test - WARNING",
            "This is a test WARNING message.",
            details={
                "Status": "Test warning",
                "Type": "WARNING",
            }
        )
        print("✅ WARNING message sent")

        # Wait a bit
        await asyncio.sleep(1)

        # Test critical message
        await manager.send_critical_alert(
            "Discord Test - CRITICAL",
            "This is a test CRITICAL message.",
            details={
                "Status": "Test critical alert",
                "Type": "CRITICAL",
            }
        )
        print("✅ CRITICAL message sent")

        print("\n✅ All test messages sent successfully!")
        print("\nCheck your Discord channel to confirm you received 3 messages:")
        print("  1. Blue message (INFO)")
        print("  2. Orange message (WARNING)")
        print("  3. Red message (CRITICAL)")

    except Exception as exc:
        print(f"❌ Failed to send messages: {exc}")


if __name__ == '__main__':
    asyncio.run(main())
