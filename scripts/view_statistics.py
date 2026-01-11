#!/usr/bin/env python3
"""
Скрипт для просмотра статистики бота.

Показывает:
1. Сколько арбитражных возможностей найдено
2. Сколько реально исполнено
3. Процент успеха
4. Фактический vs ожидаемый PnL

Usage:
    python scripts/view_statistics.py [--days 7] [--detailed]
"""

import argparse
import csv
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def read_opportunities(stats_file: Path, days: int = 7):
    """Read opportunities from CSV file."""
    if not stats_file.exists():
        print(f"{Colors.RED}No statistics file found: {stats_file}{Colors.END}")
        print(f"{Colors.YELLOW}Run the bot first to collect statistics.{Colors.END}")
        return []

    cutoff_date = datetime.now() - timedelta(days=days)
    opportunities = []

    with open(stats_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            timestamp = datetime.fromisoformat(row['timestamp'])
            if timestamp >= cutoff_date:
                opportunities.append({
                    'timestamp': timestamp,
                    'buy_exchange': row['buy_exchange'],
                    'sell_exchange': row['sell_exchange'],
                    'buy_price': float(row['buy_price']),
                    'sell_price': float(row['sell_price']),
                    'spread_bps': float(row['spread_bps']),
                    'expected_pnl': float(row['expected_pnl']),
                    'position_size': float(row['position_size']),
                    'executed': row['executed'].lower() == 'true',
                    'actual_pnl': float(row['actual_pnl']) if row['actual_pnl'] else None,
                    'execution_error': row.get('execution_error'),
                })

    return opportunities


def print_summary(opportunities, days):
    """Print summary statistics."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}STATISTICS SUMMARY (Last {days} days){Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}\n")

    if not opportunities:
        print(f"{Colors.YELLOW}No data available for the last {days} days.{Colors.END}\n")
        return

    total = len(opportunities)
    executed = sum(1 for o in opportunities if o['executed'])
    execution_rate = (executed / total * 100) if total > 0 else 0

    total_expected_pnl = sum(o['expected_pnl'] for o in opportunities)
    total_actual_pnl = sum(o['actual_pnl'] for o in opportunities if o['actual_pnl'] is not None)

    avg_spread = sum(o['spread_bps'] for o in opportunities) / total if total > 0 else 0

    # Overall stats
    print(f"{Colors.BOLD}Overall Statistics:{Colors.END}")
    print(f"  Opportunities found:   {Colors.YELLOW}{total}{Colors.END}")
    print(f"  Opportunities executed: {Colors.GREEN}{executed}{Colors.END} ({execution_rate:.1f}%)")
    print(f"  Avg spread:            {avg_spread:.2f} bps")
    print(f"  Total expected PnL:    ${total_expected_pnl:.2f}")
    print(f"  Total actual PnL:      {Colors.GREEN if total_actual_pnl >= 0 else Colors.RED}${total_actual_pnl:.2f}{Colors.END}")

    if executed > 0 and total_actual_pnl != 0:
        pnl_ratio = (total_actual_pnl / total_expected_pnl * 100) if total_expected_pnl != 0 else 0
        print(f"  Actual vs Expected:    {pnl_ratio:.1f}%")

    # Exchange breakdown
    print(f"\n{Colors.BOLD}By Exchange Pair:{Colors.END}")
    pair_stats = defaultdict(lambda: {'count': 0, 'executed': 0, 'total_pnl': 0, 'spreads': []})

    for opp in opportunities:
        pair = f"{opp['buy_exchange']} → {opp['sell_exchange']}"
        pair_stats[pair]['count'] += 1
        pair_stats[pair]['spreads'].append(opp['spread_bps'])
        if opp['executed']:
            pair_stats[pair]['executed'] += 1
            if opp['actual_pnl'] is not None:
                pair_stats[pair]['total_pnl'] += opp['actual_pnl']

    for pair, stats in sorted(pair_stats.items(), key=lambda x: x[1]['count'], reverse=True):
        avg_spread_pair = sum(stats['spreads']) / len(stats['spreads'])
        exec_rate = (stats['executed'] / stats['count'] * 100) if stats['count'] > 0 else 0
        print(f"\n  {Colors.BLUE}{pair}{Colors.END}")
        print(f"    Found: {stats['count']}, Executed: {stats['executed']} ({exec_rate:.1f}%)")
        print(f"    Avg spread: {avg_spread_pair:.2f} bps, PnL: ${stats['total_pnl']:.2f}")

    # Daily breakdown
    print(f"\n{Colors.BOLD}Daily Breakdown:{Colors.END}")
    daily_stats = defaultdict(lambda: {
        'count': 0, 'executed': 0, 'expected_pnl': 0, 'actual_pnl': 0
    })

    for opp in opportunities:
        date = opp['timestamp'].strftime('%Y-%m-%d')
        daily_stats[date]['count'] += 1
        daily_stats[date]['expected_pnl'] += opp['expected_pnl']
        if opp['executed']:
            daily_stats[date]['executed'] += 1
            if opp['actual_pnl'] is not None:
                daily_stats[date]['actual_pnl'] += opp['actual_pnl']

    for date in sorted(daily_stats.keys(), reverse=True):
        stats = daily_stats[date]
        exec_rate = (stats['executed'] / stats['count'] * 100) if stats['count'] > 0 else 0
        print(f"\n  {Colors.YELLOW}{date}{Colors.END}")
        print(f"    Found: {stats['count']}, Executed: {stats['executed']} ({exec_rate:.1f}%)")
        print(f"    Expected: ${stats['expected_pnl']:.2f}, Actual: ${stats['actual_pnl']:.2f}")


def print_detailed(opportunities):
    """Print detailed list of opportunities."""
    print(f"\n{Colors.BOLD}DETAILED OPPORTUNITIES:{Colors.END}\n")

    for i, opp in enumerate(sorted(opportunities, key=lambda x: x['timestamp'], reverse=True), 1):
        status = f"{Colors.GREEN}✓ EXECUTED{Colors.END}" if opp['executed'] else f"{Colors.YELLOW}○ FOUND{Colors.END}"
        print(f"{i}. {opp['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - {status}")
        print(f"   {opp['buy_exchange']} @ {opp['buy_price']:.4f} → {opp['sell_exchange']} @ {opp['sell_price']:.4f}")
        print(f"   Spread: {opp['spread_bps']:.2f} bps, Qty: {opp['position_size']:.2f}")
        print(f"   Expected PnL: ${opp['expected_pnl']:.2f}", end='')

        if opp['actual_pnl'] is not None:
            pnl_color = Colors.GREEN if opp['actual_pnl'] >= 0 else Colors.RED
            print(f", Actual: {pnl_color}${opp['actual_pnl']:.2f}{Colors.END}")
        else:
            print()

        if opp['execution_error']:
            print(f"   {Colors.RED}Error: {opp['execution_error']}{Colors.END}")
        print()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='View bot statistics')
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to analyze (default: 7)'
    )
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed list of opportunities'
    )
    args = parser.parse_args()

    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                      ║")
    print("║                  📊 BOT STATISTICS VIEWER                           ║")
    print("║                                                                      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")

    stats_file = Path('logs/statistics/opportunities.csv')
    opportunities = read_opportunities(stats_file, args.days)

    print_summary(opportunities, args.days)

    if args.detailed and opportunities:
        print_detailed(opportunities)

    print()


if __name__ == '__main__':
    main()
