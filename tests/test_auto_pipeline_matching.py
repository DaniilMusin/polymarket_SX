import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)  # noqa: E402

from core.auto_pipeline import MarketEvent, _best_matches, _extract_outcome_token_ids  # noqa: E402


def test_best_matches_keeps_outcomes_separate():
    left_events = [
        MarketEvent(
            platform="polymarket",
            market_id="pm1",
            title="Test Event",
            description="",
            outcome="yes",
        ),
        MarketEvent(
            platform="polymarket",
            market_id="pm1",
            title="Test Event",
            description="",
            outcome="no",
        ),
    ]
    right_events = [
        MarketEvent(
            platform="sx",
            market_id="sx1",
            title="Test Event",
            description="",
            outcome="yes",
        ),
        MarketEvent(
            platform="sx",
            market_id="sx1",
            title="Test Event",
            description="",
            outcome="no",
        ),
    ]

    matches = _best_matches(left_events, right_events, min_confidence=0.0)
    assert len(matches) == 2
    assert {match.right.outcome for match in matches} == {"yes", "no"}


def test_extract_outcome_token_ids_parses_string_payloads():
    market = {
        "outcomes": '["Yes", "No"]',
        "clobTokenIds": '["111", "222"]',
    }
    assert _extract_outcome_token_ids(market) == {"yes": "111", "no": "222"}
