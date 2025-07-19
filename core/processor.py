import logging
from typing import Dict, List

from config import SLIP_BY_DEPTH
from core.metrics import g_edge, g_trades


def calculate_total_depth(orderbook: Dict[str, List[Dict]]) -> float:
    """Вычисляем общую глубину стакана"""
    total_bids = sum(order["size"] for order in orderbook.get("bids", []))
    total_asks = sum(order["size"] for order in orderbook.get("asks", []))
    return total_bids + total_asks


async def process_depth(pm_orderbook: Dict, sx_orderbook: Dict) -> float:
    """Определяем максимальное проскальзывание на основе глубины стакана с обеих бирж."""
    
    # Вычисляем общую глубину для каждой биржи
    pm_depth = calculate_total_depth(pm_orderbook)
    sx_depth = calculate_total_depth(sx_orderbook)
    
    # Берем минимальную глубину (лимитирующий фактор)
    depth_value = min(pm_depth, sx_depth)

    # По умолчанию используем максимальное проскальзывание, если глубина ниже всех порогов
    max_slip = max(SLIP_BY_DEPTH.values()) if SLIP_BY_DEPTH else 0.0
    
    # Находим подходящее проскальзывание на основе глубины
    for d, slip in sorted(SLIP_BY_DEPTH.items(), reverse=True):
        if depth_value >= d:
            max_slip = slip
            break

    g_edge.inc()
    g_trades.inc()
    
    logging.info("Depth PM %.2f SX %.2f -> max_slip %.4f", pm_depth, sx_depth, max_slip)
    return max_slip
