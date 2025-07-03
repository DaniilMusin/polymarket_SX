import asyncio
import logging
import aiohttp
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from typing import Any

API_REST = "https://api.sx.bet"


class SxError(Exception):
    """Raised when SX API responses are invalid."""


def retry(attempts: int = 3, delay: float = 1.0):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            for i in range(attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    logging.warning(
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
    """Return total USDC quantity in top-N bid levels on SX."""
    try:
        async with session.get(
            f"{API_REST}/orderbook/{market_id}", timeout=aiohttp.ClientTimeout()
        ) as r:
            if r.status != 200:
                raise SxError(f"status {r.status}")
            data: Any = await r.json()
    except ClientError as exc:
        raise SxError(f"request failed: {exc}") from exc

    try:
        bids = [float(lvl["quantity"]) for lvl in data["bids"][:depth]]
    except (KeyError, ValueError, TypeError) as exc:
        raise SxError(f"bad response format: {exc}") from exc

    return sum(bids)
