"""Offline analysis of recorded arbitrage opportunities."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from statistics import mean

from config import LOG_DIR

DATA_FILE = Path(LOG_DIR) / "data" / "opportunities.csv"


def main() -> None:
    if not DATA_FILE.exists():
        print("No opportunity data found at", DATA_FILE)
        return

    with DATA_FILE.open() as fp:
        reader = csv.DictReader(fp)
        rows = list(reader)

    if not rows:
        print("No records to analyze")
        return

    profits = [float(r["expected_profit_usd"]) for r in rows]
    profit_bps = [float(r["expected_profit_bps"]) for r in rows]
    volumes = [float(r["volume"]) for r in rows]

    exchange_pairs = Counter(f"{r['exchange_buy']}->{r['exchange_sell']}" for r in rows)

    print(f"Records: {len(rows)}")
    print(f"Avg expected PnL: ${mean(profits):.4f}")
    print(f"Avg profit (bps): {mean(profit_bps):.2f}")
    print(f"Avg volume: ${mean(volumes):.4f}")
    print("Most common routes:")
    for route, count in exchange_pairs.most_common():
        print(f"  {route}: {count}")


if __name__ == "__main__":
    main()
