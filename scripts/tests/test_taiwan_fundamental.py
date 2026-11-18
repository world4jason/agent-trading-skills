from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from scripts.taiwan_fundamental import BALANCE, STATEMENTS, STRATEGIES, evaluate, required_datasets


def _bars(end="2025-07-31", count=20, close=50.0):
    last = date.fromisoformat(end)
    rows = []
    for offset in range(count - 1, -1, -1):
        day = last - timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        rows.append(
            {
                "date": day.isoformat(),
                "open": close,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": 1000,
            }
        )
    return rows


def _statement(period, eps, revenue):
    year, month, day = period
    stamp = f"{year:04d}-{month:02d}-{day:02d}"
    return [
        {"date": stamp, "type": "EPS", "value": eps},
        {"date": stamp, "type": "Revenue", "value": revenue},
    ]


def _recent_market_inputs(*, stock_step=0.25):
    as_of = datetime.now(ZoneInfo("Asia/Taipei")).date()
    session_days = []
    cursor = as_of
    while len(session_days) < 260:
        if cursor.weekday() < 5:
            session_days.append(cursor)
        cursor -= timedelta(days=1)
    session_days.reverse()

    bars, benchmark = [], []
    previous = None
    for index, day in enumerate(session_days):
        close = 100 + stock_step * index + (0.2 if index % 2 else -0.2)
        volume = 200_000 if previous is None or close > previous else 100_000
        bars.append(
            {
                "date": day.isoformat(),
                "open": previous or close,
                "high": close + 0.25,
                "low": close - 0.25,
                "close": close,
                "volume": volume,
            }
        )
        market_close = 100 + 0.08 * index
        benchmark.append(
            {
                "date": day.isoformat(),
                "open": market_close,
                "high": market_close + 0.1,
                "low": market_close - 0.1,
                "close": market_close,
                "volume": 1_000_000,
            }
        )
        previous = close
    return as_of, bars, benchmark, [day.isoformat() for day in session_days]


def _quarter_end_on_or_before(day):
    for month, last_day in reversed(((3, 31), (6, 30), (9, 30), (12, 31))):
        candidate = date(day.year, month, last_day)
        if candidate <= day:
            return candidate
    return date(day.year - 1, 12, 31)


def _snapshot(as_of, *, currency="TWD", financial_currency="TWD", estimates=None, holders=50):
    annual_income = [
        {
            "date": f"{year}-12-31",
            "Diluted EPS": eps,
            "Basic EPS": eps,
            "Total Revenue": revenue,
            "Net Income": 100.0,
        }
        for year, eps, revenue in (
            (as_of.year - 1, 2.7, 270),
            (as_of.year - 2, 1.9, 190),
            (as_of.year - 3, 1.4, 140),
            (as_of.year - 4, 1.0, 100),
        )
    ]
    return {
        "source": "yahoo",
        "status": "ok",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "as_of": as_of.isoformat(),
        "symbol": "2330.TW",
        "currency": currency,
        "financial_currency": financial_currency,
        "info": {
            "symbol": "2330.TW",
            "currency": currency,
            "financialCurrency": financial_currency,
            "sector": "Technology",
            "heldPercentInstitutions": 0.45,
            "sharesOutstanding": 1_000_000,
            "returnOnEquity": 0.15,
            "payoutRatio": 0.3,
        },
        "annual_income": annual_income,
        "quarterly_income": [],
        "annual_balance": [
            {
                "date": f"{as_of.year - 1}-12-31",
                "Total Debt": 100,
                "Stockholders Equity": 1_000,
                "Current Assets": 500,
                "Current Liabilities": 200,
            }
        ],
        "quarterly_balance": [],
        "annual_cashflow": [
            {
                "date": f"{as_of.year - 1}-12-31",
                "Operating Cash Flow": 200,
                "Capital Expenditure": -50,
                "Free Cash Flow": 150,
                "Cash Dividends Paid": -30,
            }
        ],
        "quarterly_cashflow": [],
        "institutional_holders": [
            {
                "Holder": f"Institution {i}",
                "Shares": 1_000,
                "Date Reported": f"{as_of.year - 1}-09-30",
                "pctHeld": 0.01,
            }
            for i in range(holders)
        ],
        "estimates": estimates or [],
        "dividends": [],
        "splits": [],
        "errors": {},
    }


def _estimates(*, currency="TWD", methodology="gaap"):
    return [
        {
            "period": "0y",
            "avg": 50,
            "low": 45,
            "high": 55,
            "yearAgoEps": 40,
            "growth": 0.25,
            "numberOfAnalysts": 5,
            "currency": currency,
            "methodology": methodology,
        },
        {
            "period": "+1y",
            "avg": 65,
            "low": 58,
            "high": 72,
            "yearAgoEps": 50,
            "growth": 0.3,
            "numberOfAnalysts": 5,
            "currency": currency,
            "methodology": methodology,
        },
    ]


def _finmind_quarters(as_of, *, current_eps=2.25, previous_eps=1.5):
    current = _quarter_end_on_or_before(as_of)
    previous = current.replace(year=current.year - 1)
    return _statement(
        (previous.year, previous.month, previous.day), previous_eps, 200
    ) + _statement((current.year, current.month, current.day), current_eps, 250)


def test_strategy_contract_uses_finmind_dataset_names():
    assert set(STRATEGIES) == {
        "canslim",
        "value-dividend",
        "dividend-growth-pullback",
        "undervalued-growth",
        "pead",
    }
    assert "TaiwanStockFinancialStatements" in required_datasets("canslim")
    assert "TaiwanStockDividend" in required_datasets("value-dividend")
    assert required_datasets("pead") == []


def test_canslim_matches_same_fiscal_quarter_and_keeps_unavailable_letters_unknown():
    statements = []
    for period, eps, revenue in (
        ((2024, 3, 31), 0.8, 80),
        ((2024, 6, 30), 1.0, 100),
        ((2025, 3, 31), 0.9, 90),
        ((2025, 6, 30), 1.2, 110),
    ):
        statements.extend(_statement(period, eps, revenue))

    result = evaluate(
        "canslim",
        {"kind": "stock"},
        _bars(),
        datasets={
            "TaiwanStockFinancialStatements": statements,
        },
    )

    checks = result["metrics"]["checks"]
    assert result["status"] == "insufficient_data"
    assert checks["C"]["status"] == "pass"
    assert result["metrics"]["quarterly_eps_yoy_growth_pct"] == 20.0
    assert result["metrics"]["quarterly_revenue_yoy_growth_pct"] == 10.0
    assert checks["A"]["status"] == "unknown"
    assert checks["I"]["status"] == "unknown"
    assert result["passed"] is None


def test_missing_comparison_quarter_is_insufficient_not_a_pass():
    rows = _statement((2025, 6, 30), 2.0, 200)
    result = evaluate(
        "canslim",
        {"kind": "stock"},
        _bars(),
        datasets={
            "TaiwanStockFinancialStatements": rows,
        },
    )
    assert result["status"] == "insufficient_data"
    assert result["passed"] is None
    assert result["metrics"]["checks"]["C"]["status"] == "unknown"


def test_etf_company_screen_is_not_applicable_and_does_not_invent_eps_or_pe():
    result = evaluate("value-dividend", {"kind": "etf"}, _bars(), datasets={})
    assert result["status"] == "not_applicable"
    assert result["passed"] is None
    assert result["metrics"].get("eps_yoy_growth_pct") is None
    assert result["metrics"].get("pe_ratio") is None


def test_pead_does_not_pass_from_an_initial_gap_without_full_entry_context():
    bars = [
        {"date": "2025-06-02", "open": 99, "high": 101, "low": 98, "close": 100, "volume": 1000},
        {"date": "2025-06-03", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000},
        {"date": "2025-06-04", "open": 110, "high": 112, "low": 109, "close": 111, "volume": 1200},
        {"date": "2025-06-05", "open": 111, "high": 113, "low": 110, "close": 112, "volume": 1000},
        {"date": "2025-06-06", "open": 112, "high": 114, "low": 111, "close": 113, "volume": 1000},
    ]
    result = evaluate(
        "pead",
        {"kind": "stock", "symbol": "2330.TW"},
        bars,
        datasets={},
        events=[
            {"release_date": "2025-06-03", "timing": "amc"},
        ],
        sessions=[bar["date"] for bar in bars],
    )
    assert result["passed"] is not True

    missing_context = evaluate(
        "pead",
        {"kind": "stock"},
        bars,
        datasets={},
        events=[
            {"release_date": "2025-06-03", "timing": "amc"},
        ],
    )
    assert missing_context["status"] == "insufficient_data"
    assert missing_context["passed"] is None

    period_end_only = evaluate(
        "pead",
        {"kind": "stock", "symbol": "2330.TW"},
        bars,
        datasets={},
        events=[
            {"period_end": "2025-06-03"},
        ],
        sessions=[bar["date"] for bar in bars],
    )
    assert period_end_only["status"] == "insufficient_data"
    assert period_end_only["passed"] is None


def test_dividend_ttm_dedup_and_unknown_history():
    from scripts.taiwan_fundamental import _dividends

    rows = [
        {
            "date": f"{year}-06-01",
            "year": str(year),
            "CashExDividendTradingDate": f"{year}-06-01",
            "CashEarningsDistribution": float(year - 2020),
            "CashStatutorySurplus": 0.0,
        }
        for year in (2022, 2023, 2024, 2025)
    ]
    result = _dividends(rows + [rows[-1]], "2025-07-31", 50)
    assert result["cash_dividends_ttm"] == 5
    assert result["cash_yield_pct"] == 10
    assert result["cash_dividend_cagr_3y_pct"] > 30
    assert _dividends(rows[-1:], "2025-07-31", 50)["cash_dividend_cagr_3y_pct"] is None


def test_negative_necessary_condition_rejects_without_fabricating_missing_health():
    result = evaluate(
        "value-dividend",
        {"kind": "stock"},
        _bars(),
        datasets={"TaiwanStockPER": [{"date": "2025-07-31", "PER": 40, "PBR": 1.5}]},
    )
    assert result["passed"] is False
    assert result["metrics"]["checks"]["financial_health"]["status"] == "unknown"


def test_event_is_not_applied_to_other_symbol():
    bars = _bars()
    result = evaluate(
        "pead",
        {"kind": "stock", "symbol": "6488.TWO", "stock_id": "6488"},
        bars,
        datasets={},
        events=[{"symbol": "2330.TW", "release_date": "2025-07-20", "timing": "amc"}],
        sessions=[bar["date"] for bar in bars],
    )
    assert result["passed"] is None


def test_non_finite_financial_values_are_unknown():
    rows = _statement((2024, 6, 30), 1, 100) + _statement((2025, 6, 30), float("inf"), 10**400)
    result = evaluate(
        "canslim", {"kind": "stock"}, _bars(), datasets={"TaiwanStockFinancialStatements": rows}
    )
    assert result["passed"] is None


def test_canslim_full_seven_components_can_pass_and_uses_reported_annual_eps():
    as_of, bars, benchmark, sessions = _recent_market_inputs()
    snapshot = _snapshot(as_of)
    snapshot["institutional_summary"] = {"institutionsCount": len(snapshot["institutional_holders"])}
    result = evaluate(
        "canslim",
        {"kind": "stock", "symbol": "2330.TW"},
        bars,
        datasets={STATEMENTS: _finmind_quarters(as_of)},
        benchmark=benchmark,
        snapshot=snapshot,
        sessions=sessions,
    )

    checks = result["metrics"]["checks"]
    assert result["passed"] is True
    assert set(checks) == {"C", "A", "N", "S", "L", "I", "M"}
    assert all(check["status"] == "pass" for check in checks.values())
    assert result["metrics"]["annual_eps_source"] == "yahoo.annual_income"
    assert result["metrics"]["quarterly_eps_source"] == "finmind"
    assert result["metrics"]["annual_eps_cagr_3y_pct"] > 25
    assert result["metrics"]["canslim_score"] is not None


def test_canslim_known_weak_quarter_fails_instead_of_scoring_unknown():
    as_of, bars, benchmark, sessions = _recent_market_inputs()
    result = evaluate(
        "canslim",
        {"kind": "stock", "symbol": "2330.TW"},
        bars,
        datasets={STATEMENTS: _finmind_quarters(as_of, current_eps=1.0, previous_eps=1.5)},
        benchmark=benchmark,
        snapshot=_snapshot(as_of),
        sessions=sessions,
    )
    assert result["passed"] is False
    assert result["metrics"]["checks"]["C"]["status"] == "fail"


def test_old_splits_do_not_disable_current_quarter_eps_comparison():
    as_of, bars, benchmark, sessions = _recent_market_inputs()
    snapshot = _snapshot(as_of)
    snapshot["splits"] = [{"date": "2010-01-01", "ratio": 2.0}]
    result = evaluate(
        "canslim",
        {"kind": "stock", "symbol": "2330.TW"},
        bars,
        datasets={STATEMENTS: _finmind_quarters(as_of)},
        benchmark=benchmark,
        snapshot=snapshot,
        sessions=sessions,
    )
    assert result["metrics"]["quarterly_eps_comparison_basis_valid"] is True
    assert result["metrics"]["checks"]["C"]["status"] == "pass"


def test_split_inside_finmind_eps_comparison_period_makes_c_unknown():
    as_of, bars, benchmark, sessions = _recent_market_inputs()
    current = _quarter_end_on_or_before(as_of)
    previous = current.replace(year=current.year - 1)
    split = previous + timedelta(days=30)
    snapshot = _snapshot(as_of)
    snapshot["splits"] = [{"date": split.isoformat(), "ratio": 2.0}]
    result = evaluate(
        "canslim",
        {"kind": "stock", "symbol": "2330.TW"},
        bars,
        datasets={STATEMENTS: _finmind_quarters(as_of)},
        benchmark=benchmark,
        snapshot=snapshot,
        sessions=sessions,
    )
    assert result["metrics"]["quarterly_eps_comparison_basis_valid"] is False
    assert result["metrics"]["checks"]["C"]["status"] == "unknown"


def test_current_snapshot_is_rejected_for_historical_price_bars():
    current_as_of, _, benchmark, sessions = _recent_market_inputs()
    result = evaluate(
        "undervalued-growth",
        {"kind": "stock", "symbol": "2330.TW"},
        _bars(end="2025-07-31", count=260),
        datasets={},
        benchmark=benchmark,
        snapshot=_snapshot(current_as_of, estimates=_estimates()),
        sessions=sessions,
    )
    assert result["metrics"]["snapshot_usable"] is False
    assert result["metrics"]["ranking_eligible"] is False
    assert result["metrics"]["checks"]["dated_forward_estimates"]["status"] == "unknown"
    assert any("historical" in warning.lower() for warning in result["warnings"])


def test_future_price_bars_are_rejected_against_snapshot_as_of():
    as_of, bars, benchmark, sessions = _recent_market_inputs()
    future = date.fromisoformat(bars[-1]["date"]) + timedelta(days=1)
    while future.weekday() >= 5:
        future += timedelta(days=1)
    bars[-1] = {**bars[-1], "date": future.isoformat()}
    result = evaluate(
        "undervalued-growth",
        {"kind": "stock", "symbol": "2330.TW"},
        bars,
        datasets={},
        benchmark=benchmark,
        snapshot=_snapshot(as_of, estimates=_estimates()),
        sessions=sessions,
    )
    assert result["metrics"]["snapshot_usable"] is False
    assert result["metrics"]["ranking_eligible"] is False
    assert any("future" in warning.lower() for warning in result["warnings"])


def test_forward_earnings_ranking_requires_comparable_currency_and_methodology():
    as_of, bars, _, sessions = _recent_market_inputs()
    result = evaluate(
        "undervalued-growth",
        {"kind": "stock", "symbol": "2330.TW"},
        bars,
        datasets={},
        snapshot=_snapshot(as_of, estimates=_estimates()),
        sessions=sessions,
    )
    assert result["metrics"]["ranking_eligible"] is True
    assert result["metrics"]["forward_pe"] > 0
    assert result["metrics"]["peg"] > 0
    assert result["metrics"]["ranking_score"] > 0

    mismatch = _snapshot(as_of, estimates=_estimates(currency="USD"))
    rejected = evaluate(
        "undervalued-growth",
        {"kind": "stock", "symbol": "2330.TW"},
        bars,
        datasets={},
        snapshot=mismatch,
        sessions=sessions,
    )
    assert rejected["metrics"]["ranking_eligible"] is False
    assert rejected["metrics"]["ranking_score"] is None
    assert rejected["metrics"]["checks"]["estimate_currency"]["status"] == "fail"


def test_single_yahoo_holder_is_a_lower_bound_not_a_failed_sponsorship_count():
    as_of, bars, benchmark, sessions = _recent_market_inputs()
    result = evaluate(
        "canslim",
        {"kind": "stock", "symbol": "2330.TW"},
        bars,
        datasets={STATEMENTS: _finmind_quarters(as_of)},
        benchmark=benchmark,
        snapshot=_snapshot(as_of, holders=1),
        sessions=sessions,
    )
    assert result["metrics"]["institutional_holders_observed_minimum"] == 1
    assert result["metrics"]["checks"]["I"]["status"] == "unknown"
    assert result["passed"] is None


def test_dividend_health_uses_original_debt_cashflow_payout_and_roe_metrics():
    as_of, bars, _, sessions = _recent_market_inputs()
    snapshot = _snapshot(as_of)
    quarter = _quarter_end_on_or_before(date.fromisoformat(bars[-1]["date"]))
    snapshot["quarterly_balance"] = [
        {
            "date": quarter.isoformat(),
            "Total Debt": 80,
            "Stockholders Equity": 1_000,
            "Current Assets": 400,
            "Current Liabilities": 200,
        }
    ]
    result = evaluate(
        "value-dividend",
        {"kind": "stock", "symbol": "2330.TW"},
        bars,
        datasets={},
        snapshot=snapshot,
        sessions=sessions,
    )
    health = result["metrics"]["financial_health"]
    assert health["debt_to_equity"] == pytest.approx(0.08)
    assert health["current_ratio"] == pytest.approx(2.0)
    assert health["roe_pct"] == pytest.approx(15)
    assert health["fcf"] == pytest.approx(150)
    assert health["payout_ratio_pct"] == pytest.approx(30)
    assert health["roe_quality_score"] == pytest.approx(37.5)
    assert health["balance_source"] == "yahoo.quarterly_balance"
    assert result["metrics"]["checks"]["financial_health"]["status"] == "pass"


def test_known_negative_free_cash_flow_fails_dividend_sustainability():
    as_of, bars, _, sessions = _recent_market_inputs()
    snapshot = _snapshot(as_of)
    snapshot["annual_cashflow"] = [
        {
            "date": f"{as_of.year - 1}-12-31",
            "Operating Cash Flow": 10,
            "Capital Expenditure": -50,
            "Free Cash Flow": -40,
            "Cash Dividends Paid": -30,
        }
    ]
    result = evaluate(
        "value-dividend",
        {"kind": "stock", "symbol": "2330.TW"},
        bars,
        datasets={},
        snapshot=snapshot,
        sessions=sessions,
    )
    assert result["metrics"]["financial_health"]["fcf"] == -40
    assert result["metrics"]["checks"]["dividend_sustainability"]["status"] == "fail"


def test_short_term_borrowings_alone_do_not_stand_in_for_total_debt():
    result = evaluate(
        "value-dividend",
        {"kind": "stock"},
        _bars(),
        datasets={
            BALANCE: [
                {"date": "2025-06-30", "type": "ShortTermBorrowings", "value": 100},
                {"date": "2025-06-30", "type": "TotalEquity", "value": 1_000},
                {"date": "2025-06-30", "type": "CurrentAssets", "value": 500},
                {"date": "2025-06-30", "type": "CurrentLiabilities", "value": 200},
            ]
        },
    )
    assert result["metrics"]["financial_health"]["debt_to_equity"] is None
    assert result["metrics"]["checks"]["financial_health"]["status"] == "unknown"


def test_loss_reduction_does_not_pass_canslim_earnings():
    as_of, bars, benchmark, sessions = _recent_market_inputs()
    for current, previous, expected in (
        (-1, -2, "fail"),
        (0, -2, "fail"),
        (1, -2, "unknown"),
        (1, 0, "unknown"),
    ):
        result = evaluate(
            "canslim",
            {"kind": "stock", "symbol": "2330.TW"},
            bars,
            datasets={
                STATEMENTS: _finmind_quarters(as_of, current_eps=current, previous_eps=previous)
            },
            benchmark=benchmark,
            snapshot=_snapshot(as_of),
            sessions=sessions,
        )
        assert result["metrics"]["checks"]["C"]["status"] == expected
        assert result["passed"] is not True
        assert result["metrics"]["eps_growth"] is None


def test_reported_institution_total_does_not_use_top_holders_list_as_total():
    as_of, bars, benchmark, sessions = _recent_market_inputs()
    snapshot = _snapshot(as_of)
    snapshot["institutional_holders"] = [{"Holder": "Only visible holder"}]
    snapshot["institutional_summary"] = {"institutionsCount": 727.0}
    result = evaluate(
        "canslim",
        {"kind": "stock", "symbol": "2330.TW"},
        bars,
        datasets={STATEMENTS: _finmind_quarters(as_of)},
        benchmark=benchmark,
        snapshot=snapshot,
        sessions=sessions,
    )
    assert result["metrics"]["institutional_holders_reported_total"] == 727
    assert result["metrics"]["checks"]["I"]["status"] == "pass"
    snapshot["institutional_summary"]["institutionsCount"] = 0
    snapshot["institutional_holders"] = []
    snapshot["info"]["heldPercentInstitutions"] = 0
    result = evaluate(
        "canslim",
        {"kind": "stock", "symbol": "2330.TW"},
        bars,
        datasets={STATEMENTS: _finmind_quarters(as_of)},
        benchmark=benchmark,
        snapshot=snapshot,
        sessions=sessions,
    )
    assert result["metrics"]["checks"]["I"]["status"] == "fail"


def test_empty_provider_holder_summary_does_not_crash_canslim():
    as_of, bars, benchmark, sessions = _recent_market_inputs()
    snapshot = _snapshot(as_of)
    snapshot["institutional_summary"] = []
    snapshot["institutional_holders"] = []
    snapshot["info"].pop("heldPercentInstitutions", None)
    result = evaluate(
        "canslim",
        {"kind": "stock", "symbol": "2330.TW"},
        bars,
        datasets={STATEMENTS: _finmind_quarters(as_of)},
        benchmark=benchmark,
        snapshot=snapshot,
        sessions=sessions,
    )
    assert result["metrics"]["checks"]["I"]["status"] == "unknown"


def test_partial_holder_list_cannot_supply_exact_nonmonotonic_score():
    as_of,bars,benchmark,sessions=_recent_market_inputs()
    snapshot=_snapshot(as_of)
    result=evaluate("canslim",{"kind":"stock","symbol":"2330.TW"},bars,datasets={STATEMENTS:_finmind_quarters(as_of)},benchmark=benchmark,snapshot=snapshot,sessions=sessions)
    assert result["metrics"]["checks"]["I"]["status"]=="unknown"
    assert result["metrics"]["canslim_score"] is None
