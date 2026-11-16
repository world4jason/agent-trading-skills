# 台股交易紀錄與回顧

保留使用者原始紀錄；先讀既有檔案再新增，不能覆寫無關交易。使用字串代碼、
TWD、Asia/Taipei、整數股、實際成交時間與費用/稅額。研究價格與真實成交分開。
在原論點中保留當時來源、資料時點、風險預算、反證及狀態轉換，不以事後資訊改寫。

本版可用使用者既有 JSON/YAML/CSV 結構進行研究紀錄與回顧；需要上游 thesis schema
相容性時先檢查 schema，僅使用實際支援且市場中性的欄位與儲存功能。
不呼叫帶美國市場日曆/自動 FMP 更新的舊流程。未指定儲存位置時在對話呈現，
不能把使用者紀錄默默存進套件範例 state。資料移轉不得丟棄原欄位。

績效：已實現/未實現分開，部分出場按實際成本基礎；手續費/證交稅不能遺漏。
R 倍數的分母是當時確認的風險預算，缺分母就不計算。勝率/期望值列樣本數與期間。
週報以 Asia/Taipei 邊界選樣，不把美國日期當台灣交易日。
型態練習的 3/5 日結果按台股交易日，未成熟或無交易樣本標待定。
行為回顧只從可見紀錄評估規則遵守，避免臆測心理或將獲利等同好決策。

## 共同執行入口

在 `本專案根目錄` 執行。以下代碼與日期只是操作範例，實際使用時換成使用者的標的與研究期間。

```bash
rtk proxy .venv/bin/python scripts/taiwan_data.py universe --output /tmp/tw-universe.json
rtk proxy .venv/bin/python scripts/taiwan_data.py prices --symbol 2330 --start 2024-01-01 --end 2024-12-31 --output /tmp/tw-2330-prices.json
rtk proxy .venv/bin/python scripts/taiwan_data.py dataset --name TaiwanStockFinancialStatements --symbol 2330 --start 2024-01-01 --end 2024-12-31 --output /tmp/tw-2330-statements.json
```

`prices` 可接受裸代碼或經過市場驗證的 `.TW` / `.TWO`；`dataset` 使用裸字串代碼。
回傳 envelope 的 `status` 必須為 `ok`，再讀 `data`、`warnings` 與來源資訊。
空陣列是無資料，不是數值零。FinMind token 使用 `FINMIND_TOKEN` 環境變數。
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
