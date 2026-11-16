"""Taiwan price-pattern adapters reusing the upstream calculation functions."""
from __future__ import annotations
from argparse import Namespace
from dataclasses import asdict
from functools import lru_cache
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
STRATEGIES = ("vcp", "momentum-burst", "exhaustion-hammer", "parabolic")


@lru_cache(maxsize=None)
def _load(relative):
    path = ROOT / "skills" / relative
    name = "_taiwan_" + relative.replace("/", "_").replace("-", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    # Upstream standalone calculators use unqualified sibling imports.
    paths = [path.parent, path.parent.parent]
    names = {p.stem for directory in paths for p in directory.glob("*.py")}
    previous = {key: sys.modules.pop(key) for key in names if key in sys.modules}
    old_path = sys.path[:]
    try:
        sys.path[:0] = [str(p) for p in paths]
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
        for key in names:
            sys.modules.pop(key, None)
        sys.modules.update(previous)
    return module


def _result(passed, metrics, warnings=()):
    return {"status": "evaluated", "passed": bool(passed), "metrics": metrics, "warnings": list(warnings)}


def evaluate(strategy, listing, bars, *, benchmark=None, expected_session=None):
    if strategy not in STRATEGIES:
        raise ValueError("Unknown technical strategy")
    minimum = {"vcp": 260, "momentum-burst": 25, "exhaustion-hammer": 62, "parabolic": 51}[strategy]
    if len(bars) < minimum or (expected_session and bars[-1]["date"] != expected_session):
        return {"status": "insufficient_data", "passed": None, "metrics": {},
                "warnings": [f"Need {minimum} daily bars ending on the requested Taiwan session"]}
    recent = list(reversed(bars))
    if strategy == "vcp":
        base = "vcp-screener/scripts/calculators/"
        pattern = _load(base + "vcp_pattern_calculator.py").calculate_vcp_pattern(recent)
        trend = _load(base + "trend_template_calculator.py").calculate_trend_template(
            recent, {"price": bars[-1]["close"], "yearHigh": max(b["high"] for b in bars[-252:]),
                     "yearLow": min(b["low"] for b in bars[-252:])})
        volume = _load(base + "volume_pattern_calculator.py").calculate_volume_pattern(
            recent, pattern.get("pivot_price"), pattern.get("contractions"))
        metrics = {"pattern": pattern, "trend": trend, "volume": volume,
                   "selection_rule": "valid VCP and original price-trend template; no universe RS gate"}
        warnings = ["Price-pattern candidate only; full-universe RS rank and execution readiness not evaluated"]
        if benchmark and {b.get("adjustment") for b in benchmark} != {b.get("adjustment") for b in bars}:
            warnings.append("Benchmark adjustment basis differs; relative strength not calculated")
            benchmark = None
        if benchmark:
            by_date = {b["date"]: b for b in benchmark}
            aligned = [b for b in bars if b["date"] in by_date]
            if len(aligned) >= 253:
                relative = _load(base + "relative_strength_calculator.py").calculate_relative_strength(
                    list(reversed(aligned)), [by_date[b["date"]] for b in reversed(aligned)])
                relative.pop("rs_rank_estimate", None)
                relative.pop("score", None)
                for period in relative.get("period_details", []):
                    if "sp500_return_pct" in period:
                        period["benchmark_return_pct"] = period.pop("sp500_return_pct")
                metrics["benchmark_relative_strength"] = relative
            else:
                warnings.append("Insufficient common dates for relative strength")
        return _result(pattern.get("valid_vcp") and trend["passed"], metrics, warnings)
    if strategy == "momentum-burst":
        module = _load("stockbee-momentum-burst-screener/scripts/screen_momentum_burst.py")
        normalized = module.normalize_bars(recent)
        args = Namespace(min_volume=100_000, four_pct_threshold=4.0, dollar_threshold=float("inf"),
                         nine_million_volume=9_000_000, max_prev_day_gain_for_range=2.0)
        trigger = module.detect_triggers(normalized, args)
        base = module.detect_base_profile(normalized, 3, 20, 15.0, 5.0)
        risk = (bars[-1]["close"] - bars[-1]["low"]) / bars[-1]["close"] * 100
        checks = {"price_volume_trigger": bool(set(trigger.trigger_tags) & {"4pct_breakout", "range_expansion"}),
                  "volume_floor": bars[-1]["volume"] >= 100_000, "risk_distance": 0 < risk <= 10}
        metrics = {"trigger": asdict(trigger), "base": asdict(base), "checks": checks,
                   "risk_pct_to_low": risk, "volume_unit": "shares", "price_unit": "TWD"}
        return _result(all(checks.values()), metrics,
                       ["USD dollar-breakout trigger disabled; original percentage/volume trigger rules retained",
                        "Pattern screen only; market regime and trade execution not evaluated"])
    if strategy == "exhaustion-hammer":
        module = _load("stockbee-exhaustion-hammer-screener/scripts/screen_exhaustion_hammer.py")
        normalized = module.normalize_bars(recent)
        args = Namespace(recent_high_lookback=40, undercut_lookback=5, min_lower_wick_pct=40.0,
                         max_body_pct=35.0, max_upper_wick_pct=35.0, min_close_location_pct=60.0,
                         min_lower_wick_to_body=1.5, min_recovery_from_low_pct=2.0)
        hammer = module.detect_hammer_profile(normalized, args)
        pullback = module.detect_pullback_profile(normalized, args)
        risk = (bars[-1]["close"] - bars[-1]["low"] * .999) / bars[-1]["close"] * 100
        checks = {"lower_wick": hammer.lower_wick_pct_of_range >= 40,
                  "body": hammer.body_pct_of_range <= 35, "close_location": hammer.close_location_pct >= 60,
                  "wick_body": hammer.lower_wick_to_body >= 1.5, "recovery": hammer.recovery_from_low_pct >= 2,
                  "pullback": 6 <= abs(pullback.pullback_pct_from_high) <= 35,
                  "high_age": 3 <= pullback.days_since_recent_high <= 30, "risk_distance": 0 < risk <= 12,
                  "volume_floor": bars[-1]["volume"] >= 100_000}
        return _result(all(checks.values()), {"hammer": asdict(hammer), "pullback": asdict(pullback),
                       "checks": checks, "risk_pct_to_stop_reference": risk, "price_unit": "TWD"},
                       ["Pattern screen only; USD size/liquidity gates removed; institutional quality is not inferred"])
    base = "parabolic-short-trade-planner/scripts/calculators/"
    closes = [b["close"] for b in bars]
    extension = _load(base + "ma_extension_calculator.py").calculate_ma_extension(
        closes, [b["high"] for b in bars], [b["low"] for b in bars])
    acceleration = _load(base + "acceleration_calculator.py").calculate_acceleration([b["open"] for b in bars], closes)
    checks = {"ma20_extension": (extension["ext_20dma_pct"] or 0) >= 25,
              "atr_extension": (extension["ext_20dma_atr"] or 0) >= 4,
              "return_5d": (acceleration["return_5d_pct"] or 0) >= 30}
    return _result(all(checks.values()), {"extension": extension, "acceleration": acceleration, "checks": checks},
                   ["Overextension watchlist only; no borrow availability, short-sale eligibility or short trade plan"])
