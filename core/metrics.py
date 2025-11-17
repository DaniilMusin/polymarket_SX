"""Prometheus metrics helpers used across the project."""

from prometheus_client import start_http_server, Gauge, Counter
import threading

# Metrics
g_edge = Counter("arb_signal_total", "Signals (edge found)")
g_trades = Counter("arb_trades_total", "Executed trade pairs")
g_pnl = Gauge(
    "arb_cum_pnl_usd",
    "Cumulative PnL (USDC). This value is not automatically reset between runs.",
)

# Thread-safe PnL tracking
_pnl_total = 0.0
_pnl_lock = threading.Lock()


def init_metrics(port: int = 9090):
    """Start the Prometheus HTTP metrics server."""
    start_http_server(port)


def reset_pnl() -> None:
    """Reset the cumulative PnL gauge to zero."""
    global _pnl_total
    with _pnl_lock:
        _pnl_total = 0.0
        g_pnl.set(0.0)


def update_pnl(amount: float) -> None:
    """
    Update the cumulative PnL gauge in a thread-safe manner.

    Args:
        amount: Amount to add to PnL (can be positive or negative)
    """
    global _pnl_total
    with _pnl_lock:
        _pnl_total += amount
        g_pnl.set(_pnl_total)
