"""Prometheus metrics helpers used across the project."""

from prometheus_client import start_http_server, Gauge, Counter

# Metrics
g_edge = Counter("arb_signal_total", "Signals (edge found)")
g_trades = Counter("arb_trades_total", "Executed trade pairs")
g_pnl = Gauge(
    "arb_cum_pnl_usd",
    "Cumulative PnL (USDC). This value is not automatically reset between runs.",
)


def init_metrics(port: int = 9090):
    """Start the Prometheus HTTP metrics server."""
    start_http_server(port)


def reset_pnl() -> None:
    """Reset the cumulative PnL gauge to zero."""
    g_pnl.set(0.0)
