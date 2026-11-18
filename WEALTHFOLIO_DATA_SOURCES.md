# Wealthfolio 資料取得方式與本專案採用範圍

查閱日期：2026-11-18。

Wealthfolio 的 market-data crate 會依標的、供應商能力及使用者優先順序選擇來源，
失敗後切換其他供應商；它不是另一個提供完整財報與分析師預估的獨立資料商。
本專案採用其選源與資料驗證原則，不把整個 Rust／桌面應用程式當成 Python 依賴。

- [Provider registry](https://github.com/wealthfolio/wealthfolio/blob/main/crates/market-data/src/registry/provider_registry.rs)：能力篩選、優先順序、失敗切換、價格驗證。
- [Yahoo provider](https://github.com/wealthfolio/wealthfolio/blob/main/crates/market-data/src/provider/yahoo/mod.rs)：行情、資產資料、股利與分割事件。
- [Provider capabilities](https://github.com/wealthfolio/wealthfolio/blob/main/crates/market-data/src/provider/capabilities.rs)：支援能力分開宣告，不因有報價就假定有所有分析欄位。

## 本專案

原方法與正式入口見 [資料擴充契約](UPSTREAM_DATA_EXTENSION.md)。下列是附加工具的
現行資料行為，不表示每個原版 FMP client 都已串接這些來源。
Yahoo 快照遇到限流後會在同一 Python process 冷卻五分鐘，逐項保留缺資料原因。

`--provider auto` 先嘗試 Yahoo 日線，失敗、空資料或整段驗證不通過時改試 FinMind。
`--provider finmind` 或 `--provider yahoo` 指定偏好；候補資料須整段通過驗證，
不把兩者 K 線接成一條。報告記錄偏好、實際來源、失敗原因及還原口徑。

台股全市場目錄與交易日優先使用有該能力的 FinMind；目錄不可得時，指定股票可用
Yahoo 交易所、幣別與標的類型交叉驗證。不能從幾個 Yahoo 搜尋結果偽造完整股票池。
FinMind 交易日不可得時，可用 Yahoo 加權指數觀測日期，並明確標示可能漏資料。

財報、持股與分析師預估透過已安裝的 [yfinance Ticker API](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.html)
取得，FinMind 台股專屬資料仍可補足。各欄位保留日期與來源；預估缺席、分析師數不足、
幣別不一致及無法比對期間都不得補零。現時預估與持股快照不能冒充歷史可知資料。

Yahoo 可以查台股與美股，不代表本版全部交易制度、稅務及選股股票池已擴及美股。
附加實驗掃描器可涵蓋台灣上市、上櫃與美國股票／ETF；它不取代原始方法與管線。
