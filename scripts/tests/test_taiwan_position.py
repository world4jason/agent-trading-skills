from decimal import Decimal

import pytest

from scripts.taiwan_position import size_position, tick_size


def base(**changes):
    args = dict(account_size="1000000", entry="100", stop="95", risk_pct="1",
                kind="stock", unit="shares", fee_rate=".001425",
                sell_tax_rate=".003", minimum_fee="20")
    args.update(changes)
    return args


def test_risk_and_cash_constraints_and_maximal_quantity():
    result = size_position(**base())
    assert 0 < result["shares"] < 2000
    assert Decimal(result["estimated_stop_loss_with_costs"]) <= 10000
    assert Decimal(result["cash_required"]) <= 1000000
    n = result["shares"] + 1
    next_loss = n * Decimal(5) + sum(x.to_integral_value(rounding="ROUND_CEILING") for x in (
        n * Decimal("100") * Decimal(".001425"),
        n * Decimal("95") * Decimal(".001425"), n * Decimal("95") * Decimal(".003")))
    assert next_loss > 10000


def test_lots_floor_and_small_cash():
    assert size_position(**base(unit="lots"))["shares"] == 1000
    result = size_position(**base(cash="100"))
    assert result["shares"] == 0
    assert Decimal(result["estimated_round_trip_costs"]) == 0
    assert size_position(**base(cash="120"))["shares"] == 1


@pytest.mark.parametrize("price,tick", [("9.99", ".01"), ("10", ".05"),
    ("50", ".1"), ("100", ".5"), ("500", "1"), ("1000", "5")])
def test_stock_tick_boundaries(price, tick):
    assert tick_size(Decimal(price), "stock") == Decimal(tick)


def test_etf_ticks_and_integer_shares():
    assert tick_size(Decimal("49.99"), "etf") == Decimal(".01")
    assert tick_size(Decimal("50"), "etf") == Decimal(".05")
    result = size_position(**base(kind="etf", entry="50.05", stop="49.99"))
    assert isinstance(result["shares"], int)


def test_verified_nonstandard_trading_unit():
    result = size_position(**base(kind="etf", unit="lots", lot_size=100))
    assert result["shares"] % 100 == 0
    assert result["board_lots"] == result["shares"] // 100
    assert result["assumptions"]["board_lot_size"] == 100
    with pytest.raises(ValueError):
        size_position(**base(lot_size=0))


@pytest.mark.parametrize("changes", [{"entry": "100.1"}, {"account_size": "NaN"},
    {"cash": "Infinity"}, {"stop": "100"}, {"fee_rate": "-0.1"},
    {"sell_tax_rate": "1"}, {"risk_pct": "101"}, {"unit": "fractional"}])
def test_invalid_inputs(changes):
    with pytest.raises(ValueError):
        size_position(**base(**changes))
