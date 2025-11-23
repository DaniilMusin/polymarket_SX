import asyncio
import logging
from aiohttp import ClientSession

from core.logging_config import setup_logging
from core.metrics import init_metrics
from core.processor import process_arbitrage
from core.trader import execute_arbitrage_trade
from core.statistics import get_statistics_collector
from connectors import polymarket, sx, kalshi  # noqa: F401
import config


async def main() -> None:
    setup_logging(level=logging.INFO)

    logging.info("=" * 80)
    logging.info("🚀 Starting Polymarket-SX Arbitrage Bot")
    logging.info("=" * 80)
    logging.info("Mode: %s", "REAL TRADING" if config.ENABLE_REAL_TRADING else "SIMULATION")
    logging.info("=" * 80)

    init_metrics()
    stats_collector = get_statistics_collector()

    try:
        async with ClientSession() as session:
            # ===============================================================================
            # CRITICAL: Replace with REAL market IDs before running!
            # ===============================================================================
            # These are placeholder IDs. The bot will fail with these values.
            #
            # To find real market IDs, run:
            #   python scripts/find_markets.py
            #
            # Then test each market individually:
            #   python scripts/check_polymarket_connector.py <market_id>
            #   python scripts/check_sx_connector.py <market_id>
            #
            # Example real IDs (verify these are current!):
            #   Polymarket: condition_id from https://gamma-api.polymarket.com/markets
            #   SX: market_id from https://api.sx.bet/markets
            # ===============================================================================
            pm_market_id = "REPLACE_WITH_REAL_POLYMARKET_MARKET_ID"
            sx_market_id = "REPLACE_WITH_REAL_SX_MARKET_ID"

            # Check if market IDs were updated
            if "REPLACE" in pm_market_id or "REPLACE" in sx_market_id:
                logging.error("=" * 80)
                logging.error("❌ CRITICAL ERROR: Market IDs not configured!")
                logging.error("=" * 80)
                logging.error("")
                logging.error("You must replace placeholder market IDs with real ones.")
                logging.error("")
                logging.error("Steps:")
                logging.error("1. Run: python scripts/find_markets.py")
                logging.error("2. Pick market IDs with high liquidity")
                logging.error("3. Test: python scripts/check_polymarket_connector.py <id>")
                logging.error("4. Update pm_market_id and sx_market_id in main.py")
                logging.error("")
                logging.error("=" * 80)
                return

            try:
                # Get full orderbooks with prices
                from core.processor import validate_orderbook
                pm_book = await polymarket.orderbook_depth(session, pm_market_id)
                # Validate orderbook format before accessing keys
                if not validate_orderbook(pm_book):
                    logging.error("Invalid Polymarket orderbook format")
                    return
                logging.info(
                    "Polymarket: bid=%.4f ask=%.4f depth=%.2f",
                    pm_book['best_bid'],
                    pm_book['best_ask'],
                    pm_book['total_depth']
                )
            except Exception as exc:
                logging.error("Failed to get Polymarket orderbook: %s", exc)
                return

            try:
                sx_book = await sx.orderbook_depth(session, sx_market_id)
                # Validate orderbook format before accessing keys
                if not validate_orderbook(sx_book):
                    logging.error("Invalid SX orderbook format")
                    return
                logging.info(
                    "SX: bid=%.4f ask=%.4f depth=%.2f",
                    sx_book['best_bid'],
                    sx_book['best_ask'],
                    sx_book['total_depth']
                )
            except Exception as exc:
                logging.error("Failed to get SX orderbook: %s", exc)
                return

            # Find arbitrage opportunity
            opportunity = await process_arbitrage(
                pm_book, sx_book, pm_market_id=pm_market_id, sx_market_id=sx_market_id, execute=False
            )

            if opportunity:
                logging.info("🎯 Arbitrage opportunity found!")
                logging.info(
                    "   Buy on %s @ %.4f",
                    opportunity['buy_exchange'],
                    opportunity['buy_price']
                )
                logging.info(
                    "   Sell on %s @ %.4f",
                    opportunity['sell_exchange'],
                    opportunity['sell_price']
                )
                logging.info(
                    "   Profit: %.2f bps ($%.2f)",
                    opportunity['profit_bps'],
                    opportunity['expected_pnl']
                )

                # Execute trade (controlled by ENABLE_REAL_TRADING in .env)
                try:
                    result = await execute_arbitrage_trade(
                        session,
                        opportunity,
                        pm_market_id,
                        sx_market_id,
                        dry_run=not config.ENABLE_REAL_TRADING
                    )
                    logging.info("Trade execution result: %s", result['status'])

                    # Log statistics
                    executed = result['status'] not in ['simulated', 'failed']
                    actual_pnl = result.get('actual_pnl')  # Will be None for simulated trades
                    stats_collector.log_opportunity(
                        opportunity,
                        executed=executed,
                        actual_pnl=actual_pnl
                    )

                except Exception as exc:
                    logging.error("Trade execution failed: %s", exc)
                    stats_collector.log_opportunity(
                        opportunity,
                        executed=False,
                        execution_error=str(exc)
                    )
            else:
                logging.info("No arbitrage opportunity found")

            logging.info("=" * 80)
            logging.info("✅ Bot cycle completed successfully")
            logging.info("=" * 80)

    except Exception as exc:
        logging.error("=" * 80)
        logging.error("❌ Bot terminated with error")
        logging.error("=" * 80)
        logging.error("Unexpected error in main: %s", exc, exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
