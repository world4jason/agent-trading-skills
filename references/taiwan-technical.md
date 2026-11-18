# 台股量價與型態分析

先解析上市/上櫃及股票/ETF 身分，按使用者期間抓取日線。需要週線時依台灣交易日聚合
OHLCV；未收完的週線標示為暫定，不拿它與完整週比較。除權息、分割和停牌可能改變
原始走勢，未查證公司行動時不要把價差當技術訊號。不同還原口徑的價格不可拼接。

## 計算與解讀

- 價格與均線：指明期間和有效觀測數。200 日均線資料不足便標不足，不使用短均線冒充。
- RSI/ATR：從原方法論確認平滑方法、週期和所需暖機期，以 Python 計算，保留方法。
- VCP：沿用純計算器的收斂、平台與量縮邏輯。這些百分比研究條件不是經台股回測保證的勝率。
- 相對強弱：須使用相同日期、同口徑的實際台股基準或使用者股票池；沒有母體不能提供市場百分位。
- 動能與槌子線：使用明確的比例、成交量與前期條件；台幣絕對價格門檻須由使用者指定，不能沿用美元數字。
- 配對：以共同日期估計關係，檢查樣本外、成本與制度限制，研究價差不等於取得空方券源。

## 可重用的 VCP 純計算器

在本 bundle 使用 Python 的 importlib.util.spec_from_file_location 載入：
`skills/vcp-screener/scripts/calculators/vcp_pattern_calculator.py` 的
`calculate_vcp_pattern(historical_prices)`，以及
`volume_pattern_calculator.py` 的
`calculate_volume_pattern(historical_prices, pivot_price=None, contractions=None)`。
這些函式要求最近日期在前；將 provider 的 `data` 反轉後傳入，OHLCV 欄位同名。
先檢查至少 30 筆型態資料及所需成交量歷史，解釋函式的 `error`：資料不足是無法判定；若是收斂次數未達等形態條件，則為不符合，不能包裝為正向候選。
不載入 `screen_vcp.py` 或 FMPClient。單檔形態結果不是完整趨勢、RS 或全市場綜合分數。

輸出：日期與來源、趨勢/型態條件、支撐壓力、量價證據、無效條件、樣本限制。
ETF 技術圖形可分析，但不附加公司 EPS/營收評分；成交量/流動性須按 ETF 本身解讀。

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
