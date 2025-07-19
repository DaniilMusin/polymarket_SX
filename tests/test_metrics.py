import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.metrics import g_pnl, reset_pnl  # noqa: E402
from core import processor  # noqa: E402


def test_reset_pnl_sets_zero():
    g_pnl.set(5.5)
    reset_pnl()
    assert g_pnl._value.get() == 0.0


@pytest.mark.asyncio
async def test_process_depth_does_not_reset_pnl():
    g_pnl.set(3.0)
    
    # Тестируем с числовыми значениями глубины
    pm_depth = 2000.0  # 1000 + 1000
    sx_depth = 2000.0  # 1000 + 1000
    
    await processor.process_depth(pm_depth, sx_depth)
    assert g_pnl._value.get() == 3.0
