import asyncio
import logging
import aiohttp
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from typing import Any

from utils.retry import retry

API_BASE = "https://api.elections.kalshi.com/trade-api/v2"


class KalshiError(Exception):
    """Raised when Kalshi API responses are invalid."""


@retry()
async def orderbook_depth(
    session: ClientSession, market_id: str, depth: int = 20
) -> float:
    """Return total USDC quantity in top-N bid levels (Yes side)."""
    try:
        # Fix: Add explicit timeout instead of using default
        timeout = aiohttp.ClientTimeout(total=10.0, connect=5.0)
        params = {"depth": depth} if depth > 0 else {}
        async with session.get(
            f"{API_BASE}/markets/{market_id}/orderbook",
            params=params,
            timeout=timeout,
        ) as r:
            if r.status != 200:
                logging.error("Kalshi API returned status %s", r.status)
                raise KalshiError(f"status {r.status}")
            data: Any = await r.json()
    except asyncio.TimeoutError as exc:
        logging.error("Kalshi request timed out: %s", exc, exc_info=True)
        raise KalshiError(f"request timeout: {exc}") from exc
    except ClientError as exc:
        logging.error("Kalshi request failed: %s", exc, exc_info=True)
        raise KalshiError(f"request failed: {exc}") from exc

    try:
        # Kalshi returns orderbook with yes/no bids as [price_cents, quantity] pairs
        # Validate response structure - this will raise KeyError if format is wrong
        orderbook = data["orderbook"]
        yes_bids = orderbook["yes"]

        if not yes_bids:
            logging.warning("Kalshi returned empty yes bids list")
            return 0.0

        # Extract quantities from top-N bids and convert from cents
        # Kalshi prices are in cents (0-100), quantities are in number of contracts
        # Each contract is worth $1, so quantity = USDC value
        bids = [float(bid[1]) for bid in yes_bids[:depth]]

        if not bids:
            logging.warning("Kalshi returned empty bids list after processing")
            return 0.0
    except (KeyError, ValueError, TypeError, IndexError) as exc:
        logging.error("Kalshi bad response format: %s", exc, exc_info=True)
        raise KalshiError(f"bad response format: {exc}") from exc

    return sum(bids)
