from datetime import date, timedelta
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import taiwan_technical as engine


def bars(count=300):
    return [dict(date=(date(2023, 1, 1)+timedelta(days=i)).isoformat(), open=100+i*.1,
                 high=102+i*.1, low=99+i*.1, close=101+i*.1, volume=200000) for i in range(count)]


@pytest.mark.parametrize("strategy", engine.STRATEGIES)
@pytest.mark.parametrize("kind", ["stock", "etf"])
def test_negative_patterns_and_insufficient_history(strategy, kind):
    listing = {"kind": kind}
    result = engine.evaluate(strategy, listing, bars())
    assert result["status"] == "evaluated"
    assert result["passed"] is False
    assert engine.evaluate(strategy, listing, bars(10))["passed"] is None
    assert engine.evaluate(strategy, listing, bars(), expected_session="2025-01-01")["status"] == "insufficient_data"


def test_momentum_actual_trigger_and_currency_scale_invariance():
    history = bars()
    latest = history[-1]
    latest.update(open=130, high=138, low=130, close=137, volume=1000000)
    first = engine.evaluate("momentum-burst", {"kind":"etf"}, history)
    scaled = [{**b, **{key:b[key]*30 for key in ("open","high","low","close")}} for b in history]
    second = engine.evaluate("momentum-burst", {"kind":"stock"}, scaled)
    assert first["passed"] is True
    assert second["passed"] is True
    assert "dollar_breakout" not in first["metrics"]["trigger"]["trigger_tags"]


def test_relative_strength_does_not_publish_fabricated_rank():
    history = bars()
    result = engine.evaluate("vcp", {"kind":"stock"}, history, benchmark=history)
    relative = result["metrics"]["benchmark_relative_strength"]
    assert "rs_rank_estimate" not in relative
    assert relative["weighted_rs"] == 0


def test_mixed_adjustment_bases_skip_relative_strength():
    stock=[{**b,"adjustment":"unadjusted"} for b in bars()]
    benchmark=[{**b,"adjustment":"provider_reported_split_adjusted_dividend_unadjusted"} for b in bars()]
    result=engine.evaluate("vcp",{"kind":"stock"},stock,benchmark=benchmark)
    assert "benchmark_relative_strength" not in result["metrics"]
    assert any("basis differs" in warning for warning in result["warnings"])


def test_dollar_trigger_only_applies_to_usd_prices():
    history=bars()
    prior=history[-2]["close"]
    history[-1].update(open=prior+.1,low=prior,high=prior+1.2,close=prior+1,volume=1000000)
    usd=engine.evaluate("momentum-burst",{"kind":"stock","currency":"USD"},history)
    twd=engine.evaluate("momentum-burst",{"kind":"stock","currency":"TWD"},history)
    assert usd["passed"] is True
    assert twd["passed"] is False
    assert usd["metrics"]["price_unit"]=="USD"
    assert "dollar_breakout" in usd["metrics"]["trigger"]["trigger_tags"]
