import asyncio
import logging
from aiohttp import ClientSession

from core.logging_config import setup_logging
from core.metrics import init_metrics
from core.processor import process_arbitrage
from core.trader import execute_arbitrage_trade
from connectors import polymarket, sx, kalshi  # noqa: F401
import config


async def main() -> None:
    setup_logging(level=logging.INFO)

    logging.info("=" * 80)
    logging.info("🚀 Starting Polymarket-SX Arbitrage Bot")
    logging.info("=" * 80)

    init_metrics()

    try:
        async with ClientSession() as session:
            # Example market ids placeholders
            pm_market_id = "pm_example"
            sx_market_id = "sx_example"

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
                result = await execute_arbitrage_trade(
                    session,
                    opportunity,
                    pm_market_id,
                    sx_market_id,
                    dry_run=not config.ENABLE_REAL_TRADING
                )
                logging.info("Trade execution result: %s", result['status'])
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
