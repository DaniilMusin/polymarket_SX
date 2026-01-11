import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from aiohttp import ClientSession

import config
from connectors import polymarket, sx, kalshi
from core.event_validator import EventValidator, EventValidationError
from core.exchange_balances import get_balance_manager
from core.matcher import MatchScore, best_match, decide_match
from core.processor import find_arbitrage_opportunity_generic
from core.statistics import get_statistics_collector
from core.trader import execute_arbitrage_trade


_POLYMARKET_MARKETS_URL = "https://gamma-api.polymarket.com/markets"
_KALSHI_MARKETS_URL = f"{config.KALSHI_API_URL}/markets"
_CATEGORY_PRIORITY = {
    "politics": 3,
    "tech": 3,
    "economics": 2,
    "mixed": 1,
    "other": 1,
    "sports": 0,
}


@dataclass(frozen=True)
class MarketEvent:
    platform: str
    market_id: str
    title: str
    description: str
    token_id: Optional[str] = None
    liquidity: float = 0.0
    volume: float = 0.0
    t_start: Optional[datetime] = None
    outcome: str = "yes"


def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
    return None


def _normalize_outcome(value: Any) -> Optional[str]:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"yes", "no"}:
        return normalized
    return None


def _extract_outcome_token_ids(market: dict) -> dict[str, str]:
    token_ids: dict[str, str] = {}
    clob_token_ids = market.get("clobTokenIds") or []
    outcomes = market.get("outcomes") or []

    if isinstance(clob_token_ids, str):
        try:
            clob_token_ids = json.loads(clob_token_ids)
        except json.JSONDecodeError:
            clob_token_ids = []
    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except json.JSONDecodeError:
            outcomes = []

    if clob_token_ids and outcomes and len(clob_token_ids) == len(outcomes):
        for index, outcome in enumerate(outcomes):
            key = _normalize_outcome(outcome)
            if key:
                token_ids[key] = str(clob_token_ids[index])

    tokens = market.get("tokens") or []
    for token in tokens:
        key = _normalize_outcome(token.get("outcome", ""))
        if not key:
            continue
        token_id = token.get("token_id") or token.get("id")
        if token_id:
            token_ids.setdefault(key, str(token_id))

    return token_ids


async def fetch_polymarket_markets(
    session: ClientSession, limit: int, min_liquidity: float
) -> list[MarketEvent]:
    params = {
        "limit": max(1, limit),
        "active": "true",
        "closed": "false",
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "Polymarket-SX/1.0 (+https://github.com)",
    }
    try:
        async with session.get(
            _POLYMARKET_MARKETS_URL, params=params, headers=headers, timeout=30
        ) as r:
            if r.status != 200:
                logging.error("Polymarket markets fetch failed: HTTP %s", r.status)
                return []
            data = await r.json()
    except Exception as exc:
        logging.error("Failed to fetch Polymarket markets: %s", exc)
        return []

    if not isinstance(data, list):
        logging.error("Unexpected Polymarket markets payload: %s", type(data).__name__)
        return []

    market_rows: list[dict] = []
    for market in data:
        if not isinstance(market, dict):
            continue
        liquidity = float(market.get("liquidity", 0) or 0)
        if liquidity < min_liquidity:
            continue
        market_id = market.get("conditionId") or market.get("condition_id") or market.get("id")
        if not market_id:
            continue
        token_ids = _extract_outcome_token_ids(market)
        if not token_ids:
            continue
        title = market.get("question") or market.get("title") or ""
        description = (
            market.get("description")
            or market.get("short_description")
            or market.get("resolution")
            or ""
        )
        start_date = _parse_datetime(
            market.get("startDate")
            or market.get("startDateIso")
            or market.get("start_date")
            or market.get("start_date_iso")
            or market.get("endDate")
            or market.get("endDateIso")
            or market.get("end_date")
            or market.get("end_date_iso")
        )
        market_rows.append(
            {
                "market_id": str(market_id),
                "token_ids": token_ids,
                "title": str(title),
                "description": str(description),
                "liquidity": liquidity,
                "volume": float(market.get("volume", 0) or 0),
                "t_start": start_date,
            }
        )

    market_rows.sort(key=lambda row: row["liquidity"], reverse=True)

    events: list[MarketEvent] = []
    for row in market_rows[:limit]:
        for outcome in ("yes", "no"):
            token_id = row["token_ids"].get(outcome)
            if not token_id:
                continue
            events.append(
                MarketEvent(
                    platform="polymarket",
                    market_id=row["market_id"],
                    token_id=token_id,
                    title=row["title"],
                    description=row["description"],
                    liquidity=row["liquidity"],
                    volume=row["volume"],
                    t_start=row["t_start"],
                    outcome=outcome,
                )
            )

    return events


async def fetch_kalshi_markets(
    session: ClientSession,
    limit: int,
    min_volume: float,
    api_key: Optional[str],
) -> list[MarketEvent]:
    if not api_key:
        logging.warning("KALSHI_API_KEY not set; skipping Kalshi auto-matching.")
        return []

    params = {"limit": max(1, limit), "status": "open"}
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with session.get(
            _KALSHI_MARKETS_URL, params=params, headers=headers, timeout=30
        ) as r:
            if r.status != 200:
                logging.error("Kalshi markets fetch failed: HTTP %s", r.status)
                return []
            data = await r.json()
    except Exception as exc:
        logging.error("Failed to fetch Kalshi markets: %s", exc)
        return []

    markets = data.get("markets") or []
    market_rows: list[dict] = []
    for market in markets:
        if not isinstance(market, dict):
            continue
        market_id = market.get("ticker") or market.get("market_id") or market.get("id")
        if not market_id:
            continue
        volume = float(market.get("volume", 0) or 0)
        open_interest = float(market.get("open_interest", 0) or 0)
        liquidity = max(volume, open_interest)
        if liquidity < min_volume:
            continue
        title = market.get("title") or market.get("event_title") or market_id
        description = (
            market.get("subtitle")
            or market.get("description")
            or market.get("event_title")
            or ""
        )
        start_date = _parse_datetime(
            market.get("close_time")
            or market.get("close_time_ts")
            or market.get("open_time")
            or market.get("open_time_ts")
        )
        market_rows.append(
            {
                "market_id": str(market_id),
                "title": str(title),
                "description": str(description),
                "liquidity": liquidity,
                "volume": volume,
                "t_start": start_date,
            }
        )

    market_rows.sort(key=lambda row: row["liquidity"], reverse=True)

    events: list[MarketEvent] = []
    for row in market_rows[:limit]:
        for outcome in ("yes", "no"):
            events.append(
                MarketEvent(
                    platform="kalshi",
                    market_id=row["market_id"],
                    title=row["title"],
                    description=row["description"],
                    liquidity=row["liquidity"],
                    volume=row["volume"],
                    t_start=row["t_start"],
                    outcome=outcome,
                )
            )

    return events


def load_sx_markets(path: str) -> list[MarketEvent]:
    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path
    if not file_path.exists():
        logging.error("SX markets file not found: %s", file_path)
        return []
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logging.error("Failed to read SX markets file: %s", exc)
        return []

    if isinstance(data, dict):
        items = data.get("markets") or data.get("data") or data.get("results") or []
    elif isinstance(data, list):
        items = data
    else:
        logging.error("Unexpected SX markets format: %s", type(data).__name__)
        return []

    events: list[MarketEvent] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        market_id = (
            item.get("market_id")
            or item.get("marketId")
            or item.get("marketHash")
            or item.get("id")
        )
        if not market_id:
            continue
        title = item.get("title") or item.get("name") or item.get("question") or ""
        description = (
            item.get("description") or item.get("details") or item.get("subtitle") or ""
        )
        start_date = _parse_datetime(
            item.get("start_date")
            or item.get("startDate")
            or item.get("start_time")
            or item.get("event_time")
        )
        raw_outcomes = item.get("outcomes")
        if raw_outcomes is None:
            raw_outcomes = item.get("outcome")

        outcomes: list[str] = []
        if isinstance(raw_outcomes, str):
            normalized = _normalize_outcome(raw_outcomes)
            if normalized:
                outcomes = [normalized]
        elif isinstance(raw_outcomes, list):
            outcomes = [
                normalized
                for normalized in (_normalize_outcome(value) for value in raw_outcomes)
                if normalized
            ]

        if not outcomes:
            outcomes = ["yes", "no"]

        for outcome in outcomes:
            events.append(
                MarketEvent(
                    platform="sx",
                    market_id=str(market_id),
                    title=str(title),
                    description=str(description),
                    liquidity=float(item.get("liquidity", 0) or 0),
                    volume=float(item.get("volume", 0) or 0),
                    t_start=start_date,
                    outcome=outcome,
                )
            )
    return events


def _best_matches(
    left_events: list[MarketEvent],
    right_events: list[MarketEvent],
    min_confidence: float,
) -> list[MatchScore]:
    scores: list[MatchScore] = []
    for left_event in left_events:
        left_outcome = _normalize_outcome(getattr(left_event, "outcome", None))
        candidates = []
        for event in right_events:
            right_outcome = _normalize_outcome(getattr(event, "outcome", None))
            if left_outcome and right_outcome and left_outcome != right_outcome:
                continue
            candidates.append(event)
        if not candidates:
            continue
        score = best_match(left_event, candidates)
        if score and score.confidence >= min_confidence:
            scores.append(score)

    deduped: dict[tuple[str, str], MatchScore] = {}
    for score in scores:
        right_id = getattr(score.right, "market_id", "")
        if not right_id:
            continue
        right_outcome = getattr(score.right, "outcome", "")
        if right_outcome is None:
            right_outcome = ""
        outcome_key = _normalize_outcome(right_outcome) or str(right_outcome).strip().lower()
        key = (right_id, outcome_key)
        current = deduped.get(key)
        if current is None or score.confidence > current.confidence:
            deduped[key] = score
    return list(deduped.values())


def _candidate_sort_key(candidate: dict) -> tuple[float, int, float]:
    opportunity = candidate["opportunity"]
    match_score = candidate["match_score"]
    priority = _CATEGORY_PRIORITY.get(match_score.category, 1)
    return (opportunity["profit_bps"], priority, match_score.confidence)


def _llm_candidate_sort_key(candidate: dict) -> tuple[float, float, int]:
    opportunity = candidate["opportunity"]
    match_score = candidate["match_score"]
    priority = _CATEGORY_PRIORITY.get(match_score.category, 1)
    return (match_score.confidence, opportunity["profit_bps"], priority)


async def _fetch_orderbook(
    session: ClientSession, event: MarketEvent
) -> Optional[dict]:
    if event.platform == "polymarket":
        if not event.token_id:
            return None
        return await polymarket.orderbook_depth(session, event.token_id)
    if event.platform == "sx":
        return await sx.orderbook_depth(session, event.market_id, outcome=event.outcome)
    if event.platform == "kalshi":
        return await kalshi.orderbook_depth(
            session, event.market_id, outcome=event.outcome
        )
    raise ValueError(f"Unknown platform: {event.platform}")


async def _build_candidate(
    session: ClientSession, score: MatchScore
) -> Optional[dict]:
    left_event: MarketEvent = score.left
    right_event: MarketEvent = score.right

    try:
        left_book = await _fetch_orderbook(session, left_event)
        right_book = await _fetch_orderbook(session, right_event)
    except Exception as exc:
        logging.warning(
            "Orderbook fetch failed for %s/%s: %s",
            left_event.market_id,
            right_event.market_id,
            exc,
        )
        return None

    if not left_book or not right_book:
        return None

    opportunity = find_arbitrage_opportunity_generic(
        left_book,
        right_book,
        left_event.platform,
        right_event.platform,
        outcome_a=left_event.outcome,
        outcome_b=right_event.outcome,
        market_a=left_event.market_id,
        market_b=right_event.market_id,
    )
    if not opportunity:
        return None

    pm_event = left_event if left_event.platform == "polymarket" else None
    if pm_event is None and right_event.platform == "polymarket":
        pm_event = right_event

    sx_event = left_event if left_event.platform == "sx" else None
    if sx_event is None and right_event.platform == "sx":
        sx_event = right_event

    kalshi_event = left_event if left_event.platform == "kalshi" else None
    if kalshi_event is None and right_event.platform == "kalshi":
        kalshi_event = right_event

    return {
        "left_event": left_event,
        "right_event": right_event,
        "pm_event": pm_event,
        "sx_event": sx_event,
        "kalshi_event": kalshi_event,
        "match_score": score,
        "opportunity": opportunity,
    }


def _resolve_total_budget(active_exchanges: set[str]) -> float:
    balance_manager = get_balance_manager()
    balances = [
        balance_manager.get_balance(exchange) for exchange in sorted(active_exchanges)
    ]
    if not balances:
        return 0.0
    base_budget = min(balances)
    if config.AUTO_MATCH_TOTAL_BUDGET > 0:
        base_budget = min(base_budget, config.AUTO_MATCH_TOTAL_BUDGET)
    return base_budget


async def run_auto_pipeline(
    session: ClientSession,
    *,
    dry_run: bool,
    pm_api_key: Optional[str] = None,
    sx_api_key: Optional[str] = None,
    kalshi_api_key: Optional[str] = None,
) -> dict:
    stats_collector = get_statistics_collector()
    logging.info("Auto-match pipeline enabled.")

    pm_events = await fetch_polymarket_markets(
        session,
        config.AUTO_MATCH_PM_LIMIT,
        config.AUTO_MATCH_PM_MIN_LIQUIDITY,
    )
    sx_events = load_sx_markets(config.AUTO_MATCH_SX_FILE)
    kalshi_events: list[MarketEvent] = []
    if config.AUTO_MATCH_INCLUDE_KALSHI:
        kalshi_events = await fetch_kalshi_markets(
            session,
            config.AUTO_MATCH_KALSHI_LIMIT,
            config.AUTO_MATCH_KALSHI_MIN_VOLUME,
            kalshi_api_key,
        )

    if not pm_events:
        logging.warning("No Polymarket markets available for auto-matching.")
    if not sx_events:
        logging.warning("No SX markets available for auto-matching.")
    if config.AUTO_MATCH_INCLUDE_KALSHI and not kalshi_events:
        logging.warning("No Kalshi markets available for auto-matching.")

    active_events = {
        "polymarket": pm_events,
        "sx": sx_events,
        "kalshi": kalshi_events,
    }
    active_exchanges = {
        exchange for exchange, events in active_events.items() if events
    }
    if len(active_exchanges) < 2:
        logging.error("Auto-match requires at least two exchanges with markets.")
        return {"status": "insufficient_exchanges"}

    match_scores: list[MatchScore] = []
    pairings = [
        (pm_events, sx_events),
        (pm_events, kalshi_events),
        (sx_events, kalshi_events),
    ]
    for left_events, right_events in pairings:
        if left_events and right_events:
            match_scores.extend(
                _best_matches(
                    left_events,
                    right_events,
                    min_confidence=config.AUTO_MATCH_MIN_CONFIDENCE,
                )
            )
    if not match_scores:
        logging.warning("No candidate matches found.")
        return {"status": "no_matches"}

    candidates: list[dict] = []
    for score in match_scores:
        candidate = await _build_candidate(session, score)
        if candidate:
            candidates.append(candidate)

    if not candidates:
        logging.info("No arbitrage opportunities found for matched events.")
        return {"status": "no_opportunities"}

    candidates.sort(key=_candidate_sort_key, reverse=True)
    candidates = candidates[: config.AUTO_MATCH_MAX_PAIRS]

    total_budget = _resolve_total_budget(active_exchanges)
    if total_budget <= 0:
        logging.warning("Auto-match budget is zero or negative.")
        return {"status": "no_budget"}

    remaining_budget = total_budget
    budget_fraction = max(0.0, min(1.0, config.AUTO_MATCH_BUDGET_FRACTION))
    target_trades = max(1, config.AUTO_MATCH_TARGET_TRADES)
    max_llm_validations = max(0, config.AUTO_MATCH_MAX_LLM_VALIDATIONS)

    executed_trades = 0
    matched_trades = 0
    spent_budget = 0.0
    llm_checks = 0
    validator: Optional[EventValidator] = None

    high_conf_candidates = [
        candidate
        for candidate in candidates
        if candidate["match_score"].confidence >= config.EVENT_MATCH_CONFIDENCE
    ]
    borderline_candidates = [
        candidate
        for candidate in candidates
        if candidate["match_score"].confidence < config.EVENT_MATCH_CONFIDENCE
    ]
    borderline_candidates.sort(key=_llm_candidate_sort_key, reverse=True)

    async def _try_execute(candidate: dict) -> None:
        nonlocal executed_trades, matched_trades, remaining_budget, spent_budget
        if remaining_budget <= 0 or executed_trades >= target_trades:
            return

        pm_event: Optional[MarketEvent] = candidate.get("pm_event")
        sx_event: Optional[MarketEvent] = candidate.get("sx_event")
        kalshi_event: Optional[MarketEvent] = candidate.get("kalshi_event")
        opportunity = candidate["opportunity"]

        matched_trades += 1

        per_trade_budget = remaining_budget * budget_fraction
        per_trade_budget = min(per_trade_budget, remaining_budget)
        cost_per_qty = max(
            opportunity.get("buy_cost_per_qty", 0.0),
            opportunity.get("sell_cost_per_qty", 0.0),
        )
        if cost_per_qty <= 0:
            logging.info("Invalid cost_per_qty for candidate, skipping.")
            return
        budget_qty = per_trade_budget / cost_per_qty
        qty = min(opportunity["qty"], budget_qty)
        if "kalshi" in {opportunity["buy_exchange"], opportunity["sell_exchange"]}:
            qty = float(int(qty))
            if qty < 1:
                logging.info("Kalshi trade qty below 1 contract, skipping.")
                return
        if qty < 0.01:
            logging.info("Trade qty too small (%.4f), skipping.", qty)
            return

        trade_opportunity = dict(opportunity)
        if pm_event:
            trade_opportunity["pm_outcome"] = pm_event.outcome
            if pm_event.token_id:
                trade_opportunity["pm_token_id"] = pm_event.token_id
        trade_opportunity["position_size"] = qty
        trade_opportunity["qty"] = qty
        trade_opportunity["buy_notional"] = qty * trade_opportunity["buy_cost_per_qty"]
        trade_opportunity["sell_notional"] = qty * trade_opportunity["sell_cost_per_qty"]
        trade_opportunity["expected_pnl"] = trade_opportunity["profit"] * qty

        try:
            result = await execute_arbitrage_trade(
                session,
                trade_opportunity,
                pm_event.market_id if pm_event else None,
                sx_event.market_id if sx_event else None,
                pm_token_id=pm_event.token_id if pm_event else None,
                dry_run=dry_run,
                pm_api_key=pm_api_key,
                sx_api_key=sx_api_key,
                kalshi_market_id=kalshi_event.market_id if kalshi_event else None,
                kalshi_api_key=kalshi_api_key,
                kalshi_side=config.KALSHI_CONTRACT_SIDE,
            )
            executed = result.get("status") not in ["failed"]
            actual_pnl = result.get("actual_pnl")
            stats_collector.log_opportunity(
                trade_opportunity, executed=executed, actual_pnl=actual_pnl
            )
            if executed:
                executed_trades += 1
                trade_notional = qty * cost_per_qty
                remaining_budget -= trade_notional
                spent_budget += trade_notional
        except Exception as exc:
            logging.error("Trade execution failed: %s", exc)
            stats_collector.log_opportunity(
                trade_opportunity, executed=False, execution_error=str(exc)
            )

    for candidate in high_conf_candidates:
        if remaining_budget <= 0 or executed_trades >= target_trades:
            break
        await _try_execute(candidate)

    if (
        executed_trades < target_trades
        and remaining_budget > 0
        and borderline_candidates
        and max_llm_validations > 0
    ):
        validator = EventValidator()
        for candidate in borderline_candidates:
            if remaining_budget <= 0 or executed_trades >= target_trades:
                break
            if llm_checks >= max_llm_validations:
                break

            match_score: MatchScore = candidate["match_score"]
            left_event: MarketEvent = candidate["left_event"]
            right_event: MarketEvent = candidate["right_event"]

            llm_checks += 1
            try:
                decision = await decide_match(
                    left_event,
                    right_event,
                    config.EVENT_MATCH_CONFIDENCE,
                    validator=validator,
                    session=session,
                    llm_min_confidence=config.EVENT_LLM_CONFIDENCE,
                )
            except EventValidationError as exc:
                logging.warning(
                    "LLM validation failed for %s/%s: %s",
                    left_event.market_id,
                    right_event.market_id,
                    exc,
                )
                continue
            if not decision.accepted:
                logging.info(
                    "Match rejected (confidence %.2f, category %s).",
                    match_score.confidence,
                    match_score.category,
                )
                continue

            await _try_execute(candidate)

    return {
        "status": "ok",
        "candidates": len(candidates),
        "matched": matched_trades,
        "executed": executed_trades,
        "spent_budget": spent_budget,
        "remaining_budget": remaining_budget,
    }
