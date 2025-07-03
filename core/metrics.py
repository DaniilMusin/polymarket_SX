"""Prometheus metrics for the arbitrage bot."""

from prometheus_client import start_http_server, Gauge

g_edge = Gauge("arb_signal_total", "Signals (edge found)")
g_trades = Gauge("arb_trades_total", "Executed trade pairs")
g_pnl = Gauge(
    "arb_cum_pnl_usd",
    "Cumulative PnL (USDC). Call :func:`reset_pnl` to reset this value.",
)


def init_metrics(port: int = 9090):
    """Expose metrics on the given HTTP ``port``."""
    start_http_server(port)


def reset_pnl() -> None:
    """Reset the cumulative PnL gauge to ``0.0``."""
    g_pnl.set(0.0)
