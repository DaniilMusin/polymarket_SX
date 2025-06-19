import asyncio
import logging
import signal
from aiohttp import ClientSession

from core.metrics import init_metrics
from core.alerts import TelegramHandler
from core.processor import process_depth


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger().addHandler(TelegramHandler())
    init_metrics()

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    async with ClientSession() as session:
        # Example market ids placeholders
        await process_depth(session, "pm_example", "sx_example")
        await stop.wait()


if __name__ == "__main__":
    asyncio.run(main(), debug=True)
