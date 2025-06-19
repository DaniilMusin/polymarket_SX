from prometheus_client import start_http_server, Gauge

g_edge = Gauge("arb_signal_total", "Signals (edge found)")
g_trades = Gauge("arb_trades_total", "Executed trade pairs")
g_pnl = Gauge("arb_cum_pnl_usd", "Cumulative PnL (USDC)")


def init_metrics(port: int = 9090):
    start_http_server(port)
