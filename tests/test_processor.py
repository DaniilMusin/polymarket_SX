import os
import sys
import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)  # noqa: E402

from core import processor  # noqa: E402


async def _dummy_pm(*_args, **_kwargs):
    return 1100


async def _dummy_sx(*_args, **_kwargs):
    return 800


@pytest.mark.asyncio
async def test_process_depth(monkeypatch):
    monkeypatch.setattr(processor.polymarket, "orderbook_depth", _dummy_pm)
    monkeypatch.setattr(processor.sx, "orderbook_depth", _dummy_sx)

    result = await processor.process_depth(None, "pm", "sx")
    assert abs(result - 0.0015) < 1e-6
