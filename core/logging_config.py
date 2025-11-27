"""Centralized logging configuration with rotation and dedicated loggers."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from config import LOG_DIR, LOG_MAX_BYTES, LOG_BACKUP_COUNT


BOT_LOG_FILE = Path(LOG_DIR) / "bot.log"
TRADE_LOG_FILE = Path(LOG_DIR) / "trades.log"
ERROR_LOG_FILE = Path(LOG_DIR) / "errors.log"
ALERT_LOG_FILE = Path(LOG_DIR) / "alerts.log"


class _Formatter(logging.Formatter):
    def format(
        self, record: logging.LogRecord
    ) -> str:  # pragma: no cover - thin wrapper
        if not hasattr(record, "exchange"):
            record.exchange = "-"
        if not hasattr(record, "market"):
            record.market = "-"
        return super().format(record)


def _build_handler(path: Path, level: int) -> RotatingFileHandler:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT
    )
    handler.setLevel(level)
    handler.setFormatter(
        _Formatter(
            "%(asctime)s | %(levelname)-8s | %(exchange)s | %(market)s | %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
    )
    return handler


def setup_logging(
    level: int = logging.INFO, logger: Optional[logging.Logger] = None
) -> None:
    """Configure root logging with rotation and dedicated trade/error streams."""

    target_logger = logger or logging.getLogger()
    target_logger.setLevel(level)

    # Avoid duplicate handlers when running multiple times
    if any(isinstance(h, RotatingFileHandler) for h in target_logger.handlers):
        return

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(
        _Formatter("%(asctime)s | %(levelname)-8s | %(message)s", "%Y-%m-%d %H:%M:%S")
    )

    bot_handler = _build_handler(BOT_LOG_FILE, level)
    error_handler = _build_handler(ERROR_LOG_FILE, logging.WARNING)

    target_logger.addHandler(console_handler)
    target_logger.addHandler(bot_handler)
    target_logger.addHandler(error_handler)

    # Dedicated trade logger
    trade_logger = logging.getLogger("trades")
    trade_logger.setLevel(logging.INFO)
    trade_logger.addHandler(_build_handler(TRADE_LOG_FILE, logging.INFO))
    trade_logger.propagate = False

    # Dedicated alert/error logger (reuses errors handler)
    alert_logger = logging.getLogger("alerts")
    alert_logger.setLevel(logging.INFO)
    alert_logger.addHandler(_build_handler(ALERT_LOG_FILE, logging.INFO))
    alert_logger.propagate = False

    target_logger.info("Logging configured. Writing to %s", BOT_LOG_FILE)


def get_trade_logger() -> logging.Logger:
    return logging.getLogger("trades")


def get_alert_logger() -> logging.Logger:
    return logging.getLogger("alerts")
