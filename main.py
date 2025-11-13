import asyncio
import logging
from aiohttp import ClientSession

from core.metrics import init_metrics
from core.alerts import TelegramHandler
from core.processor import process_depth
from connectors import polymarket, sx, kalshi  # noqa: F401


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger().addHandler(TelegramHandler())
    init_metrics()

    try:
        async with ClientSession() as session:
            # Example market ids placeholders
            try:
                pm_depth = await polymarket.orderbook_depth(session, "pm_example")
            except Exception as exc:
                logging.error("Failed to get Polymarket depth: %s", exc)
                return

            try:
                sx_depth = await sx.orderbook_depth(session, "sx_example")
            except Exception as exc:
                logging.error("Failed to get SX depth: %s", exc)
                return

            await process_depth(pm_depth, sx_depth)
    except Exception as exc:
        logging.error("Unexpected error in main: %s", exc, exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
