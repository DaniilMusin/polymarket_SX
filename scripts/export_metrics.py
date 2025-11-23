#!/usr/bin/env python3
"""
Metrics Export Script

Exports current bot metrics to JSON/CSV for offline analysis.

Exports:
- Prometheus metrics (trades, PnL, opportunities)
- Balance state (available, locked, used)
- Risk state (exposure, open arbitrages)
- Recent statistics from CSV

Usage:
    python scripts/export_metrics.py [--format json|csv] [--output FILE]

Examples:
    # Export to JSON
    python scripts/export_metrics.py --format json --output metrics.json

    # Export to CSV
    python scripts/export_metrics.py --format csv --output metrics.csv

    # Print to stdout (default)
    python scripts/export_metrics.py
"""

import argparse
import json
import csv
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from core.risk import get_risk_manager
from core.exchange_balances import get_balance_manager
from core.metrics import (
    g_trades,
    g_edge,
    g_pnl,
    g_balance_pm,
    g_balance_sx,
    g_balance_kalshi
)


class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class MetricsExporter:
    def __init__(self):
        self.risk_manager = get_risk_manager()
        self.balance_manager = get_balance_manager()

    def collect_metrics(self) -> dict:
        """Collect all metrics into a dictionary."""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'prometheus': self._collect_prometheus_metrics(),
            'balances': self._collect_balance_metrics(),
            'risk': self._collect_risk_metrics(),
            'statistics': self._collect_statistics(),
        }
        return metrics

    def _collect_prometheus_metrics(self) -> dict:
        """Collect Prometheus metrics."""
        # Access internal counter values
        # Note: prometheus_client doesn't expose easy access to values,
        # so we track them ourselves or use collect() method

        return {
            'total_trades': self._get_counter_value(g_trades),
            'arbitrage_opportunities': self._get_counter_value(g_edge),
            'total_pnl': self._get_gauge_value(g_pnl),
            'balance_polymarket': self._get_gauge_value(g_balance_pm),
            'balance_sx': self._get_gauge_value(g_balance_sx),
            'balance_kalshi': self._get_gauge_value(g_balance_kalshi),
        }

    def _get_counter_value(self, counter) -> float:
        """Get value from Prometheus Counter."""
        try:
            # Try to collect metric value
            samples = list(counter.collect())[0].samples
            if samples:
                return samples[0].value
        except Exception:
            pass
        return 0.0

    def _get_gauge_value(self, gauge) -> float:
        """Get value from Prometheus Gauge."""
        try:
            samples = list(gauge.collect())[0].samples
            if samples:
                return samples[0].value
        except Exception:
            pass
        return 0.0

    def _collect_balance_metrics(self) -> dict:
        """Collect balance state from balance manager."""
        all_balances = self.balance_manager.get_all_balances()

        result = {}
        for exchange, balances in all_balances.items():
            result[exchange] = {
                'initial': balances['initial'],
                'available': balances['available'],
                'locked': balances['locked'],
                'total': balances['total'],
                'used': balances['initial'] - balances['total'],
                'used_percent': (balances['initial'] - balances['total']) / balances['initial'] * 100
                    if balances['initial'] > 0 else 0,
            }

        return result

    def _collect_risk_metrics(self) -> dict:
        """Collect risk state from risk manager."""
        return {
            'open_arbitrages': self.risk_manager._open_arbs,
            'panic_mode': self.risk_manager.is_panic(),
            'panic_reason': self.risk_manager._panic_reason,
            'exchange_exposure': dict(self.risk_manager._exchange_exposure),
            'market_exposure': dict(self.risk_manager._market_exposure),
        }

    def _collect_statistics(self) -> dict:
        """Collect recent statistics from CSV file."""
        stats_file = Path('data/opportunities.csv')

        if not stats_file.exists():
            return {
                'file_exists': False,
                'total_opportunities': 0,
                'recent_opportunities': [],
            }

        # Read last 10 opportunities
        try:
            with open(stats_file, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            return {
                'file_exists': True,
                'total_opportunities': len(rows),
                'recent_opportunities': rows[-10:] if rows else [],
            }
        except Exception as e:
            return {
                'file_exists': True,
                'error': str(e),
            }

    def export_json(self, metrics: dict, output_file: str = None):
        """Export metrics to JSON."""
        json_str = json.dumps(metrics, indent=2, default=str)

        if output_file:
            with open(output_file, 'w') as f:
                f.write(json_str)
            print(f"{Colors.GREEN}✓ Metrics exported to {output_file}{Colors.END}")
        else:
            print(json_str)

    def export_csv(self, metrics: dict, output_file: str = None):
        """Export metrics to CSV (flattened)."""
        # Flatten nested dict for CSV
        rows = []

        # Prometheus metrics
        for key, value in metrics['prometheus'].items():
            rows.append({'category': 'prometheus', 'metric': key, 'value': value})

        # Balance metrics
        for exchange, balances in metrics['balances'].items():
            for key, value in balances.items():
                rows.append({'category': f'balance_{exchange}', 'metric': key, 'value': value})

        # Risk metrics
        for key, value in metrics['risk'].items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    rows.append({'category': f'risk_{key}', 'metric': sub_key, 'value': sub_value})
            else:
                rows.append({'category': 'risk', 'metric': key, 'value': value})

        # Write CSV
        if output_file:
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['category', 'metric', 'value'])
                writer.writeheader()
                writer.writerows(rows)
            print(f"{Colors.GREEN}✓ Metrics exported to {output_file}{Colors.END}")
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=['category', 'metric', 'value'])
            writer.writeheader()
            writer.writerows(rows)

    def print_summary(self, metrics: dict):
        """Print human-readable summary."""
        print(f"{Colors.BOLD}{Colors.BLUE}")
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║                                                              ║")
        print("║              📊  METRICS EXPORT                              ║")
        print("║                                                              ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print(f"{Colors.END}\n")

        print(f"Export Time: {metrics['timestamp']}\n")

        # Prometheus
        print(f"{Colors.BOLD}Prometheus Metrics:{Colors.END}")
        prom = metrics['prometheus']
        print(f"  Total Trades: {prom['total_trades']}")
        print(f"  Opportunities Found: {prom['arbitrage_opportunities']}")
        print(f"  Total PnL: ${prom['total_pnl']:.2f}")

        # Balances
        print(f"\n{Colors.BOLD}Balances:{Colors.END}")
        for exchange, balances in metrics['balances'].items():
            print(f"  {exchange.upper()}:")
            print(f"    Available: ${balances['available']:.2f}")
            print(f"    Locked:    ${balances['locked']:.2f}")
            print(f"    Used:      ${balances['used']:.2f} ({balances['used_percent']:.1f}%)")

        # Risk
        print(f"\n{Colors.BOLD}Risk State:{Colors.END}")
        risk = metrics['risk']
        print(f"  Open Arbitrages: {risk['open_arbitrages']}")
        print(f"  Panic Mode: {risk['panic_mode']}")
        if risk['panic_mode']:
            print(f"    Reason: {risk['panic_reason']}")

        # Stats
        print(f"\n{Colors.BOLD}Statistics:{Colors.END}")
        stats = metrics['statistics']
        if stats.get('file_exists'):
            print(f"  Total Opportunities Recorded: {stats['total_opportunities']}")
        else:
            print(f"  {Colors.YELLOW}No statistics file found{Colors.END}")

        print()


def main():
    parser = argparse.ArgumentParser(description="Export bot metrics")
    parser.add_argument(
        '--format',
        choices=['json', 'csv', 'summary'],
        default='summary',
        help="Export format (default: summary)"
    )
    parser.add_argument(
        '--output', '-o',
        metavar='FILE',
        help="Output file (default: stdout)"
    )

    args = parser.parse_args()

    exporter = MetricsExporter()
    metrics = exporter.collect_metrics()

    if args.format == 'json':
        exporter.export_json(metrics, args.output)
    elif args.format == 'csv':
        exporter.export_csv(metrics, args.output)
    else:  # summary
        exporter.print_summary(metrics)

        if args.output:
            # Save full metrics to file as JSON
            exporter.export_json(metrics, args.output)


if __name__ == '__main__':
    main()
