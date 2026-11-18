"""Taiwan fundamental checks with explicit unavailable upstream criteria."""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from numbers import Real
from zoneinfo import ZoneInfo

try:
    from taiwan_technical import _load
except ImportError:
    from scripts.taiwan_technical import _load

STRATEGIES = ("canslim", "value-dividend", "dividend-growth-pullback", "undervalued-growth", "pead")
STATEMENTS = "TaiwanStockFinancialStatements"
DIVIDENDS = "TaiwanStockDividend"
PER = "TaiwanStockPER"
BALANCE = "TaiwanStockBalanceSheet"
CASHFLOW = "TaiwanStockCashFlowsStatement"


def required_datasets(strategy):
    if strategy not in STRATEGIES:
        raise ValueError("Unknown fundamental strategy")
    if strategy == "pead":
        return []
    if strategy == "canslim":
        return [STATEMENTS, DIVIDENDS]
    return [STATEMENTS, DIVIDENDS, PER, BALANCE, CASHFLOW]


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
    metrics.update(
        checks=checks,
        missing_components=missing,
        preliminary_match=not failed and any(c["status"] == "pass" for c in checks.values()),
    )
    return {
        "status": "insufficient_data" if passed is None else "evaluated",
        "passed": passed,
        "metrics": metrics,
        "warnings": warnings,
    }


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
        if (day.month, day.day) not in ((3, 31), (6, 30), (9, 30), (12, 31)):
            continue
        key = (stamp, field)
        value = _number(row.get("value"))
        if key in periods and periods[key] != value:
            conflicts.add(key)
        periods[key] = value
    if not periods:
        return {}
    latest = max(stamp for stamp, _ in periods)
    previous = str(int(latest[:4]) - 1) + latest[4:]
    result = {"statement_period": latest, "comparison_period": previous}
    for field, label in (
        ("EPS", "quarterly_eps_yoy_growth_pct"),
        ("Revenue", "quarterly_revenue_yoy_growth_pct"),
    ):
        current, old = periods.get((latest, field)), periods.get((previous, field))
        result[label] = (
            round((current / old - 1) * 100, 6)
            if current is not None
            and old is not None
            and old > 0
            and not ({(latest, field), (previous, field)} & conflicts)
            else None
        )
    return result


def _anniversary(day, years):
    try:
        return day.replace(year=day.year - years)
    except ValueError:
        return day.replace(year=day.year - years, day=28)


def _dividends(rows, cutoff, price):
    last = date.fromisoformat(cutoff)
    payments = {}
    stock_distribution = False
    for row in rows:
        stamp = row.get("CashExDividendTradingDate")
        if not isinstance(stamp, str) or not stamp:
            continue
        try:
            day = date.fromisoformat(stamp)
        except ValueError:
            continue
        if _anniversary(last, 4) < day <= last and any(
            (_number(row.get(key)) or 0) > 0
            for key in ("StockEarningsDistribution", "StockStatutorySurplus")
        ):
            stock_distribution = True
        cash, capital = (
            _number(row.get("CashEarningsDistribution")),
            _number(row.get("CashStatutorySurplus")),
        )
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
        lower, upper = (
            _anniversary(last, offset + 1).isoformat(),
            _anniversary(last, offset).isoformat(),
        )
        values = [amount for (stamp, _), amount in payments.items() if lower < stamp <= upper]
        windows.append(sum(values) if values else None)
    cagr = (
        ((windows[0] / windows[3]) ** (1 / 3) - 1) * 100
        if all(v is not None and v > 0 for v in windows)
        else None
    )
    return {
        "cash_dividends_ttm": windows[0],
        "cash_yield_pct": windows[0] / price * 100 if windows[0] is not None else None,
        "cash_dividend_cagr_3y_pct": cagr,
        "ttm_cash_windows": windows,
        "share_basis_change_detected": stock_distribution,
    }


def _snapshot_state(snapshot, listing, bars, sessions):
    if not isinstance(snapshot, dict) or snapshot.get("source") != "yahoo":
        return False, "Yahoo snapshot unavailable"
    symbol = listing.get("symbol")
    if symbol and snapshot.get("symbol") != symbol:
        return False, "Yahoo snapshot symbol mismatch"
    try:
        as_of = date.fromisoformat(snapshot["as_of"])
        retrieved = datetime.fromisoformat(snapshot["retrieved_at"].replace("Z", "+00:00"))
        cutoff = date.fromisoformat(bars[-1]["date"])
    except (KeyError, TypeError, ValueError, AttributeError):
        return False, "Yahoo snapshot dates are invalid"
    if retrieved.tzinfo is None:
        return False, "Yahoo snapshot retrieval time has no timezone"
    if retrieved.astimezone(ZoneInfo(listing.get("timezone", "Asia/Taipei"))).date() != as_of:
        return False, "Yahoo snapshot as-of date does not match its retrieval date"
    if retrieved.astimezone(timezone.utc) > datetime.now(timezone.utc) + timedelta(minutes=5):
        return False, "Yahoo snapshot retrieval time is in the future"
    if cutoff > as_of:
        return False, "Price bar is future-dated relative to Yahoo snapshot"
    if (as_of - cutoff).days > 7:
        return False, "Current Yahoo snapshot rejected for historical price bars"
    if sessions:
        available = {row.get("date") if isinstance(row, dict) else row for row in sessions}
        if available and cutoff.isoformat() not in available:
            return False, "Price bar does not match the supplied Taiwan sessions"
    return True, None


def _yahoo_rows(snapshot, key, cutoff, *, annual=False):
    if not isinstance(snapshot, dict):
        return []
    rows = [
        row
        for row in snapshot.get(key, [])
        if isinstance(row, dict) and isinstance(row.get("date"), str) and row["date"] <= cutoff
    ]
    return sorted(rows, key=lambda row: row["date"], reverse=True)


def _value(row, names):
    return next((value for name in names if (value := _number(row.get(name))) is not None), None)


def _growth(current, previous):
    if current is None or previous is None or previous <= 0:
        return None
    return (current - previous) / previous * 100


def _finmind_quarter_rows(rows, cutoff):
    periods, conflicts = {}, set()
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        stamp, field = row.get("date"), row.get("type")
        if not isinstance(stamp, str) or stamp > cutoff or field not in ("EPS", "Revenue"):
            continue
        try:
            day = date.fromisoformat(stamp)
        except ValueError:
            continue
        if (day.month, day.day) not in ((3, 31), (6, 30), (9, 30), (12, 31)):
            continue
        value = _number(row.get("value"))
        key = (stamp, field)
        if key in periods and periods[key] != value:
            conflicts.add(key)
        periods[key] = value
    dates = sorted(
        {stamp for stamp, field in periods if field == "EPS" and (stamp, "Revenue") in periods},
        reverse=True,
    )
    for stamp in dates:
        day = date.fromisoformat(stamp)
        try:
            old = day.replace(year=day.year - 1).isoformat()
        except ValueError:
            continue
        keys = [(stamp, field) for field in ("EPS", "Revenue")] + [
            (old, field) for field in ("EPS", "Revenue")
        ]
        if any(key in conflicts for key in keys):
            continue
        values = [periods.get(key) for key in keys]
        if all(value is not None for value in values):
            return {
                "current_period": stamp,
                "comparison_period": old,
                "eps": values[0],
                "old_eps": values[2],
                "revenue": values[1],
                "old_revenue": values[3],
                "eps_growth": _growth(values[0], values[2]),
                "revenue_growth": _growth(values[1], values[3]),
                "eps_source": "finmind",
                "revenue_source": "finmind",
                "eps_field": "EPS",
                "revenue_field": "Revenue",
            }
    return None


def _yahoo_quarter_rows(rows):
    if not rows:
        return None
    by_date = {row["date"]: row for row in rows}
    stamp = max(by_date)
    day = date.fromisoformat(stamp)
    # Fiscal 52/53-week quarters need not end on a calendar quarter-end.
    matches = [old for old in by_date if abs((day - date.fromisoformat(old)).days - 365) <= 14]
    if len(matches) != 1:
        return None
    old = matches[0]
    current, previous = by_date[stamp], by_date[old]

    def pair(fields):
        for field in fields:
            first, second = _number(current.get(field)), _number(previous.get(field))
            if first is not None and second is not None:
                return first, second, field
        field = fields[0]
        return _number(current.get(field)), _number(previous.get(field)), field

    eps, old_eps, eps_field = pair(("Diluted EPS", "Basic EPS"))
    revenue, old_revenue, revenue_field = pair(("Total Revenue", "Operating Revenue"))
    return {
        "current_period": stamp,
        "comparison_period": old,
        "eps": eps,
        "old_eps": old_eps,
        "revenue": revenue,
        "old_revenue": old_revenue,
        "eps_growth": _growth(eps, old_eps),
        "revenue_growth": _growth(revenue, old_revenue),
        "eps_source": "yahoo.quarterly_income",
        "revenue_source": "yahoo.quarterly_income",
        "eps_field": eps_field,
        "revenue_field": revenue_field,
    }


def _quarter_data(rows, snapshot, cutoff, preference, snapshot_usable):
    finmind = _finmind_quarter_rows(rows, cutoff)
    yahoo = _yahoo_quarter_rows(
        _yahoo_rows(snapshot, "quarterly_income", cutoff) if snapshot_usable else []
    )
    ordered = (yahoo, finmind) if preference == "yahoo" else (finmind, yahoo)
    return next((data for data in ordered if data), None)


def _finmind_annual_rows(rows, cutoff):
    periods = {}
    for row in rows or []:
        if not isinstance(row, dict) or row.get("type") not in ("EPS", "Revenue"):
            continue
        stamp = row.get("date")
        if not isinstance(stamp, str) or stamp > cutoff or stamp[5:] != "12-31":
            continue
        try:
            date.fromisoformat(stamp)
        except ValueError:
            continue
        periods.setdefault(stamp[:4], {})[row["type"]] = _number(row.get("value"))
    return [
        {"year": year, "eps": data.get("EPS"), "revenue": data.get("Revenue")}
        for year, data in sorted(periods.items(), reverse=True)
    ]


def _yahoo_annual_rows(rows):
    for eps_field in ("Diluted EPS", "Basic EPS"):
        annual = []
        for row in rows:
            revenue = _value(row, ("Total Revenue", "Operating Revenue"))
            eps = _number(row.get(eps_field))
            if eps is not None and revenue is not None:
                annual.append(
                    {
                        "year": row["date"][:4],
                        "date": row["date"],
                        "eps": eps,
                        "revenue": revenue,
                        "eps_field": eps_field,
                    }
                )
        if len(annual) >= 4:
            return annual
    return []


def _annual_data(rows, snapshot, cutoff, preference, snapshot_usable):
    finmind = _finmind_annual_rows(rows, cutoff)
    yahoo = _yahoo_annual_rows(
        _yahoo_rows(snapshot, "annual_income", cutoff, annual=True) if snapshot_usable else []
    )
    ordered = (yahoo, finmind) if preference != "finmind" else (finmind, yahoo)
    for data in ordered:
        if len(data) >= 4 and all(
            data[i]["year"] == str(int(data[0]["year"]) - i) for i in range(4)
        ):
            return data[:4], "yahoo.annual_income" if data is yahoo else "finmind"
    return [], None


def _annual_metrics(rows, snapshot, cutoff, preference, snapshot_usable):
    data, source = _annual_data(rows, snapshot, cutoff, preference, snapshot_usable)
    result = {
        "annual_eps_source": source,
        "annual_eps_values": None,
        "annual_eps_cagr_3y_pct": None,
        "annual_revenue_cagr_3y_pct": None,
        "annual_eps_stable": None,
        "annual_eps_growth_score": None,
    }
    if not data:
        return result
    result.update(
        annual_eps_period_start=data[3].get("date", f"{data[3]['year']}-12-31"),
        annual_eps_period_end=data[0].get("date", f"{data[0]['year']}-12-31"),
    )
    eps = [row["eps"] for row in reversed(data)]
    revenue = [row["revenue"] for row in reversed(data)]
    result["annual_eps_values"] = eps
    if any(value is None for value in eps):
        return result
    if any(value <= 0 for value in eps):
        result["annual_eps_growth_score"] = 0
        result["annual_eps_stable"] = False
        return result
    if revenue[0] is None or revenue[-1] is None or revenue[0] <= 0 or revenue[-1] <= 0:
        return result
    eps_cagr = ((eps[-1] / eps[0]) ** (1 / 3) - 1) * 100
    revenue_cagr = ((revenue[-1] / revenue[0]) ** (1 / 3) - 1) * 100
    stable = all(eps[i] >= eps[i - 1] for i in range(1, len(eps)))
    scorer = _load("canslim-screener/scripts/calculators/growth_calculator.py").score_annual_growth
    result.update(
        annual_eps_cagr_3y_pct=round(eps_cagr, 6),
        annual_revenue_cagr_3y_pct=round(revenue_cagr, 6),
        annual_eps_stable=stable,
        annual_eps_growth_score=scorer(eps_cagr, revenue_cagr, stable),
    )
    return result


def _basis_change_between(dividend_rows, snapshot, start, end, snapshot_usable):
    for row in dividend_rows or []:
        if not isinstance(row, dict):
            continue
        stamp = row.get("CashExDividendTradingDate")
        if (
            isinstance(stamp, str)
            and start < stamp <= end
            and any(
                (_number(row.get(key)) or 0) > 0
                for key in ("StockEarningsDistribution", "StockStatutorySurplus")
            )
        ):
            return True
    if snapshot_usable:
        return any(
            isinstance(row, dict)
            and isinstance(row.get("date"), str)
            and start < row["date"] <= end
            and _number(row.get("ratio")) not in (None, 0, 1)
            for row in snapshot.get("splits", [])
        )
    return False


def _component_check(component, score, scorer):
    if score is None:
        return _check(None)
    test_scores = {name: 100 for name in "CANS LIM".replace(" ", "")}
    test_scores[component] = score
    failed = scorer.check_minimum_thresholds_phase3(
        **{f"{name.lower()}_score": value for name, value in test_scores.items()}
    )
    return _check(component not in failed["failed_components"])


def _ownership_pct(snapshot):
    info = snapshot.get("info", {}) if isinstance(snapshot, dict) else {}
    value = _number(info.get("heldPercentInstitutions"))
    if value is None and isinstance(snapshot, dict):
        summary = snapshot.get("institutional_summary")
        value = (
            _number(summary.get("institutionsPercentHeld")) if isinstance(summary, dict) else None
        )
    if value is None or value < 0:
        return None
    return value * 100


def _canslim(rows, snapshot, bars, benchmark, cutoff, preference, snapshot_usable):
    quarter = _quarter_data(rows, snapshot, cutoff, preference, snapshot_usable)
    annual = _annual_metrics(rows, snapshot, cutoff, preference, snapshot_usable)
    metrics = {**(quarter or {}), **annual}
    if quarter:
        metrics.update(
            quarterly_eps_source=quarter["eps_source"],
            quarterly_revenue_source=quarter["revenue_source"],
        )
    earnings = _load("canslim-screener/scripts/calculators/earnings_calculator.py")
    scores = {
        "C": earnings.score_current_earnings(quarter["eps_growth"], quarter["revenue_growth"])
        if quarter and quarter["eps_growth"] is not None and quarter["revenue_growth"] is not None
        else None,
        "A": annual["annual_eps_growth_score"],
    }

    if quarter and quarter["eps"] is not None and quarter["eps"] <= 0:
        scores["C"] = 0

    n_score = s_score = l_score = m_score = None
    if len(bars) >= 252:
        recent = bars[-252:]
        avg_volume = sum(_number(row.get("volume")) or 0 for row in recent[-51:-1]) / 50
        if avg_volume > 0:
            n = _load("canslim-screener/scripts/calculators/new_highs_calculator.py")
            n_score = n.calculate_newness(
                {
                    "price": _number(bars[-1].get("close")),
                    "yearHigh": max((_number(row.get("high")) or 0) for row in recent),
                    "yearLow": min((_number(row.get("low")) or 0) for row in recent),
                    "volume": _number(bars[-1].get("volume")),
                    "avgVolume": avg_volume,
                }
            )["score"]
    supply = _load("canslim-screener/scripts/calculators/supply_demand_calculator.py")
    s_result = supply.calculate_supply_demand({"historical": list(reversed(bars))})
    if not s_result.get("error"):
        s_score = s_result.get("score")

    if benchmark:
        by_date = {
            row.get("date"): row
            for row in benchmark
            if isinstance(row, dict) and isinstance(row.get("date"), str) and row["date"] <= cutoff
        }
        stock_by_date = {row.get("date"): row for row in bars if row.get("date") <= cutoff}
        common_dates = sorted(set(by_date) & set(stock_by_date))
        if len(common_dates) >= 50:
            aligned_stock = [stock_by_date[stamp] for stamp in common_dates]
            aligned_bench = [by_date[stamp] for stamp in common_dates]
            leadership = _load("canslim-screener/scripts/calculators/leadership_calculator.py")
            l_result = leadership.calculate_leadership(
                aligned_stock,
                sp500_historical=aligned_bench,
                rs_benchmark=(snapshot or {}).get("benchmark_symbol", "^TWII"),
            )
            if (
                l_result.get("weighted_relative_performance") is not None
                or l_result.get("relative_performance") is not None
            ):
                l_score = l_result.get("score")
            closes = [_number(row.get("close")) for row in aligned_bench[-50:]]
            if all(value is not None and value > 0 for value in closes):
                market = _load("canslim-screener/scripts/calculators/market_calculator.py")
                ema = market.calculate_ema(closes[::-1], 50)
                distance = (closes[-1] / ema - 1) * 100
                trend = (
                    "strong_uptrend"
                    if distance >= 2
                    else "uptrend"
                    if distance >= 0
                    else "choppy"
                    if distance >= -2
                    else "downtrend"
                    if distance >= -5
                    else "bear_market"
                )
                m_score = market.score_market_direction(trend, None)
                metrics.update(
                    benchmark_50ema=ema,
                    benchmark_distance_from_50ema_pct=round(distance, 6),
                    market_trend=trend,
                )
            metrics.update(leadership=l_result)
    metrics["supply_demand"] = s_result
    scores.update(N=n_score, S=s_score, L=l_score, M=m_score)

    holders = snapshot.get("institutional_holders", []) if snapshot_usable else []
    names = {
        str(row.get("Holder", row.get("holder", ""))).strip().casefold()
        for row in holders
        if isinstance(row, dict) and row.get("Holder", row.get("holder"))
    }
    observed = len(names)
    ownership = _ownership_pct(snapshot) if snapshot_usable else None
    i_score = None
    summary = snapshot.get("institutional_summary") if snapshot_usable else None
    reported_count = (
        _number(summary.get("institutionsCount")) if isinstance(summary, dict) else None
    )
    if reported_count is not None and (
        reported_count < observed or not reported_count.is_integer()
    ):
        reported_count = None
    count = int(reported_count) if reported_count is not None else observed
    if reported_count is not None:
        institutional = _load("canslim-screener/scripts/calculators/institutional_calculator.py")
        i_score = institutional.score_institutional_sponsorship(count, ownership, False, None)
    scores["I"] = i_score
    metrics.update(
        institutional_holders_observed_minimum=observed if holders else None,
        institutional_holders_reported_total=int(reported_count)
        if reported_count is not None
        else None,
        institutional_count_source="yahoo.major_holders"
        if reported_count is not None
        else "observed lower bound",
        institutional_ownership_pct=ownership,
        institutional_score=i_score,
        canslim_component_scores=scores,
    )

    scorer = _load("canslim-screener/scripts/scorer.py")
    checks = {key: _component_check(key, score, scorer) for key, score in scores.items()}
    if all(score is not None for score in scores.values()):
        metrics["canslim_score"] = scorer.calculate_composite_score_phase3(
            **{f"{key.lower()}_score": score for key, score in scores.items()}
        )["composite_score"]
    else:
        metrics["canslim_score"] = None
    metrics["selection_rule"] = (
        "Original seven CANSLIM component scores and minimum thresholds; composite only when all seven are measurable"
    )
    return checks, metrics


def _latest_finmind(rows, cutoff, aliases, *, annual=False):
    dates = sorted(
        {
            row.get("date")
            for row in rows or []
            if isinstance(row, dict) and isinstance(row.get("date"), str) and row["date"] <= cutoff
        },
        reverse=True,
    )
    for stamp in dates:
        if annual and stamp[5:] != "12-31":
            continue
        try:
            date.fromisoformat(stamp)
        except ValueError:
            continue
        result = {}
        for row in rows:
            if not isinstance(row, dict) or row.get("date") != stamp:
                continue
            field = "".join(ch for ch in str(row.get("type", "")).casefold() if ch.isalnum())
            for key, names in aliases.items():
                if field in names:
                    result[key] = _number(row.get("value"))
        if result:
            return result, stamp
    return {}, None


def _health(snapshot, datasets, cutoff, usable, preference, sector):
    bal_aliases = {
        "debt": {"totaldebt", "totaldebtcurrentandnoncurrent"},
        "equity": {
            "stockholdersequity",
            "totalequitygrossminorityinterest",
            "equityattributabletoownersofparent",
            "totalequity",
        },
        "current_assets": {"currentassets", "totalcurrentassets"},
        "current_liabilities": {"currentliabilities", "totalcurrentliabilities"},
    }
    fin_balance, fin_balance_date = _latest_finmind(datasets.get(BALANCE, []), cutoff, bal_aliases)
    quarterly_balance = _yahoo_rows(snapshot, "quarterly_balance", cutoff) if usable else []
    annual_balance = _yahoo_rows(snapshot, "annual_balance", cutoff) if usable else []
    yahoo_balance_rows = quarterly_balance + annual_balance
    yahoo_balance_rows.sort(key=lambda row: row["date"], reverse=True)
    yahoo_balance_row = yahoo_balance_rows[0] if yahoo_balance_rows else {}
    yahoo_balance = {}
    for key, fields in (
        ("debt", ("Total Debt",)),
        (
            "equity",
            ("Stockholders Equity", "Total Equity Gross Minority Interest", "Common Stock Equity"),
        ),
        ("current_assets", ("Current Assets",)),
        ("current_liabilities", ("Current Liabilities",)),
    ):
        yahoo_balance[key] = _value(yahoo_balance_row, fields) if yahoo_balance_rows else None
    fin_complete = all(
        fin_balance.get(key) is not None
        for key in ("debt", "equity", "current_assets", "current_liabilities")
    )
    yahoo_complete = all(
        yahoo_balance.get(key) is not None
        for key in ("debt", "equity", "current_assets", "current_liabilities")
    )
    use_fin = fin_complete and (preference == "finmind" or not yahoo_complete)
    balance = fin_balance if use_fin else yahoo_balance
    balance_source = (
        "finmind"
        if use_fin
        else "yahoo.quarterly_balance"
        if yahoo_complete and yahoo_balance_row in quarterly_balance
        else "yahoo.annual_balance"
        if yahoo_complete
        else None
    )
    debt, equity = balance.get("debt"), balance.get("equity")
    de = debt / equity if debt is not None and equity is not None and equity > 0 else None
    current_assets, current_liabilities = (
        balance.get("current_assets"),
        balance.get("current_liabilities"),
    )
    current_ratio = (
        current_assets / current_liabilities
        if current_assets is not None
        and current_liabilities is not None
        and current_liabilities > 0
        else None
    )

    cf_aliases = {
        "ocf": {"operatingcashflow", "cashflowsfromoperatingactivities"},
        "capex": {"capitalexpenditure", "paymentstoacquirepropertyplantandequipment"},
        "fcf": {"freecashflow"},
        "dividends": {"cashdividendspaid", "commonstockdividendpaid", "dividendspaid"},
    }
    fin_cf, _ = _latest_finmind(datasets.get(CASHFLOW, []), cutoff, cf_aliases, annual=True)
    yahoo_cf_rows = _yahoo_rows(snapshot, "annual_cashflow", cutoff, annual=True) if usable else []
    yahoo_cf = {}
    if yahoo_cf_rows:
        cf = yahoo_cf_rows[0]
        yahoo_cf = {
            "ocf": _value(
                cf, ("Operating Cash Flow", "Cash Flow From Continuing Operating Activities")
            ),
            "capex": _value(cf, ("Capital Expenditure",)),
            "fcf": _value(cf, ("Free Cash Flow",)),
            "dividends": _value(cf, ("Cash Dividends Paid", "Common Stock Dividend Paid")),
        }
    fin_cf_complete = all(fin_cf.get(key) is not None for key in ("ocf", "capex", "dividends"))
    yahoo_cf_complete = all(yahoo_cf.get(key) is not None for key in ("ocf", "capex", "dividends"))
    use_fin_cf = fin_cf_complete and (preference == "finmind" or not yahoo_cf_complete)
    cf = fin_cf if use_fin_cf else yahoo_cf
    cf_source = "finmind" if use_fin_cf else "yahoo.annual_cashflow" if yahoo_cf else None
    fcf = (
        cf.get("ocf") - abs(cf["capex"])
        if cf.get("ocf") is not None and cf.get("capex") is not None
        else cf.get("fcf")
    )
    dividends_paid = abs(cf["dividends"]) if cf.get("dividends") is not None else None
    info = snapshot.get("info", {}) if usable else {}
    roe = _number(info.get("returnOnEquity"))
    if roe is None and equity and equity > 0:
        income = _yahoo_rows(snapshot, "annual_income", cutoff, annual=True) if usable else []
        net_income = (
            _value(income[0], ("Net Income", "Net Income Common Stockholders")) if income else None
        )
        if net_income is not None:
            roe = net_income / equity
    roe_pct = roe * 100 if roe is not None else None
    roe_quality_score = min(max(roe_pct, 0) / 20 * 50, 50) if roe_pct is not None else None
    payout = None
    net_income = None
    if usable:
        income = _yahoo_rows(snapshot, "annual_income", cutoff, annual=True)
        net_income = (
            _value(income[0], ("Net Income", "Net Income Common Stockholders")) if income else None
        )
    if dividends_paid is not None and net_income is not None and net_income > 0:
        payout = dividends_paid / net_income * 100
    elif usable:
        raw_payout = _number(info.get("payoutRatio"))
        payout = raw_payout * 100 if raw_payout is not None else None
    fcf_payout = (
        dividends_paid / fcf * 100
        if dividends_paid is not None and fcf is not None and fcf > 0
        else None
    )
    financial_sector = any(
        term in str(sector or "").casefold()
        for term in ("financial", "bank", "insurance", "credit")
    )
    metrics = {
        "debt_to_equity": de,
        "current_ratio": current_ratio,
        "roe_pct": roe_pct,
        "roe_quality_score": roe_quality_score,
        "fcf": fcf,
        "dividends_paid": dividends_paid,
        "payout_ratio_pct": payout,
        "fcf_payout_ratio_pct": fcf_payout,
        "balance_source": balance_source,
        "cashflow_source": cf_source,
        "financial_sector": financial_sector,
        "financial_health_applicability": (
            "Debt/equity, current ratio and FCF coverage are not applied to financial-sector balance sheets"
            if financial_sector
            else "Debt/equity <2.0 and current ratio >1.0"
        ),
    }
    if financial_sector:
        health_check = {
            "status": "not_applicable",
            "reason": metrics["financial_health_applicability"],
        }
    else:
        health_check = _check(
            de is not None and current_ratio is not None and de < 2.0 and current_ratio > 1.0
            if de is not None and current_ratio is not None
            else None
        )
    if dividends_paid == 0:
        sustainability = {"status": "not_applicable", "reason": "No dividend payment reported"}
    elif financial_sector:
        sustainability = _check(payout < 80 if payout is not None else None)
    else:
        if (payout is not None and payout >= 80) or (
            dividends_paid is not None and dividends_paid > 0 and fcf is not None and fcf <= 0
        ):
            sustainability = _check(False)
        elif (
            payout is not None
            and fcf_payout is not None
            and fcf is not None
            and dividends_paid is not None
        ):
            sustainability = _check(payout < 80 and fcf_payout < 100 and fcf > dividends_paid)
        else:
            sustainability = _check(None)
    return metrics, health_check, sustainability


def _forward_estimates(snapshot, bars, usable):
    metrics = {
        "forward_pe": None,
        "peg": None,
        "forward_eps_growth_pct": None,
        "ranking_score": None,
        "ranking_eligible": False,
    }
    names = (
        "dated_forward_estimates",
        "estimate_currency",
        "estimate_methodology",
        "positive_forward_eps",
        "estimate_analyst_coverage",
        "normalized_per_share_growth",
    )
    unknown = {name: _check(None) for name in names}
    if not usable:
        return metrics, unknown
    rows = {
        row.get("period"): row for row in snapshot.get("estimates", []) if isinstance(row, dict)
    }
    current, future = rows.get("0y"), rows.get("+1y")
    if not current or not future:
        return metrics, unknown
    current_eps, future_eps = _number(current.get("avg")), _number(future.get("avg"))
    metrics.update(
        forward_eps_current=current_eps,
        forward_eps_next_year=future_eps,
        estimate_current_analysts=_number(current.get("numberOfAnalysts")),
        estimate_next_year_analysts=_number(future.get("numberOfAnalysts")),
        estimate_currency=current.get("currency"),
        estimate_methodology=current.get("methodology"),
    )
    currency = snapshot.get("financial_currency") or snapshot.get("info", {}).get(
        "financialCurrency"
    )
    market_currency = snapshot.get("currency") or snapshot.get("info", {}).get("currency")
    ccy0, ccy1 = current.get("currency"), future.get("currency")
    methods = (current.get("methodology"), future.get("methodology"))
    if all(isinstance(value, str) and value for value in (currency, market_currency, ccy0, ccy1)):
        currency_check = _check(currency == market_currency == ccy0 == ccy1)
    else:
        currency_check = _check(None)
    if all(
        isinstance(value, str) and value.casefold() in ("gaap", "normalized") for value in methods
    ):
        methodology_check = _check(methods[0].casefold() == methods[1].casefold())
    else:
        methodology_check = _check(None)
    analyst_counts = (
        _number(current.get("numberOfAnalysts")),
        _number(future.get("numberOfAnalysts")),
    )
    analyst_check = _check(all(value is not None and value >= 3 for value in analyst_counts))
    eps_check = _check(
        current_eps is not None and future_eps is not None and current_eps > 0 and future_eps > 0
        if current_eps is not None and future_eps is not None
        else None
    )
    price = _number(bars[-1].get("close")) if bars else None
    growth = (
        (future_eps / current_eps - 1) * 100
        if current_eps and future_eps and current_eps > 0
        else None
    )
    forward_pe = (
        price / current_eps
        if price is not None and price > 0 and current_eps and current_eps > 0
        else None
    )
    peg = (
        forward_pe / growth
        if forward_pe is not None and growth is not None and growth > 0
        else None
    )
    comparable = _check(growth > 0 if growth is not None else None)
    data_check = _check(current_eps is not None and future_eps is not None and price is not None)
    metrics.update(
        forward_eps_growth_pct=growth,
        forward_pe=forward_pe,
        peg=peg,
        estimate_rank_basis="forward P/E divided by next-fiscal-year EPS growth; no price target",
    )
    checks = {
        "dated_forward_estimates": data_check,
        "estimate_currency": currency_check,
        "estimate_methodology": methodology_check,
        "positive_forward_eps": eps_check,
        "estimate_analyst_coverage": analyst_check,
        "normalized_per_share_growth": comparable,
    }
    eligible = (
        all(check["status"] == "pass" for check in checks.values()) and peg is not None and peg > 0
    )
    metrics["ranking_eligible"] = eligible
    metrics["ranking_score"] = round(100 / peg, 6) if eligible else None
    return metrics, checks


def evaluate(
    strategy, listing, bars, *, datasets, benchmark=None, events=None, snapshot=None, sessions=None
):
    if strategy not in STRATEGIES:
        raise ValueError("Unknown fundamental strategy")
    if listing.get("kind") == "etf":
        return {
            "status": "not_applicable",
            "passed": None,
            "metrics": {},
            "warnings": [
                "Company earnings/valuation screens do not apply to ETFs; use technical strategies"
            ],
        }
    if not bars:
        return _finish({}, {"prices": _check(None)}, ["No price data"])
    if strategy == "pead":
        try:
            try:
                import taiwan_pead as pead
            except ImportError:
                from scripts import taiwan_pead as pead
        except ImportError:
            return _finish(
                {}, {"pead_evaluator": _check(None)}, ["Taiwan PEAD evaluator is unavailable"]
            )
        return pead.evaluate(listing, bars, events=events, snapshot=snapshot, sessions=sessions)
    cutoff = bars[-1]["date"]
    datasets = datasets or {}
    usable, snapshot_reason = _snapshot_state(snapshot, listing, bars, sessions)
    preference = (
        snapshot.get("preferred_provider", "auto") if isinstance(snapshot, dict) else "auto"
    )
    if preference not in ("auto", "finmind", "yahoo"):
        preference = "auto"
    metrics = {"snapshot_usable": usable}
    quarter = _quarter_data(datasets.get(STATEMENTS, []), snapshot, cutoff, preference, usable)
    if quarter:
        metrics.update(
            quarter,
            quarterly_eps_yoy_growth_pct=round(quarter["eps_growth"], 6)
            if quarter["eps_growth"] is not None
            else None,
            quarterly_revenue_yoy_growth_pct=round(quarter["revenue_growth"], 6)
            if quarter["revenue_growth"] is not None
            else None,
        )
    else:
        metrics.update(
            quarterly_eps_yoy_growth_pct=None,
            quarterly_revenue_yoy_growth_pct=None,
            quarterly_eps_source=None,
            quarterly_revenue_source=None,
        )
    dividend_rows = datasets.get(DIVIDENDS, [])
    yahoo_dividends = _yahoo_rows(snapshot, "dividends", cutoff) if usable else []
    if (preference == "yahoo" and yahoo_dividends) or (not dividend_rows and yahoo_dividends):
        dividend_rows = [
            {
                "year": row["date"][:4],
                "CashExDividendTradingDate": row["date"],
                "CashEarningsDistribution": row.get("amount"),
                "CashStatutorySurplus": 0,
            }
            for row in yahoo_dividends
        ]
        metrics["dividend_source"] = "yahoo.dividends"
    else:
        metrics["dividend_source"] = "finmind" if dividend_rows else None
    distributions = _dividends(dividend_rows, cutoff, _number(bars[-1].get("close")) or 0)
    if usable:
        four_year_start = _anniversary(date.fromisoformat(cutoff), 4).isoformat()
        split_dates = [
            row.get("date")
            for row in snapshot.get("splits", [])
            if isinstance(row, dict)
            and isinstance(row.get("date"), str)
            and four_year_start < row["date"] <= cutoff
            and _number(row.get("ratio")) not in (None, 0, 1)
        ]
        distributions["share_basis_change_detected"] |= bool(split_dates)
    metrics.update(distributions)
    warnings = [
        "Statement dates are fiscal periods, not availability timestamps; this is not a point-in-time backtest",
        "Original share bases and corporate actions must be reconciled before investment use",
    ]
    if snapshot_reason and snapshot is not None:
        warnings.append(f"Yahoo snapshot rejected: {snapshot_reason}")
    revenue = metrics.get("quarterly_revenue_yoy_growth_pct")
    if strategy == "canslim":
        checks, calculated = _canslim(
            datasets.get(STATEMENTS, []), snapshot, bars, benchmark, cutoff, preference, usable
        )
        metrics.update(calculated)
        quarter_basis_change = (
            calculated.get("quarterly_eps_source") == "finmind"
            and quarter is not None
            and _basis_change_between(
                datasets.get(DIVIDENDS, []),
                snapshot,
                quarter["comparison_period"],
                quarter["current_period"],
                usable,
            )
        )
        if quarter:
            metrics["quarterly_eps_comparison_basis_valid"] = not quarter_basis_change
        if quarter_basis_change:
            checks["C"] = _check(None)
            metrics["canslim_component_scores"]["C"] = None
            metrics["canslim_score"] = None
        annual_basis_change = (
            calculated.get("annual_eps_source") == "finmind"
            and calculated.get("annual_eps_period_start") is not None
            and _basis_change_between(
                datasets.get(DIVIDENDS, []),
                snapshot,
                calculated["annual_eps_period_start"],
                calculated["annual_eps_period_end"],
                usable,
            )
        )
        if calculated.get("annual_eps_source"):
            metrics["annual_eps_comparison_basis_valid"] = not annual_basis_change
        if annual_basis_change:
            checks["A"] = _check(None)
            metrics["canslim_component_scores"]["A"] = None
            metrics["canslim_score"] = None
        return _finish(
            metrics,
            checks,
            warnings
            + [
                "CANSLIM components use supplied Taiwan benchmark and price data; missing benchmark or sponsorship coverage remains unknown"
            ],
        )
    ratios = [r for r in datasets.get(PER, []) if r.get("date") == cutoff]
    ratio = ratios[-1] if ratios else {}
    pe, pb = _number(ratio.get("PER")), _number(ratio.get("PBR"))
    info = snapshot.get("info", {}) if usable else {}
    if pe is None:
        pe = _number(info.get("trailingPE"))
        metrics["pe_source"] = "yahoo.info" if pe is not None else None
    else:
        metrics["pe_source"] = "finmind"
    if pb is None:
        pb = _number(info.get("priceToBook"))
        metrics["pb_source"] = "yahoo.info" if pb is not None else None
    else:
        metrics["pb_source"] = "finmind"
    metrics.update(pe_ratio=pe, pb_ratio=pb)
    annual = _annual_metrics(datasets.get(STATEMENTS, []), snapshot, cutoff, preference, usable)
    metrics.update(annual)
    health, health_check, sustainability = _health(
        snapshot, datasets, cutoff, usable, preference, info.get("sector")
    )
    metrics["financial_health"] = health
    if strategy == "undervalued-growth":
        forward, forward_checks = _forward_estimates(snapshot, bars, usable)
        metrics.update(forward)
        checks = {
            "positive_trailing_pe": _check(pe > 0 if pe is not None else None),
            "quarterly_revenue_growth": _check(revenue > 0 if revenue is not None else None),
            **forward_checks,
            "financial_health": health_check,
        }
        return _finish(
            metrics,
            checks,
            warnings
            + [
                "Forward ranking uses comparable Yahoo EPS estimates and forward P/E; no price target is inferred"
            ],
        )
    cash_yield, growth = metrics.get("cash_yield_pct"), metrics.get("cash_dividend_cagr_3y_pct")
    is_value = strategy == "value-dividend"
    checks = {
        "cash_yield": _check(
            cash_yield >= (3 if is_value else 1.5) if cash_yield is not None else None
        ),
        "dividend_growth": _check(
            growth >= (4 if is_value else 12) if growth is not None else None
        ),
        "financial_health": health_check,
        "dividend_sustainability": sustainability,
        "comparable_annual_eps_growth": _check(metrics.get("annual_eps_stable")),
    }
    if distributions.get("share_basis_change_detected"):
        checks["dividend_growth"] = _check(None)
    if is_value:
        checks.update(
            pe=_check(0 < pe <= 20 if pe is not None else None),
            pb=_check(0 < pb <= 2 if pb is not None else None),
        )
    else:
        module = _load("dividend-growth-pullback-screener/scripts/screen_dividend_growth_rsi.py")
        rsi = module.RSICalculator.calculate_rsi([b["close"] for b in bars])
        metrics["rsi14"] = rsi
        checks["rsi_pullback"] = _check(rsi <= 40 if rsi is not None else None)
    return _finish(
        metrics,
        checks,
        warnings
        + [
            "Cash distributions use ex-dividend dates; empty windows are unknown, not zero",
            "Debt/equity <2.0, current ratio >1.0, earnings payout <80%, and FCF payout <100% follow the source dividend rules",
        ],
    )
