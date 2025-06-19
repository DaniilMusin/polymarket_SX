import logging
from aiohttp import ClientSession

from config import SLIP_BY_DEPTH
from core.metrics import g_edge, g_trades, g_pnl
from connectors import polymarket, sx


async def process_depth(
    session: ClientSession, pm_market: str, sx_market: str
) -> float:
    """Fetch depth from both exchanges and determine max slippage."""
    pm_depth = await polymarket.orderbook_depth(session, pm_market)
    sx_depth = await sx.orderbook_depth(session, sx_market)
    depth_value = min(pm_depth, sx_depth)

    max_slip = 0.0
    for threshold, slip in SLIP_BY_DEPTH:
        if depth_value >= threshold:
            max_slip = slip
            break

    g_edge.inc()
    g_trades.inc()
    g_pnl.set(0.0)
    logging.info("Depth PM %.2f SX %.2f -> max_slip %.4f", pm_depth, sx_depth, max_slip)
    return max_slip
