#!/usr/bin/env python3
"""
Real-time Log Monitor

Monitors bot logs in real-time and highlights critical patterns:
- Panic mode triggers
- Unhedged positions
- Repeated API errors
- Trade execution failures
- Balance issues

Usage:
    python scripts/monitor_logs.py [--follow] [--errors-only] [--critical-only]

Options:
    --follow        Follow logs in real-time (like tail -f)
    --errors-only   Show only ERROR and CRITICAL log levels
    --critical-only Show only CRITICAL issues (panic, unhedged, etc.)
    --send-alerts   Send Telegram/Discord alerts for critical issues
"""

import argparse
import re
import sys
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict, deque

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


# Critical patterns to detect
CRITICAL_PATTERNS = {
    'panic': re.compile(r'PANIC MODE|panic_reason|trigger_panic', re.IGNORECASE),
    'unhedged': re.compile(r'unhedged|UNHEDGED|handle_unhedged_leg', re.IGNORECASE),
    'failed_trade': re.compile(r'Trade execution failed|TradeExecutionError', re.IGNORECASE),
    'api_error': re.compile(r'API error|API returned status [45]\d\d', re.IGNORECASE),
    'insufficient_balance': re.compile(r'Insufficient balance|InsufficientBalanceError', re.IGNORECASE),
    'validation_error': re.compile(r'validation.*failed|EventValidationError', re.IGNORECASE),
}

# Log level patterns
LOG_LEVELS = {
    'CRITICAL': (re.compile(r'CRITICAL'), Colors.RED + Colors.BOLD),
    'ERROR': (re.compile(r'ERROR'), Colors.RED),
    'WARNING': (re.compile(r'WARNING|⚠'), Colors.YELLOW),
    'INFO': (re.compile(r'INFO'), Colors.GREEN),
    'DEBUG': (re.compile(r'DEBUG'), Colors.CYAN),
}


class LogMonitor:
    def __init__(self, log_dir='logs', critical_only=False, errors_only=False):
        self.log_dir = Path(log_dir)
        self.critical_only = critical_only
        self.errors_only = errors_only

        # Track error frequency for alerting
        self.error_counts = defaultdict(int)
        self.recent_errors = deque(maxlen=100)

    def colorize_line(self, line: str) -> str:
        """Add color to log line based on content."""
        # Check critical patterns first
        for pattern_name, pattern in CRITICAL_PATTERNS.items():
            if pattern.search(line):
                return f"{Colors.RED}{Colors.BOLD}🚨 {line}{Colors.END}"

        # Check log levels
        for level_name, (pattern, color) in LOG_LEVELS.items():
            if pattern.search(line):
                return f"{color}{line}{Colors.END}"

        return line

    def should_show_line(self, line: str) -> bool:
        """Determine if line should be displayed based on filters."""
        if self.critical_only:
            # Only show critical patterns
            return any(pattern.search(line) for pattern in CRITICAL_PATTERNS.values())

        if self.errors_only:
            # Show ERROR and CRITICAL only
            return any(pattern.search(line) for name, (pattern, _) in LOG_LEVELS.items()
                      if name in ['ERROR', 'CRITICAL'])

        return True

    def analyze_line(self, line: str) -> dict:
        """Analyze line for patterns and return analysis."""
        analysis = {
            'is_critical': False,
            'pattern': None,
            'level': 'INFO',
        }

        # Check critical patterns
        for pattern_name, pattern in CRITICAL_PATTERNS.items():
            if pattern.search(line):
                analysis['is_critical'] = True
                analysis['pattern'] = pattern_name
                self.error_counts[pattern_name] += 1
                self.recent_errors.append({
                    'time': datetime.now(),
                    'pattern': pattern_name,
                    'line': line.strip()
                })

        # Check log level
        for level_name, (pattern, _) in LOG_LEVELS.items():
            if pattern.search(line):
                analysis['level'] = level_name
                break

        return analysis

    def follow_logs(self, log_file: Path):
        """Follow log file in real-time (like tail -f)."""
        print(f"{Colors.BOLD}{Colors.BLUE}Following log file: {log_file}{Colors.END}")
        print(f"{Colors.YELLOW}Press Ctrl+C to stop{Colors.END}\n")

        try:
            with open(log_file, 'r') as f:
                # Go to end of file
                f.seek(0, 2)

                while True:
                    line = f.readline()
                    if line:
                        if self.should_show_line(line):
                            colored_line = self.colorize_line(line)
                            print(colored_line, end='')

                            # Analyze for alerts
                            analysis = self.analyze_line(line)
                            if analysis['is_critical']:
                                self.maybe_send_alert(analysis, line)
                    else:
                        time.sleep(0.1)

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Monitoring stopped{Colors.END}")
            self.print_summary()

    def read_logs(self, log_file: Path, tail_lines: int = None):
        """Read log file (optionally last N lines only)."""
        print(f"{Colors.BOLD}{Colors.BLUE}Reading log file: {log_file}{Colors.END}\n")

        with open(log_file, 'r') as f:
            lines = f.readlines()

            if tail_lines:
                lines = lines[-tail_lines:]

            for line in lines:
                if self.should_show_line(line):
                    colored_line = self.colorize_line(line)
                    print(colored_line, end='')

                    # Analyze
                    self.analyze_line(line)

        self.print_summary()

    def print_summary(self):
        """Print summary of detected issues."""
        if not self.error_counts:
            print(f"\n{Colors.GREEN}✓ No critical issues detected{Colors.END}")
            return

        print(f"\n{Colors.BOLD}{Colors.RED}{'=' * 80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.RED}CRITICAL ISSUES DETECTED{Colors.END}")
        print(f"{Colors.BOLD}{Colors.RED}{'=' * 80}{Colors.END}\n")

        for pattern_name, count in sorted(self.error_counts.items(), key=lambda x: -x[1]):
            print(f"  {Colors.RED}• {pattern_name.upper()}: {count} occurrences{Colors.END}")

        if self.recent_errors:
            print(f"\n{Colors.YELLOW}Recent critical events:{Colors.END}")
            for i, error in enumerate(list(self.recent_errors)[-5:], 1):
                time_str = error['time'].strftime('%H:%M:%S')
                print(f"  {i}. [{time_str}] {error['pattern']}: {error['line'][:80]}")

    def maybe_send_alert(self, analysis: dict, line: str):
        """Send alert for critical issues (if --send-alerts enabled)."""
        # This would integrate with core.alert_manager
        # For now, just highlight in console
        pass


def main():
    parser = argparse.ArgumentParser(description="Monitor bot logs in real-time")
    parser.add_argument(
        '--follow', '-f',
        action='store_true',
        help="Follow logs in real-time (like tail -f)"
    )
    parser.add_argument(
        '--errors-only', '-e',
        action='store_true',
        help="Show only ERROR and CRITICAL log levels"
    )
    parser.add_argument(
        '--critical-only', '-c',
        action='store_true',
        help="Show only critical issues (panic, unhedged, etc.)"
    )
    parser.add_argument(
        '--tail', '-n',
        type=int,
        metavar='N',
        help="Show last N lines (default: all)"
    )
    parser.add_argument(
        '--log-file',
        default='logs/bot.log',
        help="Log file to monitor (default: logs/bot.log)"
    )
    parser.add_argument(
        '--send-alerts',
        action='store_true',
        help="Send Telegram/Discord alerts for critical issues"
    )

    args = parser.parse_args()

    log_file = Path(args.log_file)

    if not log_file.exists():
        print(f"{Colors.RED}Error: Log file not found: {log_file}{Colors.END}")
        print(f"{Colors.YELLOW}Make sure the bot has been started at least once{Colors.END}")
        sys.exit(1)

    monitor = LogMonitor(
        log_dir=log_file.parent,
        critical_only=args.critical_only,
        errors_only=args.errors_only
    )

    print(f"{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                                                              ║")
    print("║              📊  REAL-TIME LOG MONITOR                       ║")
    print("║                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")

    if args.follow:
        monitor.follow_logs(log_file)
    else:
        monitor.read_logs(log_file, tail_lines=args.tail)


if __name__ == '__main__':
    main()
