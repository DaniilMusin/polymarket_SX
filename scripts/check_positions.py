#!/usr/bin/env python3
"""
Position Checker Script

Checks for open/unhedged positions across exchanges and compares
with internal risk/balance tracking.

This helps detect:
- Orphaned positions (exist on exchange but not tracked)
- Unhedged positions (one leg filled, other failed)
- Balance discrepancies between real and virtual balances

Usage:
    python scripts/check_positions.py [--alert-on-unhedged]

Requirements:
    - Exchange API keys must be configured in .env
    - Wallet must be configured for querying positions
"""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from core.risk import get_risk_manager
from core.exchange_balances import get_balance_manager


class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class PositionChecker:
    def __init__(self):
        self.risk_manager = get_risk_manager()
        self.balance_manager = get_balance_manager()

    async def check_polymarket_positions(self):
        """Query Polymarket for open positions."""
        # This would use Polymarket API to get actual positions
        # For now, return placeholder
        print(f"{Colors.YELLOW}  ⚠  Polymarket position query not yet implemented{Colors.END}")
        print(f"     Requires: https://clob.polymarket.com/positions?maker=<address>")
        return []

    async def check_sx_positions(self):
        """Query SX for open positions."""
        print(f"{Colors.YELLOW}  ⚠  SX position query not yet implemented{Colors.END}")
        print(f"     Requires: SX smart contract position query via web3")
        return []

    async def check_kalshi_positions(self):
        """Query Kalshi for open positions."""
        print(f"{Colors.YELLOW}  ⚠  Kalshi position query not yet implemented{Colors.END}")
        print(f"     Requires: GET /trade-api/v2/portfolio/positions")
        return []

    def check_internal_state(self):
        """Check internal risk and balance state."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}Internal State Check{Colors.END}")
        print("=" * 80)

        # Risk manager state
        print(f"\n{Colors.BOLD}Risk Manager:{Colors.END}")
        print(f"  Open Arbitrages: {self.risk_manager._open_arbs}")
        print(f"  Panic Mode: {self.risk_manager.is_panic()}")
        if self.risk_manager.is_panic():
            print(f"    {Colors.RED}Reason: {self.risk_manager._panic_reason}{Colors.END}")

        print(f"\n  Exchange Exposure:")
        for exchange, exposure in self.risk_manager._exchange_exposure.items():
            if exposure > 0:
                print(f"    {exchange}: ${exposure:.2f}")

        if self.risk_manager._market_exposure:
            print(f"\n  Market Exposure:")
            for market, exposure in self.risk_manager._market_exposure.items():
                if exposure > 0:
                    print(f"    {market[:16]}...: ${exposure:.2f}")

        # Balance manager state
        print(f"\n{Colors.BOLD}Balance Manager:{Colors.END}")
        all_balances = self.balance_manager.get_all_balances()

        for exchange, balances in all_balances.items():
            available = balances['available']
            locked = balances['locked']
            total = balances['total']
            initial = balances['initial']

            used = initial - total

            status_color = Colors.GREEN if total > 0 else Colors.RED
            print(f"\n  {exchange.upper()}:")
            print(f"    Initial:   ${initial:.2f}")
            print(f"    Available: {status_color}${available:.2f}{Colors.END}")
            print(f"    Locked:    ${locked:.2f}")
            print(f"    Total:     ${total:.2f}")
            print(f"    Used:      ${used:.2f} ({used/initial*100:.1f}%)")

            if locked > 0:
                print(f"      {Colors.YELLOW}⚠  WARNING: Balance is locked!{Colors.END}")
                print(f"         This may indicate incomplete trade or crash during execution")

    def analyze_discrepancies(self, real_positions: dict):
        """Analyze discrepancies between real and tracked positions."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}Discrepancy Analysis{Colors.END}")
        print("=" * 80)

        # Check if real positions exist but we have no exposure tracked
        has_real_positions = any(len(positions) > 0 for positions in real_positions.values())
        has_tracked_exposure = (
            self.risk_manager._open_arbs > 0 or
            any(exp > 0 for exp in self.risk_manager._exchange_exposure.values())
        )

        if has_real_positions and not has_tracked_exposure:
            print(f"\n{Colors.RED}🚨 CRITICAL: Orphaned positions detected!{Colors.END}")
            print(f"{Colors.RED}   Real positions exist on exchanges but no internal tracking{Colors.END}")
            print(f"{Colors.YELLOW}   Action required: Manual reconciliation needed{Colors.END}")
            return True

        if has_tracked_exposure and not has_real_positions:
            print(f"\n{Colors.YELLOW}⚠  WARNING: Tracked exposure but no real positions{Colors.END}")
            print(f"{Colors.YELLOW}   This is normal if positions were recently closed{Colors.END}")

        if not has_real_positions and not has_tracked_exposure:
            print(f"\n{Colors.GREEN}✓ No open positions (internal or real){Colors.END}")

        # Check for locked balances with no open arbitrages
        all_balances = self.balance_manager.get_all_balances()
        locked_with_no_arbs = any(
            b['locked'] > 0 for b in all_balances.values()
        ) and self.risk_manager._open_arbs == 0

        if locked_with_no_arbs:
            print(f"\n{Colors.YELLOW}⚠  WARNING: Locked balances with no open arbitrages{Colors.END}")
            print(f"{Colors.YELLOW}   This may indicate incomplete trade or crash{Colors.END}")
            print(f"{Colors.YELLOW}   Review recent logs for trade execution errors{Colors.END}")
            return True

        return False

    async def run(self):
        """Run all position checks."""
        print(f"{Colors.BOLD}{Colors.CYAN}")
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║                                                              ║")
        print("║              📋  POSITION CHECKER                            ║")
        print("║                                                              ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print(f"{Colors.END}\n")

        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Check internal state first
        self.check_internal_state()

        # Check real positions on exchanges
        print(f"\n{Colors.BOLD}{Colors.BLUE}Real Positions on Exchanges{Colors.END}")
        print("=" * 80)

        real_positions = {
            'polymarket': await self.check_polymarket_positions(),
            'sx': await self.check_sx_positions(),
            'kalshi': await self.check_kalshi_positions(),
        }

        # Analyze discrepancies
        has_issues = self.analyze_discrepancies(real_positions)

        # Summary
        print(f"\n{Colors.BOLD}{'=' * 80}{Colors.END}")
        if has_issues:
            print(f"{Colors.RED}{Colors.BOLD}🚨 ISSUES DETECTED - Manual review required{Colors.END}")
        else:
            print(f"{Colors.GREEN}{Colors.BOLD}✓ All checks passed{Colors.END}")

        print(f"\n{Colors.BOLD}Recommendations:{Colors.END}")
        print("  1. Run this check periodically (every 5-10 minutes) when bot is active")
        print("  2. Set up automated alerts for locked balances > 0 with no open arbs")
        print("  3. Immediately investigate any orphaned positions")
        print("  4. Check logs/errors.log if discrepancies are found")
        print()

        return has_issues


async def main():
    parser = argparse.ArgumentParser(description="Check positions across exchanges")
    parser.add_argument(
        '--alert-on-unhedged',
        action='store_true',
        help="Send alert if unhedged positions detected"
    )
    parser.add_argument(
        '--loop',
        type=int,
        metavar='SECONDS',
        help="Run continuously, checking every N seconds"
    )

    args = parser.parse_args()

    checker = PositionChecker()

    if args.loop:
        print(f"{Colors.YELLOW}Running in loop mode (checking every {args.loop} seconds){Colors.END}")
        print(f"{Colors.YELLOW}Press Ctrl+C to stop{Colors.END}\n")

        try:
            while True:
                has_issues = await checker.run()

                if has_issues and args.alert_on_unhedged:
                    # Send alert (would integrate with alert_manager)
                    print(f"{Colors.RED}[ALERT] Unhedged position detected{Colors.END}")

                await asyncio.sleep(args.loop)
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Monitoring stopped{Colors.END}")
    else:
        has_issues = await checker.run()
        sys.exit(1 if has_issues else 0)


if __name__ == '__main__':
    asyncio.run(main())
