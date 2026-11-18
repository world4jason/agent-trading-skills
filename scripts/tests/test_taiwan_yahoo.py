from datetime import datetime, timezone
from types import SimpleNamespace
import pandas as pd
import pytest
from scripts import taiwan_yahoo as yahoo


def test_snapshot_normalizes_statements_and_keeps_missing_fields(monkeypatch):
    statement=pd.DataFrame({pd.Timestamp("2025-12-31"):[5.0,float("nan"),10**100]},index=["Basic EPS","Total Revenue","Net Income"])
    estimates=pd.DataFrame({"avg":[6.0],"currency":["TWD"],"methodology":["gaap"],"numberOfAnalysts":[4]},index=["+1y"])
    ticker=SimpleNamespace(get_info=lambda:{"symbol":"2330.TW","currency":"TWD","financialCurrency":"TWD","privateUnneeded":"not exported"},
       get_income_stmt=lambda **k:statement,get_balance_sheet=lambda **k:statement,get_cashflow=lambda **k:statement,
       get_earnings_estimate=lambda:estimates)
    monkeypatch.setattr(yahoo.yf,"Ticker",lambda s:ticker)
    result=yahoo.snapshot("2330.TW",capabilities=["income","estimates"])
    assert result["status"] == "ok"
    assert result["annual_income"][0]["date"] == "2025-12-31"
    assert result["annual_income"][0]["Total Revenue"] is None
    assert result["estimates"][0]["period"] == "+1y"
    assert result["estimates"][0]["currency"] == "TWD"
    assert "privateUnneeded" not in result["info"]
    assert datetime.fromisoformat(result["retrieved_at"]).tzinfo is not None


def test_capability_errors_redacted_and_bounded_retry(monkeypatch):
    calls=[]
    def failed():
        calls.append(1)
        raise RuntimeError("private-secret")
    ticker=SimpleNamespace(get_info=failed,get_income_stmt=None,get_balance_sheet=None,get_cashflow=None,get_earnings_estimate=failed)
    monkeypatch.setattr(yahoo.yf,"Ticker",lambda s:ticker)
    monkeypatch.setattr(yahoo.time,"sleep",lambda _:None)
    result=yahoo.snapshot("2330.TW",capabilities=["estimates"])
    assert len(calls) == 2
    assert result["status"] == "error"
    assert result["errors"]["identity"]
    assert "private-secret" not in str(result)


def test_snapshot_rejects_wrong_identity_and_invalid_symbols(monkeypatch):
    monkeypatch.setattr(yahoo.yf,"Ticker",lambda s:SimpleNamespace(get_info=lambda:{"symbol":"AAPL"}))
    assert yahoo.snapshot("2330.TW")["status"] == "error"
    assert yahoo.snapshot("AAPL")["status"] == "error"


def test_dated_fx_excludes_future_and_invalid_values(monkeypatch):
    frame=pd.DataFrame({"Close":[31.5,float("nan"),32.0]},index=pd.to_datetime(["2026-11-16","2026-11-17","2026-11-18"]))
    monkeypatch.setattr(yahoo.yf,"Ticker",lambda s:SimpleNamespace(history=lambda **k:frame))
    result=yahoo.usd_twd("2026-11-17")
    assert result["rate"] == 31.5
    assert result["date"] == "2026-11-16"
    assert result["quote_currency"] == "TWD"


def test_missing_identity_rejects_snapshot(monkeypatch):
    monkeypatch.setattr(yahoo.yf,"Ticker",lambda s:SimpleNamespace(get_info=lambda:{"currency":"TWD"}))
    result=yahoo.snapshot("2330.TW",capabilities=["income"])
    assert result["status"] == "error"
    assert "annual_income" not in result
