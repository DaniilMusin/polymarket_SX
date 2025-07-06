# Polymarket SX Arbitrage Bot

This project demonstrates a simple arbitrage strategy between SX and Polymarket.
It looks for price differences between **SX Network sportsbook markets** and the
**YES side** on Polymarket's CLOB. The repo includes fuzzy market matching,
Prometheus metrics on `/metrics`, Telegram error alerts and a basic CI workflow.

## Quick start

```bash
pip install -r requirements.txt
black --check .
flake8 .
mypy .
pytest -q
```

To build a container locally use:

```bash
docker build -t arb-bot .
```

Copy `.env.example` to `.env` and fill in the API and Telegram tokens before running.

## Logging

The bot uses Python's `logging` module. By default, INFO level messages
report processed order book depths while DEBUG level messages show
individual retry attempts. Errors such as failed requests or malformed
responses are logged at ERROR level and will trigger Telegram alerts when
a token and chat ID are configured.
