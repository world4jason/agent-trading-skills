import importlib.util
from pathlib import Path

import pytest
import yaml

SPEC = importlib.util.spec_from_file_location("taiwan_recommend", Path(__file__).parents[1] / "recommend.py")
nav = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(nav)


@pytest.mark.parametrize("query,expected", [
    ("2330 可以買幾張", "position-sizer"), ("找台股VCP", "vcp-screener"),
    ("分析0050與00878 ETF", "us-stock-analysis"), ("6488 法人買賣超", "institutional-flow-tracker"),
    ("檢查我的台股持股", "portfolio-manager"), ("台股 RSI 技術走勢", "technical-analyst"),
])
def test_realistic_taiwan_intents(query, expected):
    assert expected in nav.recommend(query)["suggested_skills"]


@pytest.mark.parametrize("query", ["台指期貨", "options pricing", "crypto", "美股 NVDA", "cot-contrarian-detector"])
def test_out_of_scope_is_not_redirected_to_an_unrelated_stock_workflow(query):
    result = nav.recommend(query)
    assert result["routing_diagnostics"]["status"] == "out_of_scope"
    assert result["suggested_skills"] == []


def test_explicit_exclusion_and_no_paid_data_do_not_imply_availability():
    result = nav.recommend("不要期貨，分析0050 ETF", no_api=True)
    assert "us-stock-analysis" in result["suggested_skills"]
    assert result["data_access"]["live_access_verified"] is False
    assert result["executes_analysis"] is False


def test_unknown_goal_does_not_claim_exact_market_recommendation():
    assert nav.recommend("hello")["routing_diagnostics"]["status"] == "needs_goal"


def test_all_workflows_resolve_to_existing_supported_skills():
    index = yaml.safe_load((nav.ROOT / "skills-index.yaml").read_text())
    valid = {s["id"] for s in index["skills"]}
    excluded = set(index["excluded"])
    for path in (nav.ROOT / "workflows").glob("*.yaml"):
        result = nav.recommend(path.stem)
        assert result["primary_workflow"]["id"] == path.stem
        assert set(result["suggested_skills"]) <= valid
        assert not set(result["suggested_skills"]) & excluded


def test_empty_query_rejected():
    with pytest.raises(ValueError):
        nav.recommend(" ")


@pytest.mark.parametrize("query", ["分析台灣上市美股ETF 00646", "分析期貨ETF 00635U",
                                   "美股ETF00646", "期貨ETF00635U"])
def test_taiwan_etf_underlying_is_not_confused_with_listing_scope(query):
    result = nav.recommend(query)
    assert result["routing_diagnostics"]["status"] != "out_of_scope"
    assert "us-stock-analysis" in result["suggested_skills"]
