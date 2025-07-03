import logging
from aiohttp import ClientSession

from config import SLIP_BY_DEPTH
from core.metrics import g_edge, g_trades
from connectors import polymarket, sx


async def process_depth(
    session: ClientSession, pm_market: str, sx_market: str
) -> float:
    """Fetch depth from both exchanges and determine max slippage."""
    pm_depth = await polymarket.orderbook_depth(session, pm_market)
    sx_depth = await sx.orderbook_depth(session, sx_market)
    depth_value = min(pm_depth, sx_depth)

    max_slip = 0.0
    for d, slip in sorted(SLIP_BY_DEPTH.items(), reverse=True):
        if depth_value >= d:
            max_slip = slip
            break

    g_edge.inc()
    g_trades.inc()
    logging.info("Depth PM %.2f SX %.2f -> max_slip %.4f", pm_depth, sx_depth, max_slip)
    return max_slip
