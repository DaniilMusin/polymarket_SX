import asyncio
import logging
import aiohttp
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from typing import Any

from utils.retry import retry
from config import POLYMARKET_API_URL, API_TIMEOUT_TOTAL, API_TIMEOUT_CONNECT

API_CLOB = POLYMARKET_API_URL


class OrderbookError(Exception):
    """Raised when order book data cannot be retrieved or parsed."""


@retry()
async def orderbook_depth(
    session: ClientSession, token_id: str, depth: int = 20
) -> dict:
    """
    Return orderbook with best bid/ask prices and total depth.

    Polymarket CLOB uses token_id for orderbook queries.

    Returns:
        {
            'best_bid': float,  # Best bid price
            'best_ask': float,  # Best ask price
            'bid_depth': float,  # Total notional in bids (USD)
            'ask_depth': float,  # Total notional in asks (USD)
            'total_depth': float,  # bid_depth + ask_depth (USD)
            'bid_qty_depth': float,  # Total quantity in bids
            'ask_qty_depth': float,  # Total quantity in asks
            'total_qty_depth': float,  # bid_qty_depth + ask_qty_depth
            'bid_notional_depth': float,  # Total notional in bids (USD)
            'ask_notional_depth': float,  # Total notional in asks (USD)
            'total_notional_depth': float,  # Total notional depth (USD)
            'bids': list,  # Raw bid data
            'asks': list,  # Raw ask data
        }
    """
    try:
        # Use configurable timeout to handle slow networks and busy exchanges
        timeout = aiohttp.ClientTimeout(
            total=API_TIMEOUT_TOTAL, connect=API_TIMEOUT_CONNECT
        )
        endpoints = [
            (f"{API_CLOB}/book", {"token_id": token_id}),
            (f"{API_CLOB}/book/{token_id}", None),
            (f"{API_CLOB}/orderbook/{token_id}", None),
        ]
        data = None
        last_error: Exception | None = None
        for url, params in endpoints:
            async with session.get(url, params=params, timeout=timeout) as r:
                if r.status != 200:
                    logging.error(
                        "Polymarket API returned status %s for %s", r.status, url
                    )
                    last_error = OrderbookError(f"status {r.status}")
                    continue
                try:
                    data = await r.json()
                except aiohttp.ContentTypeError as exc:
                    logging.error(
                        "Polymarket API returned invalid JSON: %s",
                        exc,
                        exc_info=True,
                    )
                    last_error = OrderbookError(
                        f"invalid response format (not JSON): {exc}"
                    )
                    continue
                break

        if data is None:
            raise last_error or OrderbookError("failed to fetch orderbook")
    except asyncio.TimeoutError as exc:
        logging.error("Polymarket request timed out: %s", exc, exc_info=True)
        raise OrderbookError(f"request timeout: {exc}") from exc
    except ClientError as exc:
        logging.error("Polymarket request failed: %s", exc, exc_info=True)
        raise OrderbookError(f"request failed: {exc}") from exc

    def _normalize_levels(raw_levels: list[Any], side_name: str) -> list[dict]:
        normalized = []
        for entry in raw_levels:
            if isinstance(entry, dict):
                price = entry.get("price")
                size = entry.get("size", entry.get("quantity"))
            elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                price = entry[0]
                size = entry[1]
            else:
                raise OrderbookError(
                    f"bad response format: invalid {side_name} entry"
                )
            if price is None or size is None:
                raise OrderbookError(
                    f"bad response format: missing {side_name} price/size"
                )
            normalized.append({"price": float(price), "size": float(size)})
        return normalized

    try:
        raw_orderbook = data.get("orderbook", data)

        # Check required keys exist (bad JSON if missing)
        if "bids" not in raw_orderbook or "asks" not in raw_orderbook:
            raise OrderbookError("bad response format: missing bids or asks")

        # Safely extract bids and asks with None checks
        bids_data = raw_orderbook.get("bids")
        asks_data = raw_orderbook.get("asks")

        # Handle None values
        if bids_data is None:
            bids_data = []
        if asks_data is None:
            asks_data = []

        def _unwrap_outcome_levels(levels: Any) -> Any:
            if not isinstance(levels, dict):
                return levels
            for key in ("Yes", "yes", "YES", "No", "no", "NO"):
                candidate = levels.get(key)
                if isinstance(candidate, list) and candidate:
                    return candidate
            for key in ("Yes", "yes", "YES", "No", "no", "NO"):
                if key in levels:
                    return levels.get(key)
            return levels

        # Some APIs wrap outcomes in a dict, e.g. bids["Yes"] or bids["No"]
        bids_data = _unwrap_outcome_levels(bids_data)
        asks_data = _unwrap_outcome_levels(asks_data)

        if bids_data is None:
            bids_data = []
        if asks_data is None:
            asks_data = []

        if not isinstance(bids_data, list) or not isinstance(asks_data, list):
            raise OrderbookError("bad response format: bids/asks must be lists")

        # Limit depth
        bids_raw = bids_data[:depth] if bids_data else []
        asks_raw = asks_data[:depth] if asks_data else []

        if not bids_raw or not asks_raw:
            logging.warning("Polymarket returned empty bids or asks list")
            return {
                "best_bid": 0.0,
                "best_ask": 0.0,
                "bid_depth": 0.0,
                "ask_depth": 0.0,
                "total_depth": 0.0,
                "bid_qty_depth": 0.0,
                "ask_qty_depth": 0.0,
                "total_qty_depth": 0.0,
                "bid_notional_depth": 0.0,
                "ask_notional_depth": 0.0,
                "total_notional_depth": 0.0,
                "bids": [],
                "asks": [],
            }

        # Normalize to {price, size} entries
        bids = _normalize_levels(bids_raw, "bid")
        asks = _normalize_levels(asks_raw, "ask")

        # Best bid/ask prices (in Polymarket, price is probability 0-1)
        best_bid_price = float(bids[0]["price"])
        best_ask_price = float(asks[0]["price"])

        bid_qty_depth = sum(level["size"] for level in bids)
        ask_qty_depth = sum(level["size"] for level in asks)
        bid_notional_depth = sum(level["size"] * level["price"] for level in bids)
        ask_notional_depth = sum(level["size"] * level["price"] for level in asks)

        return {
            "best_bid": best_bid_price,
            "best_ask": best_ask_price,
            "bid_depth": bid_notional_depth,
            "ask_depth": ask_notional_depth,
            "total_depth": bid_notional_depth + ask_notional_depth,
            "bid_qty_depth": bid_qty_depth,
            "ask_qty_depth": ask_qty_depth,
            "total_qty_depth": bid_qty_depth + ask_qty_depth,
            "bid_notional_depth": bid_notional_depth,
            "ask_notional_depth": ask_notional_depth,
            "total_notional_depth": bid_notional_depth + ask_notional_depth,
            "bids": bids,
            "asks": asks,
        }
    except (AttributeError, KeyError, ValueError, TypeError) as exc:
        logging.error("Polymarket bad response format: %s", exc, exc_info=True)
        raise OrderbookError(f"bad response format: {exc}") from exc
