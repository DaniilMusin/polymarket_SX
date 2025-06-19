# Polymarket SX Arbitrage Bot

This project demonstrates a simple arbitrage strategy between SX and Polymarket.
It features fuzzy matching for markets, Prometheus metrics on `/metrics`,
Telegram error alerts and a basic CI workflow.

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
