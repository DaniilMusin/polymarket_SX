#!/usr/bin/env python3
"""
Test run script - run bot with safe test parameters.

This script temporarily overrides config to use safe test values:
- MAX_POSITION_SIZE = $10
- MIN_PROFIT_BPS = 100 (1%)
- ENABLE_REAL_TRADING = false (simulation mode)

Usage:
    python scripts/test_run.py              # Dry run mode
    python scripts/test_run.py --real       # Real trading (use with caution!)
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def main():
    """Run test with safe parameters."""
    parser = argparse.ArgumentParser(description='Test run with safe parameters')
    parser.add_argument(
        '--real',
        action='store_true',
        help='Enable REAL trading (default: simulation mode)'
    )
    parser.add_argument(
        '--position-size',
        type=float,
        default=10,
        help='Max position size in USD (default: 10)'
    )
    parser.add_argument(
        '--min-profit',
        type=float,
        default=100,
        help='Min profit in bps (default: 100 = 1%%)'
    )
    parser.add_argument(
        '--duration',
        '--timeout',
        dest='duration',
        type=int,
        default=300,
        help='Run duration in seconds (default: 300 = 5 minutes)'
    )
    args = parser.parse_args()

    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║                                                                            ║")
    print("║            🧪 TEST RUN                                                     ║")
    print("║                                                                            ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")

    # Load .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    # Display test parameters
    print(f"{Colors.BOLD}Test Parameters:{Colors.END}\n")
    mode_color = Colors.GREEN if args.real else Colors.YELLOW
    mode_text = 'REAL TRADING' if args.real else 'SIMULATION'
    print(f"  Mode: {mode_color}{mode_text}{Colors.END}")
    print(f"  Max Position Size: ${args.position_size}")
    print(f"  Min Profit: {args.min_profit} bps ({args.min_profit/100:.2f}%)")
    print(f"  Duration: {args.duration} seconds ({args.duration/60:.1f} minutes)")
    print()

    if args.real:
        print(f"{Colors.RED}{Colors.BOLD}⚠️  WARNING: REAL TRADING ENABLED!{Colors.END}")
        print(f"{Colors.RED}Real money will be used. Are you sure?{Colors.END}")
        response = input("Type 'YES' to continue: ")
        if response != 'YES':
            print(f"\n{Colors.YELLOW}Test cancelled.{Colors.END}")
            return
        print()

    # Override environment variables
    os.environ['MAX_POSITION_SIZE'] = str(args.position_size)
    os.environ['MIN_PROFIT_BPS'] = str(args.min_profit)
    os.environ['ENABLE_REAL_TRADING'] = 'true' if args.real else 'false'

    print(f"{Colors.GREEN}Starting test run...{Colors.END}\n")
    print(f"{Colors.BOLD}Press Ctrl+C to stop{Colors.END}\n")
    print("=" * 80 + "\n")

    # Import and run main
    async def run_with_timeout():
        try:
            import main

            await asyncio.wait_for(main.main(), timeout=args.duration)
        except asyncio.TimeoutError:
            print(
                f"\n\n{Colors.YELLOW}Test duration reached ({args.duration}s). "
                f"Stopping...{Colors.END}"
            )
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Test stopped by user.{Colors.END}")
        except Exception as exc:
            print(f"\n\n{Colors.RED}Test failed: {exc}{Colors.END}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    asyncio.run(run_with_timeout())


if __name__ == '__main__':
    main()
