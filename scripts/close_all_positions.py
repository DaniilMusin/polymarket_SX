"""Utility script to unwind all tracked positions across exchanges."""

import asyncio
import logging

from core.logging_config import setup_logging
from core.exchange_balances import get_balance_manager
from core.risk import get_risk_manager
from core.alert_manager import send_info_alert


async def close_positions() -> None:
    setup_logging()
    logging.info("Starting forced position close procedure")

    balance_manager = get_balance_manager()
    risk_manager = get_risk_manager()

    balances = balance_manager.get_all_balances()
    for exchange, info in balances.items():
        logging.info(
            "Resetting virtual exposure on %s (available=$%.2f locked=$%.2f)",
            exchange,
            info.get("available", 0.0),
            info.get("locked", 0.0),
        )

    balance_manager.reset_balances()
    risk_manager.trigger_panic("Manual close_all_positions invoked")

    await send_info_alert(
        "Positions closed",
        "Все позиции сброшены (виртуальные балансы обнулены).",
    )

    logging.info("Close-all routine finished")


def main() -> None:
    asyncio.run(close_positions())


if __name__ == "__main__":
    main()
