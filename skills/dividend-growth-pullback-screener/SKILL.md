---
name: dividend-growth-pullback-screener
description: 尋找台股股利成長與回檔候選。公司股利成長與殖利率配合可驗證的價格回檔；ETF 配息另列，不套公司盈餘成長與自由現金流模型。 適用於台灣上市、上櫃股票與
  ETF 的研究請求；資料來源依能力與使用者指定選擇。
---

# 尋找台股股利成長與回檔候選

公司股利成長與殖利率配合可驗證的價格回檔；ETF 配息另列，不套公司盈餘成長與自由現金流模型。

## 執行流程

1. 先讀 [台股執行環境](../../CODEX_RUNTIME.md) 與 [台股規則](../../TAIWAN_MARKET.md)。
2. 依 [本類分析操作指引](../../references/taiwan-dividend.md) 取得本題需要的資料；不要自動擴大標的或日期範圍。
3. 讀下列相關方法論，依本 skill 的重點執行分析。保留可用的比例與邏輯；美元門檻、美國市場母體、日曆及不適用的成分不能直接換名。
4. 用本機 Python 計算需要精確運算的指標，保存來源、資料日期、標的/母體、單位、還原口徑、公式及缺資料項目。未知不等於零；缺必要成分時只報能支持的分項結論。
5. 以繁體中文回覆實際結果、限制與可驗證依據；若使用者指定其他語言則遵從。不得宣稱取得未取回的資料或已執行未執行的回測。

## 方法論資源

- [dividend_growth_compounding.md](references/dividend_growth_compounding.md)
- [rsi_oversold_strategy.md](references/rsi_oversold_strategy.md)

這些資源保留上游研究方法，須套用本版適用性限制。`references/upstream-skill.md` 和舊美股執行器僅供追溯，不是本版的執行入口。

## 自動選股入口

從本專案根目錄執行：

```bash
.venv/bin/python scripts/taiwan_screen.py --strategy dividend-growth-pullback --symbols 2330 6488 0050 --start 2023-01-01 --end 2024-12-31 --output /tmp/taiwan-screen.json
```

日期與標的是操作範例，依使用者要求調整。全市場改用 `--all`；要限制上市／上櫃或股票／ETF，可用 `--exchange`、`--kind`。讀 [引擎規則與資料限制](../../TAIWAN_ENGINES.md)，完整保留未評估項目；不得把部分條件通過說成完整方法通過。
