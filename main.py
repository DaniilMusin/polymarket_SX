import asyncio
import logging
from aiohttp import ClientSession

from core.metrics import init_metrics
from core.alerts import TelegramHandler
from core.processor import process_depth
from connectors import polymarket, sx


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger().addHandler(TelegramHandler())
    init_metrics()

    async with ClientSession() as session:
        # Example market ids placeholders
        pm_depth = await polymarket.orderbook_depth(session, "pm_example")
        sx_depth = await sx.orderbook_depth(session, "sx_example")
        await process_depth(pm_depth, sx_depth)


if __name__ == "__main__":
    asyncio.run(main())
