# 台股公司、ETF、籌碼與條件選股

## 取數

使用共享資料 CLI 的 dataset，依需要取得：
`TaiwanStockFinancialStatements`、`TaiwanStockBalanceSheet`、
`TaiwanStockCashFlowsStatement`、`TaiwanStockMonthRevenue`、`TaiwanStockPER`、
`TaiwanStockDividend`、`TaiwanStockInstitutionalInvestorsBuySell`、
`TaiwanStockMarginPurchaseShortSale`。只查本題相關資料。
保留每列 `type`、`origin_name`、期間、單位；不要臆測所有財報數值以千元或元表示。
相同項目需同期間/同合併基礎，單季與累計不能直接相減混用。發布時間從 MOPS/公司公告驗證。

## 公司分析

逐項計算使用者要求的營收/盈餘成長、獲利品質、資產負債、現金流、股利與估值。
以可核對的分子分母和日期列示公式；負 EPS、缺股本、一次性收益需獨立處理。
比較同業前確認行業、規模、景氣循環與報表基礎。不能從歷史 EPS 填出未提供的未來共識。
CANSLIM、GARP、股利品質、主題及機構流向依各 skill 的方法論分項執行；
若必要成分缺資料，列待補，不能拿零分或重配權重聲稱原模型全分數已算好。
絕對市值/成交額的篩選須使用 TWD 明確門檻；未指定時不要偷把美元門檻乘一個假定匯率。

## ETF 分流

先確認 ETF 類型與實際曝險。公司財報、EPS、企業價值和 CANSLIM 不適用 ETF。
以價格/成交、配息、追蹤標的、費用、持股、NAV/折溢價等實際可得資料分析；
FinMind/Yahoo 沒有的基金欄位須查發行商正式揭露，無資料就標示未取得。
槓桿反向與海外標的 ETF 的每日重設、匯率及成分市場時區分開說明，不預設 10% 漲跌幅。

## 法人與選股

買賣超為買進減賣出，保留原始機構名稱及股數；重複子項/總項不能同時計入。
它不是持股比例，不能宣稱從買超得知機構持有水位。融資融券餘額不是放空授權。
對股票池逐檔列符合/不符合/資料不足，記錄母體版本與篩選公式，ETF 另跑適用條件。

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
