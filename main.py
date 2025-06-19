import asyncio
import logging
from aiohttp import ClientSession

from config import SLIP_BY_DEPTH
from core.metrics import g_edge, g_trades, g_pnl, init_metrics
from core.alerts import TelegramHandler
from connectors.polymarket import orderbook_depth


async def process(depth_value: float):
    for d, slip in sorted(SLIP_BY_DEPTH.items(), reverse=True):
        if depth_value >= d:
            max_slip = slip
            break
    g_edge.inc()
    g_trades.inc()
    g_pnl.set(0.0)
    logging.info("Processed with max_slip %.4f", max_slip)


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger().addHandler(TelegramHandler())
    init_metrics()

    async with ClientSession() as session:
        # Example market id placeholder
        depth = await orderbook_depth(session, "example_market")
        await process(depth)


if __name__ == "__main__":
    asyncio.run(main())
