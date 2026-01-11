import os
import sys

import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)  # noqa: E402

from core.event_validator import EventValidator  # noqa: E402


def _wrap_content(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def test_parse_response_json():
    validator = EventValidator(api_key="dummy")
    content = (
        '{"verdict":"SAME","confidence":"high","reasoning":"ok","warning":null}'
    )
    result = validator._parse_response(_wrap_content(content))
    assert result["are_same"] is True
    assert result["confidence"] == "high"
    assert result["warning"] is None


def test_parse_response_json_code_fence():
    validator = EventValidator(api_key="dummy")
    content = """```json
{"verdict":"DIFFERENT","confidence":"low","reasoning":"nope","warning":"ambiguous"}
```"""
    result = validator._parse_response(_wrap_content(content))
    assert result["are_same"] is False
    assert result["confidence"] == "low"
    assert result["warning"] == "ambiguous"


def test_parse_response_legacy_format():
    validator = EventValidator(api_key="dummy")
    content = """VERDICT: SAME
CONFIDENCE: MEDIUM
REASONING: Matches the same event.
WARNING: NONE
"""
    result = validator._parse_response(_wrap_content(content))
    assert result["are_same"] is True
    assert result["confidence"] == "medium"
    assert result["warning"] is None


@pytest.mark.asyncio
async def test_allow_unvalidated_events_sets_high_confidence(monkeypatch):
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_UNVALIDATED_EVENTS", "true")
    validator = EventValidator(api_key=None)
    result = await validator.validate_events(
        session=object(),
        event1_name="A",
        event1_description="",
        platform1="Polymarket",
        event2_name="B",
        event2_description="",
        platform2="SX",
    )
    assert result["are_same"] is True
    assert result["confidence"] == "high"
