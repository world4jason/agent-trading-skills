from datetime import date, timedelta

import pytest

from scripts.taiwan_pead import evaluate

_SYMBOL = "2330.TW"


def _week(start, rows, volume=1_500_000):
    first = date.fromisoformat(start)
    return [
        {
            "date": (first + timedelta(days=i)).isoformat(),
            "open": row[0],
            "high": row[1],
            "low": row[2],
            "close": row[3],
            "volume": row[4] if len(row) == 5 else volume,
        }
        for i, row in enumerate(rows)
    ]


def _pattern_bars():
    return (
        _week(
            "2026-06-01",
            [
                (990, 1010, 980, 1000),
                (1050, 1080, 1040, 1070),
                (1070, 1120, 1060, 1100),
                (1100, 1150, 1090, 1130),
                (1130, 1210, 1120, 1200),
            ],
        )
        + _week(
            "2026-06-08",
            [
                (1200, 1230, 1190, 1220),
                (1220, 1260, 1210, 1250),
                (1250, 1280, 1240, 1270),
                (1270, 1310, 1260, 1290),
                (1290, 1320, 1280, 1310),
            ],
        )
        + _week(
            "2026-06-15",
            [
                (1310, 1320, 1290, 1300),
                (1300, 1340, 1280, 1290),
                (1290, 1310, 1240, 1260),
                (1260, 1290, 1200, 1240),
                (1240, 1280, 1220, 1230),
            ],
        )
        + _week(
            "2026-06-22",
            [
                (1230, 1270, 1220, 1260),
                (1260, 1320, 1250, 1290),
                (1290, 1360, 1280, 1330),
                (1330, 1400, 1320, 1380),
                (1380, 1420, 1370, 1410, 1_800_000),
            ],
        )
    )


def _snapshot(as_of, *, fx=True, earnings_date="2026-06-01T20:00:00-04:00"):
    value = {
        "source": "yahoo",
        "symbol": _SYMBOL,
        "as_of": as_of,
        "evaluation_date": as_of,
        "retrieved_at": f"{as_of}T16:00:00+08:00",
        "earnings_dates": [
            {
                "date": earnings_date,
                "EPS Estimate": 6.2,
                "Reported EPS": 6.5,
                "Surprise(%)": 4.84,
            }
        ],
    }
    if fx:
        value["fx_usd_twd"] = {
            "status": "ok",
            "date": as_of,
            "rate": 30.0,
            "source": "yahoo",
            "base_currency": "USD",
            "quote_currency": "TWD",
        }
    return value


def _inputs(*, bar_end="2026-06-26", session_end=None, include_friday=True, fx=True):
    bars = [bar for bar in _pattern_bars() if bar["date"] <= bar_end]
    if not include_friday:
        bars = [bar for bar in bars if bar["date"] != "2026-06-26"]
    cutoff = session_end or bar_end
    sessions = []
    day = date.fromisoformat("2026-06-01")
    while day <= date.fromisoformat(cutoff):
        if day.weekday() < 5 and (include_friday or day.isoformat() != "2026-06-26"):
            sessions.append(day.isoformat())
        day += timedelta(days=1)
    return (
        {"symbol": _SYMBOL, "stock_id": "2330", "kind": "stock"},
        bars,
        [{"symbol": _SYMBOL, "release_date": "2026-06-02", "timing": "bmo"}],
        _snapshot(cutoff, fx=fx),
        sessions,
    )


def test_complete_pattern_scores_breakout_volume_risk_and_usd_liquidity():
    args = _inputs()
    result = evaluate(*args[:2], events=args[2], snapshot=args[3], sessions=args[4])

    assert result["status"] == "evaluated"
    assert result["passed"] is True
    metrics = result["metrics"]
    assert metrics["stage"] == "BREAKOUT"
    assert metrics["earnings_gap_pct"] == 5.0
    assert metrics["setup_score"] == 80.0
    assert metrics["breakout"]["volume_confirmation"] is True
    assert metrics["breakout"]["score"] == 100.0
    assert metrics["risk_reward"]["score"] == 70.0
    assert metrics["liquidity"]["score"] == 85.0
    assert metrics["composite_score"] == 84.2
    assert metrics["red_candle"]["high"] == 1340


def test_partial_week_above_red_high_does_not_count_as_breakout_entry():
    args = list(_inputs(bar_end="2026-06-24"))
    wed = next(bar for bar in args[1] if bar["date"] == "2026-06-24")
    wed.update(open=1330, high=1430, low=1320, close=1410)

    result = evaluate(args[0], args[1], events=args[2], snapshot=args[3], sessions=args[4])

    assert result["status"] == "evaluated"
    assert result["passed"] is False
    assert result["metrics"]["stage"] == "SIGNAL_READY"
    assert result["metrics"]["current_week_partial"] is True


def test_friday_holiday_uses_supplied_sessions_to_complete_short_week():
    args = list(_inputs(include_friday=False))
    result = evaluate(args[0], args[1], events=args[2], snapshot=args[3], sessions=args[4])

    assert result["status"] == "evaluated"
    assert result["passed"] is True
    assert result["metrics"]["current_week_partial"] is False
    assert result["metrics"]["weekly_candles"][0]["trading_days"] == 4


def test_thursday_holiday_needs_calendar_horizon_to_close_week():
    args = list(_inputs(bar_end="2026-06-25", session_end="2026-06-25", include_friday=False))
    args[3]["calendar_complete_through"] = "2026-06-26"
    result = evaluate(args[0], args[1], events=args[2], snapshot=args[3], sessions=args[4])

    assert result["status"] == "evaluated"
    assert result["passed"] is True
    assert result["metrics"]["current_week_partial"] is False


def test_nonfriday_cutoff_without_calendar_horizon_stays_partial():
    args = _inputs(bar_end="2026-06-25", session_end="2026-06-25", include_friday=False)
    result = evaluate(args[0], args[1], events=args[2], snapshot=args[3], sessions=args[4])

    assert result["status"] == "evaluated"
    assert result["passed"] is False
    assert result["metrics"]["current_week_partial"] is True


@pytest.mark.parametrize(
    ("raw_date", "as_of", "prior", "reaction", "timing", "reaction_date"),
    [
        (
            "2026-04-15T20:00:00-04:00",
            "2026-04-16",
            "2026-04-15",
            "2026-04-16",
            "bmo",
            "2026-04-16",
        ),
        (
            "2026-10-15T02:00:00-04:00",
            "2026-10-16",
            "2026-10-15",
            "2026-10-16",
            "amc",
            "2026-10-16",
        ),
    ],
)
def test_yahoo_event_timestamp_is_converted_to_taiwan_time(
    raw_date, as_of, prior, reaction, timing, reaction_date
):
    bars = [
        {"date": prior, "open": 980, "high": 1010, "low": 970, "close": 1000, "volume": 1_000_000},
        {
            "date": reaction,
            "open": 1050,
            "high": 1110,
            "low": 1040,
            "close": 1100,
            "volume": 1_000_000,
        },
    ]
    snapshot = _snapshot(as_of, fx=False, earnings_date=raw_date)
    snapshot["fx_usd_twd"] = {"status": "unavailable", "source": "yahoo"}
    result = evaluate(
        {"symbol": _SYMBOL, "kind": "stock"},
        bars,
        snapshot=snapshot,
        sessions=[prior, reaction],
    )

    assert result["status"] == "evaluated"
    expected_release = prior if timing == "amc" else reaction
    assert result["metrics"]["release_date"] == expected_release
    assert result["metrics"]["earnings_timing"] == timing
    assert result["metrics"]["reaction_date"] == reaction_date
    assert result["metrics"]["earnings_gap_pct"] == 5.0


@pytest.mark.parametrize(
    "record",
    [
        {
            "date": "2027-01-14T00:00:00-05:00",
            "EPS Estimate": 33.14,
            "Reported EPS": None,
            "Surprise(%)": None,
        },
        {
            "date": "2026-06-01T00:00:00-04:00",
            "EPS Estimate": 6.2,
            "Reported EPS": 6.5,
            "Surprise(%)": 4.84,
        },
        {
            "date": "2026-07-16T01:00:00-04:00",
            "EPS Estimate": 24.23,
            "Reported EPS": 27.25,
            "Surprise(%)": 12.48,
        },
    ],
)
def test_future_date_only_and_intraday_yahoo_records_are_not_events(record):
    if record["date"].startswith("2026-07"):
        bars = [
            {
                "date": "2026-07-15",
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100,
                "volume": 1000,
            },
            {
                "date": "2026-07-16",
                "open": 101,
                "high": 102,
                "low": 100,
                "close": 101,
                "volume": 1000,
            },
            {
                "date": "2026-07-17",
                "open": 101,
                "high": 102,
                "low": 100,
                "close": 101,
                "volume": 1000,
            },
        ]
        sessions = [bar["date"] for bar in bars]
        as_of = "2026-07-17"
    else:
        args = _inputs()
        bars, sessions, as_of = args[1], args[4], "2026-06-26"
    snapshot = _snapshot(as_of, fx=False)
    snapshot["earnings_dates"] = [record]

    result = evaluate(
        {"symbol": _SYMBOL, "kind": "stock"}, bars, snapshot=snapshot, sessions=sessions
    )

    assert result["status"] == "insufficient_data"
    assert result["passed"] is None
    assert result["metrics"] == {}


def test_future_event_is_rejected_even_when_snapshot_was_retrieved_later():
    args = list(_inputs())
    args[3]["as_of"] = "2026-06-30"
    args[3]["retrieved_at"] = "2026-07-01T08:00:00+00:00"
    args[3]["earnings_dates"] = [
        {
            "date": "2026-06-29T08:00:00+08:00",
            "EPS Estimate": 7.0,
            "Reported EPS": 7.5,
            "Surprise(%)": 7.14,
        }
    ]
    future = [{"symbol": _SYMBOL, "release_date": "2026-06-29", "timing": "bmo"}]
    result = evaluate(args[0], args[1], events=future, snapshot=args[3], sessions=args[4])

    assert result["status"] == "insufficient_data"
    assert result["passed"] is None
    assert result["metrics"] == {}


def test_fx_unavailable_keeps_twd_liquidity_and_weighted_score_unknown():
    args = list(_inputs(fx=False))
    args[3]["fx_usd_twd"] = {"status": "unavailable", "source": "yahoo"}
    result = evaluate(args[0], args[1], events=args[2], snapshot=args[3], sessions=args[4])

    assert result["status"] == "evaluated"
    assert result["passed"] is True
    assert result["metrics"]["liquidity"]["score"] is None
    assert result["metrics"]["liquidity"]["adv20_twd"] > 0
    assert result["metrics"]["composite_score"] is None


@pytest.mark.parametrize("fx_date", ["2026-06-18", "2026-06-27"])
def test_fx_quote_must_not_be_older_or_newer_than_the_price_cutoff(fx_date):
    args = list(_inputs())
    args[3]["fx_usd_twd"]["date"] = fx_date
    result = evaluate(args[0], args[1], events=args[2], snapshot=args[3], sessions=args[4])

    assert result["status"] == "evaluated"
    assert result["passed"] is True
    assert result["metrics"]["liquidity"]["score"] is None
    assert result["metrics"]["composite_score"] is None


def test_incomplete_20_session_liquidity_window_does_not_produce_full_score():
    bars = [
        {
            "date": "2026-06-25",
            "open": 980,
            "high": 1010,
            "low": 970,
            "close": 1000,
            "volume": 1_000_000,
        },
        {
            "date": "2026-06-26",
            "open": 1050,
            "high": 1080,
            "low": 1040,
            "close": 1060,
            "volume": 1_000_000,
        },
    ]
    result = evaluate(
        {"symbol": _SYMBOL, "kind": "stock"},
        bars,
        events=[{"symbol": _SYMBOL, "release_date": "2026-06-25", "timing": "amc"}],
        snapshot=_snapshot("2026-06-26"),
        sessions=[bar["date"] for bar in bars],
    )

    assert result["status"] == "evaluated"
    assert result["metrics"]["liquidity"]["sample_complete"] is False
    assert result["metrics"]["liquidity"]["score"] is None
    assert result["metrics"]["composite_score"] is None


def test_stale_bars_with_missing_latest_taiwan_session_are_insufficient():
    args = list(_inputs(bar_end="2026-06-25", session_end="2026-06-26"))
    result = evaluate(args[0], args[1], events=args[2], snapshot=args[3], sessions=args[4])

    assert result["status"] == "insufficient_data"
    assert result["passed"] is None
    assert result["metrics"] == {}


def test_price_evaluation_date_is_distinct_from_later_yahoo_snapshot_date():
    args = list(_inputs(bar_end="2026-06-25", session_end="2026-06-26"))
    args[3]["evaluation_date"] = "2026-06-25"
    result = evaluate(args[0], args[1], events=args[2], snapshot=args[3], sessions=args[4])

    assert result["status"] == "evaluated"
    assert result["passed"] is False
    assert result["metrics"]["current_week_partial"] is True


def test_zero_volume_off_session_placeholder_is_ignored_but_traded_off_session_bar_fails():
    args = list(_inputs())
    placeholder = {
        "date": "2026-06-20",
        "open": 1230,
        "high": 1230,
        "low": 1230,
        "close": 1230,
        "volume": 0,
    }
    insert_at = next(i for i, bar in enumerate(args[1]) if bar["date"] == "2026-06-22")
    args[1].insert(insert_at, placeholder)
    accepted = evaluate(args[0], args[1], events=args[2], snapshot=args[3], sessions=args[4])
    placeholder["volume"] = 100
    rejected = evaluate(args[0], args[1], events=args[2], snapshot=args[3], sessions=args[4])

    assert accepted["status"] == "evaluated"
    assert accepted["passed"] is True
    assert rejected["status"] == "insufficient_data"
    assert rejected["passed"] is None


def test_event_symbol_must_match_listing_and_etfs_are_not_applicable():
    args = list(_inputs())
    wrong_symbol = [{"symbol": "2330", "release_date": "2026-06-02", "timing": "bmo"}]
    mismatch = evaluate(args[0], args[1], events=wrong_symbol, sessions=args[4])
    etf = evaluate({"symbol": "0050.TW", "kind": "etf"}, [], sessions=[])

    assert mismatch["status"] == "insufficient_data"
    assert mismatch["passed"] is None
    assert etf == {
        "status": "not_applicable",
        "passed": None,
        "metrics": {},
        "warnings": ["PEAD earnings patterns do not apply to ETFs"],
    }


def test_adv20_includes_zero_volume_trading_sessions():
    from datetime import date, timedelta

    from scripts.taiwan_pead import _liquidity

    days = [date(2026, 6, 1) + timedelta(days=i) for i in range(20)]
    bars = [
        {
            "date": day.isoformat(),
            "open": 300,
            "high": 300,
            "low": 300,
            "close": 300,
            "volume": 3_000_000 if i < 16 else 0,
        }
        for i, day in enumerate(days)
    ]
    result = _liquidity(bars, (days[-1], 30), set(days))
    assert result["sample_complete"] is True
    assert result["adv20_twd"] == 720_000_000
    assert result["adv20_usd"] == 24_000_000
    assert result["avg_volume_20d"] == 2_400_000
    assert result["passes_all"] is False
    assert result["score"] == 40
