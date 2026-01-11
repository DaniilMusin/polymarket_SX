import logging
from typing import Dict, List, Optional

from config import (
    SLIP_BY_DEPTH,
    EXCHANGE_FEES,
    DEFAULT_FEE,
    MAX_POSITION_SIZE,
    MAX_POSITION_PERCENT,
    MIN_PROFIT_BPS,
    KALSHI_CONTRACT_COLLATERAL,
    KALSHI_CONTRACT_SIDE,
)
from core.metrics import g_edge, g_trades
from core.exchange_balances import get_balance_manager, InsufficientBalanceError
from core.opportunity_recorder import record_opportunity


def calculate_total_depth(orderbook: Dict[str, List[Dict]]) -> float:
    """Calculate total notional depth from orderbook levels."""
    total_bids = 0.0
    total_asks = 0.0
    for order in orderbook.get("bids", []):
        price = order.get("price", 0.0)
        size = order.get("size", 0.0)
        total_bids += float(price) * float(size)
    for order in orderbook.get("asks", []):
        price = order.get("price", 0.0)
        size = order.get("size", 0.0)
        total_asks += float(price) * float(size)
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
        logging.warning(
            "Invalid orderbook: not a dictionary (type: %s)", type(orderbook).__name__
        )
        return False

    required_keys = [
        "best_bid",
        "best_ask",
        "bid_qty_depth",
        "ask_qty_depth",
        "bid_notional_depth",
        "ask_notional_depth",
        "total_qty_depth",
        "total_notional_depth",
    ]
    if not all(key in orderbook for key in required_keys):
        missing_keys = [key for key in required_keys if key not in orderbook]
        logging.warning("Invalid orderbook: missing keys: %s", missing_keys)
        return False

    # Check for valid prices (must be positive)
    if orderbook["best_bid"] <= 0 or orderbook["best_ask"] <= 0:
        logging.warning(
            "Invalid orderbook: non-positive prices: bid=%.4f, ask=%.4f",
            orderbook["best_bid"],
            orderbook["best_ask"],
        )
        return False

    # Check prices are in valid range [0, 1] for probability markets
    if orderbook["best_bid"] > 1.0 or orderbook["best_ask"] > 1.0:
        logging.warning(
            "Invalid orderbook: prices out of range [0,1]: bid=%.4f, ask=%.4f",
            orderbook["best_bid"],
            orderbook["best_ask"],
        )
        return False

    # Check bid < ask
    if orderbook["best_bid"] >= orderbook["best_ask"]:
        logging.warning(
            "Invalid orderbook: bid %.4f >= ask %.4f",
            orderbook["best_bid"],
            orderbook["best_ask"],
        )
        return False

    # Check for valid depth
    if orderbook["total_notional_depth"] < 0:
        logging.warning(
            "Invalid orderbook: negative total_notional_depth: %.2f",
            orderbook["total_notional_depth"],
        )
        return False

    # Check bid/ask depths are non-negative
    if orderbook["bid_qty_depth"] < 0 or orderbook["ask_qty_depth"] < 0:
        logging.warning(
            "Invalid orderbook: negative qty depth: bid_qty_depth=%.2f, ask_qty_depth=%.2f",
            orderbook["bid_qty_depth"],
            orderbook["ask_qty_depth"],
        )
        return False
    if orderbook["bid_notional_depth"] < 0 or orderbook["ask_notional_depth"] < 0:
        logging.warning(
            "Invalid orderbook: negative notional depth: bid_notional_depth=%.2f, ask_notional_depth=%.2f",
            orderbook["bid_notional_depth"],
            orderbook["ask_notional_depth"],
        )
        return False

    logging.debug(
        "Orderbook validated successfully: bid=%.4f, ask=%.4f",
        orderbook["best_bid"],
        orderbook["best_ask"],
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
    return orderbook["best_ask"] - orderbook["best_bid"]


def calculate_spread_percent(orderbook: dict) -> float:
    """
    Calculate the spread as a percentage of mid price.

    Args:
        orderbook: Orderbook dictionary

    Returns:
        Spread percentage
    """
    spread = calculate_spread(orderbook)
    mid_price = (orderbook["best_bid"] + orderbook["best_ask"]) / 2.0
    if mid_price == 0:
        return 0.0
    return (spread / mid_price) * 100.0


def _resolve_fee(exchange_a: str, exchange_b: str) -> float:
    return (
        EXCHANGE_FEES.get(exchange_a.lower(), DEFAULT_FEE)
        + EXCHANGE_FEES.get(exchange_b.lower(), DEFAULT_FEE)
    )


def _normalize_kalshi_price(price: float) -> float:
    try:
        value = float(price)
    except (TypeError, ValueError):
        return 0.0
    if value > 1.0:
        value /= 100.0
    return max(0.0, min(1.0, value))


def _normalize_outcome(outcome: Optional[str]) -> Optional[str]:
    if not outcome:
        return None
    normalized = str(outcome).strip().lower()
    if normalized in {"yes", "no"}:
        return normalized
    return None


def _effective_price(exchange: str, price: float, outcome: Optional[str]) -> float:
    if exchange.lower() == "sx" and outcome == "no":
        return 1.0 - price
    return price


def _kalshi_cost_per_qty(price: float, side: str, contract_side: str = "yes") -> float:
    price = _normalize_kalshi_price(price)
    side = (side or "buy").lower()
    base = price if side == "buy" else (1.0 - price)
    return max(0.0, base) * KALSHI_CONTRACT_COLLATERAL


def _cost_per_qty(
    exchange: str, price: float, side: str, contract_side: str = "yes"
) -> float:
    if exchange.lower() == "kalshi":
        return _kalshi_cost_per_qty(price, side, contract_side=contract_side)
    return float(price)


def find_arbitrage_opportunity_generic(
    book_a: dict,
    book_b: dict,
    exchange_a: str,
    exchange_b: str,
    min_profit_bps: float = None,
    outcome_a: str | None = None,
    outcome_b: str | None = None,
    market_a: str | None = None,
    market_b: str | None = None,
) -> Optional[Dict]:
    """
    Find arbitrage opportunity between two orderbooks for any exchange pair.

    Strategy:
    - Buy on exchange with lower ask
    - Sell on exchange with higher bid
    - Profit = (higher_bid - lower_ask) - slippage - fees
    """
    if min_profit_bps is None:
        min_profit_bps = MIN_PROFIT_BPS
    outcome_a = _normalize_outcome(outcome_a)
    outcome_b = _normalize_outcome(outcome_b)

    logging.debug(
        "Finding arbitrage between %s and %s (min profit: %.2f bps)",
        exchange_a,
        exchange_b,
        min_profit_bps,
    )

    if not validate_orderbook(book_a):
        logging.warning("%s orderbook validation failed", exchange_a)
        return None
    if not validate_orderbook(book_b):
        logging.warning("%s orderbook validation failed", exchange_b)
        return None

    min_depth = min(book_a["total_notional_depth"], book_b["total_notional_depth"])
    max_slip = calculate_slippage(min_depth)

    scenario_1_profit = book_b["best_bid"] - book_a["best_ask"]
    scenario_2_profit = book_a["best_bid"] - book_b["best_ask"]

    fees = _resolve_fee(exchange_a, exchange_b)
    scenario_1_net = scenario_1_profit - max_slip - fees
    scenario_2_net = scenario_2_profit - max_slip - fees

    if scenario_1_net > scenario_2_net:
        profit = scenario_1_net
        buy_exchange = exchange_a.lower()
        sell_exchange = exchange_b.lower()
        buy_price = book_a["best_ask"]
        sell_price = book_b["best_bid"]
        buy_book = book_a
        sell_book = book_b
        buy_market = market_a
        sell_market = market_b
        buy_outcome = outcome_a
        sell_outcome = outcome_b
    else:
        profit = scenario_2_net
        buy_exchange = exchange_b.lower()
        sell_exchange = exchange_a.lower()
        buy_price = book_b["best_ask"]
        sell_price = book_a["best_bid"]
        buy_book = book_b
        sell_book = book_a
        buy_market = market_b
        sell_market = market_a
        buy_outcome = outcome_b
        sell_outcome = outcome_a

    buy_order_price = _effective_price(buy_exchange, buy_price, buy_outcome)
    sell_order_price = _effective_price(sell_exchange, sell_price, sell_outcome)
    buy_contract_side = (
        buy_outcome if buy_exchange == "kalshi" and buy_outcome else KALSHI_CONTRACT_SIDE
    )
    sell_contract_side = (
        sell_outcome
        if sell_exchange == "kalshi" and sell_outcome
        else KALSHI_CONTRACT_SIDE
    )

    profit_bps = profit * 10000
    if profit_bps < min_profit_bps:
        logging.debug(
            "No arbitrage: profit %.2f bps < min %.2f bps", profit_bps, min_profit_bps
        )
        return None

    max_qty = min(buy_book["ask_qty_depth"], sell_book["bid_qty_depth"])

    buy_cost_per_qty = _cost_per_qty(
        buy_exchange, buy_order_price, "buy", contract_side=buy_contract_side
    )
    sell_cost_per_qty = _cost_per_qty(
        sell_exchange, sell_order_price, "sell", contract_side=sell_contract_side
    )

    try:
        balance_manager = get_balance_manager()
        max_buy_balance = balance_manager.get_balance(buy_exchange)
        max_sell_balance = balance_manager.get_balance(sell_exchange)
        max_balance_qty = min(
            max_buy_balance / max(buy_cost_per_qty, 1e-9),
            max_sell_balance / max(sell_cost_per_qty, 1e-9),
        )

        max_qty_by_usd = min(
            MAX_POSITION_SIZE / max(buy_cost_per_qty, 1e-9),
            MAX_POSITION_SIZE / max(sell_cost_per_qty, 1e-9),
        )

        position_size = min(
            max_qty * MAX_POSITION_PERCENT, max_qty_by_usd, max_balance_qty
        )
    except InsufficientBalanceError as exc:
        logging.warning(
            "Balance manager unavailable or insufficient balance: %s, using default",
            exc,
        )
        max_qty_by_usd = min(
            MAX_POSITION_SIZE / max(buy_cost_per_qty, 1e-9),
            MAX_POSITION_SIZE / max(sell_cost_per_qty, 1e-9),
        )
        position_size = min(max_qty * MAX_POSITION_PERCENT, max_qty_by_usd)
    except Exception as exc:
        logging.warning(
            "Unexpected error getting balance: %s, using default limit",
            exc,
            exc_info=True,
        )
        max_qty_by_usd = min(
            MAX_POSITION_SIZE / max(buy_cost_per_qty, 1e-9),
            MAX_POSITION_SIZE / max(sell_cost_per_qty, 1e-9),
        )
        position_size = min(max_qty * MAX_POSITION_PERCENT, max_qty_by_usd)

    min_position_size = 0.01
    if "kalshi" in {buy_exchange, sell_exchange}:
        position_size = float(int(position_size))
        min_position_size = 1.0
    if position_size < min_position_size:
        logging.debug(
            "Position size too small: qty %.6f < %.2f, skipping arbitrage",
            position_size,
            min_position_size,
        )
        return None

    buy_notional = position_size * buy_cost_per_qty
    sell_notional = position_size * sell_cost_per_qty

    opportunity = {
        "buy_exchange": buy_exchange,
        "sell_exchange": sell_exchange,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "buy_outcome": buy_outcome,
        "sell_outcome": sell_outcome,
        "profit": profit,
        "profit_bps": profit_bps,
        "profit_percent": profit * 100,
        "slippage": max_slip,
        "fees": fees,
        "net_profit": profit,
        "position_size": position_size,
        "qty": position_size,
        "buy_notional": buy_notional,
        "sell_notional": sell_notional,
        "buy_cost_per_qty": buy_cost_per_qty,
        "sell_cost_per_qty": sell_cost_per_qty,
        "expected_pnl": profit * position_size,
    }
    if "kalshi" in {buy_exchange, sell_exchange}:
        kalshi_side = buy_outcome if buy_exchange == "kalshi" else sell_outcome
        opportunity["kalshi_side"] = kalshi_side or KALSHI_CONTRACT_SIDE

    g_edge.inc()

    buy_market_label = (
        f"{buy_market}:{buy_outcome}" if buy_market and buy_outcome else buy_market
    )
    sell_market_label = (
        f"{sell_market}:{sell_outcome}" if sell_market and sell_outcome else sell_market
    )

    record_opportunity(
        buy_exchange,
        sell_exchange,
        buy_price,
        sell_price,
        position_size,
        profit * position_size,
        profit_bps,
        profit * 100,
        buy_market=buy_market_label,
        sell_market=sell_market_label,
        buy_depth=buy_book["ask_notional_depth"],
        sell_depth=sell_book["bid_notional_depth"],
    )

    logging.info(
        "ARBITRAGE FOUND: Buy %s @ %.4f, Sell %s @ %.4f | "
        "Profit: %.2f bps (%.4f%%) | Qty: %.4f | Expected PnL: $%.2f",
        buy_exchange,
        buy_price,
        sell_exchange,
        sell_price,
        profit_bps,
        profit * 100,
        position_size,
        profit * position_size,
    )

    return opportunity


def find_arbitrage_opportunity(
    pm_book: dict,
    sx_book: dict,
    min_profit_bps: float = None,  # Minimum profit in basis points (from config if None)
    pm_market_id: str | None = None,
    sx_market_id: str | None = None,
    pm_outcome: str | None = None,
    sx_outcome: str | None = None,
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
    return find_arbitrage_opportunity_generic(
        pm_book,
        sx_book,
        "polymarket",
        "sx",
        min_profit_bps=min_profit_bps,
        outcome_a=pm_outcome,
        outcome_b=sx_outcome,
        market_a=pm_market_id,
        market_b=sx_market_id,
    )


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
    pm_market_id: str | None = None,
    sx_market_id: str | None = None,
) -> Optional[Dict]:
    """
    Process arbitrage between Polymarket and SX.

    This function finds arbitrage opportunities but does NOT execute them.
    Use execute_arbitrage_trade() from core.trader to actually place orders.

    Args:
        pm_book: Polymarket orderbook
        sx_book: SX orderbook
        pm_market_id: Polymarket market identifier
        sx_market_id: SX market identifier

    Returns:
        Arbitrage opportunity dict or None
    """
    opportunity = find_arbitrage_opportunity(
        pm_book, sx_book, pm_market_id=pm_market_id, sx_market_id=sx_market_id
    )

    return opportunity
