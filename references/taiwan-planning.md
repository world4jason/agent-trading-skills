# 台股曝險、倉位與交易前計畫

要求明確的標的類型、資金/可用現金、進場/停損、風險百分比及實際費率。
價格皆 TWD，數量是整數股；先確認普通整張或零股及標的交易單位。
先讀 TAIWAN_MARKET.md 的漲跌停、跳動單位和停損成交限制。

## 含成本現股計算

以下費率與價格僅為計算範例，不是任何使用者適用稅率或報價：

```bash
rtk proxy .venv/bin/python scripts/taiwan_position.py --account-size 1000000 --cash 200000 --entry 100 --stop 95 --risk-pct 1 --kind stock --unit lots --fee-rate .001425 --sell-tax-rate .003 --minimum-fee 20
```

`--unit shares` 允許整數股數；`--unit lots` 只取整張。`--lot-size` 預設1000，
特殊交易單位必須使用經確認的數字。ETF 使用 `--kind etf` 的跳動規則。
費率參數為小數，不是百分數，且沒有自動預設稅率。結果提供現金、估計停損含成本風險、
張數及剩餘零股；成本採保守整元向上取整，未含滑價、多次成交費用或無法成交的尾部風險。

ATR/Kelly 可參考既有純計算方法，但 ATR 必須用台股有效觀測、Kelly 樣本須真實且成本一致。
計算得到的預算仍須換成台股整數股、合法價格及成本，不使用原版 fractional shares。
若分析股票空方策略，額外查核標的資格、券源、價格與交割規則；本現股 sizing CLI
只算多方買進，不能拿多方停損公式當空方風險，也不建立自動下單功能。

帳戶回撤按 Asia/Taipei 的日週月界線與使用者限制計算，冷卻期使用台股日曆。
不要直接跑原版 NYSE 冷卻期程式。曝險姿態需實際台股市場證據與持股資料；
關鍵未知則保留待確認，不能給虛假的 PASS/GO。

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
