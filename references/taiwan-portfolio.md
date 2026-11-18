# 台股與 ETF 持股檢視

讀取使用者指定的券商匯出或手動持股，至少確認字串代碼、股數或張數、成本/市值口徑、
幣別、資料時點與是否包含現金/負債。張數只有在確認交易單位後才轉股。
範例資料不是使用者帳戶，重複列不一定是重複持股，需分清帳戶/分筆成本。

用共享資料 CLI 取得實際可用價格，對齊資料日期。公司行動、部分成交、匯率或
成本不確定時標記，不用零代替。若市值與帳單不一致，先保留兩者與時點差，不強行對齊。
計算持股比重、股票/ETF 分類、產業曝險與未實現盈虧，明列計算是否含現金。
ETF 持股重疊必須有基金實際成分與日期，不能從名稱猜成分比例。

只拿到持股檔可做持股配置檢視，不能宣稱已對券商全帳戶/負債/授信/全部風險完成對帳。
Alpaca 不是台股帳戶來源；本版不設定券商連線、不替使用者下單。
再平衡如被要求，提出台股合法整數股方案並驗證成本/現金，保留未完成的條件。

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
