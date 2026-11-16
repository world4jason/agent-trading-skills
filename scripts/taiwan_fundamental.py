"""Taiwan fundamental checks with explicit unavailable upstream criteria."""
from __future__ import annotations
from datetime import date
import math
from numbers import Real

try:
    from taiwan_technical import _load
except ImportError:
    from scripts.taiwan_technical import _load

STRATEGIES = ("canslim", "value-dividend", "dividend-growth-pullback", "undervalued-growth", "pead")
STATEMENTS = "TaiwanStockFinancialStatements"
DIVIDENDS = "TaiwanStockDividend"
PER = "TaiwanStockPER"


def required_datasets(strategy):
    if strategy not in STRATEGIES:
        raise ValueError("Unknown fundamental strategy")
    if strategy == "pead":
        return []
    return [STATEMENTS, DIVIDENDS] if strategy == "canslim" else [STATEMENTS, DIVIDENDS, PER]


def _number(value):
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    try:
        result = float(value)
    except (OverflowError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _check(value):
    return {"status": "unknown" if value is None else "pass" if value else "fail"}


def _finish(metrics, checks, warnings):
    missing = [name for name, check in checks.items() if check["status"] == "unknown"]
    failed = any(check["status"] == "fail" for check in checks.values())
    passed = False if failed else None if missing else True
    metrics.update(checks=checks, missing_components=missing,
                   preliminary_match=not failed and any(c["status"] == "pass" for c in checks.values()))
    return {"status": "insufficient_data" if passed is None else "evaluated", "passed": passed,
            "metrics": metrics, "warnings": warnings}


def _quarter_growth(rows, cutoff):
    periods = {}
    conflicts = set()
    for row in rows:
        stamp, field = row.get("date", ""), row.get("type")
        if not isinstance(stamp, str) or stamp > cutoff or field not in ("EPS", "Revenue"):
            continue
        try:
            day = date.fromisoformat(stamp)
        except ValueError:
            continue
        if (day.month, day.day) not in ((3,31),(6,30),(9,30),(12,31)):
            continue
        key = (stamp, field)
        value = _number(row.get("value"))
        if key in periods and periods[key] != value:
            conflicts.add(key)
        periods[key] = value
    if not periods:
        return {}
    latest = max(stamp for stamp, _ in periods)
    previous = str(int(latest[:4])-1) + latest[4:]
    result = {"statement_period": latest, "comparison_period": previous}
    for field, label in (("EPS", "quarterly_eps_yoy_growth_pct"), ("Revenue", "quarterly_revenue_yoy_growth_pct")):
        current, old = periods.get((latest,field)), periods.get((previous,field))
        result[label] = round((current/old-1)*100, 6) if current is not None and old is not None and old > 0 and not ({(latest,field),(previous,field)} & conflicts) else None
    return result


def _anniversary(day, years):
    try:
        return day.replace(year=day.year-years)
    except ValueError:
        return day.replace(year=day.year-years, day=28)


def _dividends(rows, cutoff, price):
    last = date.fromisoformat(cutoff)
    payments = {}
    stock_distribution = False
    for row in rows:
        stamp = row.get("CashExDividendTradingDate")
        if any((_number(row.get(key)) or 0) > 0 for key in ("StockEarningsDistribution", "StockStatutorySurplus")):
            stock_distribution = True
        if not isinstance(stamp, str) or not stamp:
            continue
        try:
            day = date.fromisoformat(stamp)
        except ValueError:
            continue
        cash, capital = _number(row.get("CashEarningsDistribution")), _number(row.get("CashStatutorySurplus"))
        if day > last or cash is None or capital is None or cash < 0 or capital < 0:
            continue
        year = row.get("year")
        if not isinstance(year, str):
            continue
        key = (stamp, year)
        total = cash + capital
        if key in payments and payments[key] != total:
            return {"dividend_data_conflict": True}
        payments[key] = total
    windows = []
    for offset in range(4):
        lower, upper = _anniversary(last,offset+1).isoformat(), _anniversary(last,offset).isoformat()
        values = [amount for (stamp,_), amount in payments.items() if lower < stamp <= upper]
        windows.append(sum(values) if values else None)
    cagr = ((windows[0]/windows[3])**(1/3)-1)*100 if all(v is not None and v > 0 for v in windows) else None
    return {"cash_dividends_ttm": windows[0], "cash_yield_pct": windows[0]/price*100 if windows[0] is not None else None,
            "cash_dividend_cagr_3y_pct": cagr, "ttm_cash_windows": windows,
            "share_basis_change_detected": stock_distribution}


def _pead(listing, bars, events):
    symbol = listing.get("symbol")
    candidates = []
    for event in events or []:
        if not isinstance(event, dict) or (symbol and event.get("symbol") not in (symbol, listing.get("stock_id"))):
            continue
        stamp, timing = event.get("release_date"), event.get("timing")
        if not isinstance(stamp,str) or timing not in ("bmo","amc"):
            continue
        try:
            date.fromisoformat(stamp)
        except ValueError:
            continue
        if stamp <= bars[-1]["date"]:
            candidates.append(event)
    if not candidates:
        return _finish({}, {"verified_earnings_event": _check(None)}, ["Supply symbol, verified release_date and bmo/amc timing; period-end dates are not events"])
    event = max(candidates, key=lambda e:e["release_date"])
    stamp = event["release_date"]
    after = [i for i,b in enumerate(bars) if b["date"] >= stamp] if event["timing"] == "bmo" else [i for i,b in enumerate(bars) if b["date"] > stamp]
    if not after or after[0] == 0:
        return _finish({}, {"event_price_bars": _check(None)}, ["Need both pre-event close and first post-event open"])
    index = after[0]
    gap = (bars[index]["open"] / bars[index-1]["close"] - 1) * 100
    age = (date.fromisoformat(bars[-1]["date"]) - date.fromisoformat(bars[index]["date"])).days
    metrics = {"release_date": stamp, "reaction_date": bars[index]["date"], "earnings_gap_pct": round(gap,6),
               "selection_rule": "initial earnings gap >=3% within five calendar weeks; not a breakout/entry rating"}
    return _finish(metrics, {"earnings_gap": _check(gap >= 3), "watch_window": _check(age <= 35)},
                   ["Event source must be verified by the caller; no automatic Taiwan earnings calendar is inferred"])


def evaluate(strategy, listing, bars, *, datasets, benchmark=None, events=None):
    if strategy not in STRATEGIES:
        raise ValueError("Unknown fundamental strategy")
    if listing.get("kind") == "etf":
        return {"status":"not_applicable", "passed":None, "metrics":{},
                "warnings":["Company earnings/valuation screens do not apply to ETFs; use technical strategies"]}
    if not bars:
        return _finish({}, {"prices":_check(None)}, ["No price data"])
    if strategy == "pead":
        return _pead(listing,bars,events)
    cutoff = bars[-1]["date"]
    metrics = _quarter_growth(datasets.get(STATEMENTS,[]), cutoff)
    distributions = _dividends(datasets.get(DIVIDENDS,[]), cutoff, bars[-1]["close"])
    metrics.update(distributions)
    warnings = ["Statement dates are fiscal periods, not availability timestamps; this is not a point-in-time backtest",
                "Original share bases and corporate actions must be reconciled before investment use"]
    eps, revenue = metrics.get("quarterly_eps_yoy_growth_pct"), metrics.get("quarterly_revenue_yoy_growth_pct")
    if strategy == "canslim":
        current = None if eps is None or revenue is None or metrics.get("share_basis_change_detected") else eps >= 18 and revenue >= 10
        checks = {"C":_check(current), "A":_check(None), "I":_check(None), "L":_check(None), "M":_check(None)}
        metrics["selection_rule"] = "quarterly EPS >=18% and revenue >=10%; full CANSLIM requires remaining verified components"
        return _finish(metrics, checks, warnings + ["Annual comparable EPS, institutional sponsorship, universe rank and market regime unavailable; no complete CANSLIM pass"])
    ratios = [r for r in datasets.get(PER,[]) if r.get("date") == cutoff]
    ratio = ratios[-1] if ratios else {}
    pe, pb = _number(ratio.get("PER")), _number(ratio.get("PBR"))
    metrics.update(pe_ratio=pe, pb_ratio=pb)
    if strategy == "undervalued-growth":
        checks = {"positive_trailing_pe":_check(pe > 0 if pe is not None else None),
                  "quarterly_revenue_growth":_check(revenue > 0 if revenue is not None else None),
                  "dated_forward_estimates":_check(None), "normalized_per_share_growth":_check(None)}
        return _finish(metrics, checks, warnings + ["FinMind trailing PE cannot replace dated forward estimates; no forward valuation ranking"])
    cash_yield, growth = metrics.get("cash_yield_pct"), metrics.get("cash_dividend_cagr_3y_pct")
    is_value = strategy == "value-dividend"
    checks = {"cash_yield":_check(cash_yield >= (3 if is_value else 1.5) if cash_yield is not None else None),
              "dividend_growth":_check(growth >= (4 if is_value else 12) if growth is not None else None),
              "financial_health":_check(None), "comparable_annual_eps_growth":_check(None)}
    if distributions.get("share_basis_change_detected"):
        checks["dividend_growth"] = _check(None)
    if is_value:
        checks.update(pe=_check(0 < pe <= 20 if pe is not None else None), pb=_check(0 < pb <= 2 if pb is not None else None))
    else:
        module = _load("dividend-growth-pullback-screener/scripts/screen_dividend_growth_rsi.py")
        rsi = module.RSICalculator.calculate_rsi([b["close"] for b in bars])
        metrics["rsi14"] = rsi
        checks["rsi_pullback"] = _check(rsi <= 40 if rsi is not None else None)
    return _finish(metrics, checks, warnings + ["Cash distributions use ex-dividend dates; empty windows are unknown, not zero",
                                               "Financial health and comparable annual EPS remain required; preliminary matches are not full passes"])
