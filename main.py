import asyncio
import logging
from aiohttp import ClientSession

from core.metrics import init_metrics
from core.alerts import TelegramHandler
from core.processor import process_depth


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger().addHandler(TelegramHandler())
    init_metrics()

    async with ClientSession() as session:
        # Example market ids placeholders
        await process_depth(session, "pm_example", "sx_example")


if __name__ == "__main__":
    asyncio.run(main())
