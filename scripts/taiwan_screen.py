#!/usr/bin/env python3
"""Taiwan stock/ETF screening with capability-based provider selection."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import date, datetime, timedelta
import json
import math
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

import taiwan_data as data

TECHNICAL = ("vcp", "momentum-burst", "exhaustion-hammer", "parabolic")
FUNDAMENTAL = ("canslim", "value-dividend", "dividend-growth-pullback", "undervalued-growth", "pead")
STRATEGIES = TECHNICAL + FUNDAMENTAL


def screen(*, strategies, start, end, symbols=None, exchange="all", kind="all", limit=None,
           benchmark_symbol=None, events=None, provider="auto"):
    first, last = data._bounds(start, end)
    today = datetime.now(ZoneInfo("Asia/Taipei")).date()
    if last >= today:
        raise data.DataError("Use a completed date before today in Asia/Taipei")
    if provider not in ("auto", "finmind", "yahoo"):
        raise data.DataError("Unsupported provider preference")
    if not strategies or any(s not in STRATEGIES for s in strategies):
        raise data.DataError("Unknown screening strategy")
    if limit is not None and (type(limit) is not int or limit < 1):
        raise data.DataError("Limit must be a positive integer")
    catalog = data.universe(symbols=symbols)
    if catalog["status"] != "ok":
        raise data.DataError(catalog.get("error", "Universe unavailable"))
    listings = catalog["data"]
    selected = [data._resolve(s, listings) for s in symbols] if symbols else listings
    selected = list({r["stock_id"]: r for r in selected}.values())
    selected = [r for r in selected if (exchange == "all" or r["exchange"] == exchange)
                and (kind == "all" or r["kind"] == kind)]
    requested = len(selected)
    selected = selected[:limit] if limit else selected
    if not selected:
        raise data.DataError("No symbols match the requested scope")
    benchmark_meta = None
    benchmark = None
    # Include the rest of the calendar week to distinguish holidays from unfinished weeks.
    calendar_end = (last + timedelta(days=max(0,4-last.weekday()))).isoformat() if "pead" in strategies else end
    calendar = data.dataset("TaiwanStockTradingDate", None, start, calendar_end, listings=listings)
    observed = None
    if calendar["status"] != "ok" or not calendar["data"]:
        observed = data.market_benchmark(start,end,provider=provider)
        if observed["status"] != "ok" or not observed["data"]:
            raise data.DataError("Taiwan completed-session calendar unavailable")
        calendar = {"status":"ok", "source":observed.get("source","yahoo"), "data":[{"date":row["date"]} for row in observed["data"]],
                    "warnings":["FinMind calendar unavailable; using observed TAIEX sessions, which may omit missing provider dates"]}
    sessions = sorted({row["date"] for row in calendar["data"]})
    completed_sessions = [day for day in sessions if day <= end]
    if not completed_sessions:
        raise data.DataError("No completed Taiwan sessions in requested range")
    expected = max(completed_sessions)
    if benchmark_symbol:
        benchmark_meta = data.prices(benchmark_symbol,start,end,listings=listings,provider=provider,expected_session=expected)
    elif "canslim" in strategies:
        benchmark_meta = observed if observed and observed["as_of"] == expected else data.market_benchmark(start,end,provider=provider,expected_session=expected)
    if benchmark_meta and benchmark_meta["status"] == "ok" and benchmark_meta["as_of"] == expected:
        benchmark = benchmark_meta["data"]
    fundamental_start = (last - timedelta(days=6 * 366)).isoformat()
    fx = None
    if "pead" in strategies:
        import taiwan_yahoo
        fx = taiwan_yahoo.usd_twd(expected)
    results = []
    for i, listing in enumerate(selected, 1):
        print(f"[{i}/{len(selected)}] {listing['symbol']}", file=sys.stderr)
        price = data.prices(listing["symbol"], start, end, listings=listings, provider=provider, expected_session=expected)
        datasets, dataset_meta = {}, {}
        snapshot = None
        if any(s in FUNDAMENTAL for s in strategies) and listing["kind"] == "stock":
            import taiwan_fundamental as fundamental
            import taiwan_yahoo
            capabilities = set()
            if "pead" in strategies:
                capabilities.add("events")
            if any(s in strategies for s in ("canslim","value-dividend","dividend-growth-pullback","undervalued-growth")):
                capabilities.update(("income","actions"))
            if "canslim" in strategies:
                capabilities.add("holders")
            if any(s in strategies for s in ("value-dividend","dividend-growth-pullback","undervalued-growth")):
                capabilities.update(("balance","cashflow"))
            if "undervalued-growth" in strategies:
                capabilities.add("estimates")
            snapshot = taiwan_yahoo.snapshot(listing["symbol"], capabilities=capabilities)
            snapshot["preferred_provider"] = provider
            snapshot["evaluation_date"] = end
            if "pead" in strategies and observed is None:
                snapshot["calendar_complete_through"] = calendar_end
            if fx is not None:
                snapshot["fx_usd_twd"] = fx
            dataset_meta["YahooFinance"] = {k:v for k,v in snapshot.items() if k in ("source","status","symbol","as_of","retrieved_at","currency","financial_currency","errors","warnings")}
            names = set().union(*(fundamental.required_datasets(s) for s in strategies if s in FUNDAMENTAL))
            for name in sorted(names):
                response = data.dataset(name, listing["stock_id"], fundamental_start, end, listings=listings)
                datasets[name] = response["data"] if response["status"] == "ok" else []
                dataset_meta[name] = {k: v for k, v in response.items() if k != "data"}
        for strategy in strategies:
            common = {"symbol": listing["symbol"], "kind": listing["kind"], "exchange": listing["exchange"],
                      "strategy": strategy, "price_source": price["source"], "as_of": price["as_of"],
                      "price_warnings": price["warnings"], "datasets": dataset_meta}
            if price["status"] != "ok" or price["as_of"] != expected:
                result = {"status": "insufficient_data", "passed": None, "metrics": {},
                          "warnings": [price.get("error", "No bar for requested completed Taiwan session")]}
            else:
                if strategy in TECHNICAL:
                    import taiwan_technical as technical
                    result = technical.evaluate(strategy, listing, price["data"], benchmark=benchmark, expected_session=expected)
                else:
                    import taiwan_fundamental as fundamental
                    result = fundamental.evaluate(strategy, listing, price["data"], datasets=datasets,
                                                  benchmark=benchmark, events=events, snapshot=snapshot, sessions=sessions)
            results.append({**common, **result})
    eligible = [r for r in results if r["strategy"] == "undervalued-growth" and r["metrics"].get("ranking_eligible") is True
                and type(r["metrics"].get("ranking_score")) in (int,float) and math.isfinite(r["metrics"]["ranking_score"])]
    eligible.sort(key=lambda r: (-r["metrics"]["ranking_score"], r["symbol"]))
    previous_score, rank = None, 0
    for position, row in enumerate(eligible, 1):
        score = row["metrics"]["ranking_score"]
        if score != previous_score:
            rank = position
        row["metrics"].update(rank=rank, ranked_universe_size=len(eligible), ranking_scope="requested eligible symbols only")
        previous_score = score
    counts = Counter(r["status"] for r in results)
    evaluated = counts["evaluated"]
    return {"schema_version": 2, "provider_preference":provider, "status": "complete" if not counts["insufficient_data"] else "partial" if evaluated else "insufficient_data",
            "currency": "TWD", "timezone": "Asia/Taipei", "start": start, "end": end,
            "expected_session": expected, "retrieved_at": datetime.now(ZoneInfo("Asia/Taipei")).isoformat(),
            "calendar": {k:v for k,v in calendar.items() if k != "data"},
            "scope": {"requested_symbols": requested, "processed_symbols": len(selected),
                      "not_processed_symbols": requested-len(selected), "selection": "explicit" if symbols else "FinMind catalog", "catalog_source":catalog.get("source"),
                      "exchange": exchange, "kind": kind},
            "summary": {**counts, "passed": sum(r["passed"] is True for r in results)},
            "benchmark": {k: v for k, v in (benchmark_meta or {}).items() if k != "data"},
            "warnings": [*catalog["warnings"], "Raw price research, not total return or a point-in-time backtest",
                         "Check corporate actions before using price patterns; Yahoo and FinMind adjustment bases differ",
                         "Strategy passes refer only to the explicitly reported checks, not trade permission"],
            "results": results}


def main(argv=None, *, default_strategy=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategy", nargs="+", choices=STRATEGIES, required=default_strategy is None,
                        default=[default_strategy] if default_strategy else None)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--symbols", "--universe", nargs="+")
    group.add_argument("--all", action="store_true", help="Scan the FinMind TWSE/TPEX stock and ETF catalog")
    parser.add_argument("--provider", choices=("auto", "yahoo", "finmind"), default="auto", help="Preferred price provider; unavailable capabilities use alternatives")
    parser.add_argument("--exchange", choices=("all", "twse", "tpex"), default="all")
    parser.add_argument("--kind", choices=("all", "stock", "etf"), default="all")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True, help="Completed date before today, Asia/Taipei")
    parser.add_argument("--limit", type=int, help="Explicit subset limit; report counts disclose omissions")
    parser.add_argument("--benchmark", help="Verified Taiwan stock/ETF symbol for comparative calculations")
    parser.add_argument("--events", type=Path, help="JSON array of verified earnings events; see TAIWAN_ENGINES.md")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        events = json.loads(args.events.read_text()) if args.events else None
        if events is not None and not isinstance(events, list):
            raise data.DataError("Events must be a JSON array")
        report = screen(strategies=args.strategy, start=args.start, end=args.end, symbols=args.symbols,
                        exchange=args.exchange, kind=args.kind, limit=args.limit,
                        benchmark_symbol=args.benchmark, events=events, provider=args.provider)
    except (data.DataError, OSError, ValueError) as exc:
        report = {"status": "error", "error": str(exc) if isinstance(exc, data.DataError) else "Invalid input file or data"}
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    except (OSError, ValueError):
        print("Could not write finite JSON report", file=sys.stderr)
        return 1
    return 0 if report["status"] == "complete" else 2 if report["status"] == "partial" else 1


if __name__ == "__main__":
    raise SystemExit(main())
