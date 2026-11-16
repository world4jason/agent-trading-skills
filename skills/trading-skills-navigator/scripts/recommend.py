"""Deterministic Taiwan-only skill routing; never executes a workflow."""

import argparse
import json
from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[3]
INTENTS = [
    ("position-sizer", ("買幾股", "買幾張", "買多少", "倉位", "部位大小", "position siz", "risk per trade")),
    ("vcp-screener", ("vcp", "波動收斂", "minervini")),
    ("canslim-screener", ("canslim", "歐尼爾")),
    ("institutional-flow-tracker", ("法人", "買賣超", "籌碼", "institutional")),
    ("earnings-calendar", ("財報日曆", "法說日期", "earnings calendar")),
    ("earnings-trade-analyzer", ("財報後", "法說後", "post-earnings")),
    ("economic-calendar-fetcher", ("經濟日曆", "總經日曆", "economic calendar")),
    ("weekly-performance-digest", ("週報", "每週績效", "weekly performance")),
    ("trade-performance-coach", ("績效", "performance")),
    ("trader-memory-core", ("交易紀錄", "交易日誌", "journal", "記錄交易")),
    ("signal-postmortem", ("復盤", "回顧交易", "postmortem")),
    ("drawdown-circuit-breaker", ("回撤限制", "circuit breaker")),
    ("portfolio-manager", ("持股", "投資組合", "配置", "portfolio", "holdings")),
    ("dividend-growth-pullback-screener", ("股利成長回檔", "dividend growth pullback")),
    ("value-dividend-screener", ("股利選股", "高殖利率選股", "dividend screen")),
    ("kanchi-dividend-sop", ("股利", "配息", "殖利率", "dividend")),
    ("market-breadth-analyzer", ("廣度", "breadth")),
    ("uptrend-analyzer", ("上升趨勢比例", "uptrend ratio")),
    ("market-environment-analysis", ("大盤", "市場環境", "market regime", "每日市場", "daily market")),
    ("sector-analyst", ("產業輪動", "sector")),
    ("theme-detector", ("題材", "投資主題", "theme")),
    ("market-news-analyst", ("新聞", "news")),
    ("macro-regime-detector", ("總經", "macro")),
    ("backtest-expert", ("回測", "backtest")),
    ("edge-strategy-designer", ("策略設計", "strategy design")),
    ("technical-analyst", ("技術", "k線", "k 線", "rsi", "均線", "支撐", "technical")),
    ("us-undervalued-growth-screener", ("低估成長", "garp", "undervalued")),
    ("finviz-screener", ("選股", "篩選", "screen")),
    ("us-stock-analysis", ("分析", "比較", "估值", "營收", "財報", "analy", "compare", " vs ")),
]


def recommend(query, *, project_root=ROOT, no_api=False, time_budget="any", experience=None):
    root = Path(project_root)
    metadata = yaml.safe_load((root / "skills-index.yaml").read_text())
    if metadata.get("edition") != "taiwan":
        raise ValueError("The selected metadata is not the Taiwan edition")
    skills = {s["id"]: s for s in metadata["skills"]}
    workflows = {p.stem: yaml.safe_load(p.read_text()) for p in (root / "workflows").glob("*.yaml")}
    text = query.strip().lower()
    if not text:
        raise ValueError("query must not be empty")
    # Ignore explicit exclusions rather than treating them as desired instruments.
    scope_text = re.sub(r"(?:不做|不要|排除|不含|不需要|先不做|先不用)\s*(?:期貨|選擇權|加密貨幣|美股)", "", text)
    scope_text = re.sub(r"(?:期貨|選擇權|加密貨幣|美股)\s*(?:先不用|先不做|不要|不需要)", "", scope_text)
    taiwan_etf = "etf" in scope_text and bool(re.search(
        r"台股|台灣|臺灣|上市|上櫃|\b0\d{3,5}[a-z]?(?:\.tw|\.two)?\b|etf\s*0\d{3,5}[a-z]?(?:\.tw|\.two)?(?![a-z0-9])", scope_text))
    if taiwan_etf:
        # The ETF's underlying exposure is not the instrument's listing venue.
        scope_text = re.sub(r"(?:美股|期貨|us stock|futures?)\s*(?=etf)", "", scope_text)
    unsupported = bool(re.search(r"期貨|選擇權|加密貨幣|美股|\bfutures?\b|\boptions?\b|\bcrypto\b|\bus stocks?\b", scope_text))
    excluded_ids = [name for name in metadata.get("excluded", {}) if name in text]
    explicit = [name for name in skills if name in text]
    workflow_ids = [name for name in workflows if name in text]
    matched = []
    primary = None
    if unsupported or excluded_ids:
        status, rationale = "out_of_scope", "本版只支援台灣上市、上櫃股票與 ETF；請將範圍外部分分開處理。"
    elif workflow_ids:
        primary = workflows[workflow_ids[0]]
        matched = primary["required_skills"]
        status, rationale = "exact", "找到明確指定的台股流程；僅說明，不自動執行。"
    elif explicit:
        matched = explicit
        status, rationale = "exact", "找到明確指定且已納入台股版的 skill。"
    else:
        matched = [name for name, words in INTENTS if any(word in text for word in words)]
        if not matched and re.search(r"\b\d{4,6}[a-z]?(?:\.tw|\.two)?\b|etf|台股|上市|上櫃", text):
            matched = ["us-stock-analysis"]
        status = "matched" if len(matched) == 1 else "ambiguous" if matched else "needs_goal"
        rationale = "依台股研究意圖建議 skill；多項命中時依使用者實際問題選取，不自動擴張工作。" if matched else "請描述要分析的台股問題，例如持股、股利、VCP 或倉位。"
    missing = [name for name in matched if name not in skills or not (root / "skills" / name / "SKILL.md").is_file()]
    if missing:
        raise ValueError("Workflow refers to missing Taiwan skills: " + ", ".join(missing))
    related = [w for w in workflows.values() if set(matched) & set(w["required_skills"])]
    return {
        "query": query, "edition": "taiwan", "scope": ["TWSE stocks", "TPEX stocks", "ETFs"],
        "routing_diagnostics": {"status": status, "explanation": rationale},
        "suggested_skills": matched, "primary_workflow": primary,
        "related_workflows": [{"id": w["id"], "display_name": w["display_name"]} for w in related],
        "setup_bundle": {"required": matched, "recommended": [], "optional": []},
        "already_installed_edition": "taiwan", "no_api": no_api,
        "data_access": {"primary": "FinMind", "price_supplement": "Yahoo Finance",
                        "live_access_verified": False, "paid_access_required": "dataset-dependent",
                        "note": "--no-api 表示不使用付費資料；可用免費資料或使用者輸入，但不能保證每項分析可完整完成。" if no_api else "實際資料可得性、token、額度及日期範圍須執行時確認。"},
        "time_budget": time_budget, "experience": experience,
        "constraints_note": "時間與經驗是供後續對話參考的偏好，未用來保證執行時長。",
        "executes_analysis": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--no-api", action="store_true", help="No paid data; availability still must be checked")
    parser.add_argument("--time-budget", choices=["15m", "30m", "60m", "90m", "any"], default="any")
    parser.add_argument("--experience", choices=["beginner", "intermediate", "advanced"])
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--project-root", type=Path, default=ROOT)
    args = vars(parser.parse_args(argv))
    format_ = args.pop("format")
    try:
        result = recommend(**args)
    except (ValueError, OSError, yaml.YAMLError) as exc:
        parser.error(str(exc))
    if format_ == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["routing_diagnostics"]["explanation"])
        print("建議：" + (", ".join("$" + s for s in result["suggested_skills"]) or "尚無"))
        print(result["data_access"]["note"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
