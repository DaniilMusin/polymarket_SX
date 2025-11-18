#!/usr/bin/env python3
"""
Check balances on all exchanges before starting the bot.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.wallet import Wallet  # noqa: E402
import aiohttp  # noqa: E402


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


async def check_polygon_balance(wallet: Wallet):
    """Check USDC balance on Polygon (for Polymarket)."""
    print(f"\n{Colors.BOLD}Checking Polygon (Polymarket)...{Colors.END}")

    try:
        # Polygon RPC
        rpc_url = "https://polygon-rpc.com"

        # USDC contract on Polygon
        usdc_address = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"

        # ERC20 balanceOf function signature
        balance_of_sig = "0x70a08231"  # balanceOf(address)
        wallet_address = wallet.address

        # Pad address to 32 bytes
        padded_address = "0" * 24 + wallet_address[2:]

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_call",
            "params": [{
                "to": usdc_address,
                "data": balance_of_sig + padded_address
            }, "latest"]
        }

        # Add timeout to prevent hanging on network issues
        timeout = aiohttp.ClientTimeout(total=10.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(rpc_url, json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    balance_hex = result.get('result', '0x0')
                    balance_wei = int(balance_hex, 16)
                    balance_usdc = balance_wei / 1e6  # USDC has 6 decimals

                    print(f"  Address: {wallet.address}")
                    print(f"  USDC Balance: ${balance_usdc:.2f}")

                    if balance_usdc < 10:
                        print(f"  {Colors.RED}⚠  Low balance! Recommended >= $10{Colors.END}")
                    elif balance_usdc < 100:
                        print(
                            f"  {Colors.YELLOW}⚠  Moderate balance. "
                            f"Recommended >= $100 for production{Colors.END}"
                        )
                    else:
                        print(f"  {Colors.GREEN}✓ Good balance{Colors.END}")

                    return balance_usdc
                else:
                    print(f"  {Colors.RED}✗ Failed to fetch balance{Colors.END}")
                    return None

    except Exception as exc:
        print(f"  {Colors.RED}✗ Error: {exc}{Colors.END}")
        return None


async def check_sx_balance():
    """Check balance on SX (would need API key and endpoint)."""
    print(f"\n{Colors.BOLD}Checking SX...{Colors.END}")
    print(f"  {Colors.YELLOW}ℹ  SX balance check requires specific API endpoint{Colors.END}")
    print("  Please check manually at: https://sx.bet/")
    return None


async def check_kalshi_balance():
    """Check balance on Kalshi (would need API key)."""
    print(f"\n{Colors.BOLD}Checking Kalshi...{Colors.END}")
    print(f"  {Colors.YELLOW}ℹ  Kalshi balance check requires API authentication{Colors.END}")
    print("  Please check manually at: https://kalshi.com/")
    return None


async def main():
    """Check balances on all exchanges."""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║                                                                            ║")
    print("║            💰 BALANCE CHECK                                                ║")
    print("║                                                                            ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")

    # Load .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print(f"{Colors.YELLOW}⚠  python-dotenv not installed{Colors.END}\n")

    # Load wallet
    try:
        private_key = os.getenv('PRIVATE_KEY')
        if not private_key:
            print(f"{Colors.RED}✗ PRIVATE_KEY not set in .env{Colors.END}")
            return

        wallet = Wallet(private_key)
        print(f"Wallet: {wallet.address}\n")

    except Exception as exc:
        print(f"{Colors.RED}✗ Failed to load wallet: {exc}{Colors.END}")
        return

    # Check balances
    polygon_balance = await check_polygon_balance(wallet)
    await check_sx_balance()
    await check_kalshi_balance()

    # Summary
    print(f"\n{Colors.BOLD}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}SUMMARY{Colors.END}\n")

    if polygon_balance is not None and polygon_balance > 0:
        print(f"  {Colors.GREEN}✓ Polymarket (Polygon): ${polygon_balance:.2f}{Colors.END}")
    else:
        print(f"  {Colors.RED}✗ Polymarket: Unable to check or zero balance{Colors.END}")

    print(f"\n{Colors.YELLOW}Note: SX and Kalshi balances need to be checked manually{Colors.END}")
    print(f"\n{Colors.BOLD}RECOMMENDATIONS:{Colors.END}")
    print("  • Keep at least $100 on each exchange for testing")
    print("  • Start with MAX_POSITION_SIZE = $10-50")
    print("  • Monitor balances regularly\n")


if __name__ == '__main__':
    asyncio.run(main())
