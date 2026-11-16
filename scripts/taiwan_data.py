#!/usr/bin/env python3
"""FinMind-first Taiwan stock/ETF data with an explicit Yahoo price fallback."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
import math
from numbers import Real
import os
from pathlib import Path
import re
import sys
import time

import requests


FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"
DATASETS = frozenset({
    "TaiwanStockFinancialStatements",
    "TaiwanStockBalanceSheet",
    "TaiwanStockCashFlowsStatement",
    "TaiwanStockMonthRevenue",
    "TaiwanStockDividend",
    "TaiwanStockPER",
    "TaiwanStockInstitutionalInvestorsBuySell",
    "TaiwanStockMarginPurchaseShortSale",
    "TaiwanStockTradingDate",
})
SYMBOL = re.compile(r"^(\d{4,6}[A-Z]?)(?:\.(TW|TWO))?$")
STOCK = re.compile(r"^[1-9]\d{3}[A-Z]?$")
ETF = re.compile(r"^0\d{3,5}[A-Z]?$")
EXCHANGE = {"twse": "TW", "tpex": "TWO"}
EXCLUDED_CATEGORIES = ("權證", "指數", "大盤", "所有證券", "受益證券", "存託憑證", "債券", "基金", "ETN", "INDEX")


class DataError(Exception):
    """A safe, fixed-text error for CLI and import callers."""


def _envelope(status: str, source: str | None, data: list, warnings: list[str], error: str | None = None, *, request: dict | None = None) -> dict:
    """as_of is the latest row date, never a publication or availability timestamp."""
    result = {
        "status": status,
        "source": source,
        "data": data,
        "warnings": warnings,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "as_of": max((row.get("as_of") or row.get("date") for row in data), default=None),
        "request": request or {},
    }
    if error:
        result["error"] = error
    return result


def _date(value: str) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise DataError("Invalid date; expected YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise DataError("Invalid calendar date") from None


def _bounds(start: str, end: str) -> tuple[date, date]:
    first, last = _date(start), _date(end)
    if first > last:
        raise DataError("Start date is after end date")
    return first, last


def _finmind(dataset: str, *, symbol: str | None = None, start: str | None = None, end: str | None = None) -> list[dict]:
    params = {"dataset": dataset}
    if symbol is not None:
        params["data_id"] = symbol
    if start is not None:
        params.update(start_date=start, end_date=end)
    token = os.environ.get("FINMIND_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    for attempt in range(2):
        try:
            response = requests.get(FINMIND_URL, params=params, headers=headers, timeout=10)
        except requests.RequestException:
            if attempt == 0:
                time.sleep(0.25)
                continue
            raise DataError("FinMind request failed") from None
        if response.status_code in (429, 500, 502, 503, 504) and attempt == 0:
            time.sleep(0.25)
            continue
        if response.status_code in (401, 403):
            raise DataError("FinMind access denied; check FINMIND_TOKEN or plan")
        if response.status_code == 402:
            raise DataError("FinMind dataset requires a higher plan")
        if response.status_code == 429:
            raise DataError("FinMind rate limit reached")
        if response.status_code != 200:
            raise DataError("FinMind HTTP error")
        try:
            payload = response.json()
        except (ValueError, TypeError):
            raise DataError("Invalid FinMind response") from None
        if not isinstance(payload, dict):
            raise DataError("Invalid FinMind response")
        if payload.get("status") in (401, 403):
            raise DataError("FinMind access denied; check FINMIND_TOKEN or plan")
        if payload.get("status") == 402:
            raise DataError("FinMind dataset requires a higher plan")
        if payload.get("status") == 429:
            raise DataError("FinMind rate limit reached")
        if payload.get("status") != 200 or not isinstance(payload.get("data"), list):
            raise DataError("FinMind dataset unavailable")
        if not all(isinstance(row, dict) for row in payload["data"]):
            raise DataError("Invalid FinMind rows")
        return payload["data"]
    raise DataError("FinMind request failed")


def _kind(code: str, category: object) -> str | None:
    if not isinstance(category, str) or not category:
        return None
    upper = category.upper()
    if "ETF" in upper:
        return "etf" if ETF.fullmatch(code) else None
    if any(term in upper for term in EXCLUDED_CATEGORIES):
        return None
    return "stock" if STOCK.fullmatch(code) else None


def _universe_rows() -> list[dict]:
    latest: dict[str, dict] = {}
    for row in _finmind("TaiwanStockInfo"):
        code = row.get("stock_id")
        if not isinstance(code, str) or not (STOCK.fullmatch(code) or ETF.fullmatch(code)):
            continue
        stamp = row.get("date")
        _date(stamp)
        previous = latest.get(code)
        if previous is None or stamp > previous["date"]:
            latest[code] = row
        elif stamp == previous["date"]:
            if row.get("type") != previous.get("type") or _kind(code, row.get("industry_category")) != _kind(code, previous.get("industry_category")):
                raise DataError("Conflicting FinMind exchange records")
    result = []
    for code, row in latest.items():
        market = row.get("type")
        category = row.get("industry_category")
        # Invalid market metadata cannot establish a verified exchange suffix.
        if not isinstance(market, str) or market not in EXCHANGE or not isinstance(category, str):
            continue
        kind = _kind(code, category)
        if kind:
            result.append({"stock_id": code, "symbol": f"{code}.{EXCHANGE[market]}", "exchange": market, "kind": kind, "name": row.get("stock_name"), "industry_category": category, "as_of": row["date"]})
    return sorted(result, key=lambda item: item["stock_id"])


def universe() -> dict:
    """Return TWSE/TPEX stock and ETF records from FinMind's historical catalog."""
    try:
        rows = _universe_rows()
        if not rows:
            raise DataError("FinMind universe is empty")
        return _envelope("ok", "finmind", rows, ["FinMind TaiwanStockInfo includes historical listings; as_of is the latest record date, not proof of current trading activity"], request={"dataset": "TaiwanStockInfo"})
    except DataError as exc:
        return _envelope("error", "finmind", [], [], str(exc), request={"dataset": "TaiwanStockInfo"})


def _resolve(symbol: str, listings: list[dict], *, suffix_allowed: bool = True) -> dict:
    match = SYMBOL.fullmatch(symbol) if isinstance(symbol, str) else None
    if not match or (not suffix_allowed and match.group(2)):
        raise DataError("Invalid Taiwan stock or ETF symbol")
    code, suffix = match.groups()
    listing = next((row for row in listings if row["stock_id"] == code), None)
    if listing is None or (suffix and listing["symbol"] != symbol):
        raise DataError("Symbol or exchange not in FinMind stock/ETF catalog")
    return listing


def _number(value) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise DataError("Invalid price bar")
    try:
        number = float(value)
    except (OverflowError, ValueError, TypeError):
        raise DataError("Invalid price bar") from None
    if not math.isfinite(number):
        raise DataError("Invalid price bar")
    return number


def _bar(row: dict, listing: dict, first: date, last: date, source: str) -> dict:
    stamp = _date(row.get("date"))
    if not first <= stamp <= last:
        raise DataError("Price outside requested date range")
    if row.get("stock_id", listing["stock_id"]) != listing["stock_id"]:
        raise DataError("Price symbol mismatch")
    try:
        keys = ("open", "max", "min", "close") if source == "finmind" else ("open", "high", "low", "close")
        open_, high, low, close = (_number(row[key]) for key in keys)
        volume = row["Trading_Volume"] if source == "finmind" else row["volume"]
    except KeyError:
        raise DataError("Missing price bar field") from None
    if any(price <= 0 for price in (open_, high, low, close)) or high < max(open_, close, low) or low > min(open_, close, high):
        raise DataError("Invalid price bar")
    if isinstance(volume, bool) or not isinstance(volume, Real):
        raise DataError("Invalid share volume")
    try:
        volume_number = float(volume)
    except (OverflowError, ValueError, TypeError):
        raise DataError("Invalid share volume") from None
    if not math.isfinite(volume_number) or volume_number < 0 or int(volume_number) != volume_number:
        raise DataError("Invalid share volume")
    bar = {"date": stamp.isoformat(), "symbol": listing["symbol"], "open": open_, "high": high, "low": low, "close": close, "volume": int(volume), "volume_unit": "shares", "currency": "TWD", "timezone": "Asia/Taipei", "source": source, "adjustment": "unadjusted" if source == "finmind" else "provider_reported_split_adjusted_dividend_unadjusted"}
    if source == "yahoo":
        bar["adjustment_verified"] = False
    return bar


def _bars(rows: list[dict], listing: dict, first: date, last: date, source: str) -> list[dict]:
    bars = sorted((_bar(row, listing, first, last, source) for row in rows), key=lambda row: row["date"])
    if len({row["date"] for row in bars}) != len(bars):
        raise DataError("Duplicate price date")
    return bars


def _yahoo_download(symbol: str, **kwargs):
    import yfinance as yf

    return yf.download(symbol, **kwargs)


def _yahoo_rows(listing: dict, first: date, last: date) -> list[dict]:
    try:
        frame = _yahoo_download(listing["symbol"], start=first.isoformat(), end=(last + timedelta(days=1)).isoformat(), auto_adjust=False, repair=False, progress=False, threads=False, timeout=10)
        if getattr(frame, "empty", True):
            raise DataError("Yahoo prices unavailable")
        if getattr(frame.columns, "nlevels", 1) > 1:
            frame = frame.xs(listing["symbol"], axis=1, level=-1)
        rows = []
        for index, values in frame.iterrows():
            rows.append({"date": index.date().isoformat(), "open": values["Open"], "high": values["High"], "low": values["Low"], "close": values["Close"], "volume": values["Volume"]})
        return rows
    except DataError:
        raise
    except Exception:
        raise DataError("Yahoo prices unavailable") from None


def prices(symbol: str, start: str, end: str, *, listings: list[dict] | None = None) -> dict:
    """Return daily OHLCV; Yahoo is used only after a verified FinMind price miss."""
    request = {"dataset": "TaiwanStockPrice", "requested_symbol": symbol, "start": start, "end": end}
    try:
        first, last = _bounds(start, end)
        listing = _resolve(symbol, _universe_rows() if listings is None else listings)
        request["resolved_symbol"] = listing["symbol"]
    except DataError as exc:
        return _envelope("error", "finmind", [], [], str(exc), request=request)
    try:
        rows = _finmind("TaiwanStockPrice", symbol=listing["stock_id"], start=start, end=end)
        finmind_warning = "FinMind returned no price rows"
    except DataError as exc:
        rows = []
        finmind_warning = str(exc)
    if rows:
        try:
            return _envelope("ok", "finmind", _bars(rows, listing, first, last, "finmind"), [], request=request)
        except DataError as exc:
            return _envelope("error", "finmind", [], [], str(exc), request=request)
    try:
        yahoo = _bars(_yahoo_rows(listing, first, last), listing, first, last, "yahoo")
        if not yahoo:
            raise DataError("Yahoo prices unavailable")
        return _envelope("ok", "yahoo", yahoo, [finmind_warning, "Yahoo used for entire range", "Yahoo reports split-adjusted, dividend-unadjusted OHLC; adjustment not independently verified and no repair applied"], request=request)
    except DataError as exc:
        return _envelope("error", None, [], [finmind_warning], str(exc), request=request)


def dataset(name: str, symbol: str | None, start: str, end: str, *, listings: list[dict] | None = None) -> dict:
    """Return raw rows for an allowed FinMind dataset; no provider substitution."""
    request = {"dataset": name, "requested_symbol": symbol, "start": start, "end": end}
    try:
        if name not in DATASETS:
            raise DataError("Unsupported FinMind dataset")
        first, last = _bounds(start, end)
        if name == "TaiwanStockTradingDate":
            if symbol is not None:
                raise DataError("Trading calendar does not take a symbol")
            code = None
        else:
            listing = _resolve(symbol, _universe_rows() if listings is None else listings, suffix_allowed=False)
            code = listing["stock_id"]
            request["resolved_symbol"] = listing["symbol"]
        rows = _finmind(name, symbol=code, start=start, end=end)
        for row in rows:
            if not first <= _date(row.get("date")) <= last or (code and row.get("stock_id", code) != code):
                raise DataError("FinMind dataset row outside request")
        warnings = ["FinMind returned no rows"] if not rows else []
        if name == "TaiwanStockMonthRevenue":
            warnings.append("date is the revenue period, not release date; create_time is FinMind ingestion time, not verified public release time. Point-in-time analysis requires the actual release date")
        return _envelope("ok", "finmind", rows, warnings, request=request)
    except DataError as exc:
        return _envelope("error", "finmind", [], [], str(exc), request=request)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("universe", "prices", "dataset"):
        sub = commands.add_parser(command)
        if command == "prices":
            sub.add_argument("--symbol", required=True)
        elif command == "dataset":
            sub.add_argument("--name", required=True, choices=sorted(DATASETS))
            sub.add_argument("--symbol", help="Required except for TaiwanStockTradingDate")
        if command != "universe":
            sub.add_argument("--start", required=True)
            sub.add_argument("--end", required=True)
        sub.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    result = universe() if args.command == "universe" else prices(args.symbol, args.start, args.end) if args.command == "prices" else dataset(args.name, args.symbol, args.start, args.end)
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        print("Could not write output file", file=sys.stderr)
        return 1
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
