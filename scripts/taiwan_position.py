"""Cash-only Taiwan stock/ETF sizing; fees and tax are explicit user inputs."""

import argparse
import json
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from pathlib import Path


def decimal(value):
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("numeric input required") from exc
    if not result.is_finite():
        raise ValueError("finite numeric input required")
    return result


def tick_size(price, kind):
    if kind == "etf":
        return Decimal("0.01") if price < 50 else Decimal("0.05")
    if kind != "stock":
        raise ValueError("kind must be stock or etf")
    for limit, tick in [(10, ".01"), (50, ".05"), (100, ".1"),
                        (500, ".5"), (1000, "1")]:
        if price < limit:
            return Decimal(tick)
    return Decimal(5)


def size_position(*, account_size, entry, stop, risk_pct, kind, unit,
                  fee_rate, sell_tax_rate, minimum_fee, cash=None, lot_size=1000):
    account, entry, stop, risk, fee, tax, minimum = map(decimal, (
        account_size, entry, stop, risk_pct, fee_rate, sell_tax_rate, minimum_fee))
    cash = account if cash is None else decimal(cash)
    if not (account > 0 and entry > stop > 0 and 0 < risk <= 100 and cash >= 0):
        raise ValueError("require positive equity, entry > stop > 0, risk in (0,100], cash >= 0")
    if not (0 <= fee < 1 and 0 <= tax < 1 and minimum >= 0):
        raise ValueError("fee/tax must be decimal rates in [0,1); minimum fee >= 0")
    if unit not in ("shares", "lots"):
        raise ValueError("unit must be shares or lots")
    if isinstance(lot_size, bool) or not isinstance(lot_size, int) or lot_size <= 0:
        raise ValueError("lot_size must be a positive integer")
    for price in (entry, stop):
        if price % tick_size(price, kind):
            raise ValueError("entry/stop is not on the Taiwan stock/ETF price tick")
    step = lot_size if unit == "lots" else 1
    budget = account * risk / 100

    def costs(shares):
        if shares == 0:
            return Decimal(0), Decimal(0), Decimal(0)
        # Conservative whole-TWD rounding; actual broker rounding can differ.
        buy_fee = max(minimum, shares * entry * fee).to_integral_value(rounding=ROUND_CEILING)
        sell_fee = max(minimum, shares * stop * fee).to_integral_value(rounding=ROUND_CEILING)
        sell_tax = (shares * stop * tax).to_integral_value(rounding=ROUND_CEILING)
        total = buy_fee + sell_fee + sell_tax
        return shares * entry + buy_fee, shares * (entry - stop) + total, total

    low, high = 0, min(int(cash / entry / step), int(budget / (entry - stop) / step))
    while low < high:
        middle = (low + high + 1) // 2
        used_cash, loss, _ = costs(middle * step)
        if used_cash <= cash and loss <= budget:
            low = middle
        else:
            high = middle - 1
    shares = low * step
    used_cash, loss, total = costs(shares)
    return {
        "currency": "TWD", "kind": kind, "unit": unit, "shares": shares,
        "board_lots": shares // lot_size, "odd_shares": shares % lot_size,
        "entry": str(entry), "stop": str(stop), "risk_budget": str(budget),
        "cash_required": str(used_cash), "gross_stop_loss": str(shares * (entry - stop)),
        "estimated_stop_loss_with_costs": str(loss), "estimated_round_trip_costs": str(total),
        "assumptions": {"fee_rate": str(fee), "sell_tax_rate": str(tax),
                        "minimum_fee_per_side": str(minimum), "board_lot_size": lot_size},
        "warnings": [
            "Planning calculation, not an order. Verify instrument trading unit and broker fees/tax.",
            "Costs rounded upward to whole TWD; excludes slippage and multiple-fill fees.",
            "Stop fill is not guaranteed, especially at price limits; actual loss may exceed this estimate.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("account-size", "entry", "stop", "risk-pct", "fee-rate",
                 "sell-tax-rate", "minimum-fee"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--kind", choices=("stock", "etf"), required=True)
    parser.add_argument("--unit", choices=("shares", "lots"), required=True)
    parser.add_argument("--cash")
    parser.add_argument("--lot-size", type=int, default=1000,
                        help="Verified instrument trading unit; default 1000, exceptions must be specified")
    parser.add_argument("--output", type=Path)
    args = vars(parser.parse_args())
    output = args.pop("output")
    try:
        result = size_position(**args)
    except ValueError as exc:
        parser.error(str(exc))
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload)
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
