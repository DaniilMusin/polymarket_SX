import asyncio
from aiohttp import ClientSession

API_CLOB = "https://polymarket.com/api"


def retry(attempts: int = 3, delay: float = 1.0):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            for i in range(attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception:
                    if i == attempts - 1:
                        raise
                    await asyncio.sleep(delay)
        return wrapper
    return decorator


@retry()
async def orderbook_depth(session: ClientSession, market_id: str, depth: int = 20) -> float:
    """Return total USDC quantity in top-N bid levels (Yes side)."""
    async with session.get(f"{API_CLOB}/orderbook/{market_id}") as r:
        ob = await r.json()
    bids = [float(lvl["quantity"]) for lvl in ob["bids"]["Yes"][:depth]]
    return sum(bids)
