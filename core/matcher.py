from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from collections.abc import Sequence
from typing import Any, Iterable, Optional

from rapidfuzz import fuzz


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "if",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "will",
    "with",
    "yes",
    "no",
    "resolve",
    "resolves",
    "resolution",
    "event",
    "events",
    "market",
    "markets",
    "question",
    "questions",
    "happen",
    "happens",
    "occur",
    "occurs",
    "occurred",
    "occurring",
    "after",
    "before",
    "day",
    "days",
    "month",
    "months",
    "year",
    "price",
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
}

_CATEGORY_KEYWORDS = {
    "sports": {
        "nba",
        "nfl",
        "nhl",
        "mlb",
        "soccer",
        "football",
        "basketball",
        "baseball",
        "tennis",
        "golf",
        "ufc",
        "mma",
        "nhl",
    },
    "politics": {
        "election",
        "president",
        "presidential",
        "senate",
        "congress",
        "parliament",
        "prime",
        "minister",
        "governor",
        "mayor",
        "ballot",
        "vote",
        "voter",
        "referendum",
        "primary",
        "nomination",
        "candidate",
        "campaign",
        "democrat",
        "republican",
        "labour",
        "conservative",
        "coalition",
        "european",
        "union",
        "policy",
        "policies",
        "legislation",
        "bill",
        "law",
        "ban",
        "bans",
        "sanction",
        "sanctions",
        "approval",
        "approve",
        "poll",
        "polls",
        "runoff",
        "incumbent",
        "impeachment",
        "administration",
        "cabinet",
        "whitehouse",
        "supreme",
        "court",
        "scotus",
        "nato",
        "ukraine",
        "russia",
        "china",
        "taiwan",
        "israel",
        "iran",
        "gaza",
    },
    "tech": {
        "ai",
        "artificial",
        "intelligence",
        "llm",
        "gpt",
        "model",
        "models",
        "chip",
        "chips",
        "gpu",
        "semiconductor",
        "semiconductors",
        "datacenter",
        "cloud",
        "compute",
        "server",
        "software",
        "hardware",
        "smartphone",
        "iphone",
        "android",
        "openai",
        "anthropic",
        "google",
        "microsoft",
        "apple",
        "meta",
        "nvidia",
        "tesla",
        "amazon",
        "alphabet",
        "tiktok",
        "bytedance",
        "tsmc",
        "intel",
        "amd",
        "arm",
        "qualcomm",
        "oracle",
        "samsung",
        "spacex",
        "robot",
        "robotics",
        "crypto",
        "bitcoin",
        "ethereum",
        "blockchain",
        "ipo",
        "antitrust",
        "regulation",
    },
    "economics": {
        "inflation",
        "cpi",
        "ppi",
        "gdp",
        "recession",
        "rate",
        "rates",
        "interest",
        "fed",
        "fomc",
        "sec",
        "doj",
        "ftc",
        "fda",
        "etf",
        "unemployment",
        "jobs",
        "yield",
        "treasury",
        "debt",
        "budget",
        "tariff",
    },
}
_CATEGORY_KEYWORDS_FLAT = set().union(*_CATEGORY_KEYWORDS.values())

_DIRECTION_POS = {"above", "over", "greater", "higher", "more"}
_DIRECTION_NEG = {"below", "under", "less", "lower"}

_CANONICAL = {
    "presidential": "election",
    "president": "election",
    "elected": "election",
    "election": "election",
    "victory": "win",
    "wins": "win",
    "winner": "win",
    "btc": "bitcoin",
    "bitcoin": "bitcoin",
    "eth": "ethereum",
    "ethereum": "ethereum",
    "ai": "ai",
    "artificial": "ai",
    "intelligence": "ai",
    "llms": "llm",
    "gpts": "gpt",
    "chatgpt": "gpt",
    "gpt4": "gpt",
    "gpt3": "gpt",
    "release": "release",
    "releases": "release",
    "released": "release",
    "launch": "release",
    "launches": "release",
    "launched": "release",
    "ship": "release",
    "ships": "release",
    "shipped": "release",
    "announce": "announce",
    "announces": "announce",
    "announced": "announce",
    "approval": "approve",
    "approve": "approve",
    "approves": "approve",
    "approved": "approve",
    "mention": "mention",
    "mentions": "mention",
    "mentioning": "mention",
    "eoy": "year",
    "year": "year",
    "end": "year",
    "usa": "us",
}

_NUMBER_RE = re.compile(r"(?<!\w)(\d+(?:\.\d+)?)(%|k|m|b|t)?", re.IGNORECASE)
_TEAM_SPLIT_RE = re.compile(r"\s+(?:vs\.?|v)\s+", re.IGNORECASE)
_ABBREV_DOT_RE = re.compile(r"(?<=\b[a-z])\.(?=[a-z]\b)")
_PERCENT_WORD_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:percent|percentage|pct|per\s*cent)\b",
    re.IGNORECASE,
)
_MAGNITUDE_WORD_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(thousand|million|billion|trillion|mn|bn)s?\b",
    re.IGNORECASE,
)
_MAGNITUDE_SUFFIXES = {
    "thousand": "k",
    "million": "m",
    "mn": "m",
    "billion": "b",
    "bn": "b",
    "trillion": "t",
}
_PHRASE_REPLACEMENTS = (
    (re.compile(r"\bunited states of america\b", re.IGNORECASE), "us"),
    (re.compile(r"\bunited states\b", re.IGNORECASE), "us"),
    (re.compile(r"\bunited kingdom\b", re.IGNORECASE), "uk"),
    (re.compile(r"\beuropean union\b", re.IGNORECASE), "eu"),
    (re.compile(r"\bwhite house\b", re.IGNORECASE), "whitehouse"),
    (re.compile(r"\bsupreme court\b", re.IGNORECASE), "scotus"),
    (re.compile(r"\bfederal reserve\b", re.IGNORECASE), "fed"),
    (re.compile(r"\bdepartment of justice\b", re.IGNORECASE), "doj"),
    (re.compile(r"\bsecurities and exchange commission\b", re.IGNORECASE), "sec"),
    (re.compile(r"\bfederal trade commission\b", re.IGNORECASE), "ftc"),
    (re.compile(r"\bfood and drug administration\b", re.IGNORECASE), "fda"),
    (re.compile(r"\bartificial intelligence\b", re.IGNORECASE), "ai"),
    (re.compile(r"\bopen ai\b", re.IGNORECASE), "openai"),
    (re.compile(r"\bchat gpt\b", re.IGNORECASE), "gpt"),
)


def _normalize(s: str) -> str:
    return s.lower().replace(" at ", " @ ").replace("-", " ")


def _extract_teams(title: str) -> tuple[str, str]:
    """`Boston Celtics @ LA Clippers` -> ('boston celtics','la clippers')"""
    normalized = _normalize(title)
    if "@" in normalized:
        left, right = (x.strip() for x in normalized.split("@", 1))
        return left, right
    match = _TEAM_SPLIT_RE.split(normalized, maxsplit=1)
    if len(match) == 2:
        return match[0].strip(), match[1].strip()
    return (normalized, "")


def _get_attr(event: Any, name: str, default: Any = "") -> Any:
    if isinstance(event, dict):
        return event.get(name, default)
    return getattr(event, name, default)


def _normalize_magnitudes(text: str) -> str:
    def repl(match: re.Match) -> str:
        number = match.group(1)
        word = match.group(2).lower()
        suffix = _MAGNITUDE_SUFFIXES.get(word)
        if not suffix:
            return match.group(0)
        return f"{number}{suffix}"

    return _MAGNITUDE_WORD_RE.sub(repl, text)


def _normalize_comparators(text: str) -> str:
    text = re.sub(r"(>=|>)\s*(\d)", r" above \2", text)
    text = re.sub(r"(<=|<)\s*(\d)", r" below \2", text)
    text = re.sub(
        r"\b(at least|no less than|greater than or equal to)\b",
        " above ",
        text,
    )
    text = re.sub(
        r"\b(at most|no more than|less than or equal to)\b",
        " below ",
        text,
    )
    return text


def _normalize_text(text: str) -> str:
    lowered = text.lower()
    for pattern, replacement in _PHRASE_REPLACEMENTS:
        lowered = pattern.sub(replacement, lowered)
    lowered = _ABBREV_DOT_RE.sub("", lowered)
    lowered = _PERCENT_WORD_RE.sub(r"\1%", lowered)
    lowered = _normalize_magnitudes(lowered)
    lowered = _normalize_comparators(lowered)
    cleaned = re.sub(r"[^a-z0-9%$]+", " ", lowered)
    return " ".join(cleaned.split())


def _split_tokens(normalized_text: str) -> list[str]:
    if not normalized_text:
        return []
    tokens = normalized_text.split()
    return [t for t in tokens if t not in _STOPWORDS]


def _tokenize(text: str) -> list[str]:
    return _split_tokens(_normalize_text(text))


def _canonical_tokens(tokens: list[str]) -> list[str]:
    normalized: list[str] = []
    for token in tokens:
        value = _normalize_token(token)
        if not value or value in _STOPWORDS:
            continue
        normalized.append(value)
    return normalized


def _phrase_tokens(tokens: list[str]) -> set[str]:
    phrases: set[str] = set()
    for index in range(len(tokens) - 1):
        left = tokens[index]
        right = tokens[index + 1]
        if left and right:
            phrases.add(f"{left}_{right}")
    return phrases


def _overlap_score(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))


def _extract_numbers(text: str) -> list[float]:
    numbers: list[float] = []
    cleaned = text.replace(",", "")
    for match in _NUMBER_RE.finditer(cleaned.lower()):
        value = float(match.group(1))
        suffix = match.group(2)
        if suffix == "k":
            value *= 1_000
        elif suffix == "m":
            value *= 1_000_000
        elif suffix == "b":
            value *= 1_000_000_000
        elif suffix == "t":
            value *= 1_000_000_000_000
        elif suffix == "%":
            value /= 100.0
        numbers.append(value)
    return numbers


def _numbers_close(a: float, b: float) -> bool:
    if a == b:
        return True
    if 1900 <= a <= 2100 and 1900 <= b <= 2100:
        return abs(a - b) <= 1
    if a == 0 or b == 0:
        return False
    return abs(a - b) / max(abs(a), abs(b)) <= 0.02


def _numeric_score(nums_a: list[float], nums_b: list[float]) -> float:
    if not nums_a and not nums_b:
        return 0.5
    if not nums_a or not nums_b:
        return 0.2
    matches = 0
    for num in nums_a:
        if any(_numbers_close(num, other) for other in nums_b):
            matches += 1
    return matches / max(len(nums_a), len(nums_b))


def _is_sports_text(text: str) -> bool:
    lowered = text.lower()
    if "@" in lowered or _TEAM_SPLIT_RE.search(lowered):
        return True
    tokens = set(_tokenize(lowered))
    return bool(tokens & _CATEGORY_KEYWORDS["sports"])


def _categorize_text(text: str) -> str:
    if _is_sports_text(text):
        return "sports"
    tokens = set(_canonical_tokens(_tokenize(text)))
    scores = {
        category: len(tokens & _CATEGORY_KEYWORDS[category])
        for category in ("politics", "tech", "economics")
    }
    max_score = max(scores.values(), default=0)
    if max_score <= 0:
        return "other"
    best = [category for category, score in scores.items() if score == max_score]
    if len(best) == 1:
        return best[0]
    for category in ("tech", "economics", "politics"):
        if category in best:
            return category
    return "other"


def _normalize_token(token: str) -> str:
    token = token.lstrip("$")
    if not token:
        return ""
    normalized = _CANONICAL.get(token, token)
    if normalized.endswith("s") and len(normalized) > 3:
        singular = normalized[:-1]
        if singular in _CANONICAL or singular in _CATEGORY_KEYWORDS_FLAT:
            normalized = _CANONICAL.get(singular, singular)
    return normalized


def _keywords_for(text: str) -> set[str]:
    normalized_text = _normalize_text(text)
    tokens = _canonical_tokens(_split_tokens(normalized_text))
    keyword_set: set[str] = set(tokens)
    for number in _extract_numbers(normalized_text):
        if number.is_integer():
            keyword_set.add(str(int(number)))
        else:
            keyword_set.add(f"{number:.6f}".rstrip("0").rstrip("."))
    return keyword_set


def _date_score(left: Any, right: Any) -> float:
    left_date = _get_attr(left, "t_start", None) or _get_attr(left, "start_date", None)
    right_date = _get_attr(right, "t_start", None) or _get_attr(
        right, "start_date", None
    )
    if not isinstance(left_date, datetime) or not isinstance(right_date, datetime):
        return 0.5
    days = abs((left_date.date() - right_date.date()).days)
    if days == 0:
        return 1.0
    if days <= 1:
        return 0.8
    if days <= 3:
        return 0.6
    if days <= 7:
        return 0.4
    return 0.2


def _date_distance_days(left: Any, right: Any) -> Optional[int]:
    left_date = _get_attr(left, "t_start", None) or _get_attr(left, "start_date", None)
    right_date = _get_attr(right, "t_start", None) or _get_attr(
        right, "start_date", None
    )
    if not isinstance(left_date, datetime) or not isinstance(right_date, datetime):
        return None
    return abs((left_date.date() - right_date.date()).days)


def _date_tag(event: Any) -> str:
    date_value = _get_attr(event, "t_start", None) or _get_attr(
        event, "start_date", None
    )
    if isinstance(date_value, datetime):
        return date_value.strftime("%Y-%m-%d")
    return ""


def _closest_by_date(left: Any, candidates: Sequence[Any]) -> Optional[Any]:
    best: Optional[Any] = None
    best_days: Optional[int] = None
    for candidate in candidates:
        days = _date_distance_days(left, candidate)
        if days is None:
            if best is None:
                best = candidate
            continue
        if best_days is None or days < best_days:
            best_days = days
            best = candidate
    return best


def _sports_score(left: Any, right: Any) -> float:
    teams_left = " ".join(_extract_teams(_get_attr(left, "title", "")))
    teams_right = " ".join(_extract_teams(_get_attr(right, "title", "")))
    team_score = fuzz.token_set_ratio(teams_left, teams_right) / 100.0
    return (team_score * 0.75) + (_date_score(left, right) * 0.25)


def _weight_profile(category: str) -> tuple[float, float, float]:
    if category in {"politics", "tech", "economics"}:
        return (0.2, 0.6, 0.2)
    if category == "sports":
        return (0.5, 0.25, 0.25)
    return (0.35, 0.45, 0.2)


@dataclass(frozen=True)
class MatchScore:
    left: Any
    right: Any
    confidence: float
    category: str
    title_score: float
    keyword_score: float
    numeric_score: float


@dataclass(frozen=True)
class MatchDecision:
    left: Any
    right: Any
    confidence: float
    category: str
    matched_by: str
    accepted: bool
    validation: Optional[dict] = None


def score_event_match(left: Any, right: Any) -> MatchScore:
    left_title = _get_attr(left, "title", "")
    right_title = _get_attr(right, "title", "")
    left_desc = _get_attr(left, "description", "")
    right_desc = _get_attr(right, "description", "")

    left_text = f"{left_title} {left_desc}".strip()
    right_text = f"{right_title} {right_desc}".strip()
    left_norm = _normalize_text(left_text)
    right_norm = _normalize_text(right_text)

    left_category = _categorize_text(left_text)
    right_category = _categorize_text(right_text)
    category = left_category if left_category == right_category else "mixed"

    if left_category == "sports" and right_category == "sports":
        confidence = _sports_score(left, right)
        return MatchScore(
            left=left,
            right=right,
            confidence=confidence,
            category="sports",
            title_score=confidence,
            keyword_score=confidence,
            numeric_score=_numeric_score(
                _extract_numbers(left_norm), _extract_numbers(right_norm)
            ),
        )

    left_tokens = _canonical_tokens(_split_tokens(left_norm))
    right_tokens = _canonical_tokens(_split_tokens(right_norm))
    if left_tokens and right_tokens:
        title_score = fuzz.token_set_ratio(
            " ".join(left_tokens), " ".join(right_tokens)
        ) / 100.0
    else:
        title_score = fuzz.token_set_ratio(left_norm, right_norm) / 100.0
    keywords_left = _keywords_for(left_text)
    keywords_right = _keywords_for(right_text)
    overlap = keywords_left & keywords_right
    keyword_score = _overlap_score(keywords_left, keywords_right)
    phrase_score = _overlap_score(
        _phrase_tokens(left_tokens), _phrase_tokens(right_tokens)
    )
    if phrase_score > 0:
        keyword_score = max(keyword_score, phrase_score * 0.9)
    numeric_score = _numeric_score(
        _extract_numbers(left_norm), _extract_numbers(right_norm)
    )

    weight_title, weight_keywords, weight_numbers = _weight_profile(category)
    confidence = (
        (title_score * weight_title)
        + (keyword_score * weight_keywords)
        + (numeric_score * weight_numbers)
    )
    if left_category != right_category:
        confidence *= 0.6
    if category in {"politics", "tech", "economics"} and len(overlap) < 2:
        if phrase_score < 0.2:
            confidence *= 0.75
    if category in {"politics", "tech", "economics"} and keyword_score < 0.2:
        if phrase_score < 0.2:
            confidence *= 0.8
    if (keywords_left & _DIRECTION_POS and keywords_right & _DIRECTION_NEG) or (
        keywords_left & _DIRECTION_NEG and keywords_right & _DIRECTION_POS
    ):
        confidence *= 0.7
    focus_left = keywords_left & _CATEGORY_KEYWORDS_FLAT
    focus_right = keywords_right & _CATEGORY_KEYWORDS_FLAT
    focus_score = _overlap_score(focus_left, focus_right)
    if focus_score > 0:
        confidence = (confidence * 0.9) + (focus_score * 0.1)
    elif category in {"politics", "tech", "economics"}:
        confidence *= 0.85

    return MatchScore(
        left=left,
        right=right,
        confidence=max(0.0, min(1.0, confidence)),
        category=category,
        title_score=title_score,
        keyword_score=keyword_score,
        numeric_score=numeric_score,
    )


def best_match(left: Any, candidates: Iterable[Any]) -> Optional[MatchScore]:
    best_score: Optional[MatchScore] = None
    for candidate in candidates:
        score = score_event_match(left, candidate)
        if best_score is None or score.confidence > best_score.confidence:
            best_score = score
    return best_score


def match_scored(
    left_list: Sequence[Any], right_list: Sequence[Any], min_confidence: float = 0.0
) -> list[MatchScore]:
    results: list[MatchScore] = []
    for left in left_list:
        score = best_match(left, right_list)
        if score and score.confidence >= min_confidence:
            results.append(score)
    return results


def _platform_name(event: Any) -> str:
    value = _get_attr(event, "platform", "")
    return value or "Unknown"


def _llm_confidence_ok(confidence: str, minimum: str) -> bool:
    order = {"low": 0, "medium": 1, "high": 2}
    return order.get(confidence, -1) >= order.get(minimum, 1)


async def decide_match(
    left: Any,
    right: Any,
    min_confidence: float,
    validator: Optional[Any] = None,
    session: Optional[Any] = None,
    llm_min_confidence: str = "medium",
) -> MatchDecision:
    score = score_event_match(left, right)
    if score.confidence >= min_confidence:
        return MatchDecision(
            left=left,
            right=right,
            confidence=score.confidence,
            category=score.category,
            matched_by="keyword",
            accepted=True,
            validation=None,
        )

    if validator is None or session is None:
        return MatchDecision(
            left=left,
            right=right,
            confidence=score.confidence,
            category=score.category,
            matched_by="keyword",
            accepted=False,
            validation=None,
        )

    validation = await validator.validate_events(
        session,
        event1_name=_get_attr(left, "title", ""),
        event1_description=_get_attr(left, "description", ""),
        platform1=_platform_name(left),
        event2_name=_get_attr(right, "title", ""),
        event2_description=_get_attr(right, "description", ""),
        platform2=_platform_name(right),
    )
    accepted = bool(validation.get("are_same")) and _llm_confidence_ok(
        validation.get("confidence", "unknown"), llm_min_confidence
    )
    return MatchDecision(
        left=left,
        right=right,
        confidence=score.confidence,
        category=score.category,
        matched_by="llm",
        accepted=accepted,
        validation=validation,
    )


async def match_with_validation(
    left_list: Sequence[Any],
    right_list: Sequence[Any],
    min_confidence: float,
    validator: Optional[Any] = None,
    session: Optional[Any] = None,
    llm_min_confidence: str = "medium",
) -> list[MatchDecision]:
    results: list[MatchDecision] = []
    used_right: set[int] = set()
    for left in left_list:
        best = best_match(left, right_list)
        if best is None:
            continue
        if id(best.right) in used_right:
            continue
        decision = await decide_match(
            left,
            best.right,
            min_confidence,
            validator=validator,
            session=session,
            llm_min_confidence=llm_min_confidence,
        )
        results.append(decision)
        used_right.add(id(best.right))
    return results


def match(
    pm_list: Sequence[Any], sx_list: Sequence[Any], min_score: int = 87
) -> list[tuple[Any, Any]]:
    pairs: list[tuple[Any, Any]] = []
    sx_index: dict[str, list[Any]] = {}
    for sx in sx_list:
        sx_title = str(_get_attr(sx, "title", "") or "")
        sx_index.setdefault(_normalize(sx_title), []).append(sx)

    for pm in pm_list:
        pm_title = str(_get_attr(pm, "title", "") or "")
        key = _normalize(pm_title)
        if key in sx_index:
            best_same = _closest_by_date(pm, sx_index[key])
            if best_same is not None:
                pairs.append((pm, best_same))
            continue

        pteams = _extract_teams(pm_title)
        pm_date_tag = _date_tag(pm)
        candidates = []
        for sx in sx_list:
            sx_title = str(_get_attr(sx, "title", "") or "")
            sx_date_tag = _date_tag(sx)
            left_text = " ".join(pteams)
            right_text = " ".join(_extract_teams(sx_title))
            if pm_date_tag and sx_date_tag:
                left_text = f"{left_text} {pm_date_tag}"
                right_text = f"{right_text} {sx_date_tag}"
            candidates.append(
                (sx, fuzz.token_set_ratio(right_text.strip(), left_text.strip()))
            )

        # Fix: Check if candidates list is empty to avoid ValueError
        if not candidates:
            continue

        best, score = max(candidates, key=lambda x: x[1])
        if score >= min_score:
            pairs.append((pm, best))
    return pairs
