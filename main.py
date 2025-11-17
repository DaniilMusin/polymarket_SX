import asyncio
import logging
from aiohttp import ClientSession

from core.metrics import init_metrics
from core.alerts import TelegramHandler
from core.processor import process_arbitrage
from core.trader import execute_arbitrage_trade
from connectors import polymarket, sx, kalshi  # noqa: F401


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger().addHandler(TelegramHandler())

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
                pm_book = await polymarket.orderbook_depth(session, pm_market_id)
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
            opportunity = await process_arbitrage(pm_book, sx_book, execute=False)

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

                # Execute trade (dry run by default)
                result = await execute_arbitrage_trade(
                    session,
                    opportunity,
                    pm_market_id,
                    sx_market_id,
                    dry_run=True  # Set to False for real trading
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
