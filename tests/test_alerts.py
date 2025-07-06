import os
import sys
import logging
import importlib
import asyncio
import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)  # noqa: E402

import core.alerts as alerts  # noqa: E402


def reload_alerts(monkeypatch, token=None, chat="1"):
    if token is None:
        monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    else:
        monkeypatch.setenv("TELEGRAM_TOKEN", token)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", chat)
    importlib.reload(alerts)
    return alerts


def test_bot_not_created_without_token(monkeypatch):
    mod = reload_alerts(monkeypatch, token="")
    handler = mod.TelegramHandler()
    assert handler.bot is None


@pytest.mark.asyncio
async def test_emit_handles_network_error(monkeypatch):
    class DummyBot:
        async def send_message(self, *_, **__):
            raise RuntimeError("fail")

    mod = reload_alerts(monkeypatch, token="token")
    monkeypatch.setattr(mod, "Bot", lambda _: DummyBot())
    handler = mod.TelegramHandler()

    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="oops",
        args=(),
        exc_info=None,
    )
    handler.emit(record)
    await asyncio.sleep(0)
