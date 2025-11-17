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
) -> dict:
    """
    Return orderbook with best bid/ask prices and total depth.

    Returns:
        {
            'best_bid': float,  # Best bid price
            'best_ask': float,  # Best ask price
            'bid_depth': float,  # Total USDC in bids
            'ask_depth': float,  # Total USDC in asks
            'total_depth': float,  # bid_depth + ask_depth
            'bids': list,  # Raw bid data
            'asks': list,  # Raw ask data
        }
    """
    try:
        # Use 30 second timeout to handle slow networks and busy exchanges
        timeout = aiohttp.ClientTimeout(total=30.0, connect=10.0)
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
        bids_data = data["bids"][:depth]
        asks_data = data["asks"][:depth]

        if not bids_data or not asks_data:
            logging.warning("SX returned empty bids or asks list")
            return {
                'best_bid': 0.0,
                'best_ask': 0.0,
                'bid_depth': 0.0,
                'ask_depth': 0.0,
                'total_depth': 0.0,
                'bids': [],
                'asks': [],
            }

        # Extract prices and quantities
        bid_quantities = [float(lvl["quantity"]) for lvl in bids_data]
        ask_quantities = [float(lvl["quantity"]) for lvl in asks_data]

        # Best bid/ask prices
        best_bid_price = float(bids_data[0]["price"])
        best_ask_price = float(asks_data[0]["price"])

        bid_depth = sum(bid_quantities)
        ask_depth = sum(ask_quantities)

        return {
            'best_bid': best_bid_price,
            'best_ask': best_ask_price,
            'bid_depth': bid_depth,
            'ask_depth': ask_depth,
            'total_depth': bid_depth + ask_depth,
            'bids': bids_data,
            'asks': asks_data,
        }
    except (KeyError, ValueError, TypeError) as exc:
        logging.error("SX bad response format: %s", exc, exc_info=True)
        raise SxError(f"bad response format: {exc}") from exc
