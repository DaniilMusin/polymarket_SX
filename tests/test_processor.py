import os
import sys
import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)  # noqa: E402

from core import processor  # noqa: E402


@pytest.mark.asyncio
async def test_process_depth():
    # Тестируем с числовыми значениями глубины
    pm_depth = 1900.0  # 1100 + 800
    sx_depth = 1900.0  # 800 + 1100

    result = await processor.process_depth(pm_depth, sx_depth)
    assert abs(result - 0.0010) < 1e-6  # Ожидаем проскальзывание для глубины 1900


@pytest.mark.asyncio
async def test_process_depth_empty_config():
    """Test that process_depth handles empty SLIP_BY_DEPTH gracefully."""
    # Save original config
    original_slip_by_depth = processor.SLIP_BY_DEPTH

    try:
        # Set empty dictionary
        processor.SLIP_BY_DEPTH = {}

        # Тестируем с числовыми значениями глубины
        pm_depth = 1900.0
        sx_depth = 1900.0

        # Should not raise ValueError and should return 0.0
        result = await processor.process_depth(pm_depth, sx_depth)
        assert result == 0.0
    finally:
        # Restore original config
        processor.SLIP_BY_DEPTH = original_slip_by_depth
