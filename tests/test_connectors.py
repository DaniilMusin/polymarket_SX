import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from connectors import polymarket, sx  # noqa: E402


class DummyResponse:
    def __init__(self, data, status=200):
        self._data = data
        self.status = status

    async def json(self):
        return self._data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass


class DummySession:
    def __init__(self, data):
        self._data = data

    def get(self, *args, **kwargs):
        return DummyResponse(self._data)


@pytest.mark.asyncio
async def test_polymarket_bad_json():
    session = DummySession({"foo": "bar"})
    with pytest.raises(polymarket.OrderbookError) as excinfo:
        await polymarket.orderbook_depth(session, "m")
    msg = str(excinfo.value)
    assert "bad response format" in msg
    assert "bids" in msg


@pytest.mark.asyncio
async def test_sx_bad_json():
    session = DummySession({"foo": "bar"})
    with pytest.raises(sx.SxError) as excinfo:
        await sx.orderbook_depth(session, "m")
    msg = str(excinfo.value)
    assert "bad response format" in msg
    assert "bids" in msg
