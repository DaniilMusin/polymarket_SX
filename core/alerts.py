"""
Alert system using standard Python logging.

This module provides enhanced logging capabilities for critical events,
errors, and important trading activities.
"""

import logging
import os
from typing import Optional
from logging.handlers import RotatingFileHandler


# Configure alert log file path
ALERT_LOG_PATH = os.getenv("ALERT_LOG_PATH", "logs/alerts.log")
ALERT_LOG_MAX_BYTES = int(os.getenv("ALERT_LOG_MAX_BYTES", str(10 * 1024 * 1024)))  # 10MB
ALERT_LOG_BACKUP_COUNT = int(os.getenv("ALERT_LOG_BACKUP_COUNT", "5"))


class CriticalAlertHandler(logging.Handler):
    """
    Custom logging handler for critical alerts.

    This handler:
    - Logs critical errors to a separate alerts.log file
    - Uses rotating file handler to prevent disk space issues
    - Formats messages with clear severity indicators
    - Can be extended to send emails, Slack messages, etc.
    """

    def __init__(self, level: int = logging.ERROR) -> None:
        super().__init__(level)

        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(ALERT_LOG_PATH)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except OSError as e:
                logging.warning("Could not create log directory %s: %s", log_dir, e)

        # Set up rotating file handler
        self.file_handler: Optional[RotatingFileHandler] = None
        try:
            self.file_handler = RotatingFileHandler(
                ALERT_LOG_PATH,
                maxBytes=ALERT_LOG_MAX_BYTES,
                backupCount=ALERT_LOG_BACKUP_COUNT
            )

            # Format: timestamp | level | message
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            self.file_handler.setFormatter(formatter)

        except (OSError, IOError) as e:
            logging.warning("Could not create alert log file %s: %s", ALERT_LOG_PATH, e)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the alerts file."""
        if self.file_handler:
            try:
                self.file_handler.emit(record)
            except Exception:
                # Don't let logging errors crash the application
                self.handleError(record)
        else:
            # Fallback: just print to stderr
            try:
                msg = self.format(record)
                print(f"ALERT: {msg}", flush=True)
            except Exception:
                pass


def setup_alert_logging(logger: Optional[logging.Logger] = None) -> None:
    """
    Set up alert logging for critical events.

    Args:
        logger: Logger to add alert handler to (default: root logger)
    """
    if logger is None:
        logger = logging.getLogger()

    # Add critical alert handler
    alert_handler = CriticalAlertHandler(level=logging.ERROR)
    logger.addHandler(alert_handler)

    logging.info("Alert logging configured: %s", ALERT_LOG_PATH)
