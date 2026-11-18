# 原方法不換，只擴充資料來源

本 fork 以 `tradermonty/claude-trading-skills` 的方法、工作流程、計算器與原始 CLI 為主。
基準版本：`fdfff010e1efe181ebe9c11a0109ef5f8b736147`。Codex、Claude、OpenCode
讀取同一份 `SKILL.md`；台股支援是附加資料與市場口徑指引，不是另一套策略。

## 上游原本怎麼取資料

| 用途 | 上游實作 | 台股附加來源與限制 |
| --- | --- | --- |
| 行情、公司資料、財報 | 各 skill 的 FMP client；多數先 stable，再 v3；共用產生器維護 | Yahoo 可取 `.TW`／`.TWO`；FinMind 補台股資料。不得把幣別與報表期間直接改名 |
| CANSLIM 法人持股 | FMP 持股摘要／持有人；部分資料補 FINVIZ | Yahoo 目前持股快照不等於歷史持股；FinMind 三大法人買賣超也不是持股比例 |
| 股利選股 | FMP 篩選、比率、三大報表、股利；可選 FINVIZ Elite 初篩 | 沿用原本健康檢查；缺資料就列缺項，ETF 不套公司 EPS 條件 |
| 預估盈餘、GARP | FMP analyst estimates、SQLite cache、分批收集、原管線品質檢查 | Yahoo 預估只能填實際取得且期間／幣別一致的欄位，不能推定 GAAP 或發布時間 |
| PEAD | FMP earnings calendar、實際／預估 EPS、報告時間、行情 | Yahoo 事件資料不足時不得推算公告時刻；必須對齊台股交易日與盤前／盤後 |
| 股票池 | FMP screener；VCP 的 S&P 500 名單另有公開 CSV 備援 | `market_universe.py` 可取 TWSE/TPEX 官方股票／ETF 名單及美股交易所名單 |
| 人工研究 | `SKILL.md` 指定的公開網站、新聞、圖表、使用者檔案 | 保留原研究方法，換成相應台灣來源並記錄證據；沒有 script 的 skill 不代表要另造引擎 |

原始程式入口現在直接執行原管線，沒有轉接到 `taiwan_screen.py`。
美股原有 FMP／FINVIZ 憑證需求仍存在。附加 Yahoo／FinMind 工具可使用，但目前**不是
所有原 CLI 都已接上這些來源**；不能把台股代號塞進原本的美股 CLI 就宣稱完成台股移植。

## 可直接使用的資料工具

```bash
.venv/bin/python scripts/taiwan_data.py prices --symbol 2330.TW --start 2026-10-01 --end 2026-10-30 --provider auto --output /tmp/taiwan-prices.json
```

`taiwan_data.py` 提供股票身分驗證、日線與 FinMind 原始資料集；
`taiwan_yahoo.snapshot()` 按需取得財報、持股、預估與事件，保留欄位缺失及取得日期。
`market_universe.py` 提供現行交易所名單。它們是資料取得工具，不是替代評分方法。
讀 [資料口徑](TAIWAN_MARKET.md)；以資料日期、幣別、單位、還原口徑及公告可知時間
核對原計算器所需輸入。資料不足時保留原條件並標示未評估，不降低門檻。

來源依所需能力與使用者偏好選擇，不規定 FinMind 一律優先。目前日線工具的 `auto`
順序為 Yahoo → FinMind；指定來源表示優先嘗試，若失敗會以另一來源重取完整區間。
這是現行工具的語意，不等同 Wealthfolio 的所有 provider 選項。

台股使用 `.TW`／`.TWO`、Asia/Taipei、TWD、實際上市／上櫃名單與交易日。
原版美元絕對門檻、NYSE 日曆、S&P 500 基準、SEC、Alpaca 等不能只換代號照搬。
ETF 可使用適用的價格／成交量方法；企業獲利與財報事件條件標示不適用。
範圍是台美股票與 ETF；原上游目錄保留其他 skill，不表示本 fork 安裝或執行期貨、選擇權。

## 參考 Wealthfolio 的地方

直接參考其 [ProviderRegistry](https://github.com/wealthfolio/wealthfolio/blob/main/crates/market-data/src/registry/provider_registry.rs)
與 [Yahoo provider](https://github.com/wealthfolio/wealthfolio/blob/main/crates/market-data/src/provider/yahoo/mod.rs)：
按標的／能力選源、確認交易所身分、驗證回傳資料、失敗備援、限流後冷卻、保留診斷。
本次 Yahoo 快照遇到 `YFRateLimitError` 後會在該 Python process 冷卻五分鐘，
後續欄位與標的不再立刻重試；其他來源仍可使用。這不代表已移植 Wealthfolio 的完整 registry、
跨 process token bucket 或所有付費供應商。

## 先前批次掃描的定位

`taiwan_screen.py`／`market_scan.py` 及其報告保留為**實驗性 fork 掃描器**。
它們重用部分上游計算器，但沒有與每條原始管線建立完整等價性，不能當作原版完整
CANSLIM、GARP、PEAD 或其他方法的驗收結果。預設 skill 指引不再把它們當成正式入口。
之前的全市場報告仍是當次實驗掃描結果，不能追溯改稱原版流程驗證。

完整台股 CLI 接線仍須逐條處理資料契約、幣別門檻、交易日與基準，再跑原管線回歸；
目前不宣稱這部分已完成。README 的上游內容與繁體中文版本保留。

## 本次驗證（2026-11-18）

- 2,611 項測試通過（另有 13 個 subtests）：原 CANSLIM、VCP、PEAD、股利、GARP、
  Stockbee、parabolic，以及原導航器、安裝與附加資料工具。
- FMP client 產生器 `--check`、skills index／workflow 嚴格驗證及 skillset 驗證通過。
- Yahoo 即時資產資料抽查：2330.TW、6488.TWO、0050.TW、AAPL 的回傳代號、幣別、
  股票／ETF 類型均成功取得且符合抽查標的。這只驗證該資料能力，不代表完整財報／預估。
- 本次沒有重跑全市場掃描，也沒有完成所有原版 CLI 的台股端到端驗證。
