"""The fork extends market guidance without replacing upstream routing."""
from recommend import recommend
import pytest


@pytest.mark.parametrize("chinese,english", [
    ("台股策略回測", "backtest"),
    ("台股高股息候選", "high-yield dividend stocks"),
    ("檢查台股持股", "holdings"),
    ("台股財報後漂移", "post-earnings"),
    ("台股波段突破", "swing breakout"),
    ("台股每日市場風險", "each morning"),
    ("記錄交易紀錄", "journal"),
])
def test_chinese_intents_use_original_router(chinese, english, repo_metadata):
    actual = recommend(chinese, repo_metadata)
    expected = recommend(english, repo_metadata)
    assert actual["primary_workflow"] == expected["primary_workflow"]
    assert actual["setup_bundle"] == expected["setup_bundle"]


def test_us_request_retains_original_workflow(repo_metadata):
    result = recommend("I want to review my holdings and dividend candidates this week", repo_metadata)
    assert result["primary_workflow"]["id"] == "core-portfolio-weekly"
    assert result["routing_diagnostics"]["status"] != "out_of_scope"


def test_taiwan_request_uses_the_same_method(repo_metadata):
    result = recommend("Taiwan stocks: research and backtest a strategy", repo_metadata)
    assert result["primary_workflow"]["id"] == "strategy-research-pipeline"
