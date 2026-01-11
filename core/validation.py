"""
Runtime validation of risk parameters and trading configuration.

This module enforces hard limits to prevent dangerous configurations
from being used in production, regardless of what's in .env file.
"""

import logging
import config


def validate_risk_config() -> None:
    """
    Validate risk configuration before starting trading.

    Raises RuntimeError if configuration is unsafe for real trading.
    This provides a runtime safety net against dangerous .env defaults.
    """
    logger = logging.getLogger(__name__)

    # If we're in simulation mode, be lenient (but still warn)
    if not config.ENABLE_REAL_TRADING:
        if config.MIN_PROFIT_BPS < 50:
            logger.warning(
                f"MIN_PROFIT_BPS={config.MIN_PROFIT_BPS} is low. "
                "This is OK for simulation, but would be risky for real trading."
            )
        if config.MAX_POSITION_SIZE > 100:
            logger.warning(
                f"MAX_POSITION_SIZE={config.MAX_POSITION_SIZE} is high. "
                "This is OK for simulation (dry-run), but would be risky for real trading."
            )
        logger.info("Simulation mode - risk checks are warnings only")
        return

    # ========================================================================
    # REAL TRADING MODE - ENFORCE HARD LIMITS
    # ========================================================================

    logger.info("=" * 60)
    logger.info("REAL TRADING MODE ENABLED - Validating risk parameters...")
    logger.info("=" * 60)

    errors = []

    # Check #1: MIN_PROFIT_BPS must be reasonable
    if config.MIN_PROFIT_BPS < 50:
        errors.append(
            f"MIN_PROFIT_BPS={config.MIN_PROFIT_BPS} bps is TOO LOW for real trading.\n"
            f"  -> Requirement: MIN_PROFIT_BPS >= 50 bps (0.5%)\n"
            f"  -> Recommended: MIN_PROFIT_BPS >= 100 bps (1.0%)\n"
            f"  -> Reason: Need margin for fees, slippage, and execution delays"
        )

    # Check #2: MAX_POSITION_SIZE must be conservative for initial trading
    if config.MAX_POSITION_SIZE > 100:
        errors.append(
            f"MAX_POSITION_SIZE=${config.MAX_POSITION_SIZE} is TOO HIGH for real trading.\n"
            f"  -> Requirement: MAX_POSITION_SIZE <= $100 for first runs\n"
            f"  -> Recommended: Start with $10-50\n"
            f"  -> Reason: Limit exposure until you've validated strategy with real data"
        )

    # Check #3: MAX_EXCHANGE_EXPOSURE should be reasonable
    if config.MAX_EXCHANGE_EXPOSURE > 500:
        errors.append(
            f"MAX_EXCHANGE_EXPOSURE=${config.MAX_EXCHANGE_EXPOSURE} is TOO HIGH.\n"
            f"  -> Requirement: MAX_EXCHANGE_EXPOSURE <= $500 for initial trading\n"
            f"  -> Reason: Limit total risk per exchange"
        )

    # Check #4: Warn about MAX_POSITION_PERCENT
    if config.MAX_POSITION_PERCENT > 0.2:
        errors.append(
            f"MAX_POSITION_PERCENT={config.MAX_POSITION_PERCENT} (20%+) is aggressive.\n"
            f"  -> Recommended: <= 0.1 (10%)\n"
            f"  -> Reason: Don't risk too much of available balance on single trade"
        )

    # If any errors, refuse to start
    if errors:
        logger.error("RISK VALIDATION FAILED")
        logger.error("")
        for i, error in enumerate(errors, 1):
            logger.error(f"ERROR #{i}:")
            for line in error.split("\n"):
                logger.error(f"  {line}")
            logger.error("")

        logger.error("=" * 60)
        logger.error("TO FIX: Update your .env file with safer parameters:")
        logger.error("  MIN_PROFIT_BPS=50.0        # Or higher (100+ recommended)")
        logger.error("  MAX_POSITION_SIZE=10.0     # Start small")
        logger.error("  MAX_EXCHANGE_EXPOSURE=500.0")
        logger.error("  MAX_POSITION_PERCENT=0.1")
        logger.error("=" * 60)

        raise RuntimeError(
            f"Risk validation failed with {len(errors)} error(s). "
            "Configuration is too risky for real trading. "
            "See log messages above for details."
        )

    # All checks passed
    logger.info("All risk checks PASSED")
    logger.info(f"  MIN_PROFIT_BPS: {config.MIN_PROFIT_BPS} bps")
    logger.info(f"  MAX_POSITION_SIZE: ${config.MAX_POSITION_SIZE}")
    logger.info(f"  MAX_EXCHANGE_EXPOSURE: ${config.MAX_EXCHANGE_EXPOSURE}")
    logger.info(f"  MAX_POSITION_PERCENT: {config.MAX_POSITION_PERCENT * 100}%")
    logger.info("=" * 60)


def validate_wallet_config() -> None:
    """
    Validate that wallet and API keys are configured for real trading.

    Raises RuntimeError if real trading is enabled but credentials are missing.
    """
    import os

    logger = logging.getLogger(__name__)

    if not config.ENABLE_REAL_TRADING:
        logger.info("Simulation mode - wallet validation skipped")
        return

    logger.info("Validating wallet and API configuration...")

    errors = []

    # Check private key
    private_key = os.getenv("PRIVATE_KEY", "")
    if not private_key or "YOUR-PRIVATE-KEY" in private_key.upper():
        errors.append("PRIVATE_KEY not configured (still has placeholder value)")

    # Check API keys (at least one exchange should be configured)
    pm_key = os.getenv("POLYMARKET_API_KEY", "")
    sx_key = os.getenv("SX_API_KEY", "")
    kalshi_key = os.getenv("KALSHI_API_KEY", "")

    configured_exchanges = []
    if pm_key and "YOUR" not in pm_key.upper():
        configured_exchanges.append("Polymarket")
    if sx_key and "YOUR" not in sx_key.upper():
        configured_exchanges.append("SX")
    if kalshi_key and "YOUR" not in kalshi_key.upper():
        configured_exchanges.append("Kalshi")

    if not configured_exchanges:
        errors.append(
            "No exchange API keys configured. Need at least one of:\n"
            "  - POLYMARKET_API_KEY\n"
            "  - SX_API_KEY\n"
            "  - KALSHI_API_KEY"
        )

    # If any errors, refuse to start
    if errors:
        logger.error("WALLET/API VALIDATION FAILED")
        logger.error("")
        for i, error in enumerate(errors, 1):
            logger.error(f"ERROR #{i}: {error}")
        logger.error("")
        logger.error("Cannot run in REAL TRADING mode without valid credentials.")
        logger.error("Either configure credentials or set ENABLE_REAL_TRADING=false")

        raise RuntimeError(
            "Wallet/API validation failed. Cannot run real trading without credentials."
        )

    logger.info("Wallet validation PASSED")
    logger.info(f"  Configured exchanges: {', '.join(configured_exchanges)}")


def validate_all() -> None:
    """
    Run all validation checks.

    Call this at the start of main.py before any trading logic.
    """
    validate_risk_config()
    validate_wallet_config()
