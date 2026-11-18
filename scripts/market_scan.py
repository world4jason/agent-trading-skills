#!/usr/bin/env python3
"""Resumable full-directory Taiwan/US scan using the shared strategy evaluators."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import taiwan_data as data
import taiwan_fundamental as fundamental
import taiwan_technical as technical
import taiwan_yahoo as yahoo
from taiwan_screen import STRATEGIES, TECHNICAL

EVALUATOR_REVISION = hashlib.sha256(
    b"".join(
        (Path(__file__).parent / name).read_bytes()
        for name in (
            "market_scan.py",
            "taiwan_data.py",
            "taiwan_yahoo.py",
            "taiwan_fundamental.py",
            "taiwan_technical.py",
            "taiwan_pead.py",
        )
    )
).hexdigest()[:16]


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    if path.suffix == ".gz":
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            f.write(raw)
    else:
        tmp.write_text(raw, encoding="utf-8")
    os.replace(tmp, path)


def read(path):
    if str(path).endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(Path(path).read_text())


def context(start, end):
    import pandas_market_calendars as mcal

    last = date.fromisoformat(end)
    horizon = (last + timedelta(days=max(0, 4 - last.weekday()))).isoformat()
    result = {}
    tw = data.dataset("TaiwanStockTradingDate", None, start, horizon)
    observed = None
    if tw["status"] != "ok" or not tw.get("data"):
        observed = data.market_benchmark(start, end)
    for market in ("tw", "us"):
        if market == "tw":
            if observed is not None and (
                observed.get("status") != "ok" or not observed.get("data")
            ):
                result[market] = {
                    "error": "Taiwan calendar and observed benchmark sessions unavailable",
                    "expected_session": end,
                    "benchmark": {"status": "error", "data": []},
                }
                continue
            sessions = [r["date"] for r in (observed or tw)["data"]]
            calendar_source = (
                "observed TAIEX sessions (may omit provider gaps)" if observed else "finmind"
            )
            closes = {}
        else:
            schedule = mcal.get_calendar("NYSE").schedule(start_date=start, end_date=horizon)
            sessions = [i.date().isoformat() for i in schedule.index]
            closes = {
                i.date().isoformat(): row["market_close"]
                .tz_convert("America/New_York")
                .strftime("%H:%M")
                for i, row in schedule.iterrows()
            }
            calendar_source = "pandas_market_calendars.NYSE"
        expected = max(s for s in sessions if s <= end)
        symbol = "^TWII" if market == "tw" else "^GSPC"
        if market == "tw":
            bench = observed or data.market_benchmark(start, end, expected_session=expected)
        else:
            listing = {
                "symbol": symbol,
                "stock_id": symbol,
                "currency": "USD",
                "timezone": "America/New_York",
            }
            try:
                bars = data._bars(
                    data._yahoo_rows(listing, date.fromisoformat(start), last),
                    listing,
                    date.fromisoformat(start),
                    last,
                    "yahoo",
                )
                if not bars or bars[-1]["date"] != expected:
                    raise data.DataError("Stale US benchmark")
                bench = {"status": "ok", "source": "yahoo", "data": bars}
            except data.DataError as exc:
                bench = {"status": "error", "error": str(exc), "data": []}
        result[market] = {
            "sessions": sessions,
            "calendar_source": calendar_source,
            "calendar_complete_through": None
            if market == "tw" and observed is not None
            else horizon,
            "session_closes": closes,
            "expected_session": expected,
            "benchmark_symbol": symbol,
            "benchmark": bench,
        }
    if "error" not in result["tw"]:
        result["tw"]["fx"] = yahoo.usd_twd(result["tw"]["expected_session"])
    return result


_YAHOO_BACKOFF_FILE = None


def yahoo_deferred():
    return (
        _YAHOO_BACKOFF_FILE is not None
        and _YAHOO_BACKOFF_FILE.exists()
        and time.time() < float(_YAHOO_BACKOFF_FILE.read_text())
    )


def chart_prices(listing, start, end):
    """One chart request supplies verified prices and dated corporate actions."""
    import yfinance as yf

    if yahoo_deferred():
        raise data.DataError("Yahoo rate limit reached; retry deferred")
    local = ZoneInfo(listing["timezone"])
    first = date.fromisoformat(start)
    last = date.fromisoformat(end)
    action_start = min(first, last - timedelta(days=6 * 366))
    params = {
        "period1": int(datetime.combine(action_start, datetime.min.time(), local).timestamp()),
        "period2": int(
            datetime.combine(last + timedelta(days=1), datetime.min.time(), local).timestamp()
        ),
        "interval": "1d",
        "events": "div,splits",
    }
    # yfinance's authenticated transport retains its cookie/crumb and rate-limit handling.
    try:
        payload = yf.Ticker(listing["symbol"])._data.get_raw_json(
            "https://query2.finance.yahoo.com/v8/finance/chart/" + listing["symbol"],
            params=params,
            timeout=10,
        )
    except yf.exceptions.YFRateLimitError:
        if _YAHOO_BACKOFF_FILE is not None:
            temporary = _YAHOO_BACKOFF_FILE.with_suffix(f".{os.getpid()}.tmp")
            temporary.write_text(str(time.time() + 300))
            os.replace(temporary, _YAHOO_BACKOFF_FILE)
        raise data.DataError("Yahoo rate limit reached") from None
    chart = payload["chart"]["result"][0]
    meta = chart["meta"]
    if (
        meta.get("symbol") != listing["symbol"]
        or meta.get("currency") != listing["currency"]
        or meta.get("instrumentType") != ("ETF" if listing["kind"] == "etf" else "EQUITY")
    ):
        raise data.DataError("Yahoo chart identity/currency/type mismatch")
    quote = chart["indicators"]["quote"][0]
    rows = []
    for i, stamp in enumerate(chart["timestamp"]):
        day = datetime.fromtimestamp(stamp, local).date().isoformat()
        if start <= day <= end:
            rows.append(
                {
                    "date": day,
                    **{key: quote[key][i] for key in ("open", "high", "low", "close", "volume")},
                }
            )
    bars = data._bars(rows, listing, first, last, "yahoo")
    events = chart.get("events", {})
    actions = {}
    for key, field in (("dividends", "amount"), ("splits", "ratio")):
        values = []
        for event in events.get(key, {}).values():
            day = datetime.fromtimestamp(event["date"], local).date().isoformat()
            if day > end:
                continue
            number = (
                data._number(event["amount"])
                if key == "dividends"
                else data._number(event["numerator"]) / data._number(event["denominator"])
            )
            values.append({"date": day, field: number})
        actions[key] = sorted(values, key=lambda row: row["date"])
    return bars, actions


def fetch_price(listing, start, end, expected):
    actions = None
    try:
        bars, actions = chart_prices(listing, start, end)
        if not bars or bars[-1]["date"] != expected:
            raise data.DataError("No price for completed market session")
        price = {
            "status": "ok",
            "source": "yahoo",
            "data": bars,
            "as_of": bars[-1]["date"],
            "warnings": [],
        }
    except Exception as exc:
        reason = (
            str(exc)
            if isinstance(exc, data.DataError)
            else "Yahoo chart unavailable: " + type(exc).__name__
        )
        if listing["market"] == "tw":
            try:
                rows = data._finmind(
                    "TaiwanStockPrice", symbol=listing["stock_id"], start=start, end=end
                )
                bars = data._bars(rows, listing, *data._bounds(start, end), "finmind")
                if not bars or bars[-1]["date"] != expected:
                    raise data.DataError("FinMind missing requested completed session")
                price = {
                    "status": "ok",
                    "source": "finmind",
                    "data": bars,
                    "as_of": bars[-1]["date"],
                    "warnings": [reason],
                }
            except data.DataError as fallback:
                price = {
                    "status": "error",
                    "source": None,
                    "data": [],
                    "as_of": None,
                    "warnings": [reason],
                    "error": str(fallback),
                }
        else:
            price = {
                "status": "error",
                "source": "yahoo",
                "data": [],
                "as_of": None,
                "warnings": [],
                "error": reason,
            }
    if price["status"] == "ok":
        price["identity_verified"] = True
    return price, actions


def fetch_one(listing, start, end, ctx):
    symbol = listing["symbol"]
    market = listing["market"]
    expected = ctx["expected_session"]
    started = time.monotonic()
    if ctx.get("error"):
        return {
            "listing": listing,
            "price": {
                "status": "error",
                "source": None,
                "data": [],
                "as_of": None,
                "warnings": [],
                "error": ctx["error"],
            },
            "snapshot": None,
            "datasets": {},
            "dataset_metadata": {},
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": 0,
        }
    price, actions = fetch_price(listing, start, end, expected)
    snapshot = None
    datasets = {}
    metadata = {}
    if listing["kind"] == "stock" and price["status"] == "ok":
        capabilities = {"income", "balance", "cashflow", "holders", "estimates", "events"}
        if actions is None:
            capabilities.add("actions")
        snapshot = (
            {
                "status": "error",
                "source": "yahoo",
                "symbol": symbol,
                "errors": {"rate_limit": "Yahoo rate limit reached; retry deferred"},
            }
            if yahoo_deferred()
            else yahoo.snapshot(symbol, market=market, capabilities=capabilities, compact=True)
        )
        if actions is not None:
            snapshot.update(actions)
        snapshot.update(
            evaluation_date=end,
            calendar_complete_through=ctx["calendar_complete_through"],
            benchmark_symbol=ctx["benchmark_symbol"],
            session_closes=ctx["session_closes"],
        )
        if market == "tw":
            snapshot["fx_usd_twd"] = ctx.get("fx")
            needed = []
            if not snapshot.get("annual_income") or not snapshot.get("quarterly_income"):
                needed.append(fundamental.STATEMENTS)
            if not snapshot.get("dividends"):
                needed.append(fundamental.DIVIDENDS)
            if not snapshot.get("quarterly_balance") and not snapshot.get("annual_balance"):
                needed.append(fundamental.BALANCE)
            if not snapshot.get("annual_cashflow"):
                needed.append(fundamental.CASHFLOW)
            info = snapshot.get("info", {})
            if info.get("trailingPE") is None or info.get("priceToBook") is None:
                needed.append(fundamental.PER)
            for name in needed:
                response = data.dataset(
                    name,
                    listing["stock_id"],
                    (date.fromisoformat(end) - timedelta(days=6 * 366)).isoformat(),
                    end,
                    listings=[listing],
                )
                datasets[name] = response["data"] if response["status"] == "ok" else []
                metadata[name] = {k: v for k, v in response.items() if k != "data"}
    return {
        "listing": listing,
        "price": price,
        "snapshot": snapshot,
        "datasets": datasets,
        "dataset_metadata": metadata,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.monotonic() - started, 2),
    }


def evaluate_one(inputs, ctx):
    listing = inputs["listing"]
    price = inputs["price"]
    rows = []
    for strategy in STRATEGIES:
        if strategy not in TECHNICAL and listing["kind"] == "etf":
            r = {
                "status": "not_applicable",
                "passed": None,
                "metrics": {},
                "warnings": ["Company earnings criteria do not apply to ETFs"],
            }
        elif price["status"] != "ok":
            r = {
                "status": "insufficient_data",
                "passed": None,
                "metrics": {},
                "warnings": [price.get("error", "Prices unavailable")],
            }
        else:
            try:
                if strategy in TECHNICAL:
                    r = technical.evaluate(
                        strategy,
                        listing,
                        price["data"],
                        benchmark=ctx["benchmark"].get("data"),
                        expected_session=ctx["expected_session"],
                    )
                else:
                    r = fundamental.evaluate(
                        strategy,
                        listing,
                        price["data"],
                        datasets=inputs["datasets"],
                        snapshot=inputs["snapshot"],
                        benchmark=ctx["benchmark"].get("data"),
                        sessions=ctx["sessions"],
                    )
            except Exception as exc:
                r = {
                    "status": "evaluation_error",
                    "passed": None,
                    "metrics": {},
                    "warnings": ["Evaluator error: " + type(exc).__name__],
                }
        rows.append(
            {
                "symbol": listing["symbol"],
                "name": listing["name"],
                "market": listing["market"],
                "exchange": listing["exchange"],
                "kind": listing["kind"],
                "currency": listing["currency"],
                "strategy": strategy,
                "engine_revision": EVALUATOR_REVISION,
                "as_of": price.get("as_of"),
                "price_source": price.get("source"),
                "fundamentals_as_of": (inputs.get("snapshot") or {}).get("as_of"),
                "fundamentals_retrieved_at": (inputs.get("snapshot") or {}).get("retrieved_at"),
                "provider_errors": (inputs.get("snapshot") or {}).get("errors", {}),
                "price_warnings": price.get("warnings", []),
                **r,
            }
        )
    return rows


def work(listing, start, end, ctx, directory, reevaluate, retry_prices=False):
    global _YAHOO_BACKOFF_FILE
    base = Path(directory)
    _YAHOO_BACKOFF_FILE = base / "yahoo-cooldown.txt"
    data._FINMIND_BACKOFF_FILE = base / "finmind-cooldown.txt"
    key = listing["symbol"]
    input_path = base / "inputs" / (key + ".json.gz")
    result_path = base / "results" / (key + ".json.gz")
    if result_path.exists() and not reevaluate and not retry_prices:
        return {"symbol": key, "cached": True}
    if reevaluate or retry_prices:
        result_path.unlink(missing_ok=True)
    if input_path.exists() and retry_prices and read(input_path)["price"]["status"] != "ok":
        archive = base / "attempts" / (key + "-" + str(time.time_ns()) + ".json.gz")
        archive.parent.mkdir(parents=True, exist_ok=True)
        os.replace(input_path, archive)
    if input_path.exists():
        inputs = read(input_path)
    else:
        inputs = fetch_one(listing, start, end, ctx)
        save(input_path, inputs)
    if inputs["price"]["status"] == "ok" and any(
        "identity/currency/type mismatch" in warning
        for warning in inputs["price"].get("warnings", [])
    ):
        save(base / "attempts" / (key + "-" + str(time.time_ns()) + ".json.gz"), inputs)
        inputs["price"], actions = fetch_price(listing, start, end, ctx["expected_session"])
        inputs["price_revalidated_at"] = datetime.now(timezone.utc).isoformat()
        if actions is not None and inputs.get("snapshot"):
            inputs["snapshot"].update(actions)
        save(input_path, inputs)
    snapshot = inputs.get("snapshot")
    if (
        snapshot
        and inputs["price"]["status"] == "ok"
        and snapshot.get("info", {}).get("symbol") == listing["symbol"]
        and "institutional_summary" not in snapshot
    ):
        import yfinance as yf

        try:
            if yahoo_deferred():
                raise data.DataError("Yahoo rate limit reached; retry deferred")
            frame = yf.Ticker(listing["symbol"]).get_major_holders()
            snapshot["institutional_summary"] = {
                str(k): yahoo._clean(v) for k, v in frame["Value"].items()
            }
        except Exception:
            snapshot["institutional_summary"] = {}
            snapshot.setdefault("errors", {})["institutional_summary"] = (
                "Yahoo holder summary unavailable"
            )
        snapshot["holders_supplement_retrieved_at"] = datetime.now(timezone.utc).isoformat()
        save(input_path, inputs)
    rows = evaluate_one(inputs, ctx)
    save(result_path, rows)
    (base / "errors" / (key + ".json")).unlink(missing_ok=True)
    return {
        "symbol": key,
        "market": listing["market"],
        "price_status": inputs["price"]["status"],
        "elapsed": inputs["elapsed_seconds"],
        "passed": sum(r["passed"] is True for r in rows),
        "errors": sum(r["status"] == "evaluation_error" for r in rows),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory", type=Path, required=True)
    p.add_argument("--start", default="2025-01-01")
    p.add_argument("--end", required=True)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--symbols", nargs="+")
    p.add_argument("--reevaluate", action="store_true")
    p.add_argument("--retry-prices", action="store_true")
    args = p.parse_args()
    directory = args.directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    data._FINMIND_BACKOFF_FILE = directory / "finmind-cooldown.txt"
    if not 1 <= args.workers <= 16:
        raise ValueError("workers must be 1..16")
    data._bounds(args.start, args.end)
    for zone in ("Asia/Taipei", "America/New_York"):
        if date.fromisoformat(args.end) >= datetime.now(ZoneInfo(zone)).date():
            raise ValueError("Use a completed date before today in both markets")
    universe = read(directory / "universe.json")
    listings = universe["listings"]
    if args.symbols:
        listings = [r for r in listings if r["symbol"] in args.symbols]
    if not listings:
        raise ValueError("Empty scan scope")
    from itertools import zip_longest

    groups = [
        [r for r in listings if r["market"] == m and r["kind"] == k]
        for m, k in [("tw", "stock"), ("us", "stock"), ("tw", "etf"), ("us", "etf")]
    ]
    listings = [r for batch in zip_longest(*groups) for r in batch if r is not None]
    meta_path = directory / "run.json"
    if meta_path.exists():
        meta = read(meta_path)
        if (meta["start"], meta["end"]) != (args.start, args.end):
            raise ValueError("Cache date range mismatch")
        contexts = meta["contexts"]
    else:
        contexts = context(args.start, args.end)
        save(
            meta_path,
            {
                "start": args.start,
                "end": args.end,
                "contexts": contexts,
                "strategies": list(STRATEGIES),
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    pending = [
        r
        for r in listings
        if args.reevaluate
        or not (directory / "results" / (r["symbol"] + ".json.gz")).exists()
        or (
            args.retry_prices
            and (directory / "inputs" / (r["symbol"] + ".json.gz")).exists()
            and read(directory / "inputs" / (r["symbol"] + ".json.gz"))["price"]["status"] != "ok"
        )
    ]
    print(
        json.dumps({"selected": len(listings), "pending": len(pending), "workers": args.workers}),
        flush=True,
    )
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(
                work,
                r,
                args.start,
                args.end,
                contexts[r["market"]],
                str(directory),
                args.reevaluate,
                args.retry_prices,
            ): r
            for r in pending
        }
        done = len(listings) - len(pending)
        for future in as_completed(futures):
            listing = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                (directory / "results" / (listing["symbol"] + ".json.gz")).unlink(missing_ok=True)
                result = {"symbol": listing["symbol"], "worker_error": type(exc).__name__}
                save(directory / "errors" / (listing["symbol"] + ".json"), result)
            done += 1
            if done % 10 == 0 or result.get("worker_error") or result.get("errors"):
                print(json.dumps({"done": done, "total": len(listings), **result}), flush=True)
    print(json.dumps({"finished": True, "selected": len(listings)}), flush=True)


if __name__ == "__main__":
    main()
