import sys
import os
import asyncio
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from connectors import polymarket, sx, kalshi  # noqa: E402


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


class DummyTimeoutSession:
    def get(self, *args, **kwargs):
        class CM:
            async def __aenter__(self):
                raise asyncio.TimeoutError("boom")

            async def __aexit__(self, exc_type, exc, tb):
                pass

        return CM()


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


@pytest.mark.asyncio
async def test_polymarket_timeout():
    session = DummyTimeoutSession()
    with pytest.raises(polymarket.OrderbookError) as excinfo:
        await polymarket.orderbook_depth(session, "m")
    msg = str(excinfo.value).lower()
    assert "timeout" in msg


@pytest.mark.asyncio
async def test_sx_timeout():
    session = DummyTimeoutSession()
    with pytest.raises(sx.SxError) as excinfo:
        await sx.orderbook_depth(session, "m")
    msg = str(excinfo.value).lower()
    assert "timeout" in msg


@pytest.mark.asyncio
async def test_kalshi_bad_json():
    session = DummySession({"foo": "bar"})
    with pytest.raises(kalshi.KalshiError) as excinfo:
        await kalshi.orderbook_depth(session, "m")
    msg = str(excinfo.value)
    assert "bad response format" in msg


@pytest.mark.asyncio
async def test_kalshi_timeout():
    session = DummyTimeoutSession()
    with pytest.raises(kalshi.KalshiError) as excinfo:
        await kalshi.orderbook_depth(session, "m")
    msg = str(excinfo.value).lower()
    assert "timeout" in msg


@pytest.mark.asyncio
async def test_kalshi_valid_response():
    # Test with valid Kalshi response format
    data = {
        "orderbook": {
            "yes": [[50, 100], [49, 200], [48, 150]],
            "no": [[51, 100], [52, 200]],
        }
    }
    session = DummySession(data)
    result = await kalshi.orderbook_depth(session, "TEST_MARKET", depth=3)
    # Result is now a dict with orderbook structure
    assert isinstance(result, dict)
    assert 'total_depth' in result
    assert 'total_qty_depth' in result
    # Should sum yes quantities: 100 + 200 + 150 = 450
    # and no quantities: 100 + 200 = 300
    # total qty = 450 + 300 = 750
    assert result['total_qty_depth'] == 750.0
    # Notional uses price * qty for each side
    assert result['total_depth'] == 365.0


@pytest.mark.asyncio
async def test_kalshi_empty_bids():
    # Test with empty yes bids
    data = {"orderbook": {"yes": [], "no": [[51, 100]]}}
    session = DummySession(data)
    result = await kalshi.orderbook_depth(session, "TEST_MARKET")
    # Result is now a dict
    assert isinstance(result, dict)
    assert result['total_depth'] == 0.0
    assert result['total_qty_depth'] == 0.0
