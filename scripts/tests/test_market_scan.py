import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from market_report import candidate, gaps
from market_universe import taiwan_rows, us_rows
from taiwan_fundamental import _annual_metrics
from taiwan_pead import _event_from_yahoo, _liquidity


def test_us_directory_keeps_preferred_stock_etf_but_excludes_preferred_security():
    source = "Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\n"
    source += "PREF|Preferred Stock ETF|G|N|N|100|Y|N\n"
    source += "PRA|Company Preferred Stock|G|N|N|100|N|N\n"
    source += "BRK.B|Company Common Stock|G|N|N|100|N|N\n"
    source += "TEST|Test Common Stock|G|Y|N|100|N|N\n"
    source += "File Creation Time: 1117202621:31|||||||\n"
    rows, excluded, stamp = us_rows(source, "nasdaq")
    assert [r["symbol"] for r in rows] == ["PREF", "BRK-B"]
    assert rows[0]["kind"] == "etf" and rows[1]["currency"] == "USD"
    assert len(excluded) == 2 and stamp == "1117202621:31"


def test_taiwan_current_directory_section_excludes_warrants():
    source = "<table><tr><td>股票</td></tr><tr><td>2330　台積電</td><td>ISIN</td><td>1994/09/05</td><td>上市</td><td>半導體</td><td>ESVUFR</td><td></td></tr><tr><td>上市認購權證</td></tr><tr><td>123456　權證</td><td>ISIN</td><td>2026/01/01</td><td>上市</td><td></td><td>RWSCCA</td><td></td></tr></table>"
    assert [r["symbol"] for r in taiwan_rows(source, "twse")] == ["2330.TW"]


def test_non_december_fiscal_years_are_usable():
    snapshot = {
        "annual_income": [
            {"date": f"{year}-09-30", "Diluted EPS": eps, "Total Revenue": eps * 1000}
            for year, eps in [(2026, 4), (2025, 3), (2024, 2), (2023, 1)]
        ]
    }
    m = _annual_metrics([], snapshot, "2026-11-17", "auto", True)
    assert m["annual_eps_source"] == "yahoo.annual_income"
    assert m["annual_eps_values"] == [1, 2, 3, 4]
    assert m["annual_eps_period_start"] == "2023-09-30"
    assert m["annual_eps_period_end"] == "2026-09-30"


def test_us_pead_uses_eastern_market_hours_and_half_day_close():
    listing = {"symbol": "AAPL", "market": "us", "timezone": "America/New_York"}
    snapshot = {
        "source": "yahoo",
        "symbol": "AAPL",
        "earnings_dates": [{"date": "2026-11-17T18:00:00+00:00", "Reported EPS": 2}],
    }
    assert _event_from_yahoo(listing, snapshot, date(2026, 11, 17)) is None
    snapshot["earnings_dates"][0]["date"] = "2026-11-17T21:05:00+00:00"
    assert _event_from_yahoo(listing, snapshot, date(2026, 11, 17))["timing"] == "amc"
    snapshot["earnings_dates"][0]["date"] = "2026-11-27T18:05:00+00:00"
    snapshot["session_closes"] = {"2026-11-27": "13:00"}
    assert _event_from_yahoo(listing, snapshot, date(2026, 11, 27))["timing"] == "amc"


def test_us_liquidity_needs_no_currency_conversion():
    days = [date(2026, 10, 1) + timedelta(days=i) for i in range(20)]
    bars = [
        {"date": d.isoformat(), "open": 30, "high": 30, "low": 30, "close": 30, "volume": 1_000_000}
        for d in days
    ]
    result = _liquidity(bars, None, set(days), currency="USD")
    assert result["adv20_usd"] == 30_000_000 and result["passes_all"] is True
    assert result["adv20_twd"] is None and result["fx_rate_twd_per_usd"] is None


def test_partial_entry_score_never_becomes_complete_candidate():
    row = {
        "strategy": "pead",
        "status": "evaluated",
        "passed": True,
        "metrics": {"score_completeness": "partial"},
    }
    assert gaps(row) and candidate(row) is False
    row["metrics"]["score_completeness"] = "full"
    assert candidate(row) is True


def test_revenue_growth_survives_missing_eps_and_fiscal_week_dates():
    from taiwan_fundamental import _yahoo_quarter_rows

    result = _yahoo_quarter_rows(
        [
            {"date": "2026-10-03", "Diluted EPS": None, "Total Revenue": 120},
            {"date": "2025-09-27", "Diluted EPS": 2, "Total Revenue": 100},
        ]
    )
    assert result["eps_growth"] is None
    assert abs(result["revenue_growth"] - 20) < 1e-9
    assert result["comparison_period"] == "2025-09-27"


def test_yahoo_fractional_ratios_above_one_are_not_relabelled_as_percent():
    from taiwan_fundamental import _health, _ownership_pct

    snapshot = {"info": {"returnOnEquity": 1.5, "payoutRatio": 1.2, "heldPercentInstitutions": 1.1}}
    metrics, _, _ = _health(snapshot, {}, "2026-11-17", True, "auto", "Technology")
    assert metrics["roe_pct"] == 150
    assert metrics["payout_ratio_pct"] == 120
    assert abs(_ownership_pct(snapshot) - 110) < 1e-9


def test_official_non_etf_equities_need_no_name_keyword():
    source = "ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\nAAP|Advance Auto Parts Inc.|N|AAP|N|100|N|AAP\nACEL|Accel Entertainment, Inc.|N|ACEL|N|100|N|ACEL\nFile Creation Time: 1117202621:31|||||||\n"
    rows, excluded, _ = us_rows(source, "other")
    assert [r["symbol"] for r in rows] == ["AAP", "ACEL"] and excluded == []


def test_worker_error_overrides_old_complete_candidate(tmp_path):
    from market_report import build
    from market_scan import save

    listing = {
        "symbol": "AAPL",
        "name": "Apple",
        "market": "us",
        "exchange": "nasdaq",
        "kind": "stock",
        "currency": "USD",
    }
    save(tmp_path / "universe.json", {"listings": [listing], "excluded": []})
    save(tmp_path / "run.json", {"start": "2025-01-01", "end": "2026-11-17", "strategies": ["vcp"]})
    save(
        tmp_path / "results/AAPL.json.gz",
        [
            {
                **listing,
                "strategy": "vcp",
                "status": "evaluated",
                "passed": True,
                "metrics": {},
                "warnings": [],
            }
        ],
    )
    save(tmp_path / "errors/AAPL.json", {"worker_error": "ValueError"})
    summary = build(tmp_path)
    assert summary["processed_symbols"] == 0
    assert summary["strategy_results"]["us"]["vcp"]["qualified"] == 0
    assert "Worker error" in (tmp_path / "missing-data.csv").read_text()


def test_bulk_chart_validates_identity_currency_and_preserves_action_dates(monkeypatch):
    from datetime import datetime, timezone
    from types import SimpleNamespace

    import pytest
    import yfinance as yf
    from market_scan import chart_prices
    from taiwan_data import DataError

    stamp = int(datetime(2026, 11, 17, 14, 30, tzinfo=timezone.utc).timestamp())
    chart = {
        "meta": {"symbol": "AAPL", "currency": "USD", "instrumentType": "EQUITY"},
        "timestamp": [stamp],
        "indicators": {
            "quote": [{"open": [10], "high": [11], "low": [9], "close": [10.5], "volume": [100]}]
        },
        "events": {
            "dividends": {"x": {"date": stamp, "amount": 0.2}},
            "splits": {"x": {"date": stamp, "numerator": 2, "denominator": 1}},
        },
    }
    monkeypatch.setattr(
        yf,
        "Ticker",
        lambda _: SimpleNamespace(
            _data=SimpleNamespace(get_raw_json=lambda *a, **k: {"chart": {"result": [chart]}})
        ),
    )
    listing = {
        "symbol": "AAPL",
        "stock_id": "AAPL",
        "currency": "USD",
        "timezone": "America/New_York",
        "kind": "stock",
    }
    bars, actions = chart_prices(listing, "2026-11-16", "2026-11-17")
    assert bars[0]["date"] == "2026-11-17" and bars[0]["currency"] == "USD"
    assert actions["splits"] == [{"date": "2026-11-17", "ratio": 2}]
    chart["meta"]["currency"] = "TWD"
    with pytest.raises(DataError, match="mismatch"):
        chart_prices(listing, "2026-11-16", "2026-11-17")


def test_failed_reevaluation_removes_old_result(tmp_path, monkeypatch):
    import market_scan as scan
    import pytest

    listing = {"symbol": "AAPL", "market": "us"}
    scan.save(
        tmp_path / "inputs/AAPL.json.gz",
        {
            "listing": listing,
            "price": {"status": "ok", "identity_verified": True},
            "snapshot": None,
            "elapsed_seconds": 1,
        },
    )
    scan.save(tmp_path / "results/AAPL.json.gz", [{"passed": True}])

    def fail(*a):
        raise ValueError("test evaluator failure")

    monkeypatch.setattr(scan, "evaluate_one", fail)
    with pytest.raises(ValueError):
        scan.work(listing, "2025-01-01", "2026-11-17", {}, tmp_path, True)
    assert not (tmp_path / "results/AAPL.json.gz").exists()


def test_taiwan_calendar_outage_does_not_block_us_context(monkeypatch):
    from types import SimpleNamespace

    import market_scan as scan
    import pandas as pd

    schedule = pd.DataFrame(
        {"market_close": pd.to_datetime(["2026-11-16T21:00:00Z", "2026-11-17T21:00:00Z"])},
        index=pd.to_datetime(["2026-11-16", "2026-11-17"]),
    )
    monkeypatch.setitem(
        sys.modules,
        "pandas_market_calendars",
        SimpleNamespace(get_calendar=lambda _: SimpleNamespace(schedule=lambda **kw: schedule)),
    )
    monkeypatch.setattr(scan.data, "dataset", lambda *a, **k: {"status": "error", "data": []})
    monkeypatch.setattr(
        scan.data, "market_benchmark", lambda *a, **k: {"status": "error", "data": []}
    )
    monkeypatch.setattr(scan.data, "_yahoo_rows", lambda *a: [])
    monkeypatch.setattr(scan.data, "_bars", lambda *a: [{"date": "2026-11-17"}])
    contexts = scan.context("2026-11-16", "2026-11-17")
    assert contexts["tw"]["error"]
    assert contexts["us"]["benchmark"]["status"] == "ok"
    assert contexts["us"]["expected_session"] == "2026-11-17"


def test_bulk_rejected_yahoo_cannot_bypass_identity_gate(monkeypatch):
    import market_scan as scan

    def reject(*a, **k):
        raise scan.data.DataError("Yahoo metadata mismatch")

    monkeypatch.setattr(scan, "chart_prices", reject)
    monkeypatch.setattr(scan.data, "_finmind", reject)
    monkeypatch.setattr(
        scan.data,
        "prices",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("unvalidated retry")),
    )
    price, _ = scan.fetch_price(
        {"symbol": "2330.TW", "stock_id": "2330", "market": "tw"},
        "2026-11-16",
        "2026-11-17",
        "2026-11-17",
    )
    assert price["status"] == "error"
    assert not price.get("identity_verified")


def test_finmind_cooldown_survives_worker_restart(tmp_path, monkeypatch):
    import market_scan as scan
    import pytest

    monkeypatch.setattr(scan.data, "_FINMIND_BACKOFF_FILE", tmp_path / "cooldown.txt")
    monkeypatch.setattr(scan.data, "_FINMIND_BACKOFF_UNTIL", 0)
    scan.data._defer_finmind()
    monkeypatch.setattr(scan.data, "_FINMIND_BACKOFF_UNTIL", 0)
    monkeypatch.setattr(
        scan.data.requests,
        "get",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("request during shared cooldown")),
    )
    with pytest.raises(scan.data.DataError, match="retry deferred"):
        scan.data._finmind("TaiwanStockPrice")


def test_cached_prices_revalidated_before_evaluation(tmp_path, monkeypatch):
    import market_scan as scan

    listing = {"symbol": "AAPL", "market": "us"}
    scan.save(
        tmp_path / "inputs/AAPL.json.gz",
        {
            "listing": listing,
            "price": {"status": "ok", "warnings": ["Yahoo chart identity/currency/type mismatch"]},
            "snapshot": None,
            "elapsed_seconds": 1,
        },
    )
    monkeypatch.setattr(
        scan, "fetch_price", lambda *a: ({"status": "error", "error": "metadata mismatch"}, None)
    )
    monkeypatch.setattr(
        scan,
        "evaluate_one",
        lambda inputs, ctx: [{"passed": None, "status": "insufficient_data"}]
        if inputs["price"]["status"] == "error"
        else [],
    )
    result = scan.work(
        listing, "2025-01-01", "2026-11-17", {"expected_session": "2026-11-17"}, tmp_path, True
    )
    assert result["price_status"] == "error"
    assert len(list((tmp_path / "attempts").glob("*.gz"))) == 1


def test_yahoo_cooldown_blocks_chart_requests(tmp_path, monkeypatch):
    import market_scan as scan
    import pytest

    path = tmp_path / "yahoo-cooldown.txt"
    path.write_text(str(scan.time.time() + 300))
    monkeypatch.setattr(scan, "_YAHOO_BACKOFF_FILE", path)
    with pytest.raises(scan.data.DataError, match="retry deferred"):
        scan.chart_prices({}, "2026-11-16", "2026-11-17")


def test_yahoo_cooldown_blocks_snapshot_after_finmind_fallback(tmp_path, monkeypatch):
    import market_scan as scan

    path = tmp_path / "yahoo-cooldown.txt"
    path.write_text(str(scan.time.time() + 300))
    monkeypatch.setattr(scan, "_YAHOO_BACKOFF_FILE", path)
    monkeypatch.setattr(
        scan,
        "fetch_price",
        lambda *a: (
            {
                "status": "ok",
                "source": "finmind",
                "data": [],
                "as_of": "2026-11-17",
                "warnings": [],
            },
            None,
        ),
    )
    monkeypatch.setattr(
        scan.yahoo,
        "snapshot",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("snapshot during cooldown")),
    )
    monkeypatch.setattr(scan.data, "dataset", lambda *a, **k: {"status": "error", "data": []})
    result = scan.fetch_one(
        {"symbol": "2330.TW", "stock_id": "2330", "market": "tw", "kind": "stock"},
        "2025-01-01",
        "2026-11-17",
        {
            "expected_session": "2026-11-17",
            "calendar_complete_through": None,
            "benchmark_symbol": "^TWII",
            "session_closes": {},
        },
    )
    assert "retry deferred" in result["snapshot"]["errors"]["rate_limit"]


def test_taiwan_directory_decodes_cp950_extensions(monkeypatch):
    from types import SimpleNamespace

    import market_universe as universe

    html = "<table><tr><td>股票</td></tr><tr><td>2353　宏碁</td><td>ISIN</td><td>1996/09/05</td><td>上市</td><td>電腦</td><td>ESVUFR</td><td></td></tr></table>"
    monkeypatch.setattr(universe, "URLS", {"twse": "https://example.test/directory"})
    monkeypatch.setattr(
        universe.requests,
        "get",
        lambda *a, **k: SimpleNamespace(
            content=html.encode("cp950"), raise_for_status=lambda: None
        ),
    )
    assert universe.fetch_directories()["listings"][0]["name"] == "宏碁"
