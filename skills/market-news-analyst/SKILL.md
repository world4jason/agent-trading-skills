---
name: market-news-analyst
description: 整理影響台股的市場新聞。查官方公告與可靠新聞，核對發布時間、台股曝險及已發生的市場反應；不得以新聞先後順序直接推論因果。 適用於台灣上市、上櫃股票與
  ETF 的研究請求；使用 FinMind 為主、Yahoo 行情補充。
---

# 整理影響台股的市場新聞

查官方公告與可靠新聞，核對發布時間、台股曝險及已發生的市場反應；不得以新聞先後順序直接推論因果。

## 執行流程

1. 先讀 [Codex 台股執行環境](../../CODEX_RUNTIME.md) 與 [台股規則](../../TAIWAN_MARKET.md)。
2. 依 [本類分析操作指引](../../references/taiwan-events.md) 取得本題需要的資料；不要自動擴大標的或日期範圍。
3. 讀下列相關方法論，依本 skill 的重點執行分析。保留可用的比例與邏輯；美元門檻、美國市場母體、日曆及不適用的成分不能直接換名。
4. 用本機 Python 計算需要精確運算的指標，保存來源、資料日期、標的/母體、單位、還原口徑、公式及缺資料項目。未知不等於零；缺必要成分時只報能支持的分項結論。
5. 以繁體中文回覆實際結果、限制與可驗證依據；若使用者指定其他語言則遵從。不得宣稱取得未取回的資料或已執行未執行的回測。

## 方法論資源

- [corporate_news_impact.md](references/corporate_news_impact.md)
- [correlation_causation_assessment.md](references/correlation_causation_assessment.md)
- [geopolitical_commodity_correlations.md](references/geopolitical_commodity_correlations.md)
- [impact_assessment_framework.md](references/impact_assessment_framework.md)
- [market_event_patterns.md](references/market_event_patterns.md)
- [reference_index.md](references/reference_index.md)
- [report_template.md](references/report_template.md)
- [trusted_news_sources.md](references/trusted_news_sources.md)

這些資源保留上游研究方法，須套用本版適用性限制。`references/upstream-skill.md` 和舊美股執行器僅供追溯，不是本版的執行入口。
