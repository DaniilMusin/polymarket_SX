import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.event_validator import EventValidator, EventValidationError  # noqa: E402


class DummyResponse:
    def __init__(self, data, status=200):
        self._data = data
        self.status = status
        self._text = str(data)

    async def json(self):
        return self._data

    async def text(self):
        return self._text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass


class DummySession:
    def __init__(self, data, status=200):
        self._data = data
        self._status = status

    def post(self, *args, **kwargs):
        return DummyResponse(self._data, self._status)


def test_validator_without_api_key():
    """Test validator initialization without API key."""
    # Clear environment variable if set
    old_key = os.environ.pop("PERPLEXITY_API_KEY", None)
    try:
        validator = EventValidator()
        assert validator.api_key is None
    finally:
        if old_key:
            os.environ["PERPLEXITY_API_KEY"] = old_key


def test_validator_with_api_key():
    """Test validator initialization with API key."""
    validator = EventValidator(api_key="test_key")
    assert validator.api_key == "test_key"
    assert validator.model == "sonar-reasoning"


@pytest.mark.asyncio
async def test_validate_events_without_api_key():
    """Test validation when API key is not set."""
    validator = EventValidator()  # No API key
    session = DummySession({})

    result = await validator.validate_events(
        session,
        "Event 1",
        "Description 1",
        "Polymarket",
        "Event 2",
        "Description 2",
        "Kalshi",
    )

    assert result["are_same"] is True  # Defaults to True when disabled
    assert result["confidence"] == "unknown"
    assert "disabled" in result["reasoning"].lower()
    assert result["warning"] is not None


@pytest.mark.asyncio
async def test_validate_events_same_events():
    """Test validation of same events."""
    response_data = {
        "choices": [
            {
                "message": {
                    "content": """VERDICT: SAME
CONFIDENCE: HIGH
REASONING: Both events refer to the 2024 US Presidential Election with identical resolution criteria.  # noqa: E501
WARNING: NONE"""
                }
            }
        ]
    }
    session = DummySession(response_data)
    validator = EventValidator(api_key="test_key")

    result = await validator.validate_events(
        session,
        "Will Donald Trump win the 2024 election?",
        "Resolves YES if Trump wins",
        "Polymarket",
        "Trump 2024 Presidential Victory",
        "YES if Trump is elected president in 2024",
        "Kalshi",
    )

    assert result["are_same"] is True
    assert result["confidence"] == "high"
    assert "2024" in result["reasoning"] or "identical" in result["reasoning"].lower()
    assert result["warning"] is None


@pytest.mark.asyncio
async def test_validate_events_different_events():
    """Test validation of different events."""
    response_data = {
        "choices": [
            {
                "message": {
                    "content": """VERDICT: DIFFERENT
CONFIDENCE: HIGH
REASONING: Event 1 asks about winning the election, while Event 2 asks about winning the nomination. These are distinct events with different resolution criteria.  # noqa: E501
WARNING: These events resolve at different times and under different conditions."""
                }
            }
        ]
    }
    session = DummySession(response_data)
    validator = EventValidator(api_key="test_key")

    result = await validator.validate_events(
        session,
        "Will Trump win the 2024 election?",
        "Resolves YES if Trump wins general election",
        "Polymarket",
        "Will Trump win the Republican nomination?",
        "Resolves YES if Trump wins nomination",
        "Kalshi",
    )

    assert result["are_same"] is False
    assert result["confidence"] == "high"
    assert result["warning"] is not None


@pytest.mark.asyncio
async def test_validate_events_api_error():
    """Test handling of API errors."""
    session = DummySession({}, status=500)
    validator = EventValidator(api_key="test_key")

    with pytest.raises(EventValidationError) as excinfo:
        await validator.validate_events(
            session,
            "Event 1",
            "Description 1",
            "Polymarket",
            "Event 2",
            "Description 2",
            "Kalshi",
        )
    assert "500" in str(excinfo.value)


@pytest.mark.asyncio
async def test_validate_events_medium_confidence():
    """Test validation with medium confidence."""
    response_data = {
        "choices": [
            {
                "message": {
                    "content": """VERDICT: SAME
CONFIDENCE: MEDIUM
REASONING: Events appear to refer to the same occurrence but wording differs slightly.
WARNING: Resolution criteria should be verified manually."""
                }
            }
        ]
    }
    session = DummySession(response_data)
    validator = EventValidator(api_key="test_key")

    result = await validator.validate_events(
        session,
        "Bitcoin above $100k by EOY",
        "BTC price >= $100,000 on Dec 31",
        "Polymarket",
        "BTC hits $100k this year",
        "Bitcoin reaches $100k in 2024",
        "Kalshi",
    )

    assert result["are_same"] is True
    assert result["confidence"] == "medium"
    assert result["warning"] is not None


def test_parse_response_basic():
    """Test response parsing."""
    validator = EventValidator(api_key="test_key")
    data = {
        "choices": [
            {
                "message": {
                    "content": """VERDICT: SAME
CONFIDENCE: HIGH
REASONING: Test reasoning
WARNING: Test warning"""
                }
            }
        ]
    }

    result = validator._parse_response(data)
    assert result["are_same"] is True
    assert result["confidence"] == "high"
    assert result["reasoning"] == "Test reasoning"
    assert result["warning"] == "Test warning"


def test_build_validation_prompt():
    """Test prompt building."""
    validator = EventValidator(api_key="test_key")
    prompt = validator._build_validation_prompt(
        "Event 1",
        "Desc 1",
        "Platform1",
        "Event 2",
        "Desc 2",
        "Platform2",
    )

    assert "Event 1" in prompt
    assert "Event 2" in prompt
    assert "Platform1" in prompt
    assert "Platform2" in prompt
    assert "VERDICT" in prompt
    assert "CONFIDENCE" in prompt
