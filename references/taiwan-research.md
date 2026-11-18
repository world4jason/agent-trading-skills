# 台股策略研究與回測

先讀使用者策略與既有研究，保留假說/反證/實驗範圍。資料來源依資料能力與使用者指定
選擇；日線 provider 遵守 [台股市場與資料口徑](../TAIWAN_MARKET.md) 的整段 fallback 規則。
下市/停牌、股利/分割、
報表公布時間、回測當時股票池與實際可交易性都是研究假設，未處理者列限制。

研究鏈：觀察 → 可否證機制 → 明確規則 → 所需資料 → 樣本內/外檢查 → 成本/制度檢查
→ 實際結果 → 原假說是否保留。不要為讓結果變好任意擴張參數/期間或省略失敗樣本。
純概念綜合、策略設計與審查由目前使用的 AI agent 執行，以明確 JSON/YAML/Markdown 傳遞；
不啟動舊美股 orchestrator 或 Claude CLI。

如果執行回測，使用原有可用引擎前先驗證其輸入/委託模型能表達台股整數股、
實際手續費與稅、漲跌停/停牌不成交、日曆和公司行動。不能表達的部分不可宣稱已驗證。
只審查現成回測結果時，不宣稱自己執行了回測。原 backtest-expert 的純結果評估器
可對符合參數的已量測指標執行，分數不構成台股經驗有效性證明。

殘餘優勢/配對/因子研究要對齊同口徑報酬與基準，並檢查多重檢驗、估計誤差和結構改變。
主題/故事/模型產生的研究題目不是實證訊號；必須附來源、驗證步驟與未滿足的前提。

## 共同執行入口

在 `本專案根目錄` 執行。以下代碼與日期只是操作範例，實際使用時換成使用者的標的與研究期間。

```bash
rtk proxy .venv/bin/python scripts/taiwan_data.py universe --output /tmp/tw-universe.json
rtk proxy .venv/bin/python scripts/taiwan_data.py prices --symbol 2330 --start 2024-01-01 --end 2024-12-31 --output /tmp/tw-2330-prices.json
rtk proxy .venv/bin/python scripts/taiwan_data.py dataset --name TaiwanStockFinancialStatements --symbol 2330 --start 2024-01-01 --end 2024-12-31 --output /tmp/tw-2330-statements.json
```

`prices` 可接受裸代碼或經過市場驗證的 `.TW` / `.TWO`；`dataset` 使用裸字串代碼。
回傳 envelope 的 `status` 必須為 `ok`，再讀 `data`、`warnings` 與來源資訊。
空陣列是無資料，不是數值零。使用需要憑證的 FinMind dataset 時，將 token 放在 `FINMIND_TOKEN` 環境變數。
不要為了取得價格而要求使用者提供 token 到對話中。

日線每列包含 `date,symbol,open,high,low,close,volume`；日期由舊到新，
volume 為股/單位，幣別 TWD。保留 `source,adjustment,timezone`；不可把 Yahoo
的供應商調整口徑視為獨立驗證過的公司行動資料。取得資料失敗要回報，不可假造回傳。
FinMind 原始資料列的單位、報表類型與發布日期須另行查證，不能把季度截止日當公布日。

全市場要求先確認名單日期、可交易狀態、API 額度與歷史資料覆蓋；逐檔記錄成功/失敗。
如果只取得樣本，就回報樣本結果，不把它標成全市場排名。股票總覽含歷史項目，
不能單憑目錄存在判定當前仍上市。市場中性方法可沿用，來源、時區、母體不能換名假裝等價。

參考：[FinMind 技術面](https://finmind.github.io/tutor/TaiwanMarket/Technical/)、
[基本面](https://finmind.github.io/tutor/TaiwanMarket/Fundamental/)、
[籌碼面](https://finmind.github.io/tutor/TaiwanMarket/Chip/)。
