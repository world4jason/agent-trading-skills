"""Yahoo capability snapshots, with per-field absence and retrieval provenance."""

from __future__ import annotations

import math
import time
from datetime import date, datetime, timedelta, timezone
from numbers import Real
from zoneinfo import ZoneInfo

import yfinance as yf

INFO_FIELDS = (
    "symbol",
    "currency",
    "financialCurrency",
    "exchange",
    "quoteType",
    "country",
    "sector",
    "industry",
    "longName",
    "shortName",
    "marketCap",
    "sharesOutstanding",
    "floatShares",
    "heldPercentInstitutions",
    "heldPercentInsiders",
    "trailingEps",
    "forwardEps",
    "trailingPE",
    "forwardPE",
    "priceToBook",
    "bookValue",
    "regularMarketTime",
    "regularMarketPrice",
    "currentPrice",
    "returnOnEquity",
    "debtToEquity",
    "totalDebt",
    "totalCash",
    "freeCashflow",
    "operatingCashflow",
    "payoutRatio",
    "dividendRate",
    "dividendYield",
    "profitMargins",
    "earningsGrowth",
    "revenueGrowth",
    "mostRecentQuarter",
    "lastFiscalYearEnd",
    "nextFiscalYearEnd",
)


def _clean(value):
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Real):
        try:
            result = float(value)
            return result if math.isfinite(result) else None
        except (ValueError, OverflowError):
            return None
    return None


def _records(frame, *, statements=False, index_name=None):
    if frame is None or getattr(frame, "empty", True):
        return []
    frame = frame.T if statements else frame
    rows = []
    for index, series in frame.iterrows():
        row = {str(k): _clean(v) for k, v in series.items()}
        if statements:
            row["date"] = index.date().isoformat()
        elif index_name:
            row[index_name] = _clean(index)
        rows.append(row)
    return rows


def snapshot(symbol, *, capabilities=None, market="tw", compact=False):
    """Current snapshots are not historical point-in-time financial observations."""
    import re

    pattern = r"\d{4,6}[A-Z]?\.(?:TW|TWO)" if market == "tw" else r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)?"
    if (
        market not in ("tw", "us")
        or not isinstance(symbol, str)
        or not re.fullmatch(pattern, symbol)
    ):
        return {"status": "error", "errors": {"identity": "Expected verified market Yahoo symbol"}}
    wanted = set(
        capabilities
        or ("income", "balance", "cashflow", "holders", "estimates", "events", "actions")
    )
    now = datetime.now(timezone.utc)
    local_timezone = "Asia/Taipei" if market == "tw" else "America/New_York"
    output = {
        "source": "yahoo",
        "symbol": symbol,
        "retrieved_at": now.isoformat(),
        "as_of": now.astimezone(ZoneInfo(local_timezone)).date().isoformat(),
        "errors": {},
        "warnings": ["Retrieval-time snapshot; no historical availability timestamps guaranteed"],
    }
    ticker = yf.Ticker(symbol)

    def collect(key, getter):
        for attempt in range(2):
            try:
                value = getter()
                if not value:
                    output["errors"][key] = "Yahoo returned no data"
                output[key] = value
                return
            except Exception:
                if attempt == 0:
                    time.sleep(0.25)
                    continue
                output[key] = {} if key in ("info", "institutional_summary") else []
                output["errors"][key] = "Yahoo capability unavailable after retry"

    collect(
        "info", lambda: {k: _clean(v) for k, v in ticker.get_info().items() if k in INFO_FIELDS}
    )
    info = output["info"]
    if info.get("symbol") != symbol:
        return {
            "status": "error",
            "source": "yahoo",
            "symbol": symbol,
            "errors": {**output["errors"], "identity": "Yahoo identity unavailable or mismatched"},
            "as_of": output["as_of"],
            "retrieved_at": output["retrieved_at"],
        }
    output.update(currency=info.get("currency"), financial_currency=info.get("financialCurrency"))
    for capability, method in (
        ("income", ticker.get_income_stmt),
        ("balance", ticker.get_balance_sheet),
        ("cashflow", ticker.get_cashflow),
    ):
        if capability in wanted:
            periods = (("annual", "yearly"), ("quarterly", "quarterly"))
            if compact and capability == "balance":
                periods = (("quarterly", "quarterly"),)
            if compact and capability == "cashflow":
                periods = (("annual", "yearly"),)
            for label, frequency in periods:
                collect(
                    label + "_" + capability,
                    lambda method=method, frequency=frequency: _records(
                        method(pretty=True, freq=frequency), statements=True
                    ),
                )
    if compact and "balance" in wanted and not output.get("quarterly_balance"):
        collect(
            "annual_balance",
            lambda: _records(ticker.get_balance_sheet(pretty=True, freq="yearly"), statements=True),
        )
    if "holders" in wanted:
        collect("institutional_holders", lambda: _records(ticker.get_institutional_holders()))
        collect(
            "institutional_summary",
            lambda: {str(k): _clean(v) for k, v in ticker.get_major_holders()["Value"].items()},
        )
    if "estimates" in wanted:
        collect("estimates", lambda: _records(ticker.get_earnings_estimate(), index_name="period"))
    if "events" in wanted:
        collect(
            "earnings_dates",
            lambda: _records(ticker.get_earnings_dates(limit=24), index_name="date"),
        )
    if "actions" in wanted:
        for key, method, value_name in (
            ("dividends", ticker.get_dividends, "amount"),
            ("splits", ticker.get_splits, "ratio"),
        ):
            collect(
                key,
                lambda method=method, value_name=value_name: [
                    {"date": index.date().isoformat(), value_name: _clean(value)}
                    for index, value in method().items()
                ],
            )
    output["status"] = "partial" if output["errors"] else "ok"
    return output


def usd_twd(cutoff):
    """Dated FX for converting original USD liquidity thresholds, not FX trading."""
    try:
        end = date.fromisoformat(cutoff)
        frame = yf.Ticker("TWD=X").history(
            start=(end - timedelta(days=7)).isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            auto_adjust=False,
            repair=False,
            timeout=10,
        )
        rows = [
            (index.date(), _clean(value))
            for index, value in frame["Close"].items()
            if index.date() <= end
        ]
        rows = [(day, rate) for day, rate in rows if isinstance(rate, (int, float)) and rate > 0]
        if not rows:
            return {
                "status": "unavailable",
                "source": "yahoo",
                "error": "No valid dated USD/TWD quote",
            }
        day, rate = max(rows)
        return {
            "status": "ok",
            "source": "yahoo",
            "symbol": "TWD=X",
            "date": day.isoformat(),
            "rate": rate,
            "base_currency": "USD",
            "quote_currency": "TWD",
        }
    except Exception:
        return {
            "status": "unavailable",
            "source": "yahoo",
            "error": "Dated USD/TWD quote unavailable",
        }
