---
name: data-quality-checker
description: 檢查台股／美股掃描的來源、日期、幣別、交易日、每股單位與資料缺口；區分資料不足、不適用、未通過及程式錯誤。
---

# 檢查台美股研究資料品質

逐項核對來源、日期、幣別、股/張單位、還原口徑、缺值及計算；將資料缺口與數字錯誤分開，勿修改原始資料以通過檢查。

## 台股執行流程

1. 先讀 [台股執行環境](../../CODEX_RUNTIME.md) 與 [台股規則](../../TAIWAN_MARKET.md)。
2. 依 [本類分析操作指引](../../references/taiwan-meta.md) 取得本題需要的資料；不要自動擴大標的或日期範圍。
3. 讀下列相關方法論，依本 skill 的重點執行分析。保留可用的比例與邏輯；美元門檻、美國市場母體、日曆及不適用的成分不能直接換名。
4. 用本機 Python 計算需要精確運算的指標，保存來源、資料日期、標的/母體、單位、還原口徑、公式及缺資料項目。未知不等於零；缺必要成分時只報能支持的分項結論。
5. 以繁體中文回覆實際結果、限制與可驗證依據；若使用者指定其他語言則遵從。不得宣稱取得未取回的資料或已執行未執行的回測。

## 方法論資源

- [common_data_errors.md](references/common_data_errors.md)
- [instrument_notation_standard.md](references/instrument_notation_standard.md)

這些資源保留上游研究方法，須套用本版適用性限制。`references/upstream-skill.md` 和舊美股執行器僅供追溯，不是本版的執行入口。

## 台股與美股全市場批次

使用者要求台股／美股全市場掃描時，讀 [跨市場掃描說明](../../CROSS_MARKET_SCAN.md)，使用 `scripts/market_scan.py` 與 `scripts/market_report.py`。官方目錄、實際處理數、來源日期與缺資料表必須保留；台灣 TWD／台北時間與美國 USD／美東時間分開，ETF 公司財報條件不適用。
