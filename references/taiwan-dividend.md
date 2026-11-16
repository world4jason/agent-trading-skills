# 台股股利與 ETF 配息研究

取得 `TaiwanStockDividend`、公司財報/現金流、月營收及日線，必要時從發行商或
MOPS 取公告補足除息、發放及配息組成。股利的所屬年度、公告日、除息日與發放日不同，
不能從資料列日期自行推定。拆股與股票股利會改變每股比較基礎，須調整或揭露不可比。

公司研究分開檢查配息紀錄、現金股利覆蓋、盈餘/現金流品質、槓桿、資本支出與流動性。
定義殖利率的分子期間和價格時點，單次配息不可直接年化成保證收入。
成長篩選與回檔條件依使用者/原方法的百分比規則逐項計算，資料不足不推估為零。

ETF 分配可能包含不同所得或收益來源。不能套用公司股利支付率、企業自由現金流或
企業 EPS 成長評分；配息不等於總報酬。實際配息組成與 NAV 以基金正式文件為準。
本版不移植美國稅務：若要求稅後結果，先取得使用者適用身分/費率或官方規則，
未確認時只報稅前，不能將美國 withholding/qualified-dividend 概念替換成台灣。

清單追蹤保留原投資論點、公告證據、檢視觸發條件和更新日，未發布資料不可前視。

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
