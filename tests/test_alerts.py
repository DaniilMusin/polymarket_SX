"""Tests for alert logging system."""

import os
import sys
import logging
import tempfile
import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)  # noqa: E402

from core.alerts import CriticalAlertHandler, setup_alert_logging  # noqa: E402


def test_alert_handler_creation():
    """Test that CriticalAlertHandler can be created."""
    handler = CriticalAlertHandler(level=logging.ERROR)
    assert handler is not None
    assert handler.level == logging.ERROR


def test_alert_handler_emit():
    """Test that alert handler can emit log records."""
    with tempfile.TemporaryDirectory() as tmpdir:
        alert_path = os.path.join(tmpdir, "test_alerts.log")

        # Patch the ALERT_LOG_PATH
        import core.alerts
        original_path = core.alerts.ALERT_LOG_PATH
        core.alerts.ALERT_LOG_PATH = alert_path

        try:
            handler = CriticalAlertHandler(level=logging.ERROR)

            # Create a log record
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname=__file__,
                lineno=1,
                msg="Test alert message",
                args=(),
                exc_info=None,
            )

            # Emit the record
            handler.emit(record)

            # Check that file was created and contains the message
            assert os.path.exists(alert_path)
            with open(alert_path, 'r') as f:
                content = f.read()
                assert "Test alert message" in content
                assert "ERROR" in content
        finally:
            core.alerts.ALERT_LOG_PATH = original_path


def test_setup_alert_logging():
    """Test that setup_alert_logging configures logging correctly."""
    test_logger = logging.getLogger('test_logger')
    initial_handlers = len(test_logger.handlers)

    setup_alert_logging(test_logger)

    # Should have added one handler
    assert len(test_logger.handlers) == initial_handlers + 1

    # The new handler should be a CriticalAlertHandler
    new_handler = test_logger.handlers[-1]
    assert isinstance(new_handler, CriticalAlertHandler)


def test_alert_handler_handles_errors():
    """Test that alert handler doesn't crash on emit errors."""
    handler = CriticalAlertHandler(level=logging.ERROR)

    # Force file_handler to None to trigger fallback
    handler.file_handler = None

    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    # Should not raise an exception
    try:
        handler.emit(record)
    except Exception as e:
        pytest.fail(f"Handler raised exception: {e}")
