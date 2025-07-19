import asyncio
import logging
import aiohttp
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from typing import Any

from utils.retry import retry

API_REST = "https://api.sx.bet"


class SxError(Exception):
    """Raised when SX API responses are invalid."""


@retry()
async def orderbook_depth(
    session: ClientSession, market_id: str, depth: int = 20
) -> float:
    """Return total USDC quantity in top-N bid levels on SX."""
    try:
        # Fix: Add explicit timeout instead of using default
        timeout = aiohttp.ClientTimeout(total=10.0, connect=5.0)
        async with session.get(
            f"{API_REST}/orderbook/{market_id}", timeout=timeout
        ) as r:
            if r.status != 200:
                logging.error("SX API returned status %s", r.status)
                raise SxError(f"status {r.status}")
            data: Any = await r.json()
    except asyncio.TimeoutError as exc:
        logging.error("SX request timed out: %s", exc, exc_info=True)
        raise SxError(f"request timeout: {exc}") from exc
    except ClientError as exc:
        logging.error("SX request failed: %s", exc, exc_info=True)
        raise SxError(f"request failed: {exc}") from exc

    try:
        bids = [float(lvl["quantity"]) for lvl in data["bids"][:depth]]
        if not bids:
            logging.warning("SX returned empty bids list")
            return 0.0
    except (KeyError, ValueError, TypeError) as exc:
        logging.error("SX bad response format: %s", exc, exc_info=True)
        raise SxError(f"bad response format: {exc}") from exc

    return sum(bids)
