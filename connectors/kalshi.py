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
) -> dict:
    """
    Return orderbook with best bid/ask prices and total depth.

    Returns:
        {
            'best_bid': float,  # Best bid price (0-1 probability)
            'best_ask': float,  # Best ask price (0-1 probability)
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
        orderbook = data["orderbook"]
        yes_bids = orderbook["yes"][:depth] if orderbook.get("yes") else []
        no_bids = orderbook["no"][:depth] if orderbook.get("no") else []

        if not yes_bids or not no_bids:
            logging.warning("Kalshi returned empty yes or no bids list")
            return {
                'best_bid': 0.0,
                'best_ask': 0.0,
                'bid_depth': 0.0,
                'ask_depth': 0.0,
                'total_depth': 0.0,
                'bids': [],
                'asks': [],
            }

        # Kalshi prices are in cents (0-100), convert to probability (0-1)
        # yes_bids are buy orders for YES (our bids)
        # no_bids are buy orders for NO (inverse of asks for YES)

        # Extract quantities and prices
        bid_quantities = [float(bid[1]) for bid in yes_bids]

        # For asks, we use NO bids and convert: ask_price = 1 - no_bid_price
        ask_quantities = [float(bid[1]) for bid in no_bids]

        # Best prices (convert from cents to probability)
        best_bid_price = float(yes_bids[0][0]) / 100.0
        best_ask_price = 1.0 - (float(no_bids[0][0]) / 100.0)

        bid_depth = sum(bid_quantities)
        ask_depth = sum(ask_quantities)

        return {
            'best_bid': best_bid_price,
            'best_ask': best_ask_price,
            'bid_depth': bid_depth,
            'ask_depth': ask_depth,
            'total_depth': bid_depth + ask_depth,
            'bids': yes_bids,
            'asks': no_bids,
        }
    except (KeyError, ValueError, TypeError, IndexError) as exc:
        logging.error("Kalshi bad response format: %s", exc, exc_info=True)
        raise KalshiError(f"bad response format: {exc}") from exc
