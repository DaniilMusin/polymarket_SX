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
        # Check required keys exist (bad JSON if missing)
        if "bids" not in data or "asks" not in data:
            raise OrderbookError(f"bad response format: missing bids or asks")

        # Safely extract bids and asks with None checks
        bids_data = data["bids"]
        asks_data = data["asks"]

        # Handle None values
        if bids_data is None:
            bids_data = {}
        if asks_data is None:
            asks_data = {}

        # Check for "Yes" key
        if "Yes" not in bids_data or "Yes" not in asks_data:
            raise OrderbookError(f"bad response format: missing bids['Yes'] or asks['Yes']")

        bids_yes = bids_data["Yes"]
        asks_yes = asks_data["Yes"]

        # Handle None values
        if bids_yes is None:
            bids_yes = []
        if asks_yes is None:
            asks_yes = []

        # Limit depth
        bids_yes = bids_yes[:depth] if bids_yes else []
        asks_yes = asks_yes[:depth] if asks_yes else []

        if not bids_yes or not asks_yes:
            logging.warning("Polymarket returned empty bids or asks list")
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
        bid_quantities = [float(lvl["quantity"]) for lvl in bids_yes]
        ask_quantities = [float(lvl["quantity"]) for lvl in asks_yes]

        # Best bid/ask prices (in Polymarket, price is probability 0-1)
        best_bid_price = float(bids_yes[0]["price"])
        best_ask_price = float(asks_yes[0]["price"])

        bid_depth = sum(bid_quantities)
        ask_depth = sum(ask_quantities)

        return {
            'best_bid': best_bid_price,
            'best_ask': best_ask_price,
            'bid_depth': bid_depth,
            'ask_depth': ask_depth,
            'total_depth': bid_depth + ask_depth,
            'bids': bids_yes,
            'asks': asks_yes,
        }
    except (KeyError, ValueError, TypeError) as exc:
        logging.error("Polymarket bad response format: %s", exc, exc_info=True)
        raise OrderbookError(f"bad response format: {exc}") from exc
