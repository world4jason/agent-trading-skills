"""Offline contract tests for the Taiwan market data boundary."""

from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import pytest
import requests

from scripts import taiwan_data as td


def finmind_prices(*args, **kwargs):
    return td.prices(*args, provider="finmind", **kwargs)


INFO = [
    {"stock_id": "0050", "stock_name": "ETF", "type": "twse", "industry_category": "ETF", "date": "2024-01-01"},
    {"stock_id": "2330", "stock_name": "Stock", "type": "twse", "industry_category": "半導體業", "date": "2024-01-01"},
    {"stock_id": "2330", "stock_name": "Stock", "type": "twse", "industry_category": "電子工業", "date": "2024-01-01"},
    {"stock_id": "6488", "stock_name": "Stock", "type": "tpex", "industry_category": "電子工業", "date": "2024-01-01"},
    {"stock_id": "00980A", "stock_name": "ETF", "type": "twse", "industry_category": "ETF", "date": "2024-01-01"},
    {"stock_id": "00687B", "stock_name": "ETF", "type": "tpex", "industry_category": "上櫃指數股票型基金(ETF)", "date": "2024-01-01"},
    {"stock_id": "2881A", "stock_name": "Preferred", "type": "twse", "industry_category": "金融保險業", "date": "2024-01-01"},
    {"stock_id": "7777", "stock_name": "Old market", "type": "twse", "industry_category": "電子工業", "date": "2020-01-01"},
    {"stock_id": "7777", "stock_name": "Emerging", "type": "emerging", "industry_category": "電子工業", "date": "2024-01-01"},
    {"stock_id": "1234", "stock_name": "Warrant", "type": "twse", "industry_category": "權證", "date": "2024-01-01"},
    {"stock_id": "9999", "stock_name": "Index", "type": "twse", "industry_category": "指數", "date": "2024-01-01"},
    {"stock_id": "TAIEX", "stock_name": "Index", "type": "twse", "industry_category": "大盤", "date": "None"},
]


class Response:
    def __init__(self, rows=None, *, status=200, message="success"):
        self.status_code = status
        self.rows = rows if rows is not None else []
        self.message = message

    def json(self):
        return {"status": self.status_code, "msg": self.message, "data": self.rows}


def finmind(monkeypatch, datasets):
    calls = []

    def get(url, *, params, headers, timeout):
        calls.append((url, params, headers, timeout))
        item = datasets[params["dataset"]]
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(td.requests, "get", get)
    return calls


def test_universe_latest_listing_and_verified_suffix(monkeypatch):
    finmind(monkeypatch, {"TaiwanStockInfo": Response(INFO)})
    result = td.universe()
    assert result["status"] == "ok"
    assert result["source"] == "finmind"
    assert [(x["stock_id"], x["symbol"]) for x in result["data"]] == [
        ("0050", "0050.TW"), ("00687B", "00687B.TWO"), ("00980A", "00980A.TW"),
        ("2330", "2330.TW"), ("2881A", "2881A.TW"), ("6488", "6488.TWO")
    ]
    assert result["data"][0]["as_of"] == "2024-01-01"
    assert result["as_of"] == "2024-01-01"
    assert result["request"] == {"dataset": "TaiwanStockInfo"}
    assert datetime.fromisoformat(result["retrieved_at"]).tzinfo is not None
    assert "historical" in result["warnings"][0].lower()


def test_symbol_requires_verified_exchange(monkeypatch):
    finmind(monkeypatch, {"TaiwanStockInfo": Response(INFO)})
    assert finmind_prices("6488.TW", "2024-01-02", "2024-01-02")["status"] == "error"
    assert finmind_prices("7777", "2024-01-02", "2024-01-02")["status"] == "error"
    assert finmind_prices("2330.TW;evil", "2024-01-02", "2024-01-02")["status"] == "error"
    assert td._resolve("00980A.TW", td.universe()["data"])["stock_id"] == "00980A"


def test_finmind_price_semantics_and_inclusive_dates(monkeypatch):
    bars = [
        {"date": "2024-01-03", "stock_id": "0050", "open": 120, "max": 122, "min": 119, "close": 121, "Trading_Volume": 2000},
        {"date": "2024-01-02", "stock_id": "0050", "open": 118, "max": 120, "min": 117, "close": 119, "Trading_Volume": 1000},
    ]
    calls = finmind(monkeypatch, {"TaiwanStockInfo": Response(INFO), "TaiwanStockPrice": Response(bars)})
    result = finmind_prices("0050.TW", "2024-01-02", "2024-01-03")
    assert result["status"] == "ok" and result["source"] == "finmind"
    assert [x["date"] for x in result["data"]] == ["2024-01-02", "2024-01-03"]
    assert result["data"][0]["volume"] == 1000
    assert result["data"][0]["volume_unit"] == "shares"
    assert result["data"][0]["currency"] == "TWD"
    assert result["data"][0]["timezone"] == "Asia/Taipei"
    assert result["data"][0]["adjustment"] == "unadjusted"
    assert result["as_of"] == "2024-01-03"
    assert result["request"] == {"dataset": "TaiwanStockPrice", "requested_symbol": "0050.TW", "resolved_symbol": "0050.TW", "start": "2024-01-02", "end": "2024-01-03", "provider_preference": "finmind"}
    assert calls[-1][1]["end_date"] == "2024-01-03"


def test_yahoo_fallback_is_whole_result_and_explicit(monkeypatch):
    finmind(monkeypatch, {"TaiwanStockInfo": Response(INFO), "TaiwanStockPrice": Response(status=503)})
    calls = []

    def download(symbol, **kwargs):
        calls.append((symbol, kwargs))
        return pd.DataFrame(
            {"Open": [10.0], "High": [11.0], "Low": [9.0], "Close": [10.5], "Volume": [500]},
            index=pd.to_datetime(["2024-01-03"]),
        )

    monkeypatch.setattr(td, "_yahoo_download", download)
    result = finmind_prices("6488.TWO", "2024-01-03", "2024-01-03")
    assert result["status"] == "ok" and result["source"] == "yahoo"
    assert result["data"][0]["source"] == "yahoo"
    assert result["data"][0]["adjustment"] == "provider_reported_split_adjusted_dividend_unadjusted"
    assert result["data"][0]["adjustment_verified"] is False
    assert result["data"][0]["close"] == 10.5
    assert any("not independently verified" in warning for warning in result["warnings"])
    assert calls[0][0] == "6488.TWO"
    assert calls[0][1]["end"] == "2024-01-04"
    assert calls[0][1]["auto_adjust"] is False
    assert calls[0][1]["repair"] is False


def test_yahoo_multiindex_and_date_bounds_fail_closed(monkeypatch):
    finmind(monkeypatch, {"TaiwanStockInfo": Response(INFO), "TaiwanStockPrice": Response([])})
    columns = pd.MultiIndex.from_product([["Open", "High", "Low", "Close", "Volume"], ["0050.TW"]])
    frame = pd.DataFrame([[10, 11, 9, 10.5, 100]], columns=columns, index=pd.to_datetime(["2024-01-03"]))
    monkeypatch.setattr(td, "_yahoo_download", lambda *a, **k: frame)
    assert finmind_prices("0050", "2024-01-03", "2024-01-03")["status"] == "ok"
    assert finmind_prices("0050", "2024-01-02", "2024-01-02")["status"] == "error"


def test_no_yahoo_on_unverified_symbol_or_dataset_failure(monkeypatch):
    finmind(monkeypatch, {"TaiwanStockInfo": Response(INFO), "TaiwanStockFinancialStatements": Response(status=403)})
    monkeypatch.setattr(td, "_yahoo_download", lambda *a, **k: pytest.fail("Yahoo must not run"))
    assert finmind_prices("9999", "2024-01-01", "2024-01-02")["status"] == "error"
    result = td.dataset("TaiwanStockFinancialStatements", "2330", "2024-01-01", "2024-01-02")
    assert result["status"] == "error" and result["source"] == "finmind"
    assert "access denied" in result["error"]


def test_plan_and_empty_data_are_distinct_without_response_leak(monkeypatch):
    secret = "secret-in-provider-message"
    finmind(monkeypatch, {"TaiwanStockInfo": Response(INFO), "TaiwanStockDividend": Response(status=402, message=secret)})
    denied = td.dataset("TaiwanStockDividend", "2330", "2024-01-01", "2024-01-02")
    assert "higher plan" in denied["error"]
    assert secret not in json.dumps(denied)
    finmind(monkeypatch, {"TaiwanStockInfo": Response(INFO), "TaiwanStockDividend": Response([])})
    empty = td.dataset("TaiwanStockDividend", "2330", "2024-01-01", "2024-01-02")
    assert empty["status"] == "ok" and empty["data"] == []
    assert "no rows" in empty["warnings"][0]


def test_reject_out_of_range_and_invalid_price_rows(monkeypatch):
    rows = [{"date": "2024-01-04", "stock_id": "2330", "open": 10, "max": 11, "min": 9, "close": 10, "Trading_Volume": 10}]
    finmind(monkeypatch, {"TaiwanStockInfo": Response(INFO), "TaiwanStockPrice": Response(rows)})
    monkeypatch.setattr(td, "_yahoo_download", lambda *a, **k: pd.DataFrame())
    assert finmind_prices("2330", "2024-01-02", "2024-01-03")["status"] == "error"
    rows[0]["date"] = "2024-01-03"
    rows[0]["close"] = 0
    assert finmind_prices("2330", "2024-01-02", "2024-01-03")["status"] == "error"


@pytest.mark.parametrize("field,error", [("open", "Invalid price bar"), ("Trading_Volume", "Invalid share volume")])
def test_oversized_provider_number_is_fixed_error(monkeypatch, field, error):
    row = {"date": "2024-01-03", "stock_id": "2330", "open": 10, "max": 11, "min": 9, "close": 10, "Trading_Volume": 100}
    row[field] = 10**400
    finmind(monkeypatch, {"TaiwanStockInfo": Response(INFO), "TaiwanStockPrice": Response([row])})
    monkeypatch.setattr(td, "_yahoo_download", lambda *a, **k: pd.DataFrame())
    result = finmind_prices("2330", "2024-01-03", "2024-01-03")
    assert result["status"] == "error" and error in result["error"]
    assert result["data"] == []


def test_malformed_catalog_market_cannot_resolve_symbol(monkeypatch):
    malformed = {"stock_id": "4444", "stock_name": "Unknown", "type": [], "industry_category": "電子工業", "date": "2024-01-01"}
    finmind(monkeypatch, {"TaiwanStockInfo": Response(INFO + [malformed])})
    result = td.universe()
    assert result["status"] == "ok"
    assert "4444" not in {row["stock_id"] for row in result["data"]}
    assert finmind_prices("4444", "2024-01-02", "2024-01-02")["status"] == "error"


def test_calendar_and_dataset_allowlist(monkeypatch):
    calls = finmind(monkeypatch, {"TaiwanStockTradingDate": Response([{"date": "2024-01-02"}])})
    result = td.dataset("TaiwanStockTradingDate", None, "2024-01-02", "2024-01-02")
    assert result["data"] == [{"date": "2024-01-02"}]
    assert "data_id" not in calls[0][1]
    assert td.dataset("TaiwanFuturesDaily", "2330", "2024-01-02", "2024-01-02")["status"] == "error"
    assert td.dataset("TaiwanStockPriceAdj", "2330", "2024-01-02", "2024-01-02")["status"] == "error"


def test_month_revenue_keeps_raw_release_context(monkeypatch):
    row = {"date": "2026-10-01", "stock_id": "2330", "revenue_month": 9, "revenue_year": 2026, "create_time": "2026-10-08"}
    finmind(monkeypatch, {"TaiwanStockInfo": Response(INFO), "TaiwanStockMonthRevenue": Response([row])})
    result = td.dataset("TaiwanStockMonthRevenue", "2330", "2026-10-01", "2026-10-07")
    assert result["data"] == [row]
    assert "not release date" in result["warnings"][0]
    assert "actual release date" in result["warnings"][0]


def test_redacted_errors_and_cli_exit(monkeypatch, tmp_path, capsys):
    secret = "highly-sensitive-test-token"
    monkeypatch.setenv("FINMIND_TOKEN", secret)
    finmind(monkeypatch, {"TaiwanStockInfo": requests.Timeout(secret)})
    path = tmp_path / "out.json"
    assert td.main(["universe", "--output", str(path)]) != 0
    output = path.read_text()
    assert secret not in output and secret not in capsys.readouterr().err
    assert json.loads(output)["status"] == "error"
    assert td.main(["prices", "--symbol", "2330", "--start", "2024-02-31", "--end", "2024-03-01", "--output", str(path)]) != 0


def test_cli_creates_output_parent(monkeypatch, tmp_path):
    finmind(monkeypatch, {"TaiwanStockInfo": Response(INFO)})
    path = tmp_path / "nested" / "market" / "universe.json"
    assert td.main(["universe", "--output", str(path)]) == 0
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "ok"


def test_auto_prefers_yahoo_and_invalid_series_falls_back_whole(monkeypatch):
    rows=[{"date":"2024-01-03","stock_id":"2330","open":10,"max":11,"min":9,"close":10,"Trading_Volume":100}]
    calls=finmind(monkeypatch,{"TaiwanStockInfo":Response(INFO),"TaiwanStockPrice":Response(rows)})
    good=pd.DataFrame({"Open":[20],"High":[22],"Low":[19],"Close":[21],"Volume":[100]},index=pd.to_datetime(["2024-01-03"]))
    monkeypatch.setattr(td,"_yahoo_download",lambda *a,**k:good)
    result=td.prices("2330","2024-01-03","2024-01-03")
    assert result["source"] == "yahoo" and result["data"][0]["close"] == 21
    assert all(call[1]["dataset"] != "TaiwanStockPrice" for call in calls)
    good.loc[:,"Low"] = 0
    result=td.prices("2330","2024-01-03","2024-01-03")
    assert result["source"] == "finmind" and result["data"][0]["close"] == 10
    assert any("Invalid price bar" in x for x in result["warnings"])


def test_explicit_symbols_can_resolve_without_finmind(monkeypatch):
    finmind(monkeypatch,{"TaiwanStockInfo":Response(status=403)})
    monkeypatch.setattr(td,"_yahoo_listing",lambda s:{"stock_id":"6488","symbol":"6488.TWO","exchange":"tpex","kind":"stock","as_of":"2024-01-01"})
    assert td.universe(symbols=["6488"])["source"] == "yahoo"
    assert td.universe()["status"] == "error"


def test_missing_expected_session_uses_alternative(monkeypatch):
    rows=[{"date":"2024-01-03","stock_id":"2330","open":10,"max":11,"min":9,"close":10,"Trading_Volume":100}]
    finmind(monkeypatch,{"TaiwanStockInfo":Response(INFO),"TaiwanStockPrice":Response(rows)})
    frame=pd.DataFrame({"Open":[20],"High":[22],"Low":[19],"Close":[21],"Volume":[100]},index=pd.to_datetime(["2024-01-02"]))
    monkeypatch.setattr(td,"_yahoo_download",lambda *a,**k:frame)
    result=td.prices("2330","2024-01-02","2024-01-03",expected_session="2024-01-03")
    assert result["source"] == "finmind"
    assert result["as_of"] == "2024-01-03"


def test_finmind_402_quota_is_not_a_plan_error_and_backs_off(monkeypatch):
    from types import SimpleNamespace
    from scripts import taiwan_data as module
    calls=[]
    def request(*args,**kwargs):
        calls.append(1)
        return SimpleNamespace(status_code=402,json=lambda:{"status":402,"msg":"Requests reach the upper limit. https://finmindtrade.com/"})
    monkeypatch.setattr(module,"_FINMIND_BACKOFF_UNTIL",0)
    monkeypatch.setattr(module.requests,"get",request)
    for _ in range(2):
        with pytest.raises(module.DataError,match="rate limit"):
            module._finmind("TaiwanStockPrice",symbol="2330",start="2026-11-16",end="2026-11-17")
    assert len(calls)==1
