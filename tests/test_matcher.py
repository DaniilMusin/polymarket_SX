import os
import sys
from datetime import datetime

import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)  # noqa: E402

from core.matcher import match, score_event_match, decide_match  # noqa: E402


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


def test_match_not_found():
    pm_list = [Obj("A @ B", datetime(2025, 6, 19))]
    sx_list = [Obj("C @ D", datetime(2025, 6, 19))]
    pairs = match(pm_list, sx_list, min_score=95)
    assert pairs == []


def test_match_prefers_closest_date_for_exact_title():
    pm_list = [Obj("Boston Celtics @ LA Clippers", datetime(2025, 6, 19))]
    sx_list = [
        Obj("Boston Celtics @ LA Clippers", datetime(2025, 6, 18)),
        Obj("Boston Celtics @ LA Clippers", datetime(2025, 6, 19)),
    ]
    pairs = match(pm_list, sx_list)
    assert len(pairs) == 1
    assert pairs[0][1] is sx_list[1]


def test_match_handles_missing_dates():
    pm_list = [Obj("A @ B", None)]
    sx_list = [Obj("A @ B", None)]
    pairs = match(pm_list, sx_list)
    assert len(pairs) == 1


class RichEvent:
    def __init__(self, title, description="", platform="Test", t_start=None):
        self.title = title
        self.description = description
        self.platform = platform
        self.t_start = t_start


def test_score_event_match_politics_confident():
    left = RichEvent(
        "Will Trump win the 2024 election?",
        "Resolves YES if Trump wins the general election in 2024.",
        platform="Polymarket",
    )
    right = RichEvent(
        "Trump 2024 Presidential Victory",
        "YES if Donald Trump is elected president in 2024.",
        platform="SX",
    )
    score = score_event_match(left, right)
    assert score.category in {"politics", "mixed"}
    assert score.confidence >= 0.7


def test_score_event_match_tech_confident():
    left = RichEvent(
        "Bitcoin above $100k by EOY",
        "BTC price is at least $100,000 on Dec 31, 2024.",
        platform="Polymarket",
    )
    right = RichEvent(
        "BTC hits $100,000 in 2024",
        "Bitcoin reaches 100k before year end.",
        platform="SX",
    )
    score = score_event_match(left, right)
    assert score.category in {"tech", "mixed", "economics"}
    assert score.confidence >= 0.5


def test_score_event_match_mismatch_low():
    left = RichEvent(
        "Will Trump win the 2024 election?",
        "Resolves YES if Trump wins the general election in 2024.",
        platform="Polymarket",
    )
    right = RichEvent(
        "Fed cuts rates in September",
        "Federal Reserve cuts the policy rate in September.",
        platform="Kalshi",
    )
    score = score_event_match(left, right)
    assert score.confidence < 0.6


def test_score_event_match_percent_words():
    left = RichEvent(
        "CPI above 3 percent in 2024",
        "CPI at least 3 percent year over year.",
        platform="Kalshi",
    )
    right = RichEvent(
        "CPI above 3% in 2024",
        "CPI above 3% YoY.",
        platform="Polymarket",
    )
    score = score_event_match(left, right)
    assert score.numeric_score == 1.0
    assert score.confidence >= 0.6


def test_score_event_match_magnitude_words():
    left = RichEvent(
        "US debt above 1 trillion",
        "Debt above 1 trillion.",
        platform="Kalshi",
    )
    right = RichEvent(
        "US debt above 1T",
        "Debt above 1T.",
        platform="Polymarket",
    )
    score = score_event_match(left, right)
    assert score.numeric_score == 1.0
    assert score.confidence >= 0.5


def test_score_event_match_ai_abbreviation():
    left = RichEvent(
        "A.I. model release in 2025",
        "A major AI model release in 2025.",
        platform="Polymarket",
    )
    right = RichEvent(
        "AI model release in 2025",
        "Major AI lab releases a model in 2025.",
        platform="SX",
    )
    score = score_event_match(left, right)
    assert score.category in {"tech", "mixed"}
    assert score.confidence >= 0.6


def test_score_event_match_fed_alias():
    left = RichEvent(
        "Will the Federal Reserve cut rates in 2024?",
        "Fed cuts rates before year end.",
        platform="Polymarket",
    )
    right = RichEvent(
        "Fed rate cuts in 2024",
        "Federal Reserve cuts rates by the end of 2024.",
        platform="SX",
    )
    score = score_event_match(left, right)
    assert score.category in {"economics", "mixed"}
    assert score.confidence >= 0.6


def test_score_event_match_sec_alias():
    left = RichEvent(
        "SEC approves spot Bitcoin ETF",
        "Securities and Exchange Commission approves a spot BTC ETF.",
        platform="Polymarket",
    )
    right = RichEvent(
        "Securities and Exchange Commission spot bitcoin ETF approval",
        "SEC approval for spot BTC ETF.",
        platform="SX",
    )
    score = score_event_match(left, right)
    assert score.category in {"tech", "mixed", "economics"}
    assert score.confidence >= 0.6


def test_score_event_match_mentions_keyword():
    left = RichEvent(
        "Will Nvidia mention AI on earnings call?",
        "Mentions AI during Q2 earnings call.",
        platform="Polymarket",
    )
    right = RichEvent(
        "NVIDIA mentions AI in Q2 earnings call",
        "Nvidia mentions AI on the earnings call.",
        platform="SX",
    )
    score = score_event_match(left, right)
    assert score.category in {"tech", "mixed"}
    assert score.confidence >= 0.6


def test_score_event_match_openai_spacing():
    left = RichEvent(
        "Open AI releases a new model in 2025",
        "Open AI releases a model in 2025.",
        platform="Polymarket",
    )
    right = RichEvent(
        "OpenAI releases a new model in 2025",
        "OpenAI releases a model in 2025.",
        platform="SX",
    )
    score = score_event_match(left, right)
    assert score.category in {"tech", "mixed"}
    assert score.confidence >= 0.6


@pytest.mark.parametrize(
    "left_title,left_desc,right_title,right_desc,min_conf,expected_categories",
    [
        (
            "US Congress passes AI regulation bill in 2025",
            "Congress passes AI regulation bill.",
            "AI regulation bill passes Congress in 2025",
            "",
            0.6,
            {"politics", "tech", "mixed"},
        ),
        (
            "UK election: Labour wins majority",
            "Labour wins majority in the UK general election.",
            "Labour wins majority in UK general election",
            "",
            0.6,
            {"politics", "mixed"},
        ),
        (
            "SCOTUS rules on abortion pill",
            "Supreme Court ruling on abortion pill case.",
            "Supreme Court ruling on abortion pill",
            "",
            0.6,
            {"politics", "mixed"},
        ),
        (
            "Biden approval above 45 percent in June",
            "Approval above 45 percent in June.",
            "Biden approval >45% in June",
            "",
            0.6,
            {"politics", "mixed"},
        ),
        (
            "EU sanctions on Russia in 2025",
            "European Union sanctions Russia in 2025.",
            "European Union sanctions Russia in 2025",
            "",
            0.6,
            {"politics", "mixed"},
        ),
        (
            "Sweden joins NATO in 2024",
            "Sweden joins NATO by the end of 2024.",
            "NATO admits Sweden by 2024",
            "",
            0.55,
            {"politics", "mixed"},
        ),
        (
            "Taiwan presidential election winner 2024",
            "Winner of the Taiwan election in 2024.",
            "Taiwan election winner in 2024",
            "",
            0.6,
            {"politics", "mixed"},
        ),
        (
            "UN votes on Israel ceasefire",
            "UN votes on a ceasefire for Israel.",
            "Israel ceasefire vote in UN",
            "",
            0.55,
            {"politics", "mixed"},
        ),
            (
                "US bans TikTok in 2025",
                "US ban on TikTok in 2025.",
                "US ban on TikTok in 2025",
                "",
                0.6,
                {"politics", "tech", "mixed"},
            ),
        (
            "OpenAI releases GPT model in 2025",
            "OpenAI releases a GPT model in 2025.",
            "Open AI releases a GPT model in 2025",
            "",
            0.6,
            {"tech", "mixed"},
        ),
        (
            "Anthropic launches Claude model",
            "Anthropic launches the Claude model.",
            "Anthropic releases Claude model",
            "",
            0.6,
            {"tech", "mixed"},
        ),
        (
            "Nvidia mentions AI on earnings call",
            "Nvidia mentions AI during earnings call.",
            "NVIDIA mentions AI in earnings call",
            "",
            0.6,
            {"tech", "mixed"},
        ),
        (
            "Microsoft settles antitrust case in 2025",
            "Microsoft antitrust case settlement in 2025.",
            "Microsoft antitrust case settlement in 2025",
            "",
            0.6,
            {"tech", "mixed", "economics"},
        ),
        (
            "Apple Vision Pro 2 release in 2025",
            "Apple releases Vision Pro 2 in 2025.",
            "Apple releases Vision Pro 2 in 2025",
            "",
            0.6,
            {"tech", "mixed"},
        ),
        (
            "TSMC announces new chip fab in 2025",
            "TSMC announces a chip fab in 2025.",
            "TSMC announces chip fab in 2025",
            "",
            0.6,
            {"tech", "mixed"},
        ),
        (
            "Meta launches new Llama model",
            "Meta launches the Llama model.",
            "Meta releases Llama model",
            "",
            0.6,
            {"tech", "mixed"},
        ),
        (
            "Google releases Gemini model in 2024",
            "Google releases the Gemini model in 2024.",
            "Google Gemini model release in 2024",
            "",
            0.6,
            {"tech", "mixed"},
        ),
        (
            "AMD releases AI chip in 2025",
            "AMD launches AI chips in 2025.",
            "AMD launches AI chips in 2025",
            "",
            0.6,
            {"tech", "mixed"},
        ),
        (
            "Arm files for IPO in 2024",
            "Arm IPO in 2024.",
            "ARM IPO in 2024",
            "",
            0.55,
            {"tech", "mixed", "economics"},
        ),
        (
            "SEC approves spot Bitcoin ETF in 2024",
            "Securities and Exchange Commission approves spot BTC ETF.",
            "Securities and Exchange Commission approves spot BTC ETF",
            "",
            0.6,
            {"tech", "mixed", "economics"},
        ),
        (
            "Department of Justice sues Apple for antitrust",
            "DoJ antitrust suit against Apple.",
            "DoJ antitrust suit against Apple",
            "",
            0.55,
            {"tech", "mixed", "economics"},
        ),
        (
            "Musk mentions AI in interview",
            "Elon Musk mentions AI in interview.",
            "Elon Musk mentions AI in interview",
            "",
            0.6,
            {"tech", "mixed"},
        ),
        (
            "Earnings call mentions recession",
            "CEO mentions recession on earnings call.",
            "CEO mentions recession on earnings call",
            "",
            0.55,
            {"economics", "mixed"},
        ),
        (
            "Company mentions BTC during earnings call",
            "Company mentions bitcoin on earnings call.",
            "Company mentions bitcoin on earnings call",
            "",
            0.55,
            {"tech", "mixed"},
        ),
        (
            "GDP above 2 percent in 2025",
            "GDP growth above 2% in 2025.",
            "GDP growth above 2% in 2025",
            "",
            0.6,
            {"economics", "mixed"},
        ),
        (
            "Treasury yields over 5% in 2024",
            "US Treasury yield above 5% in 2024.",
            "US Treasury yield above 5% in 2024",
            "",
            0.6,
            {"economics", "mixed"},
        ),
        (
            "Unemployment below 4 percent in 2024",
            "US unemployment rate below 4% in 2024.",
            "US unemployment rate below 4% in 2024",
            "",
            0.6,
            {"economics", "mixed"},
        ),
    ],
)
def test_score_event_match_many_positive_cases(
    left_title,
    left_desc,
    right_title,
    right_desc,
    min_conf,
    expected_categories,
):
    left = RichEvent(left_title, left_desc, platform="Polymarket")
    right = RichEvent(right_title, right_desc, platform="SX")
    score = score_event_match(left, right)
    assert score.confidence >= min_conf
    assert score.category in expected_categories


@pytest.mark.parametrize(
    "left_title,left_desc,right_title,right_desc,max_conf",
    [
        (
            "Trump wins 2024 election",
            "Trump wins the 2024 election.",
            "Bitcoin above 100k in 2024",
            "BTC above 100k by year end.",
            0.5,
        ),
        (
            "Fed cuts rates in 2024",
            "Federal Reserve cuts rates in 2024.",
            "Apple releases Vision Pro 2 in 2025",
            "Apple releases Vision Pro 2.",
            0.5,
        ),
        (
            "Nvidia mentions AI on earnings call",
            "Nvidia mentions AI during earnings call.",
            "Biden approval above 45% in June",
            "Approval above 45% in June.",
            0.5,
        ),
        (
            "Ethereum upgrade in 2025",
            "ETH network upgrade in 2025.",
            "Ukraine peace deal in 2025",
            "Ukraine peace deal in 2025.",
            0.5,
        ),
        (
            "US bans TikTok in 2025",
            "US ban on TikTok.",
            "TSMC announces chip fab in 2025",
            "TSMC announces chip fab.",
            0.5,
        ),
        (
            "GDP above 2% in 2025",
            "GDP growth above 2% in 2025.",
            "Supreme Court rules on abortion pill",
            "Supreme Court ruling on abortion pill.",
            0.5,
        ),
        (
            "SEC approves spot Bitcoin ETF",
            "SEC approves spot BTC ETF.",
            "Taiwan election winner in 2024",
            "Taiwan election winner in 2024.",
            0.5,
        ),
        (
            "Meta releases Llama model",
            "Meta releases the Llama model.",
            "UN votes on Israel ceasefire",
            "UN votes on a ceasefire for Israel.",
            0.5,
        ),
    ],
)
def test_score_event_match_many_negative_cases(
    left_title,
    left_desc,
    right_title,
    right_desc,
    max_conf,
):
    left = RichEvent(left_title, left_desc, platform="Polymarket")
    right = RichEvent(right_title, right_desc, platform="SX")
    score = score_event_match(left, right)
    assert score.confidence <= max_conf


@pytest.mark.asyncio
async def test_decide_match_llm_fallback():
    class DummyValidator:
        async def validate_events(self, *args, **kwargs):
            return {
                "are_same": True,
                "confidence": "high",
                "reasoning": "stub",
                "warning": None,
            }

    left = RichEvent(
        "Will a new AI model be released in 2025?",
        "Resolves YES if a major AI lab releases a new model in 2025.",
        platform="Polymarket",
    )
    right = RichEvent(
        "Major AI lab releases a new model in 2025",
        "YES if a top AI lab ships a model in 2025.",
        platform="SX",
    )

    decision = await decide_match(
        left,
        right,
        min_confidence=1.01,
        validator=DummyValidator(),
        session=object(),
        llm_min_confidence="medium",
    )

    assert decision.matched_by == "llm"
    assert decision.accepted is True
