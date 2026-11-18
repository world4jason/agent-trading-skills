# 台股廣度、產業與市場狀態

先定義研究範圍：上市、上櫃或兩者，普通股/特別股/ETF 是否分開。
台股歷史總覽必須確認交易狀態和資料覆蓋，價格來源遵守 `TAIWAN_MARKET.md` 的 provider policy。對每檔取得同時點同口徑日線。
從股票池自行計算可驗證的上漲/下跌數、均線上方占比、新高低與趨勢參與度。
每一項分母只包含達到該指標歷史長度的樣本，並列排除數；停牌/無行情不可補平價假裝交易。

不要使用原版美股 breadth/uptrend CSV、NYSE 日曆、S&P 500 股票池或 SPY 冒充台股。
若要求加權/櫃買指數，從交易所取得真正指數；共享價格 CLI 僅驗證股票/ETF，
它不把 `^TWII` 或 `TAIEX` 自動當股票。若使用者選擇 0050 等 ETF 作為代理，
清楚標明代理與差異，不把其成交量稱為全市場成交量。

產業輪動按 FinMind/官方分類，明列等權或市值權重。缺市值資料時不能宣稱市值加權。
跟進日/出貨日依原方法的研究條件逐日追蹤實際台股時段；資料不足就不能判定。
泡沫/頂部/宏觀綜合框架缺乏對應成分時輸出分項風險，不產生未驗證的台股總分。
圖表判讀須核對市場、來源、日期、座標、樣本口徑，不能猜圖中未提供的精確值。

產物包含母體、觀測/缺漏數、資料截止時間、公式、分項結果、限制及原始來源。

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
