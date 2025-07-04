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
