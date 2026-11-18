"""Taiwan PEAD weekly-pattern and entry scoring."""

from __future__ import annotations

import math
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

_PEAD_SCRIPTS = str(Path(__file__).resolve().parents[1] / "skills" / "pead-screener" / "scripts")
if _PEAD_SCRIPTS not in sys.path:
    sys.path.insert(0, _PEAD_SCRIPTS)

from calculators.breakout_calculator import calculate_breakout
from calculators.liquidity_calculator import calculate_liquidity
from calculators.risk_reward_calculator import calculate_risk_reward
from calculators.weekly_candle_calculator import analyze_weekly_pattern
from scorer import calculate_composite_score

_TAIPEI = ZoneInfo("Asia/Taipei")


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _date(value):
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _timestamp(value):
    if not isinstance(value, str) or "T" not in value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None


def _snapshot_as_of(snapshot, default):
    if snapshot is None:
        return default, None
    if not isinstance(snapshot, dict) or snapshot.get("source") != "yahoo":
        return None, "Yahoo snapshot source is missing or invalid"
    source_as_of = _date(snapshot.get("as_of"))
    if source_as_of is None:
        stamp = _timestamp(snapshot.get("as_of"))
        source_as_of = stamp.astimezone(_TAIPEI).date() if stamp else None
    requested = snapshot.get("evaluation_date")
    evaluation_date = _date(requested) if requested is not None else default
    if requested is not None and evaluation_date is None:
        stamp = _timestamp(requested)
        evaluation_date = stamp.astimezone(_TAIPEI).date() if stamp else None
    if source_as_of is None or _timestamp(snapshot.get("retrieved_at")) is None:
        return None, "Yahoo snapshot needs a valid as_of date and timezone-aware retrieved_at"
    if evaluation_date is None or evaluation_date > source_as_of:
        return None, "evaluation_date must be on or before the Yahoo snapshot as_of date"
    return evaluation_date, None


def _valid_bars(listing, bars, sessions, as_of):
    if not isinstance(listing, dict) or not isinstance(listing.get("symbol"), str):
        return None, None, "Listing symbol is missing"
    if not isinstance(bars, list) or not bars:
        return None, None, "No price bars"
    session_dates = {_date(value) for value in sessions} if isinstance(sessions, list) else set()
    session_dates.discard(None)
    if not session_dates:
        return None, None, "Taiwan session dates are missing"
    parsed_bars, input_dates, bar_dates = [], set(), set()
    last_day = None
    for bar in bars:
        if not isinstance(bar, dict):
            return None, None, "Price bars must be canonical OHLCV records"
        day = _date(bar.get("date"))
        values = {key: _number(bar.get(key)) for key in ("open", "high", "low", "close", "volume")}
        if day is None or any(value is None for value in values.values()):
            return None, None, "Price bars contain an invalid date or non-finite OHLCV value"
        if day in input_dates or (last_day is not None and day <= last_day):
            return None, None, "Price bars must be unique and chronological"
        input_dates.add(day)
        last_day = day
        if min(values["open"], values["high"], values["low"], values["close"]) <= 0:
            return None, None, "OHLC prices must be positive"
        if values["volume"] < 0 or values["high"] < max(values["open"], values["close"]):
            return None, None, "OHLCV values are inconsistent"
        if values["low"] > min(values["open"], values["close"]):
            return None, None, "OHLCV values are inconsistent"
        if day not in session_dates:
            if (
                values["volume"] == 0
                and len({values[key] for key in ("open", "high", "low", "close")}) == 1
            ):
                continue
            return None, None, "A traded price bar falls outside the supplied Taiwan sessions"
        normalized = dict(bar)
        normalized.update(values)
        parsed_bars.append(normalized)
        bar_dates.add(day)
    last_day = max(bar_dates, default=None)
    if last_day is None:
        return None, None, "No price bars match the supplied Taiwan sessions"
    if as_of is None or last_day > as_of:
        return None, None, "Price bars fall after the snapshot as_of date"
    latest_session = max((day for day in session_dates if day <= as_of), default=None)
    if latest_session != last_day:
        return None, None, "Price bars are stale relative to the supplied Taiwan sessions"
    return parsed_bars, session_dates, None


def _event_from_yahoo(listing, snapshot, as_of):
    if not isinstance(snapshot, dict) or snapshot.get("source") != "yahoo":
        return None
    if snapshot.get("symbol") != listing.get("symbol"):
        return None
    records = snapshot.get("earnings_dates")
    if not isinstance(records, list):
        return None
    found = []
    for row in records:
        if not isinstance(row, dict) or _number(row.get("Reported EPS")) is None:
            continue
        stamp = _timestamp(row.get("date"))
        if stamp is None or stamp.timetz().replace(tzinfo=None) == time(0):
            continue
        local = stamp.astimezone(ZoneInfo(listing.get("timezone", "Asia/Taipei")))
        if local.date() > as_of:
            continue
        clock = local.time().replace(tzinfo=None)
        us = listing.get("market") == "us"
        opening, closing = (time(9, 30), time(16)) if us else (time(9), time(13, 30))
        session_close = snapshot.get("session_closes", {}).get(local.date().isoformat())
        if us and session_close:
            closing = time.fromisoformat(session_close)
        timing = "bmo" if clock < opening else "amc" if clock >= closing else None
        if timing is None:
            continue
        found.append(
            {
                "symbol": listing["symbol"],
                "release_date": local.date().isoformat(),
                "timing": timing,
                "reported_eps": _number(row.get("Reported EPS")),
                "eps_estimate": _number(row.get("EPS Estimate")),
                "surprise_pct": _number(row.get("Surprise(%)")),
            }
        )
    return max(found, key=lambda item: item["release_date"]) if found else None


def _resolve_event(listing, events, snapshot, as_of):
    symbol = listing["symbol"].strip().upper()
    found = []
    for row in events if isinstance(events, list) else []:
        if not isinstance(row, dict) or str(row.get("symbol", "")).strip().upper() != symbol:
            continue
        release_date = _date(row.get("release_date"))
        timing = row.get("timing")
        if release_date and release_date <= as_of and timing in ("bmo", "amc"):
            found.append(
                {"symbol": symbol, "release_date": release_date.isoformat(), "timing": timing}
            )
    if found:
        return max(found, key=lambda item: item["release_date"])
    return _event_from_yahoo(listing, snapshot, as_of)


def _fx(snapshot, bars_end):
    fx = snapshot.get("fx_usd_twd") if isinstance(snapshot, dict) else None
    if not isinstance(fx, dict) or fx.get("status") != "ok":
        return None
    fx_date = _date(fx.get("date"))
    rate = _number(fx.get("rate"))
    if (
        fx.get("source") != "yahoo"
        or fx.get("base_currency") != "USD"
        or fx.get("quote_currency") != "TWD"
        or fx_date is None
        or fx_date > bars_end
        or (bars_end - fx_date).days > 7
        or rate is None
        or rate <= 0
    ):
        return None
    return fx_date, rate


def _reaction_dates(event, sessions):
    release = date.fromisoformat(event["release_date"])
    days = sorted(sessions)
    if event["timing"] == "bmo":
        later = [day for day in days if day >= release]
        reaction = later[0] if later else None
        before = [day for day in days if reaction is not None and day < reaction]
        base = before[-1] if before else None
    else:
        before = [day for day in days if day <= release]
        later = [day for day in days if day > release]
        base = before[-1] if before else None
        reaction = later[0] if later else None
    return base, reaction


def _weekly_candles(bars, sessions, as_of, event_anchor, calendar_complete_through=None):
    by_day = {date.fromisoformat(bar["date"]): bar for bar in bars}
    grouped = defaultdict(list)
    for day in sessions:
        grouped[day.isocalendar()[:2]].append(day)
    anchor_week = event_anchor.isocalendar()[:2]
    as_of_week = as_of.isocalendar()[:2]
    week_friday = as_of + timedelta(days=4 - as_of.weekday())
    calendar_proves_week_end = (
        calendar_complete_through is not None and calendar_complete_through >= week_friday
    )
    current_expected = grouped.get(as_of_week, [])
    current_observed = [day for day in current_expected if day in by_day and day <= as_of]
    current_closed = as_of.weekday() >= 4 or calendar_proves_week_end
    current_partial = not (current_closed and len(current_observed) == len(current_expected))
    candles = []
    signal_candles = []
    for key in sorted(grouped):
        expected = sorted(grouped[key])
        used = [day for day in expected if key != anchor_week or day >= event_anchor]
        values = [by_day[day] for day in used if day in by_day and day <= as_of]
        if not values:
            continue
        calendar_closed = key < as_of_week or (key == as_of_week and current_closed)
        data_complete = len(values) == len(used)
        event_split = key == anchor_week and len(used) < len(expected)
        complete = calendar_closed and data_complete
        partial = not complete or event_split
        monday = date.fromisocalendar(key[0], key[1], 1)
        candle = {
            "week_start": monday.isoformat(),
            "year": key[0],
            "week": key[1],
            "open": round(values[0]["open"], 2),
            "high": round(max(bar["high"] for bar in values), 2),
            "low": round(min(bar["low"] for bar in values), 2),
            "close": round(values[-1]["close"], 2),
            "volume": sum(bar["volume"] for bar in values),
            "is_green": values[-1]["close"] >= values[0]["open"],
            "partial_week": partial,
            "trading_days": len(values),
        }
        candles.append((key, candle, complete))
        if complete or key == anchor_week:
            signal_candles.append(candle)
    candles.reverse()
    signal_candles.reverse()
    return [item[1] for item in candles], signal_candles, current_partial


def _setup_score(gap_pct, pattern):
    score = (
        50
        if gap_pct >= 10
        else 40
        if gap_pct >= 7
        else 30
        if gap_pct >= 5
        else 20
        if gap_pct >= 3
        else 10
    )
    stage = pattern.get("stage", "MONITORING")
    if stage == "BREAKOUT":
        score += 50
    elif stage == "SIGNAL_READY":
        score += 40
        red = pattern.get("red_candle") or {}
        if red.get("lower_wick_pct", 0) > 30:
            score += 5
    elif stage == "MONITORING":
        score += 25 if pattern.get("weeks_since_earnings", 0) <= 2 else 15
    return min(100.0, float(score))


def _liquidity(bars, fx, sessions, currency="TWD"):
    bar_end = date.fromisoformat(bars[-1]["date"])
    expected = sorted(day for day in sessions if day <= bar_end)[-20:]
    expected_set = set(expected)
    recent = [bar for bar in bars if date.fromisoformat(bar["date"]) in expected_set]
    sample_complete = len(expected) == 20 and len(recent) == 20
    value_rows = [bar for bar in recent if bar["volume"] >= 0 and bar["close"] > 0]
    adv_twd = (
        sum(bar["volume"] * bar["close"] for bar in value_rows) / len(value_rows)
        if value_rows
        else None
    )
    average_volume = sum(bar["volume"] for bar in recent) / len(recent) if recent else None
    result = {
        "adv20_twd": round(adv_twd, 2) if adv_twd is not None else None,
        "adv20_usd": None,
        "avg_volume_20d": round(average_volume, 0) if average_volume is not None else None,
        "sessions_used": len(recent),
        "sample_complete": sample_complete,
        "price_twd": bars[-1]["close"],
        "fx_date": None,
        "fx_rate_twd_per_usd": None,
        "price_usd": None,
        "passes_all": None,
        "score": None,
        "score_reason": None,
    }
    result["currency"] = currency
    if currency == "USD":
        result.update(adv20_twd=None, price_twd=None)
    if fx is None and currency != "USD":
        result["score_reason"] = "Valid dated Yahoo TWD/USD rate unavailable"
        return result
    fx_date, rate = (bar_end, 1.0) if currency == "USD" else fx
    result.update(
        price_usd=round(bars[-1]["close"] / rate, 4),
        fx_date=fx_date.isoformat() if currency != "USD" else None,
        fx_rate_twd_per_usd=rate if currency != "USD" else None,
    )
    if not sample_complete:
        result["score_reason"] = "Complete 20-session liquidity sample unavailable"
        return result
    usd_bars = [
        {**bar, **{key: bar[key] / rate for key in ("open", "high", "low", "close")}}
        for bar in recent
    ]
    scored = calculate_liquidity(usd_bars, bars[-1]["close"] / rate)
    result.update(
        adv20_usd=scored["adv20_dollar"],
        avg_volume_20d=scored["avg_volume_20d"],
        score_reason=None,
        passes_all=scored["passes_all"],
        score=scored["score"],
    )
    return result


def _insufficient(warning):
    return {"status": "insufficient_data", "passed": None, "metrics": {}, "warnings": [warning]}


def evaluate(listing, bars, events=None, snapshot=None, sessions=None):
    """Evaluate an earnings gap, completed Taiwan weekly pattern, and entry score."""
    if isinstance(listing, dict) and str(listing.get("kind", "")).lower() == "etf":
        return {
            "status": "not_applicable",
            "passed": None,
            "metrics": {},
            "warnings": ["PEAD earnings patterns do not apply to ETFs"],
        }
    if not isinstance(listing, dict) or not isinstance(listing.get("symbol"), str):
        return _insufficient("Listing symbol is missing")
    if not isinstance(bars, list) or not bars:
        return _insufficient("No price bars")
    default_as_of = _date(bars[-1].get("date")) if isinstance(bars[-1], dict) else None
    as_of, error = _snapshot_as_of(snapshot, default_as_of)
    if error:
        return _insufficient(error)
    if isinstance(snapshot, dict) and snapshot.get("symbol") not in (None, listing.get("symbol")):
        return _insufficient("Yahoo snapshot symbol does not match the listing")
    parsed_bars, session_dates, error = _valid_bars(listing, bars, sessions, as_of)
    if error:
        return _insufficient(error)
    event = _resolve_event(listing, events, snapshot, as_of)
    if event is None:
        return _insufficient(
            "No matching completed earnings event with a known Taiwan release time"
        )
    bar_days = {date.fromisoformat(bar["date"]) for bar in parsed_bars}
    base_day, reaction_day = _reaction_dates(event, session_dates)
    by_day = {date.fromisoformat(bar["date"]): bar for bar in parsed_bars}
    if (
        base_day is None
        or reaction_day is None
        or base_day not in by_day
        or reaction_day not in by_day
    ):
        return _insufficient("Need the prior session close and first post-event session open")
    bar_end = date.fromisoformat(parsed_bars[-1]["date"])
    if any(base_day <= day <= bar_end and day not in bar_days for day in session_dates):
        return _insufficient("Price bars are missing one or more Taiwan sessions around the event")
    base_close = by_day[base_day]["close"]
    if base_close <= 0:
        return _insufficient("Prior-session close is invalid")
    gap_pct = (by_day[reaction_day]["open"] / base_close - 1) * 100
    release = date.fromisoformat(event["release_date"])
    anchor = release if release in session_dates else reaction_day
    calendar_complete_through = (
        _date(snapshot.get("calendar_complete_through")) if isinstance(snapshot, dict) else None
    )
    weekly, signal_weeks, current_partial = _weekly_candles(
        parsed_bars, session_dates, as_of, anchor, calendar_complete_through
    )
    if signal_weeks:
        pattern = analyze_weekly_pattern(signal_weeks, anchor.isoformat())
    else:
        pattern = {
            "weeks_since_earnings": 0,
            "earnings_week_idx": None,
            "red_candle": None,
            "is_breakout": False,
            "breakout_pct": 0.0,
            "stage": "MONITORING",
        }
    red = pattern.get("red_candle")
    current_price = signal_weeks[0]["close"] if signal_weeks else parsed_bars[-1]["close"]
    breakout = (
        calculate_breakout(signal_weeks, red, current_price)
        if red
        else {
            "is_breakout": False,
            "breakout_pct": 0.0,
            "volume_confirmation": False,
            "score": 0.0,
        }
    )
    risk_reward = calculate_risk_reward(current_price, red)
    setup_score = _setup_score(gap_pct, pattern)
    liquidity = _liquidity(
        parsed_bars, _fx(snapshot, bar_end), session_dates, listing.get("currency", "TWD")
    )
    composite = None
    if liquidity["score"] is not None:
        composite = calculate_composite_score(
            setup_score=setup_score,
            breakout_score=breakout["score"],
            liquidity_score=liquidity["score"],
            rr_score=risk_reward["score"],
        )
    passed = gap_pct >= 3 and pattern.get("stage") == "BREAKOUT"
    metrics = {
        "release_date": event["release_date"],
        "earnings_timing": event["timing"],
        "reaction_date": reaction_day.isoformat(),
        "earnings_gap_pct": round(gap_pct, 2),
        "weeks_since_earnings": pattern["weeks_since_earnings"],
        "stage": pattern["stage"],
        "red_candle": red,
        "current_week_partial": current_partial,
        "weekly_candles": weekly,
        "setup_score": setup_score,
        "breakout": breakout,
        "risk_reward": risk_reward,
        "liquidity": liquidity,
        "component_scores": {
            "setup_quality": setup_score,
            "breakout_strength": breakout["score"],
            "liquidity": liquidity["score"],
            "risk_reward": risk_reward["score"],
        },
        "composite_score": composite["composite_score"] if composite else None,
        "rating": composite["rating"] if composite else None,
        "score_completeness": "full" if composite else "partial",
    }
    warnings = (
        []
        if composite
        else [f"USD liquidity score and weighted total are unknown: {liquidity['score_reason']}"]
    )
    if current_partial:
        warnings.append(
            "The current Taiwan weekly candle is incomplete; only completed weeks are used for entry confirmation"
        )
    return {"status": "evaluated", "passed": bool(passed), "metrics": metrics, "warnings": warnings}
