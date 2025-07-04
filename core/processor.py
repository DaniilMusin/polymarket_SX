import logging

from config import SLIP_BY_DEPTH
from core.metrics import g_edge, g_trades


async def process_depth(pm_depth: float, sx_depth: float) -> float:
    """Determine max slippage given order book depths from both exchanges."""
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
