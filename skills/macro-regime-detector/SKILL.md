---
name: macro-regime-detector
description: 評估台股總經環境。研究台灣利率、匯率、出口與全球因素；若原版美國成分無對應，改報可驗證的分項觀察，不沿用原版總分或分類閾值。 適用於台灣上市、上櫃股票與
  ETF 的研究請求；使用 FinMind 為主、Yahoo 行情補充。
---

# 評估台股總經環境

研究台灣利率、匯率、出口與全球因素；若原版美國成分無對應，改報可驗證的分項觀察，不沿用原版總分或分類閾值。

## 執行流程

1. 先讀 [Codex 台股執行環境](../../CODEX_RUNTIME.md) 與 [台股規則](../../TAIWAN_MARKET.md)。
2. 依 [本類分析操作指引](../../references/taiwan-events.md) 取得本題需要的資料；不要自動擴大標的或日期範圍。
3. 讀下列相關方法論，依本 skill 的重點執行分析。保留可用的比例與邏輯；美元門檻、美國市場母體、日曆及不適用的成分不能直接換名。
4. 用本機 Python 計算需要精確運算的指標，保存來源、資料日期、標的/母體、單位、還原口徑、公式及缺資料項目。未知不等於零；缺必要成分時只報能支持的分項結論。
5. 以繁體中文回覆實際結果、限制與可驗證依據；若使用者指定其他語言則遵從。不得宣稱取得未取回的資料或已執行未執行的回測。

## 方法論資源

- [historical_regimes.md](references/historical_regimes.md)
- [indicator_interpretation_guide.md](references/indicator_interpretation_guide.md)
- [regime_detection_methodology.md](references/regime_detection_methodology.md)

這些資源保留上游研究方法，須套用本版適用性限制。`references/upstream-skill.md` 和舊美股執行器僅供追溯，不是本版的執行入口。
