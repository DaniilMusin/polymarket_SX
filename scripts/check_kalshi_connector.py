#!/usr/bin/env python3
"""
Test Kalshi connector in isolation.

This script tests the Kalshi connector by:
1. Fetching orderbook for a real market
2. Displaying bid/ask prices and depth
3. Verifying data format
4. Checking for errors

Usage:
    python scripts/test_kalshi_connector.py <market_ticker>

Example:
    python scripts/test_kalshi_connector.py PRES-2024
"""

import asyncio
import logging
import sys
from pathlib import Path
from aiohttp import ClientSession

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure aiohttp works with aiodns on Windows
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from connectors import kalshi
from core.logging_config import setup_logging


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


async def test_orderbook(market_ticker: str):
    """Test orderbook fetch for a Kalshi market."""
    print(f"\n{Colors.BOLD}Testing Kalshi Connector{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 80}{Colors.END}\n")

    print(f"Market Ticker: {Colors.YELLOW}{market_ticker}{Colors.END}\n")

    try:
        async with ClientSession() as session:
            print(f"{Colors.BLUE}Fetching orderbook...{Colors.END}")
            orderbook = await kalshi.orderbook_depth(session, market_ticker)

            # Display results
            print(f"\n{Colors.GREEN}✓ Successfully fetched orderbook{Colors.END}\n")

            print(f"{Colors.BOLD}Orderbook Data:{Colors.END}")
            # Connector returns probabilities (0-1). Convert to cents for display.
            best_bid = orderbook['best_bid']
            best_ask = orderbook['best_ask']
            best_bid_cents = best_bid * 100.0
            best_ask_cents = best_ask * 100.0
            spread = best_ask - best_bid
            spread_cents = spread * 100.0
            spread_pct = (spread / best_bid * 100.0) if best_bid else 0.0

            print(f"  Best Bid:    {Colors.GREEN}{best_bid_cents:.2f}c{Colors.END} ({best_bid:.2%})")
            print(f"  Best Ask:    {Colors.RED}{best_ask_cents:.2f}c{Colors.END} ({best_ask:.2%})")
            print(f"  Spread:      {Colors.YELLOW}{spread_cents:.2f}c ({spread_pct:.2f}%){Colors.END}")
            print(f"  Bid Depth (qty):        {orderbook['bid_qty_depth']:.0f} contracts")
            print(f"  Ask Depth (qty):        {orderbook['ask_qty_depth']:.0f} contracts")
            print(f"  Total Depth (qty):      {orderbook['total_qty_depth']:.0f} contracts")
            print(f"  Total Depth (notional): ${orderbook['total_notional_depth']:.2f}")

            # Display top 5 bids and asks
            print(f"\n{Colors.BOLD}Top 5 Bids:{Colors.END}")
            bids = orderbook.get('bids', [])[:5]
            if bids:
                for i, bid in enumerate(bids, 1):
                    price_prob = float(bid.get('price', 0))
                    price_cents = price_prob * 100.0
                    size = float(bid.get('size', bid.get('quantity', 0)))
                    print(
                        f"  {i}. {Colors.GREEN}{price_cents:.2f}c{Colors.END} "
                        f"({price_prob:.2%}) @ {size:.0f} contracts"
                    )
            else:
                print(f"  {Colors.YELLOW}No bids available{Colors.END}")

            print(f"\n{Colors.BOLD}Top 5 Asks:{Colors.END}")
            asks = orderbook.get('asks', [])[:5]
            if asks:
                for i, ask in enumerate(asks, 1):
                    yes_price_prob = float(ask.get('price', 0))
                    yes_price_cents = yes_price_prob * 100.0
                    size = float(ask.get('size', ask.get('quantity', 0)))
                    print(
                        f"  {i}. {Colors.RED}{yes_price_cents:.2f}c{Colors.END} "
                        f"({yes_price_prob:.2%}) - {size:.0f} contracts"
                    )
            else:
                print(f"  {Colors.YELLOW}No asks available{Colors.END}")

            # Validation checks
            print(f"\n{Colors.BOLD}Validation Checks:{Colors.END}")
            checks = []

            # Check 1: Has bid and ask
            if orderbook['best_bid'] > 0 and orderbook['best_ask'] > 0:
                checks.append((True, "Has valid bid and ask prices"))
            else:
                checks.append((False, "Missing bid or ask prices"))

            # Check 2: Bid < Ask
            if orderbook['best_bid'] < orderbook['best_ask']:
                checks.append((True, "Bid < Ask (normal market)"))
            else:
                checks.append((False, "Bid >= Ask (crossed market!)"))

            # Check 3: Has depth
            if orderbook['total_qty_depth'] > 0:
                checks.append((True, f"Has liquidity ({orderbook['total_qty_depth']:.0f} contracts)"))
            else:
                checks.append((False, "No liquidity available"))

            # Check 4: Reasonable prices (0-1 probability for Kalshi)
            if 0 <= orderbook['best_bid'] <= 1 and 0 <= orderbook['best_ask'] <= 1:
                checks.append((True, "Prices in valid range (0-1 probability)"))
            else:
                checks.append((False, "Prices outside valid range"))

            for passed, msg in checks:
                symbol = f"{Colors.GREEN}✓{Colors.END}" if passed else f"{Colors.RED}✗{Colors.END}"
                print(f"  {symbol} {msg}")

            all_passed = all(c[0] for c in checks)
            if all_passed:
                print(f"\n{Colors.GREEN}{Colors.BOLD}✓ ALL CHECKS PASSED{Colors.END}")
                print(f"\n{Colors.GREEN}Connector is working correctly!{Colors.END}\n")
                return True
            else:
                print(f"\n{Colors.RED}{Colors.BOLD}✗ SOME CHECKS FAILED{Colors.END}")
                print(f"\n{Colors.YELLOW}Connector may have issues. Check the data above.{Colors.END}\n")
                return False

    except Exception as exc:
        print(f"\n{Colors.RED}✗ Error fetching orderbook:{Colors.END}")
        print(f"{Colors.RED}{exc}{Colors.END}\n")
        logging.error("Kalshi connector test failed", exc_info=True)
        return False


def main():
    """Main function."""
    setup_logging(level=logging.INFO)

    if len(sys.argv) < 2:
        print(f"{Colors.RED}Error: Market ticker required{Colors.END}")
        print(f"\nUsage: {Colors.BOLD}python {sys.argv[0]} <market_ticker>{Colors.END}")
        print(f"\nExample: python {sys.argv[0]} PRES-2024")
        print(f"\n{Colors.YELLOW}Note:{Colors.END} You need a real Kalshi market ticker.")
        print(f"Find markets at: {Colors.BLUE}https://kalshi.com{Colors.END}\n")
        sys.exit(1)

    market_ticker = sys.argv[1]

    success = asyncio.run(test_orderbook(market_ticker))
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
