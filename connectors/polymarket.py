import asyncio
import logging
import aiohttp
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from typing import Any

API_CLOB = "https://polymarket.com/api"


class OrderbookError(Exception):
    """Raised when order book data cannot be retrieved or parsed."""


def retry(attempts: int = 3, delay: float = 1.0):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            for i in range(attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    logging.debug(
                        "Attempt %s/%s failed: %s", i + 1, attempts, exc, exc_info=True
                    )
                    if i == attempts - 1:
                        raise
                    await asyncio.sleep(delay)

        return wrapper

    return decorator


@retry()
async def orderbook_depth(
    session: ClientSession, market_id: str, depth: int = 20
) -> float:
    """Return total USDC quantity in top-N bid levels (Yes side)."""
    try:
        async with session.get(
            f"{API_CLOB}/orderbook/{market_id}", timeout=aiohttp.ClientTimeout()
        ) as r:
            if r.status != 200:
                logging.error("Polymarket orderbook status %s", r.status)
                raise OrderbookError(f"status {r.status}")
            data: Any = await r.json()
    except ClientError as exc:
        logging.error("Polymarket request failed", exc_info=True)
        raise OrderbookError("request failed") from exc

    try:
        bids = [float(lvl["quantity"]) for lvl in data["bids"]["Yes"][:depth]]
    except (KeyError, ValueError, TypeError) as exc:
        logging.error("Polymarket bad response", exc_info=True)
        raise OrderbookError("bad response format") from exc

    return sum(bids)
