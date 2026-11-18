#!/usr/bin/env python3
"""Produce auditable candidate, missing-data and complete-result tables."""

import argparse
import csv
import gzip
import json
from collections import Counter
from pathlib import Path


def load(path):
    if str(path).endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(Path(path).read_text())


def gaps(row):
    m = row.get("metrics", {})
    missing = list(m.get("missing_components", []))
    if row["status"] in ("insufficient_data", "evaluation_error", "not_processed"):
        missing.extend(row.get("warnings", []) or [row["status"]])
    if row["strategy"] == "pead" and m.get("score_completeness") == "partial":
        missing.append("PEAD weighted score incomplete")
    return list(dict.fromkeys(missing))


def candidate(row):
    return row.get("passed") is True and not gaps(row)


def build(directory):
    directory = Path(directory)
    universe = load(directory / "universe.json")
    run = load(directory / "run.json")
    results = []
    processed = 0
    price_rows = []
    for listing in universe["listings"]:
        path = directory / "results" / (listing["symbol"] + ".json.gz")
        error = directory / "errors" / (listing["symbol"] + ".json")
        if path.exists() and not error.exists():
            rows = load(path)
            for row in rows:
                row["name"] = listing["name"]
            results.extend(rows)
            processed += 1
        else:
            reason = (
                "Worker error: " + load(error)["worker_error"]
                if error.exists()
                else "Not processed yet"
            )
            for strategy in run["strategies"]:
                results.append(
                    {
                        **{
                            k: listing[k]
                            for k in ("symbol", "name", "market", "exchange", "kind", "currency")
                        },
                        "strategy": strategy,
                        "status": "not_processed",
                        "passed": None,
                        "metrics": {},
                        "warnings": [reason],
                    }
                )
        input_path = directory / "inputs" / (listing["symbol"] + ".json.gz")
        if input_path.exists():
            inputs = load(input_path)
            price = inputs["price"]
            price_rows.append(
                {
                    **{k: listing[k] for k in ("market", "exchange", "symbol", "name", "kind")},
                    "price_status": price["status"],
                    "source": price.get("source"),
                    "as_of": price.get("as_of"),
                    "error": price.get("error", ""),
                    "warnings": "; ".join(price.get("warnings", [])),
                }
            )
    for market in ("tw", "us"):
        ranked = [
            r
            for r in results
            if r["market"] == market
            and r["strategy"] == "undervalued-growth"
            and r["metrics"].get("ranking_eligible") is True
        ]
        ranked.sort(key=lambda r: (-r["metrics"]["ranking_score"], r["symbol"]))
        previous = None
        rank = 0
        for index, row in enumerate(ranked, 1):
            score = row["metrics"]["ranking_score"]
            if score != previous:
                rank = index
            row["metrics"].update(
                rank=rank,
                ranked_universe_size=len(ranked),
                ranking_scope="eligible estimates in " + market + " directory",
            )
            previous = score
    columns = [
        "market",
        "exchange",
        "symbol",
        "name",
        "kind",
        "currency",
        "strategy",
        "status",
        "passed",
        "complete_candidate",
        "as_of",
        "price_source",
        "fundamentals_as_of",
        "fundamentals_retrieved_at",
        "rank",
        "ranking_score",
        "canslim_score",
        "pead_score",
        "missing",
        "warnings",
    ]
    all_rows = []
    for row in results:
        m = row["metrics"]
        flat = {k: row.get(k) for k in columns}
        flat.update(
            complete_candidate=candidate(row),
            rank=m.get("rank"),
            ranking_score=m.get("ranking_score"),
            canslim_score=m.get("canslim_score"),
            pead_score=m.get("composite_score"),
            missing="; ".join(gaps(row)),
            warnings="; ".join(row.get("warnings", []) + row.get("price_warnings", [])),
        )
        all_rows.append(flat)

    def write_csv(name, rows, fields):
        with (directory / name).open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    write_csv(
        "price-coverage.csv",
        price_rows,
        [
            "market",
            "exchange",
            "symbol",
            "name",
            "kind",
            "price_status",
            "source",
            "as_of",
            "error",
            "warnings",
        ],
    )
    write_csv("all-results.csv", all_rows, columns)
    write_csv("candidates.csv", [r for r in all_rows if r["complete_candidate"]], columns)
    write_csv("missing-data.csv", [r for r in all_rows if r["missing"]], columns)
    write_csv("excluded-securities.csv", universe["excluded"], ["symbol", "name", "reason"])
    summary = {
        "start": run["start"],
        "end": run["end"],
        "requested_symbols": len(universe["listings"]),
        "processed_symbols": processed,
        "not_processed_symbols": len(universe["listings"]) - processed,
        "scan_status": "finished" if processed == len(universe["listings"]) else "incomplete",
        "data_status": "partial" if any(gaps(r) for r in results) else "complete",
        "evaluation_errors": sum(r["status"] == "evaluation_error" for r in results),
        "engine_revisions": sorted(
            {
                r.get("engine_revision", "unversioned")
                for r in results
                if r["status"] != "not_processed"
            }
        ),
        "coverage": {},
        "strategy_results": {},
        "exclusions": dict(Counter(r["reason"] for r in universe["excluded"])),
    }
    for market in ("tw", "us"):
        group = [r for r in results if r["market"] == market]
        listing = [r for r in universe["listings"] if r["market"] == market]
        summary["coverage"][market] = {
            "symbols": len(listing),
            "symbols_with_prices": sum(
                r["market"] == market and r["price_status"] == "ok" for r in price_rows
            ),
            "symbols_without_prices": sum(
                r["market"] == market and r["price_status"] != "ok" for r in price_rows
            ),
            "stock": sum(r["kind"] == "stock" for r in listing),
            "etf": sum(r["kind"] == "etf" for r in listing),
            "symbols_with_missing_data": len({r["symbol"] for r in group if gaps(r)}),
            "symbols_with_complete_candidate": len({r["symbol"] for r in group if candidate(r)}),
        }
        summary["strategy_results"][market] = {}
        for strategy in run["strategies"]:
            subset = [r for r in group if r["strategy"] == strategy]
            summary["strategy_results"][market][strategy] = {
                **dict(Counter(r["status"] for r in subset)),
                "qualified": sum(candidate(r) for r in subset),
                "with_missing_data": sum(bool(gaps(r)) for r in subset),
            }
    (directory / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    with gzip.open(directory / "all-results.json.gz", "wt", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, allow_nan=False)
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory", type=Path)
    args = p.parse_args()
    print(json.dumps(build(args.directory), ensure_ascii=False, indent=2))
