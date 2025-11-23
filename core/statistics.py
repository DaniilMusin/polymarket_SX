"""
Statistics collection module for tracking bot performance.

This module provides functionality to:
1. Log all arbitrage opportunities found
2. Track execution success/failure rates
3. Calculate actual PnL over time
4. Generate performance reports

Statistics are stored in CSV format for easy analysis.
"""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, asdict
import threading


@dataclass
class OpportunityStats:
    """Statistics for an arbitrage opportunity."""
    timestamp: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_bps: float
    expected_pnl: float
    position_size: float
    executed: bool = False
    actual_pnl: Optional[float] = None
    execution_error: Optional[str] = None


class StatisticsCollector:
    """
    Singleton class for collecting and storing arbitrage statistics.

    Usage:
        collector = get_statistics_collector()
        collector.log_opportunity(opportunity, executed=True, actual_pnl=5.23)
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.stats_dir = Path('logs/statistics')
            self.stats_dir.mkdir(parents=True, exist_ok=True)

            # CSV files for different stats
            self.opportunities_file = self.stats_dir / 'opportunities.csv'
            self.daily_summary_file = self.stats_dir / 'daily_summary.csv'

            # Initialize CSV files if they don't exist
            self._init_csv_files()
            self.initialized = True

    def _init_csv_files(self):
        """Initialize CSV files with headers if they don't exist."""
        # Opportunities log
        if not self.opportunities_file.exists():
            with open(self.opportunities_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'buy_exchange',
                    'sell_exchange',
                    'buy_price',
                    'sell_price',
                    'spread_bps',
                    'expected_pnl',
                    'position_size',
                    'executed',
                    'actual_pnl',
                    'execution_error',
                ])

        # Daily summary
        if not self.daily_summary_file.exists():
            with open(self.daily_summary_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'date',
                    'opportunities_found',
                    'opportunities_executed',
                    'execution_rate',
                    'total_expected_pnl',
                    'total_actual_pnl',
                    'avg_spread_bps',
                ])

    def log_opportunity(
        self,
        opportunity: Dict,
        executed: bool = False,
        actual_pnl: Optional[float] = None,
        execution_error: Optional[str] = None,
    ):
        """
        Log an arbitrage opportunity.

        Args:
            opportunity: Opportunity dict from processor
            executed: Whether the opportunity was executed
            actual_pnl: Actual profit/loss if executed
            execution_error: Error message if execution failed
        """
        try:
            stats = OpportunityStats(
                timestamp=datetime.now().isoformat(),
                buy_exchange=opportunity.get('buy_exchange', 'unknown'),
                sell_exchange=opportunity.get('sell_exchange', 'unknown'),
                buy_price=opportunity.get('buy_price', 0.0),
                sell_price=opportunity.get('sell_price', 0.0),
                spread_bps=opportunity.get('profit_bps', 0.0),
                expected_pnl=opportunity.get('expected_pnl', 0.0),
                position_size=opportunity.get('position_size', 0.0),
                executed=executed,
                actual_pnl=actual_pnl,
                execution_error=execution_error,
            )

            # Write to CSV
            with open(self.opportunities_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=asdict(stats).keys())
                writer.writerow(asdict(stats))

            # Log to logger
            if executed:
                if actual_pnl is not None:
                    logging.info(
                        "📊 Opportunity executed: %s->%s, spread=%.2f bps, "
                        "expected=$%.2f, actual=$%.2f",
                        stats.buy_exchange,
                        stats.sell_exchange,
                        stats.spread_bps,
                        stats.expected_pnl,
                        actual_pnl,
                    )
                else:
                    logging.warning(
                        "📊 Opportunity execution attempted but PnL unknown: %s->%s",
                        stats.buy_exchange,
                        stats.sell_exchange,
                    )
            else:
                logging.info(
                    "📊 Opportunity found (not executed): %s->%s, spread=%.2f bps, "
                    "expected=$%.2f",
                    stats.buy_exchange,
                    stats.sell_exchange,
                    stats.spread_bps,
                    stats.expected_pnl,
                )

        except Exception as exc:
            logging.error("Failed to log opportunity statistics: %s", exc, exc_info=True)

    def get_daily_stats(self, date: Optional[str] = None) -> Dict:
        """
        Get statistics for a specific date.

        Args:
            date: Date in YYYY-MM-DD format. If None, uses today.

        Returns:
            Dict with daily statistics
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        opportunities_found = 0
        opportunities_executed = 0
        total_expected_pnl = 0.0
        total_actual_pnl = 0.0
        spreads = []

        try:
            with open(self.opportunities_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['timestamp'].startswith(date):
                        opportunities_found += 1
                        total_expected_pnl += float(row.get('expected_pnl', 0))
                        spreads.append(float(row.get('spread_bps', 0)))

                        if row['executed'].lower() == 'true':
                            opportunities_executed += 1
                            if row['actual_pnl']:
                                total_actual_pnl += float(row['actual_pnl'])

        except FileNotFoundError:
            logging.warning("Statistics file not found: %s", self.opportunities_file)
        except Exception as exc:
            logging.error("Error reading statistics: %s", exc, exc_info=True)

        execution_rate = (
            (opportunities_executed / opportunities_found * 100)
            if opportunities_found > 0 else 0
        )
        avg_spread = sum(spreads) / len(spreads) if spreads else 0

        return {
            'date': date,
            'opportunities_found': opportunities_found,
            'opportunities_executed': opportunities_executed,
            'execution_rate': execution_rate,
            'total_expected_pnl': total_expected_pnl,
            'total_actual_pnl': total_actual_pnl,
            'avg_spread_bps': avg_spread,
        }

    def save_daily_summary(self, date: Optional[str] = None):
        """
        Save daily summary to CSV.

        Args:
            date: Date in YYYY-MM-DD format. If None, uses today.
        """
        stats = self.get_daily_stats(date)

        try:
            with open(self.daily_summary_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=stats.keys())
                writer.writerow(stats)

            logging.info(
                "📊 Daily summary saved: %d opportunities, %d executed (%.1f%%), "
                "expected=$%.2f, actual=$%.2f",
                stats['opportunities_found'],
                stats['opportunities_executed'],
                stats['execution_rate'],
                stats['total_expected_pnl'],
                stats['total_actual_pnl'],
            )

        except Exception as exc:
            logging.error("Failed to save daily summary: %s", exc, exc_info=True)


# Singleton accessor
_collector = None
_collector_lock = threading.Lock()


def get_statistics_collector() -> StatisticsCollector:
    """Get the global statistics collector instance."""
    global _collector
    if _collector is None:
        with _collector_lock:
            if _collector is None:
                _collector = StatisticsCollector()
    return _collector
