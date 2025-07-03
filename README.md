# Polymarket SX Arbitrage Bot

This project demonstrates a simple arbitrage strategy between SX and Polymarket.
It looks for price differences between **SX Network sportsbook markets** and the
**YES side** on Polymarket's CLOB. The repo includes fuzzy market matching,
Prometheus metrics on `/metrics`, Telegram error alerts and a basic CI workflow.

## Quick start

```bash
pip install -r requirements.txt
flake8 .
pytest -q
```

To build a container locally use:

```bash
docker build -t arb-bot .
```

Copy `.env.example` to `.env` and fill in the API and Telegram tokens before running.

## Logging

The bot logs operational information at the `INFO` level. Retry attempts are
logged at `DEBUG` and can be enabled with a verbose log level. Errors that
prevent depth retrieval are logged at `ERROR` and forwarded to the configured
Telegram chat via `TelegramHandler`.
