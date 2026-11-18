# 實驗性台股／美股全市場掃描

本掃描器與既有報告保留追溯，未建立與所有原始策略管線的等價性。
正式 skill 沿用原版流程；見 [資料擴充契約](UPSTREAM_DATA_EXTENSION.md)。

`scripts/market_scan.py` 使用現有九個策略計算器，研究上市、上櫃及美國交易所掛牌股票／ETF。
這是研究條件掃描，不包含下單、期貨、選擇權或放空資格查證。

## 母體與資料

- 台股：TWSE ISIN 公開目錄的「股票」「ETF」分類，分 TWSE 與 TPEX；不將 FinMind 的歷史目錄當成仍掛牌名單。
- 美股：Nasdaq Trader 的 `nasdaqlisted.txt` 與 `otherlisted.txt`，保留來源時間、原始代號及交易所。普通股、存託憑證／股份與 ETF 納入；測試證券、權證、權利、特別股、單位組合、債券、ETN 另列排除表（不以名稱含有 common 等關鍵字作為必要條件）。未知交易所代碼保留原代碼，不猜名稱。
- 價格及基本面沿用 Yahoo；台股缺項可由 FinMind 補足。美股不把 FinMind 台股資料當成候補。
- 美股使用 USD、美東交易時間與 NYSE 交易日曆；PEAD 使用實際日曆提早收盤時間，美元流動性不經 USD/TWD 轉換。台股保留 TWD 與台灣交易日。
- Yahoo 的非 12 月會計年度及 52／53 週季度可比期間分開處理。EPS 缺值不抹除已取得的營收成長；非正 EPS 不偽裝一般盈餘成長。

## 執行

需安裝專案環境及 `market-calendar` 選用依賴。

```bash
mkdir -p reports/scan
.venv/bin/python -c 'import json; from scripts.market_universe import fetch_directories; print(json.dumps(fetch_directories(),ensure_ascii=False))' > reports/scan/universe.json
.venv/bin/python scripts/market_scan.py --directory reports/scan --end YYYY-MM-DD --workers 8
.venv/bin/python scripts/market_report.py reports/scan
```

`--end` 使用已完成交易日；同一次掃描維持同一日期區間。
每檔原始輸入與評估結果分開壓縮保存，重跑會略過已完成標的。
`--retry-prices` 只重試失敗行情，保留先前嘗試。Yahoo／FinMind 限流後共用五分鐘暫停狀態，跨工作程序及重啟保留；暫停期間明列缺資料，不假裝已成功取得。
程式修正後以 `--reevaluate` 重算已保存資料；仍未取得資料的標的不能變成合格候選。
原始輸入、結果、報告均在忽略的 `reports/`，不把全市場原始資料推上 GitHub。

## 結果判讀

- `candidates.csv`：必要條件通過，且沒有已知缺項的策略候選。
- `missing-data.csv`：含必要缺項、取得失敗、運算錯誤或尚未處理的逐檔／逐策略清單。
- `all-results.csv`：所有名單標的的九策略狀態，包括 ETF 公司基本面不適用。
- `excluded-securities.csv`：不在本次股票／ETF 範圍，證券與原因。
- `price-coverage.csv`：逐檔行情狀態、來源與取得失敗原因；有行情不代表所有基本面條件都有資料。
- `summary.json`：要求／已處理／未處理數量，分市場、策略的合格與缺資料數。
- `all-results.json.gz`：完整指標、條件與警告；`inputs/` 保存實際來源資料供重算。

PEAD 形態成立但總分缺資料時不列為完整進場候選；急漲 `parabolic` 是風險觀察名單。
估值排名分台／美市場，母體是有可比預估資料的股票，不是把缺估值者補零後排名。
共同技術策略仍以 [已公開的條件範圍](TAIWAN_ENGINES.md) 為準；美股恢復原版 0.90 美元動能觸發。
不宣稱全部上游市場環境、法人品質或交易準備度均已完成。現時財報快照不是歷史可知資料。
