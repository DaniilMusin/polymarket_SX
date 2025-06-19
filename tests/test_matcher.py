import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))  # noqa: E402

from core.matcher import match  # noqa: E402


class Obj:
    def __init__(self, title, t_start):
        self.title = title
        self.t_start = t_start


def test_match_found():
    pm_list = [Obj("Boston Celtics @ LA Clippers", datetime(2025, 6, 19))]
    sx_list = [Obj("LA Clippers @ Boston Celtics", datetime(2025, 6, 19))]
    pairs = match(pm_list, sx_list)
    assert len(pairs) == 1
    assert pairs[0][0] is pm_list[0]
    assert pairs[0][1] is sx_list[0]
