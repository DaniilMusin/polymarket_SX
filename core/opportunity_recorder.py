"""Record arbitrage opportunities for offline analysis."""

from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config import LOG_DIR

DATA_DIR = Path(LOG_DIR) / "data"
OPPORTUNITY_FILE = DATA_DIR / "opportunities.csv"


def _ensure_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not OPPORTUNITY_FILE.exists():
        with OPPORTUNITY_FILE.open("w", newline="") as fp:
            writer = csv.writer(fp)
            writer.writerow(
                [
                    "timestamp",
                    "exchange_buy",
                    "market_buy",
                    "buy_price",
                    "buy_depth",
                    "exchange_sell",
                    "market_sell",
                    "sell_price",
                    "sell_depth",
                    "expected_profit_pct",
                    "expected_profit_usd",
                    "expected_profit_bps",
                    "volume",
                ]
            )


def record_opportunity(
    buy_exchange: str,
    sell_exchange: str,
    buy_price: float,
    sell_price: float,
    volume: float,
    expected_profit_usd: float,
    expected_profit_bps: float,
    profit_percent: float,
    buy_market: Optional[str] = None,
    sell_market: Optional[str] = None,
    buy_depth: Optional[float] = None,
    sell_depth: Optional[float] = None,
) -> None:
    """Append an arbitrage opportunity to CSV for later offline analysis."""
    try:
        _ensure_file()
        with OPPORTUNITY_FILE.open("a", newline="") as fp:
            writer = csv.writer(fp)
            writer.writerow(
                [
                    datetime.now(timezone.utc).isoformat(),
                    buy_exchange,
                    buy_market or "-",
                    f"{buy_price:.6f}",
                    f"{(buy_depth or 0):.4f}",
                    sell_exchange,
                    sell_market or "-",
                    f"{sell_price:.6f}",
                    f"{(sell_depth or 0):.4f}",
                    f"{profit_percent:.4f}",
                    f"{expected_profit_usd:.4f}",
                    f"{expected_profit_bps:.2f}",
                    f"{volume:.4f}",
                ]
            )
    except Exception:
        logging.exception("Failed to record arbitrage opportunity")
