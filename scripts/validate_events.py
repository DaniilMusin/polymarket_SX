#!/usr/bin/env python3
"""
Validate Events Script

This script validates that events on different exchanges (Polymarket, SX, Kalshi)
refer to the SAME real-world occurrence before allowing arbitrage trading.

This is CRITICAL to prevent arbitrage between DIFFERENT events, which would
result in losses instead of profits.

Usage:
    python scripts/validate_events.py \
        --pm-event "Trump wins 2024 election" \
        --pm-desc "Resolves YES if Trump wins..." \
        --sx-event "Trump 2024 winner" \
        --sx-desc "Resolves to YES if Donald Trump..."

Requirements:
    - PERPLEXITY_API_KEY must be set in .env
    - Or ALLOW_UNVALIDATED_EVENTS=true (NOT RECOMMENDED)
"""

import asyncio
import argparse
import logging
import sys
from aiohttp import ClientSession

# Add parent directory to path
sys.path.insert(0, '/home/user/polymarket_SX')

from core.event_validator import EventValidator, EventValidationError
from core.logging_config import setup_logging


async def main():
    parser = argparse.ArgumentParser(description="Validate events across exchanges")
    parser.add_argument("--pm-event", required=True, help="Polymarket event name")
    parser.add_argument("--pm-desc", required=True, help="Polymarket event description")
    parser.add_argument("--sx-event", required=True, help="SX event name")
    parser.add_argument("--sx-desc", required=True, help="SX event description")
    parser.add_argument(
        "--confidence-threshold",
        default="high",
        choices=["low", "medium", "high"],
        help="Minimum confidence level required (default: high)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if events are not the same (exit code 1)"
    )

    args = parser.parse_args()

    setup_logging(level=logging.INFO)

    print("=" * 80)
    print("EVENT VALIDATION")
    print("=" * 80)
    print()
    print("Polymarket Event:")
    print(f"  Name: {args.pm_event}")
    print(f"  Desc: {args.pm_desc}")
    print()
    print("SX Event:")
    print(f"  Name: {args.sx_event}")
    print(f"  Desc: {args.sx_desc}")
    print()
    print("=" * 80)

    validator = EventValidator()

    try:
        async with ClientSession() as session:
            result = await validator.validate_events(
                session,
                event1_name=args.pm_event,
                event1_description=args.pm_desc,
                platform1="Polymarket",
                event2_name=args.sx_event,
                event2_description=args.sx_desc,
                platform2="SX"
            )

        print()
        print("VALIDATION RESULT:")
        print("=" * 80)
        print(f"Are Same: {result['are_same']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Reasoning: {result['reasoning']}")
        if result.get('warning'):
            print(f"⚠️  Warning: {result['warning']}")
        print("=" * 80)

        # Check confidence threshold
        confidence_levels = ["low", "medium", "high"]
        required_level = confidence_levels.index(args.confidence_threshold)
        actual_level = confidence_levels.index(result['confidence']) if result['confidence'] in confidence_levels else -1

        if result['are_same']:
            if actual_level >= required_level:
                print()
                print("✅ Events are THE SAME with sufficient confidence")
                print("   Safe to proceed with arbitrage trading")
                return 0
            else:
                print()
                print(f"⚠️  Events appear same but confidence ({result['confidence']}) is below threshold ({args.confidence_threshold})")
                if args.strict:
                    print("   BLOCKED: Use --confidence-threshold to lower requirements")
                    return 1
                else:
                    print("   PROCEED WITH CAUTION")
                    return 0
        else:
            print()
            print("❌ Events are DIFFERENT")
            print("   DO NOT arbitrage between these events!")
            if args.strict:
                return 1
            return 0

    except EventValidationError as exc:
        print()
        print("=" * 80)
        print(f"❌ VALIDATION FAILED: {exc}")
        print("=" * 80)
        print()
        print("Event validation is REQUIRED to prevent dangerous arbitrage.")
        print("Please ensure PERPLEXITY_API_KEY is set in your .env file.")
        print()
        return 1
    except Exception as exc:
        logging.error("Unexpected error during validation: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
