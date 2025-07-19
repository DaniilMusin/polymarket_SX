import os
import sys
import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)  # noqa: E402

from core import processor  # noqa: E402


@pytest.mark.asyncio
async def test_process_depth():
    # Создаем моковые данные стакана
    pm_orderbook = {
        "bids": [{"price": 0.65, "size": 1100}],
        "asks": [{"price": 0.66, "size": 800}]
    }
    sx_orderbook = {
        "bids": [{"price": 0.65, "size": 800}],
        "asks": [{"price": 0.66, "size": 1100}]
    }
    
    result = await processor.process_depth(pm_orderbook, sx_orderbook)
    assert abs(result - 0.0010) < 1e-6  # Ожидаем проскальзывание для глубины 800


@pytest.mark.asyncio
async def test_process_depth_empty_config():
    """Test that process_depth handles empty SLIP_BY_DEPTH gracefully."""
    # Save original config
    original_slip_by_depth = processor.SLIP_BY_DEPTH
    
    try:
        # Set empty dictionary
        processor.SLIP_BY_DEPTH = {}
        
        # Создаем моковые данные стакана
        pm_orderbook = {
            "bids": [{"price": 0.65, "size": 1100}],
            "asks": [{"price": 0.66, "size": 800}]
        }
        sx_orderbook = {
            "bids": [{"price": 0.65, "size": 800}],
            "asks": [{"price": 0.66, "size": 1100}]
        }
        
        # Should not raise ValueError and should return 0.0
        result = await processor.process_depth(pm_orderbook, sx_orderbook)
        assert result == 0.0
    finally:
        # Restore original config
        processor.SLIP_BY_DEPTH = original_slip_by_depth
