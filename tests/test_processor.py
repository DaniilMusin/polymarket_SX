import os
import sys
import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)  # noqa: E402

from core import processor  # noqa: E402


@pytest.mark.asyncio
async def test_process_depth():
    result = await processor.process_depth(1100, 800)
    assert abs(result - 0.0015) < 1e-6


@pytest.mark.asyncio
async def test_process_depth_empty_config():
    """Test that process_depth handles empty SLIP_BY_DEPTH gracefully."""
    # Save original config
    original_slip_by_depth = processor.SLIP_BY_DEPTH
    
    try:
        # Set empty dictionary
        processor.SLIP_BY_DEPTH = {}
        
        # Should not raise ValueError and should return 0.0
        result = await processor.process_depth(1100, 800)
        assert result == 0.0
    finally:
        # Restore original config
        processor.SLIP_BY_DEPTH = original_slip_by_depth
