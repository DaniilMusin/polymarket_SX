import asyncio
import logging
import os
import aiohttp
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from typing import Any

from utils.retry import retry
from config import KALSHI_API_URL, API_TIMEOUT_TOTAL, API_TIMEOUT_CONNECT

API_BASE = KALSHI_API_URL


class KalshiError(Exception):
    """Raised when Kalshi API responses are invalid."""


@retry()
async def orderbook_depth(
    session: ClientSession,
    market_id: str,
    depth: int = 20,
    outcome: str = "yes",
) -> dict:
    """
    Return orderbook with best bid/ask prices and total depth.

    outcome: 'yes' or 'no' (default: 'yes')

    Returns:
        {
            'best_bid': float,  # Best bid price (0-1 probability)
            'best_ask': float,  # Best ask price (0-1 probability)
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
        headers = {}
        api_key = os.getenv("KALSHI_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        params = {"depth": depth} if depth > 0 else {}
        async with session.get(
            f"{API_BASE}/markets/{market_id}/orderbook",
            params=params,
            headers=headers,
            timeout=timeout,
        ) as r:
            if r.status != 200:
                logging.error("Kalshi API returned status %s", r.status)
                raise KalshiError(f"status {r.status}")
            try:
                data: Any = await r.json()
            except aiohttp.ContentTypeError as exc:
                logging.error(
                    "Kalshi API returned invalid JSON: %s", exc, exc_info=True
                )
                raise KalshiError(f"invalid response format (not JSON): {exc}") from exc
    except asyncio.TimeoutError as exc:
        logging.error("Kalshi request timed out: %s", exc, exc_info=True)
        raise KalshiError(f"request timeout: {exc}") from exc
    except ClientError as exc:
        logging.error("Kalshi request failed: %s", exc, exc_info=True)
        raise KalshiError(f"request failed: {exc}") from exc

    try:
        # Kalshi returns orderbook with yes/no bids as [price_cents, quantity] pairs
        # Check required keys exist (bad JSON if missing)
        if "orderbook" not in data:
            raise KalshiError("bad response format: missing orderbook bids")

        orderbook = data["orderbook"]

        # Handle None value
        if orderbook is None:
            orderbook = {}

        # Check for yes/no keys
        if "yes" not in orderbook or "no" not in orderbook:
            raise KalshiError("bad response format: missing orderbook yes/no bids")

        yes_bids_raw = orderbook["yes"]
        no_bids_raw = orderbook["no"]

        # Handle None values
        if yes_bids_raw is None:
            yes_bids_raw = []
        if no_bids_raw is None:
            no_bids_raw = []

        yes_bids = yes_bids_raw[:depth] if yes_bids_raw else []
        no_bids = no_bids_raw[:depth] if no_bids_raw else []

        if not yes_bids or not no_bids:
            logging.warning("Kalshi returned empty yes or no bids list")
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

        outcome = (outcome or "yes").lower()
        if outcome not in {"yes", "no"}:
            raise KalshiError(f"invalid outcome: {outcome}")

        def _normalize(entries: list[list[Any]], invert: bool) -> list[dict]:
            normalized = []
            for price_cents, qty in entries:
                price = float(price_cents) / 100.0
                if invert:
                    price = 1.0 - price
                normalized.append({"price": price, "size": float(qty)})
            return normalized

        if outcome == "yes":
            bids = _normalize(yes_bids, invert=False)
            asks = _normalize(no_bids, invert=True)
        else:
            bids = _normalize(no_bids, invert=False)
            asks = _normalize(yes_bids, invert=True)

        # Best prices (convert from cents to probability)
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
    except (KeyError, ValueError, TypeError, IndexError) as exc:
        logging.error("Kalshi bad response format: %s", exc, exc_info=True)
        raise KalshiError(f"bad response format: {exc}") from exc
