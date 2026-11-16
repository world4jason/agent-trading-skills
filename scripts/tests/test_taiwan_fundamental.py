from datetime import date, timedelta

from scripts.taiwan_fundamental import STRATEGIES, evaluate, required_datasets


def _bars(end="2025-07-31", count=20, close=50.0):
    last = date.fromisoformat(end)
    rows = []
    for offset in range(count - 1, -1, -1):
        day = last - timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        rows.append({"date": day.isoformat(), "open": close, "high": close + 1,
                     "low": close - 1, "close": close, "volume": 1000})
    return rows


def _statement(period, eps, revenue):
    year, month, day = period
    stamp = f"{year:04d}-{month:02d}-{day:02d}"
    return [
        {"date": stamp, "type": "EPS", "value": eps},
        {"date": stamp, "type": "Revenue", "value": revenue},
    ]


def test_strategy_contract_uses_finmind_dataset_names():
    assert set(STRATEGIES) == {
        "canslim", "value-dividend", "dividend-growth-pullback",
        "undervalued-growth", "pead",
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

    result = evaluate("canslim", {"kind": "stock"}, _bars(), datasets={
        "TaiwanStockFinancialStatements": statements,
    })

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
    result = evaluate("canslim", {"kind": "stock"}, _bars(), datasets={
        "TaiwanStockFinancialStatements": rows,
    })
    assert result["status"] == "insufficient_data"
    assert result["passed"] is None
    assert result["metrics"]["checks"]["C"]["status"] == "unknown"


def test_etf_company_screen_is_not_applicable_and_does_not_invent_eps_or_pe():
    result = evaluate("value-dividend", {"kind": "etf"}, _bars(), datasets={})
    assert result["status"] == "not_applicable"
    assert result["passed"] is None
    assert result["metrics"].get("eps_yoy_growth_pct") is None
    assert result["metrics"].get("pe_ratio") is None


def test_pead_requires_release_date_and_calculates_gap_from_event_bars():
    bars = [
        {"date": "2025-06-02", "open": 99, "high": 101, "low": 98, "close": 100, "volume": 1000},
        {"date": "2025-06-03", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000},
        {"date": "2025-06-04", "open": 110, "high": 112, "low": 109, "close": 111, "volume": 1200},
        {"date": "2025-06-05", "open": 111, "high": 113, "low": 110, "close": 112, "volume": 1000},
        {"date": "2025-06-06", "open": 112, "high": 114, "low": 111, "close": 113, "volume": 1000},
    ]
    result = evaluate("pead", {"kind": "stock"}, bars, datasets={}, events=[
        {"release_date": "2025-06-03", "timing": "amc"},
    ])
    assert result["status"] == "evaluated"
    assert result["metrics"]["earnings_gap_pct"] == 10.0
    assert result["passed"] is True

    period_end_only = evaluate("pead", {"kind": "stock"}, bars, datasets={}, events=[
        {"period_end": "2025-06-03"},
    ])
    assert period_end_only["status"] == "insufficient_data"
    assert period_end_only["passed"] is None


def test_dividend_ttm_dedup_and_unknown_history():
    from scripts.taiwan_fundamental import _dividends
    rows = [{"date":f"{year}-06-01", "year":str(year), "CashExDividendTradingDate":f"{year}-06-01",
             "CashEarningsDistribution":float(year-2020), "CashStatutorySurplus":0.0}
            for year in (2022,2023,2024,2025)]
    result = _dividends(rows + [rows[-1]], "2025-07-31", 50)
    assert result["cash_dividends_ttm"] == 5
    assert result["cash_yield_pct"] == 10
    assert result["cash_dividend_cagr_3y_pct"] > 30
    assert _dividends(rows[-1:], "2025-07-31", 50)["cash_dividend_cagr_3y_pct"] is None


def test_negative_necessary_condition_rejects_without_fabricating_missing_health():
    result = evaluate("value-dividend", {"kind":"stock"}, _bars(), datasets={
        "TaiwanStockPER":[{"date":"2025-07-31","PER":40,"PBR":1.5}]})
    assert result["passed"] is False
    assert result["metrics"]["checks"]["financial_health"]["status"] == "unknown"


def test_event_is_not_applied_to_other_symbol():
    result = evaluate("pead", {"kind":"stock","symbol":"6488.TWO","stock_id":"6488"}, _bars(),
                      datasets={},events=[{"symbol":"2330.TW","release_date":"2025-07-20","timing":"amc"}])
    assert result["passed"] is None


def test_non_finite_financial_values_are_unknown():
    rows = _statement((2024,6,30),1,100)+_statement((2025,6,30),float("inf"),10**400)
    result=evaluate("canslim",{"kind":"stock"},_bars(),datasets={"TaiwanStockFinancialStatements":rows})
    assert result["passed"] is None
