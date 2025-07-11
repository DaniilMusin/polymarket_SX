import asyncio
import logging
import aiohttp
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from typing import Any

from utils.retry import retry

API_CLOB = "https://polymarket.com/api"


class OrderbookError(Exception):
    """Raised when order book data cannot be retrieved or parsed."""


@retry()
async def orderbook_depth(
    session: ClientSession, market_id: str, depth: int = 20
) -> float:
    """Return total USDC quantity in top-N bid levels (Yes side)."""
    try:
        # Fix: Add explicit timeout instead of using default
        timeout = aiohttp.ClientTimeout(total=10.0, connect=5.0)
        async with session.get(
            f"{API_CLOB}/orderbook/{market_id}", timeout=timeout
        ) as r:
            if r.status != 200:
                logging.error("Polymarket API returned status %s", r.status)
                raise OrderbookError(f"status {r.status}")
            data: Any = await r.json()
    except asyncio.TimeoutError as exc:
        logging.error("Polymarket request timed out: %s", exc, exc_info=True)
        raise OrderbookError(f"request timeout: {exc}") from exc
    except ClientError as exc:
        logging.error("Polymarket request failed: %s", exc, exc_info=True)
        raise OrderbookError(f"request failed: {exc}") from exc

    try:
        bids = [float(lvl["quantity"]) for lvl in data["bids"]["Yes"][:depth]]
    except (KeyError, ValueError, TypeError) as exc:
        logging.error("Polymarket bad response format: %s", exc, exc_info=True)
        raise OrderbookError(f"bad response format: {exc}") from exc

    return sum(bids)
