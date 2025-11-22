import logging
from typing import Dict, List, Optional

from config import (
    SLIP_BY_DEPTH, EXCHANGE_FEES, DEFAULT_FEE, MAX_POSITION_SIZE,
    MAX_POSITION_PERCENT, MIN_PROFIT_BPS
)
from core.metrics import g_edge, g_trades
from core.exchange_balances import get_balance_manager, InsufficientBalanceError


def calculate_total_depth(orderbook: Dict[str, List[Dict]]) -> float:
    """Вычисляем общую глубину стакана"""
    total_bids = sum(order["size"] for order in orderbook.get("bids", []))
    total_asks = sum(order["size"] for order in orderbook.get("asks", []))
    return total_bids + total_asks


def validate_orderbook(orderbook: dict) -> bool:
    """
    Validate orderbook data.

    Args:
        orderbook: Orderbook dictionary from connector

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(orderbook, dict):
        logging.warning("Invalid orderbook: not a dictionary (type: %s)", type(orderbook).__name__)
        return False

    required_keys = ['best_bid', 'best_ask', 'bid_depth', 'ask_depth', 'total_depth']
    if not all(key in orderbook for key in required_keys):
        missing_keys = [key for key in required_keys if key not in orderbook]
        logging.warning("Invalid orderbook: missing keys: %s", missing_keys)
        return False

    # Check for valid prices (must be positive)
    if orderbook['best_bid'] <= 0 or orderbook['best_ask'] <= 0:
        logging.warning(
            "Invalid orderbook: non-positive prices: bid=%.4f, ask=%.4f",
            orderbook['best_bid'],
            orderbook['best_ask']
        )
        return False

    # Check prices are in valid range [0, 1] for probability markets
    if orderbook['best_bid'] > 1.0 or orderbook['best_ask'] > 1.0:
        logging.warning(
            "Invalid orderbook: prices out of range [0,1]: bid=%.4f, ask=%.4f",
            orderbook['best_bid'],
            orderbook['best_ask']
        )
        return False

    # Check bid < ask
    if orderbook['best_bid'] >= orderbook['best_ask']:
        logging.warning(
            "Invalid orderbook: bid %.4f >= ask %.4f",
            orderbook['best_bid'],
            orderbook['best_ask']
        )
        return False

    # Check for valid depth
    if orderbook['total_depth'] < 0:
        logging.warning("Invalid orderbook: negative total_depth: %.2f", orderbook['total_depth'])
        return False

    # Check bid_depth and ask_depth are non-negative
    if orderbook['bid_depth'] < 0 or orderbook['ask_depth'] < 0:
        logging.warning(
            "Invalid orderbook: negative depth: bid_depth=%.2f, ask_depth=%.2f",
            orderbook['bid_depth'],
            orderbook['ask_depth']
        )
        return False

    logging.debug(
        "Orderbook validated successfully: bid=%.4f, ask=%.4f",
        orderbook['best_bid'], orderbook['best_ask']
    )
    return True


def calculate_spread(orderbook: dict) -> float:
    """
    Calculate the spread (ask - bid) from orderbook.

    Args:
        orderbook: Orderbook dictionary

    Returns:
        Spread as a float
    """
    return orderbook['best_ask'] - orderbook['best_bid']


def calculate_spread_percent(orderbook: dict) -> float:
    """
    Calculate the spread as a percentage of mid price.

    Args:
        orderbook: Orderbook dictionary

    Returns:
        Spread percentage
    """
    spread = calculate_spread(orderbook)
    mid_price = (orderbook['best_bid'] + orderbook['best_ask']) / 2.0
    if mid_price == 0:
        return 0.0
    return (spread / mid_price) * 100.0


def find_arbitrage_opportunity(
    pm_book: dict,
    sx_book: dict,
    min_profit_bps: float = None  # Minimum profit in basis points (from config if None)
) -> Optional[Dict]:
    """
    Find arbitrage opportunity between two orderbooks.

    Strategy:
    - Buy on exchange with lower ask
    - Sell on exchange with higher bid
    - Profit = (higher_bid - lower_ask) - slippage - fees

    Args:
        pm_book: Polymarket orderbook
        sx_book: SX orderbook
        min_profit_bps: Minimum profit in basis points (1 bp = 0.01%)

    Returns:
        Dictionary with arbitrage details or None if no opportunity
    """
    # Use config default if not specified
    if min_profit_bps is None:
        min_profit_bps = MIN_PROFIT_BPS

    logging.debug(
        "Finding arbitrage opportunity between PM and SX (min profit: %.2f bps)",
        min_profit_bps
    )

    # Validate orderbooks
    if not validate_orderbook(pm_book):
        logging.warning("Polymarket orderbook validation failed")
        return None
    if not validate_orderbook(sx_book):
        logging.warning("SX orderbook validation failed")
        return None

    # Calculate slippage based on depth
    min_depth = min(pm_book['total_depth'], sx_book['total_depth'])
    max_slip = calculate_slippage(min_depth)

    # Two scenarios:
    # 1. Buy on PM, sell on SX: profit = SX_bid - PM_ask
    # 2. Buy on SX, sell on PM: profit = PM_bid - SX_ask

    scenario_1_profit = sx_book['best_bid'] - pm_book['best_ask']
    scenario_2_profit = pm_book['best_bid'] - sx_book['best_ask']

    # Subtract slippage and fees
    # Fee is 0.1% per side, 0.2% total for round-trip (buy + sell)
    # Use configured fees per exchange, or default if not found
    fees = max(
        EXCHANGE_FEES.get('polymarket', DEFAULT_FEE),
        EXCHANGE_FEES.get('sx', DEFAULT_FEE)
    )
    scenario_1_net = scenario_1_profit - max_slip - fees
    scenario_2_net = scenario_2_profit - max_slip - fees

    # Find best scenario
    if scenario_1_net > scenario_2_net:
        profit = scenario_1_net
        buy_exchange = "polymarket"
        sell_exchange = "sx"
        buy_price = pm_book['best_ask']
        sell_price = sx_book['best_bid']
    else:
        profit = scenario_2_net
        buy_exchange = "sx"
        sell_exchange = "polymarket"
        buy_price = sx_book['best_ask']
        sell_price = pm_book['best_bid']

    # Convert to basis points
    profit_bps = profit * 10000

    # Check if profitable
    if profit_bps < min_profit_bps:
        logging.debug(
            "No arbitrage: profit %.2f bps < min %.2f bps",
            profit_bps,
            min_profit_bps
        )
        return None

    # Calculate position size based on available depth
    max_size = min(
        pm_book['bid_depth'] if buy_exchange == "sx" else pm_book['ask_depth'],
        sx_book['bid_depth'] if buy_exchange == "polymarket" else sx_book['ask_depth']
    )

    # Limit position size to avoid excessive slippage
    # CRITICAL: Also limit by available balance on BOTH exchanges!
    try:
        balance_manager = get_balance_manager()
        max_buy_balance = balance_manager.get_balance(buy_exchange)
        max_sell_balance = balance_manager.get_balance(sell_exchange)
        max_balance = min(max_buy_balance, max_sell_balance)

        # Position size is limited by:
        # 1. Market depth (configurable % to avoid slippage)
        # 2. Hard cap from config (default $1000)
        # 3. Available balance on BOTH exchanges (CRITICAL!)
        position_size = min(
            max_size * MAX_POSITION_PERCENT, MAX_POSITION_SIZE, max_balance
        )
    except InsufficientBalanceError as exc:
        # If balance manager not available or has insufficient balance, use fallback
        logging.warning(
            "Balance manager unavailable or insufficient balance: %s, using default",
            exc
        )
        position_size = min(max_size * MAX_POSITION_PERCENT, MAX_POSITION_SIZE)
    except Exception as exc:
        # Catch any other unexpected errors
        logging.warning(
            "Unexpected error getting balance: %s, using default limit",
            exc, exc_info=True
        )
        position_size = min(max_size * MAX_POSITION_PERCENT, MAX_POSITION_SIZE)

    # Check minimum position size (avoid zero or very small positions)
    min_position_size = 0.01  # Minimum $0.01
    if position_size < min_position_size:
        logging.debug(
            "Position size too small: $%.6f < $%.2f, skipping arbitrage",
            position_size, min_position_size
        )
        return None

    opportunity = {
        'buy_exchange': buy_exchange,
        'sell_exchange': sell_exchange,
        'buy_price': buy_price,
        'sell_price': sell_price,
        'profit': profit,
        'profit_bps': profit_bps,
        'profit_percent': profit * 100,
        'slippage': max_slip,
        'fees': fees,
        'net_profit': profit,
        'position_size': position_size,
        'expected_pnl': profit * position_size,
    }

    g_edge.inc()  # Increment arbitrage signal counter

    logging.info(
        "🎯 ARBITRAGE FOUND: Buy %s @ %.4f, Sell %s @ %.4f | "
        "Profit: %.2f bps (%.4f%%) | Size: $%.2f | Expected PnL: $%.2f",
        buy_exchange, buy_price, sell_exchange, sell_price,
        profit_bps, profit * 100, position_size, profit * position_size
    )

    return opportunity


def calculate_slippage(depth: float) -> float:
    """
    Calculate maximum slippage based on orderbook depth.

    Args:
        depth: Total orderbook depth (bid + ask)

    Returns:
        Maximum slippage as a float
    """
    # Validate depth
    if depth is None or depth < 0:
        logging.warning("Invalid depth: %s, using max slippage", depth)
        return max(SLIP_BY_DEPTH.values()) if SLIP_BY_DEPTH else 0.002

    # По умолчанию используем максимальное проскальзывание
    max_slip = max(SLIP_BY_DEPTH.values()) if SLIP_BY_DEPTH else 0.002

    # Находим подходящее проскальзывание на основе глубины
    for d, slip in sorted(SLIP_BY_DEPTH.items(), reverse=True):
        if depth >= d:
            max_slip = slip
            break

    return max_slip


async def process_depth(pm_depth: float, sx_depth: float) -> float:
    """
    DEPRECATED: Use find_arbitrage_opportunity instead.

    Определяем максимальное проскальзывание на основе глубины стакана с обеих бирж.
    """
    # Validate inputs
    if pm_depth is None or sx_depth is None:
        raise TypeError("pm_depth and sx_depth must not be None")

    if not isinstance(pm_depth, (int, float)) or not isinstance(sx_depth, (int, float)):
        raise TypeError("pm_depth and sx_depth must be numeric")

    # Берем минимальную глубину (лимитирующий фактор)
    depth_value = min(pm_depth, sx_depth)

    max_slip = calculate_slippage(depth_value)

    g_trades.inc()

    logging.info("Depth PM %.2f SX %.2f -> max_slip %.4f", pm_depth, sx_depth, max_slip)
    return max_slip


async def process_arbitrage(
    pm_book: dict,
    sx_book: dict,
    execute: bool = False
) -> Optional[Dict]:
    """
    Process arbitrage between Polymarket and SX.

    Args:
        pm_book: Polymarket orderbook
        sx_book: SX orderbook
        execute: If True, execute the trade (requires order placement functions)

    Returns:
        Arbitrage opportunity dict or None
    """
    opportunity = find_arbitrage_opportunity(pm_book, sx_book)

    if not opportunity:
        return None

    if execute:
        logging.warning(
            "Trade execution requested but not implemented. "
            "Arbitrage opportunity logged but not executed."
        )
        # TODO: Implement trade execution
        # - Place orders on both exchanges
        # - Monitor execution
        # - Update PnL metrics

    return opportunity
