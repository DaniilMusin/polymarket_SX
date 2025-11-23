#!/usr/bin/env python3
"""
Pre-flight check script for production deployment.
Run this before starting the bot to verify everything is configured correctly.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.wallet import Wallet, WalletError  # noqa: E402


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def check_mark(passed: bool) -> str:
    """Return checkmark or X based on status."""
    return f"{Colors.GREEN}✓{Colors.END}" if passed else f"{Colors.RED}✗{Colors.END}"


def print_header(text: str):
    """Print section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}\n")


def check_env_file() -> bool:
    """Check if .env file exists."""
    print(f"{Colors.BOLD}1. Checking .env file...{Colors.END}")

    if not os.path.exists('.env'):
        print(f"  {check_mark(False)} .env file not found!")
        print(f"  {Colors.YELLOW}→ Copy .env.example to .env and fill in your values{Colors.END}")
        return False

    print(f"  {check_mark(True)} .env file exists")
    return True


def check_private_key() -> tuple[bool, str]:
    """Check if private key is configured."""
    print(f"\n{Colors.BOLD}2. Checking wallet configuration...{Colors.END}")

    private_key = os.getenv('PRIVATE_KEY')
    if not private_key:
        print(f"  {check_mark(False)} PRIVATE_KEY not set in .env")
        return False, None

    print(f"  {check_mark(True)} PRIVATE_KEY is set")

    # Try to load wallet
    try:
        wallet = Wallet(private_key)
        print(f"  {check_mark(True)} Wallet loaded successfully")
        print(f"  {Colors.GREEN}→ Address: {wallet.address}{Colors.END}")
        return True, wallet.address
    except WalletError as e:
        print(f"  {check_mark(False)} Failed to load wallet: {e}")
        return False, None


def check_api_keys() -> dict:
    """Check if API keys are configured."""
    print(f"\n{Colors.BOLD}3. Checking API keys...{Colors.END}")

    apis = {
        'POLYMARKET_API_KEY': os.getenv('POLYMARKET_API_KEY'),
        'SX_API_KEY': os.getenv('SX_API_KEY'),
        'KALSHI_API_KEY': os.getenv('KALSHI_API_KEY'),
    }

    results = {}
    for name, value in apis.items():
        if value:
            print(f"  {check_mark(True)} {name}: {value[:8]}...")
            results[name] = True
        else:
            print(f"  {check_mark(False)} {name}: Not set")
            results[name] = False

    return results


def check_trading_config() -> dict:
    """Check trading configuration."""
    print(f"\n{Colors.BOLD}4. Checking trading configuration...{Colors.END}")

    enable_trading = os.getenv('ENABLE_REAL_TRADING', 'false').lower() == 'true'
    min_profit_bps = float(os.getenv('MIN_PROFIT_BPS', '10'))
    max_position_size = float(os.getenv('MAX_POSITION_SIZE', '1000'))

    color = Colors.GREEN if enable_trading else Colors.YELLOW
    print(f"  ENABLE_REAL_TRADING: {color}{enable_trading}{Colors.END}")

    if not enable_trading:
        print(f"    {Colors.YELLOW}⚠  Real trading is DISABLED (simulation mode){Colors.END}")

    print(f"  MIN_PROFIT_BPS: {min_profit_bps}")
    if min_profit_bps < 50:
        print(
            f"    {Colors.YELLOW}⚠  Low threshold! "
            f"Recommended >= 50 for production{Colors.END}"
        )

    print(f"  MAX_POSITION_SIZE: ${max_position_size}")
    if max_position_size > 100:
        print(
            f"    {Colors.YELLOW}⚠  Large position size! "
            f"Recommended <= $100 for testing{Colors.END}"
        )

    return {
        'enable_trading': enable_trading,
        'min_profit_bps': min_profit_bps,
        'max_position_size': max_position_size,
    }


def check_event_validation() -> dict:
    """Check event validation configuration (CRITICAL for production)."""
    print(f"\n{Colors.BOLD}5. Checking event validation (CRITICAL)...{Colors.END}")

    perplexity_key = os.getenv('PERPLEXITY_API_KEY')
    allow_unvalidated = os.getenv('ALLOW_UNVALIDATED_EVENTS', 'false').lower() == 'true'

    results = {}

    if perplexity_key:
        print(f"  {check_mark(True)} PERPLEXITY_API_KEY: {perplexity_key[:8]}...")
        print(f"    {Colors.GREEN}→ Event validation is ENABLED{Colors.END}")
        results['enabled'] = True
        results['safe'] = True
    elif allow_unvalidated:
        print(f"  {check_mark(False)} PERPLEXITY_API_KEY: Not set")
        print(f"  {Colors.YELLOW}→ ALLOW_UNVALIDATED_EVENTS=true{Colors.END}")
        print(f"    {Colors.RED}⚠  WARNING: Event validation is DISABLED!{Colors.END}")
        print(f"    {Colors.RED}   You may arbitrage between DIFFERENT events and LOSE MONEY!{Colors.END}")
        results['enabled'] = False
        results['safe'] = False
    else:
        print(f"  {check_mark(False)} PERPLEXITY_API_KEY: Not set")
        print(f"  {check_mark(False)} ALLOW_UNVALIDATED_EVENTS: false (safe default)")
        print(f"    {Colors.YELLOW}→ Bot will REFUSE to start without event validation{Colors.END}")
        print(f"    {Colors.YELLOW}   Set PERPLEXITY_API_KEY to enable validation{Colors.END}")
        results['enabled'] = False
        results['safe'] = True  # Safe because bot will refuse to start

    return results


def check_balance_limits() -> dict:
    """Check virtual balance configuration."""
    print(f"\n{Colors.BOLD}6. Checking virtual balance limits...{Colors.END}")

    exchange_balance = float(os.getenv('EXCHANGE_INITIAL_BALANCE', '10.0'))
    pm_balance = float(os.getenv('POLYMARKET_BALANCE', str(exchange_balance)))
    sx_balance = float(os.getenv('SX_BALANCE', str(exchange_balance)))
    kalshi_balance = float(os.getenv('KALSHI_BALANCE', str(exchange_balance)))

    print(f"  EXCHANGE_INITIAL_BALANCE (default): ${exchange_balance}")
    print(f"  POLYMARKET_BALANCE: ${pm_balance}")
    print(f"  SX_BALANCE: ${sx_balance}")
    print(f"  KALSHI_BALANCE: ${kalshi_balance}")

    total_exposure = pm_balance + sx_balance + kalshi_balance

    if total_exposure > 100:
        print(f"    {Colors.YELLOW}⚠  Total exposure: ${total_exposure:.2f}{Colors.END}")
        print(f"    {Colors.YELLOW}   Recommended <= $100 for initial testing{Colors.END}")

    return {
        'polymarket': pm_balance,
        'sx': sx_balance,
        'kalshi': kalshi_balance,
        'total': total_exposure,
    }


def check_risk_limits() -> dict:
    """Check risk management configuration."""
    print(f"\n{Colors.BOLD}7. Checking risk limits...{Colors.END}")

    max_market_exposure = float(os.getenv('MAX_MARKET_EXPOSURE', '1500.0'))
    max_exchange_exposure = float(os.getenv('MAX_EXCHANGE_EXPOSURE', '2500.0'))
    max_open_arbs = int(os.getenv('MAX_OPEN_ARBITRAGES', '3'))
    panic_on_partial = os.getenv('PANIC_TRIGGER_ON_PARTIAL', 'true').lower() == 'true'

    print(f"  MAX_MARKET_EXPOSURE: ${max_market_exposure}")
    print(f"  MAX_EXCHANGE_EXPOSURE: ${max_exchange_exposure}")
    print(f"  MAX_OPEN_ARBITRAGES: {max_open_arbs}")
    print(f"  PANIC_TRIGGER_ON_PARTIAL: {panic_on_partial}")

    if max_exchange_exposure > 5000:
        print(f"    {Colors.YELLOW}⚠  Very high exchange exposure limit!{Colors.END}")

    if not panic_on_partial:
        print(f"    {Colors.RED}⚠  WARNING: Panic on partial fill is DISABLED{Colors.END}")
        print(f"    {Colors.RED}   Recommended to keep PANIC_TRIGGER_ON_PARTIAL=true{Colors.END}")

    return {
        'max_market_exposure': max_market_exposure,
        'max_exchange_exposure': max_exchange_exposure,
        'max_open_arbs': max_open_arbs,
        'panic_on_partial': panic_on_partial,
    }


def check_alert_config() -> dict:
    """Check alert configuration."""
    print(f"\n{Colors.BOLD}8. Checking alert configuration...{Colors.END}")

    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')

    results = {}

    if telegram_token and telegram_chat_id:
        print(f"  {check_mark(True)} Telegram alerts configured")
        results['telegram'] = True
    else:
        print(f"  {check_mark(False)} Telegram alerts not configured")
        print(
            f"    {Colors.YELLOW}→ Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID "
            f"in .env{Colors.END}"
        )
        results['telegram'] = False

    if discord_webhook:
        print(f"  {check_mark(True)} Discord alerts configured")
        results['discord'] = True
    else:
        print(f"  {check_mark(False)} Discord alerts not configured")
        print(f"    {Colors.YELLOW}→ Set DISCORD_WEBHOOK_URL in .env{Colors.END}")
        results['discord'] = False

    if not results.get('telegram') and not results.get('discord'):
        print(f"\n  {Colors.RED}⚠  NO ALERTS CONFIGURED!{Colors.END}")
        print(
            f"  {Colors.RED}This is CRITICAL for production - "
            f"you won't be notified of issues!{Colors.END}"
        )

    return results


def print_summary(results: dict):
    """Print final summary."""
    print_header("📋 PRE-FLIGHT CHECK SUMMARY")

    all_passed = all([
        results.get('env_file'),
        results.get('wallet'),
        any(results.get('api_keys', {}).values()),
    ])

    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ BASIC CHECKS PASSED{Colors.END}")
        print("\nYour bot configuration is valid.\n")
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ SOME CHECKS FAILED{Colors.END}")
        print("\nPlease fix the issues above before starting the bot.\n")
        return False

    # Check for CRITICAL issues that block real trading
    enable_trading = results.get('trading_config', {}).get('enable_trading', False)
    event_val_safe = results.get('event_validation', {}).get('safe', True)

    critical_issues = []

    if enable_trading and not event_val_safe:
        critical_issues.append(
            "Event validation is DISABLED but real trading is ENABLED - "
            "this is DANGEROUS!"
        )

    no_telegram = not results.get('alerts', {}).get('telegram')
    no_discord = not results.get('alerts', {}).get('discord')
    if enable_trading and no_telegram and no_discord:
        critical_issues.append("Real trading enabled but NO ALERTS configured!")

    if critical_issues:
        print(f"{Colors.RED}{Colors.BOLD}🚨 CRITICAL ISSUES (BLOCKING):{Colors.END}\n")
        for issue in critical_issues:
            print(f"  • {Colors.RED}{issue}{Colors.END}\n")
        print(f"  {Colors.RED}Bot should NOT be started with these issues!{Colors.END}\n")

    # Warnings
    print(f"{Colors.YELLOW}{Colors.BOLD}⚠  IMPORTANT WARNINGS:{Colors.END}\n")

    if not enable_trading:
        print("  • Real trading is DISABLED (simulation mode)")
        print("    Set ENABLE_REAL_TRADING=true to enable real trading\n")

    if no_telegram and no_discord and not enable_trading:
        print(f"  • {Colors.YELLOW}NO ALERTS CONFIGURED{Colors.END}")
        print("    Recommended to set up Telegram or Discord alerts")
        print("    See: scripts/setup_telegram_bot.py or scripts/setup_discord_webhook.py\n")

    max_pos = results.get('trading_config', {}).get('max_position_size', 0)
    if max_pos > 100:
        print(f"  • Large MAX_POSITION_SIZE (${max_pos})")
        print("    Recommended to start with $10-100 for testing\n")

    min_profit = results.get('trading_config', {}).get('min_profit_bps', 0)
    if min_profit < 50:
        print(f"  • Low MIN_PROFIT_BPS ({min_profit})")
        print("    Recommended >= 50 bps (0.5%) for production\n")

    total_bal = results.get('balance_limits', {}).get('total', 0)
    if total_bal > 100:
        print(f"  • High total virtual balance (${total_bal:.2f})")
        print("    Recommended <= $100 for initial testing\n")

    print(f"{Colors.BOLD}NEXT STEPS:{Colors.END}\n")
    print("  1. Fix any warnings above")
    print("  2. Check balance on exchanges: python scripts/check_balances.py")
    print("  3. Run test with small amounts: python scripts/test_run.py")
    print("  4. Start bot: python main.py")
    print("  5. Monitor logs for 🚨 CRITICAL alerts\n")

    return True


def main():
    """Run all pre-flight checks."""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                      ║")
    print("║            🚀 PRODUCTION PRE-FLIGHT CHECK                            ║")
    print("║                                                                      ║")
    print("║         This script verifies your bot is ready for deployment       ║")
    print("║                                                                      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")

    # Load .env if it exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print(
            f"{Colors.YELLOW}⚠  python-dotenv not installed. "
            f"Install it: pip install python-dotenv{Colors.END}\n"
        )

    results = {}

    # Run checks
    results['env_file'] = check_env_file()
    results['wallet'], wallet_address = check_private_key()
    results['api_keys'] = check_api_keys()
    results['trading_config'] = check_trading_config()
    results['event_validation'] = check_event_validation()
    results['balance_limits'] = check_balance_limits()
    results['risk_limits'] = check_risk_limits()
    results['alerts'] = check_alert_config()

    # Print summary
    success = print_summary(results)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
