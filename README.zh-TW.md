# agent-trading-skills

適用於 Codex、Claude、OpenCode 等 AI agent 的交易研究 skills。

[English](README.md) · [日本語](README.ja.md) · **繁體中文（台灣）**

## 關於這個 fork

本專案以 [TraderMonty 的 Claude Trading Skills](https://github.com/tradermonty/claude-trading-skills) 為基礎，保留原專案的介紹、工作流程、範例、skill 目錄及 Claude 安裝說明。

本版額外提供：

- **Codex 安裝與執行說明**，以及改版 skills 的本機安裝工具。
- **供 Codex、Claude、OpenCode 等相容 agent 使用的 skill 指引**。已驗證 Codex 安裝；其他用戶端尚未在本 fork 獨立驗證。
- **台灣上市／上櫃股票與 ETF 的附加資料工具**（Yahoo Finance、FinMind），保留原策略、工作流程與 CLI 入口。另有實驗性台美股批次掃描器，不等同所有原版管線。

先讀 [原方法與資料擴充契約](UPSTREAM_DATA_EXTENSION.md)，查看原始來源、已接線範圍及待完成項目。

安裝與資料來源行為請見 [本版安裝與差異](FORK_NOTES.md)；已實作的掃描範圍請見 [台美股全市場掃描](CROSS_MARKET_SCAN.md)。
以下為原專案說明的繁中翻譯；其中的目錄、整合、發行版本及平台支援描述，不表示本版已完成所有上游流程的改寫或驗證。方案、價格與額度沿用英文版記載，實際使用前請以服務商公告為準。

---

Claude Trading Skills 最初是原作者為了用 AI 改善自己的交易流程而建立的個人專案。

這是一套以 Claude Skills 為基礎的交易工作流程工具，主要服務時間有限的個人投資人。

適合以長期投資、ETF 與股利股票為核心，並在市場條件有利時，以有紀律的波段交易作為衛星策略的投資人。

它的目的不是把買賣決策交給 AI，而是讓市場檢視、風險管理、交易規劃、紀錄與持續改善有章可循。開放原始碼，是因為有助於交易決策的流程、檢查表與檢討習慣，可以透過共同實踐而改善。

這不是報牌服務，也不承諾獲利，而是協助交易者建立更好決策流程的工具。

專案採取 **先為自己打造，再開放給他人** 的立場：先成為作者實際使用的工作流程，再分享給面臨相似限制的人。

📖 **文件網站：** <https://tradermonty.github.io/claude-trading-skills/>

**專案願景：** [`PROJECT_VISION.md`](PROJECT_VISION.md)

英文版請見 [README.md](README.md)，日文版請見 [README.ja.md](README.ja.md)。

## 免責聲明

本儲存庫僅供教育、研究與流程改善使用，不構成財務建議、投資顧問服務、稅務建議、法律建議、交易訊號服務或券商下單平台。交易與投資存在風險，可能損失本金。過去績效、回測、篩選、報告及 AI 產生的分析，都不保證未來結果。所有交易決策、部位規模、稅務與法規遵循，以及券商使用方式，均由使用者自行負責。

本專案依 MIT 授權提供，**按現狀提供，不附任何擔保**。

## 適合哪些人

- 時間有限的個人投資人。
- 希望透過有紀律的波段交易增加機會的長期投資人。
- 需要有系統檢視投資組合的股利與 ETF 投資人。
- 希望先管理風險，再尋找交易候選的交易者。
- 希望記錄並改善決策流程的投資人。

它不是為全自動交易、外包交易訊號或極短線交易而設計。

## 建議入門流程

新使用者可先選擇下列工作流程。每個連結都指向 [`workflows/`](workflows/) 下的機器可讀流程清單，依序列出需要的 skills、決策檢查關卡與產出檔案。

| 目標 | 工作流程 | 主要 skills | API 需求 |
| --- | --- | --- | --- |
| 每日 15 分鐘市場檢查 | [`market-regime-daily`](workflows/market-regime-daily.yaml) | market-breadth-analyzer、uptrend-analyzer、exposure-coach | 基本流程不需 API |
| 每週長期投資組合檢視 | [`core-portfolio-weekly`](workflows/core-portfolio-weekly.yaml)（[範例](examples/workflows/core-portfolio-weekly/sample-run/)） | portfolio-manager、kanchi-dividend-review-monitor、trader-memory-core | 需要 Alpaca；手動 CSV 為功能較受限的替代方式 |
| 風險條件允許時才尋找波段候選 | [`swing-opportunity-daily`](workflows/swing-opportunity-daily.yaml)（[範例](examples/workflows/swing-opportunity-daily/sample-run/)） | vcp-screener、drawdown-circuit-breaker、technical-analyst、position-sizer、trader-memory-core、pre-trade-discipline-gate | 篩選使用 FMP；風險與紀律關卡使用本機狀態 |
| 記錄每筆已平倉交易並從中學習 | [`trade-memory-loop`](workflows/trade-memory-loop.yaml) | trader-memory-core、signal-postmortem | 手動流程不需 API |
| 每月檢討績效與調整規則 | [`monthly-performance-review`](workflows/monthly-performance-review.yaml)（[範例](examples/workflows/monthly-performance-review/sample-run/)） | trader-memory-core、signal-postmortem、backtest-expert | 手動流程不需 API |

如何讀取流程清單並手動執行，請見 [`workflows/README.md`](workflows/README.md)。想快速知道適合自己的流程，可閱讀 [尋找適合的工作流程](docs/en/find-your-workflow.md)（[日文](docs/ja/find-your-workflow.md)）。

第一次使用可跟著 [第一週入門](docs/en/your-first-week.md)（[日文](docs/ja/your-first-week.md)），完成安裝、不需付費資料 API 的市場檢查、第一筆交易日誌與第一次每週檢討。

### 產出範例

以下圖片使用虛構資料，讓你在安裝前先了解產出形式。它們是示意圖，不是即時行情或交易指示。

點選預覽可開啟完整 SVG；手機使用者可在開啟後放大。

[![Navigator 示意：每日 15 分鐘市場檢查，列出三個必要 skills 與不需付費 API 的流程](docs/assets/previews/navigator-recommendation.svg)](docs/assets/previews/navigator-recommendation.svg)

**選擇流程：** [Trading Skills Navigator](docs/en/skills/trading-skills-navigator.md) 會根據你的目標建議起點。

[![市場風險姿態示意：曝險上限 36%，僅能降低曝險 REDUCE_ONLY；因重要輸入缺漏而標為低信心 LOW](docs/assets/previews/market-posture.svg)](docs/assets/previews/market-posture.svg)

**檢視市場風險：** [每日市場環境流程](workflows/market-regime-daily.yaml) 最後產出 Exposure Coach 的風險姿態，供人判斷，不會下單。

[![每週績效摘要示意：四筆虛構已平倉交易，勝率 50%，已實現獲利 75 美元](docs/assets/previews/weekly-digest.svg)](docs/assets/previews/weekly-digest.svg)

**從已平倉交易學習：** [Weekly Performance Digest](docs/en/skills/weekly-performance-digest.md) 彙整已實現結果與流程上的教訓。

### 實際使用成本

英文版記載 Claude 網頁版 Skills 可供 Free、Pro、Max、Team 與 Enterprise 帳號使用；權限可能變動，請參閱 Anthropic 的 [Skills 說明](https://support.claude.com/en/articles/12512180-use-skills-in-claude)。Claude Code 有獨立的帳號需求，Claude.ai Free 方案不包含它；詳見 [Claude Code 安裝指南](https://code.claude.com/docs/en/getting-started)。

FMP、FINVIZ Elite 與 Alpaca 是特定流程選用的資料或券商整合。下列五個 skills 的入門流程可使用公開 CSV、圖表截圖與本機檔案，不需要訂閱付費市場資料 API。

### 不需 API 金鑰的入門流程

若沒有訂閱 FMP／FINVIZ／Alpaca，可先手動使用這五個 skills：

1. `market-breadth-analyzer`：用公開 CSV 評估市場廣度，不需 API 金鑰。
2. `uptrend-analyzer`：用公開 CSV 評估上升趨勢參與度，不需 API 金鑰。
3. `position-sizer`：純計算，不進行輸入／輸出操作。
4. `trader-memory-core`：以本機 YAML 記錄交易日誌。
5. `signal-postmortem`：交易訊號檢討框架。

這個流程讓你在 **不使用付費資料 API** 的情況下，檢視市場、計算部位、記錄決策與檢討結果。「不需 API」不代表「不需外部資料」：仍需要公開 CSV、圖表截圖或本機檔案。確切輸入需求請看 [`skills-index.yaml`](skills-index.yaml) 中各 skill 的 `integrations:` 欄位。

> **權威來源：** [`skills-index.yaml`](skills-index.yaml) 是 skills 的正式索引。若 README、`CLAUDE.md` 或文件與索引不一致，以索引為準。多 skill 工作流程則以 [`workflows/*.yaml`](workflows/) 為準。

## 儲存庫結構

- `skills/<skill-name>/`：各交易 skill 的原始檔，包含 `SKILL.md`、參考資料與輔助程式。
- `skills-index.yaml`：所有 skills 的正式中繼資料索引，包含 ID、分類、整合及所屬流程。
- `workflows/`：核心＋衛星策略的操作流程清單，透過 `--strict-workflows` 驗證。
- `skill-packages/`：預先打包的 `.skill` 檔，可上傳至 Claude 網頁版的 **Skills** 頁籤。
- `docs/`：文件網站內容、自動產生的 skill 頁面，以及結構規格 `docs/dev/metadata-and-workflow-schema.md`。
- `scripts/`：儲存庫層級的自動化工具，包括結構驗證與一次性初始化工具。
- `skillsets/`：按用途定義必要、建議與選用 skills 的安裝組合。上游提供六組：market-regime、core-portfolio、dividend-income、swing-opportunity、trade-memory、strategy-research，由 Navigator 使用。

## 開始使用

第一次使用請先讀 [常見問題](docs/en/faq.md)，了解方案、成本、安全與適用範圍。

更新已安裝的 skill 前，請閱讀 [變更紀錄](CHANGELOG.md) 與 [版本相容性及遷移政策](docs/dev/release-compatibility.md)。

### Claude 網頁版

1. 開啟 [上游最新 GitHub Release](https://github.com/tradermonty/claude-trading-skills/releases/latest)，下載需要的 `.skill` 檔與 `SHA256SUMS`，依 [發行政策](docs/dev/release-compatibility.md) 驗證雜湊值。若沒有發行版本，可依下方方式使用原始資料夾，或用 `scripts/package_skills.py` 在本機打包。
2. 個人帳號請到 **Settings > Capabilities** 啟用 **Code execution and file creation**。Team 與 Enterprise 可能需要組織擁有者開啟 Skills。
3. 開啟 **Customize > Skills**，上傳 ZIP，確認已列出並視需要啟用；詳見 [Skills 說明](https://support.claude.com/en/articles/12512180-use-skills-in-claude)。

### Claude Code（桌面版或 CLI）

1. 複製或下載此儲存庫。
2. 將需要的 skill 資料夾，例如 `backtest-expert`，複製到個人使用的 `~/.claude/skills/`，或專案內的 `.claude/skills/`；詳見 [安裝指南](https://code.claude.com/docs/en/getting-started)。
3. Claude Code 會偵測既有 skills 目錄的變更。只有在工作階段開始後才新建頂層 skills 目錄時，才需要重新啟動。

> 提示：`.skill` 套件由原始資料夾打包，會排除測試與本機建置產物。若要自訂 skill，先修改原始資料夾，再執行 `python3 scripts/package_skills.py --skill <skill-name>`，然後上傳至網頁版。

## 支援平台

共用專案環境支援 Linux、Windows 與 macOS 上的 Python **3.11 至 3.13**；獨立打包 skills 的原始碼最低版本維持 Python **3.9**。只有經專案 CI 實際測試的組合才算正式支援；範圍內其他組合僅盡力相容，尚未驗證。確切矩陣與執行方式請見 [相容性矩陣](docs/dev/compatibility-matrix.md)。

## 搭配使用的工作套件

想要可直接執行的 agent 工作流程，可參考 [Hermes Trading Research Agent Work Package](https://github.com/tradermonty/hermes-trading-research-agent-work-package)。

它將這些 skills 整合進 Hermes 設定檔，提供 `/pre-market-routine`、`/after-close-review`、`/trade-journal`、`/weekly-portfolio-review`、`/monthly-performance-review` 等按任務設計的斜線指令。

這是研究、日誌與風險檢視助理，**不是自動交易系統**。它不會下單、不提供報牌服務，也不會執行隱藏的排程；**人工決策關卡仍是核心**。

## 主要 skill 領域

| 領域 | 代表 skills |
| --- | --- |
| 市場環境 | `market-breadth-analyzer`、`uptrend-analyzer`、`exposure-coach` |
| 核心投資組合 | `portfolio-manager`、`us-undervalued-growth-screener` |
| 股利收入 | `kanchi-dividend-sop`、`value-dividend-screener`、`dividend-growth-pullback-screener` |
| 波段機會 | `vcp-screener`、`canslim-screener`、`breakout-trade-planner` |
| 交易規劃 | `position-sizer`、`technical-analyst`、`pre-trade-discipline-gate` |
| 交易紀錄 | `trader-memory-core`、`signal-postmortem` |
| 策略研究 | `backtest-expert`、`manifoldbt-backtester`、`edge-pipeline-orchestrator` |
| 進階衛星策略 | `parabolic-short-trade-planner`、`earnings-trade-analyzer`、`options-strategy-advisor` |

英文版的詳細目錄由 `scripts/generate_catalog_from_index.py` 根據 `skills-index.yaml` 自動產生。更新英文描述時，請修改索引並重新執行 `python3 scripts/generate_catalog_from_index.py`。繁中目錄是對保留之上游英文目錄的人工翻譯，需隨英文版同步維護，不由該工具產生。

想更方便瀏覽，可使用文件網站；skill 生命週期、測試覆蓋與執行健康度的自動摘要，請見 [品質儀表板](https://tradermonty.github.io/claude-trading-skills/en/quality-dashboard/)。

## 詳細 skill 目錄

以下保留上游 skill 名稱、ID、整合需求與狀態；這些上游標示不代表本 fork 對每個項目都已驗證。

### 市場環境

| Skill | 說明 | 整合需求 | 角色 | 上游狀態 |
|---|---|---|---|---|
| **Breadth Chart Analyst** (`breadth-chart-analyst`) | 分析市場廣度圖，尤其是以 200 日均線為基礎的 S&P 500 廣度指數，以及美股上升趨勢股票占比圖。 | `chart_image` **必要** | 獨立使用 | 正式版 |
| **COT Contrarian Detector** (`cot-contrarian-detector`) | 利用 CFTC 交易人持倉報告（COT）辨識大型投機者的擁擠部位，實作 Jason Shapiro 逆向方法的第一步。 | `fmp` **必要** | 流程步驟 | 正式版 |
| **Crypto Regime Analyzer** (`crypto-regime-analyzer`) | 使用不需金鑰的免費公開資料，從六項成分評估加密市場環境，綜合分數 0–100，100 代表積極承擔風險。 | `coingecko` **必要**, `binance_funding` _建議_, `prices_json` 選用 | 獨立使用 | 測試版 |
| **Downtrend Duration Analyzer** (`downtrend-duration-analyzer`) | 分析歷史下跌趨勢持續時間，產生互動式 HTML 直方圖，呈現各產業與市值規模的典型修正期間。 | `fmp` **必要** | 僅供研究 | 正式版 |
| **Exposure Coach** (`exposure-coach`) | 整合市場廣度、環境與資金流訊號，產出單頁風險姿態摘要，包含淨曝險上限、成長／價值偏向、參與廣度，以及可否建立新部位或應優先保留現金。 | `local_calculation` — | 流程步驟 | 正式版 |
| **FTD Detector** (`ftd-detector`) | 依 William O'Neil 方法辨識後續跟進日（FTD），協助確認市場底部。 | `fmp` **必要** | 獨立使用 | 正式版 |
| **IBD Distribution Day Monitor** (`ibd-distribution-day-monitor`) | 辨識 QQQ／SPY 的 IBD 式出貨日（放量且收盤下跌至少 0.2%），追蹤 25 個交易日到期及上漲 5% 失效規則，統計 d5／d15／d25 群聚，分類 NORMAL／CAUTION／HIGH／SEVERE 風險，並產出 TQQQ／QQQ… | `fmp` **必要** | 獨立使用 | 正式版 |
| **Macro Regime Detector** (`macro-regime-detector`) | 透過跨資產比率分析，辨識一至兩年尺度的總經結構轉變。 | `yfinance` **必要**, `fmp` 選用 | 流程步驟 | 正式版 |
| **Market Breadth Analyzer** (`market-breadth-analyzer`) | 使用 TraderMonty 的公開 CSV 資料量化市場廣度健康度。 | `public_csv` **必要** | 流程步驟 | 正式版 |
| **Market Environment Analysis** (`market-environment-analysis`) | 提供完整的市場環境分析與報告。 | `websearch` **必要**, `chart_image` 選用 | 流程步驟 | 正式版 |
| **Market News Analyst** (`market-news-analyst`) | 分析近期牽動市場的新聞，以及對股票與商品市場的影響。 | `websearch` **必要** | 流程步驟 | 正式版 |
| **Market Top Detector** (`market-top-detector`) | 結合 O'Neil 出貨日、Minervini 領導股轉弱與 Monty 防禦性類股輪動，評估市場高檔風險。 | `fmp` **必要**, `public_csv` 選用 | 流程步驟 | 正式版 |
| **News Reaction Failure Analyzer** (`news-reaction-failure-analyzer`) | 判斷市場是否未對有利於擁擠投機部位的消息作出預期反應，實作 Jason Shapiro 方法第二步，並使用經蒙地卡羅驗證的漂移顯著性判定。 | `fmp` **必要**, `websearch` **必要** | 流程步驟 | 正式版 |
| **Sector Analyst** (`sector-analyst`) | 分析產業輪動模式及市場循環位置。 | `chart_image` **必要** | 流程步驟 | 正式版 |
| **Uptrend Analyzer** (`uptrend-analyzer`) | 使用 Monty 上升趨勢比例儀表板資料分析市場廣度，判讀目前市場環境。 | `public_csv` **必要** | 流程步驟 | 正式版 |
| **US Market Bubble Detector** (`us-market-bubble-detector`) | 依修訂版 Minsky／Kindleberger v2.1 框架，以量化資料評估市場泡沫風險。 | `user_input` **必要** | 獨立使用 | 正式版 |

### 核心投資組合

| Skill | 說明 | 整合需求 | 角色 | 上游狀態 |
|---|---|---|---|---|
| **Portfolio Manager** (`portfolio-manager`) | 透過 Alpaca MCP Server 取得持股與部位，分析資產配置、風險指標、個股部位與分散程度，並提出再平衡建議。 | `alpaca` 選用 | 流程步驟 | 正式版 |
| **US Undervalued Growth Screener** (`us-undervalued-growth-screener`) | 篩選並排名美國上市中小型低估成長股；使用產生的 stable 優先 FMP 用戶端、持久化 SQLite 快取、可調整的掛牌名單列舉、FY1 預估正規化、經驗證的 20 日流動性、確定性的四路探索、同口徑預估估值、一般及股份基礎薪酬（SBC）調整後自由現金流，並檢查稀釋、同業、景氣循環與專利獨占期結束（LOE），執行嚴格終評、發布前稽核及完整證據打包。 | `fmp` _建議_, `alternate_market_data` 選用, `sec_edgar` **必要**, `company_ir` **必要**, `official_macro` **必要**, `local_calculation` — | 獨立使用 | 測試版 |

### 股利收入

| Skill | 說明 | 整合需求 | 角色 | 上游狀態 |
|---|---|---|---|---|
| **Dividend Growth Pullback Screener** (`dividend-growth-pullback-screener`) | 尋找年度股利成長至少 12%、殖利率至少 1.5%，且因 RSI ≤40 顯示短暫回檔的優質股利成長股。 | `fmp` **必要**, `finviz` _建議_ | 流程步驟 | 正式版 |
| **Kanchi Dividend Review Monitor** (`kanchi-dividend-review-monitor`) | 以 Kanchi 式強制檢視條件 T1–T5 監控股利投資組合，將異常標記為 OK／WARN／REVIEW，不自動賣出。 | `fmp` _建議_ | 流程步驟 | 正式版 |
| **Kanchi Dividend SOP** (`kanchi-dividend-sop`) | 將 Kanchi 股利投資方法轉為可重複執行的美股操作流程。 | `fmp` _建議_ | 流程步驟 | 正式版 |
| **Kanchi Dividend US Tax Accounting** (`kanchi-dividend-us-tax-accounting`) | 提供 Kanchi 式收益投資組合的美國股利稅務與帳戶配置流程。 | `local_calculation` — | 流程步驟 | 正式版 |
| **Value Dividend Screener** (`value-dividend-screener`) | 結合價值條件（本益比低於 20、股價淨值比低於 2）、至少 3% 殖利率，以及三年股利／營收／EPS 持續成長，篩選美股股利機會。 | `fmp` **必要**, `finviz` _建議_ | 流程步驟 | 正式版 |

### 波段機會

| Skill | 說明 | 整合需求 | 角色 | 上游狀態 |
|---|---|---|---|---|
| **Breakout Trade Planner** (`breakout-trade-planner`) | 依 VCP 篩選結果產生 Minervini 式突破交易計畫，包含最壞情境風險、投資組合總風險管理，以及相容 Alpaca 的訂單範本（預掛使用 stop-limit bracket，確認後使用 limit bracket…）。 | `local_calculation` — | 流程步驟 | 正式版 |
| **CANSLIM Screener** (`canslim-screener`) | 以 William O'Neil 的 CANSLIM 成長股方法篩選美股。 | `fmp` **必要** | 流程步驟 | 正式版 |
| **Finviz Screener** (`finviz-screener`) | 將自然語言需求轉為 FinViz 篩選網址並開啟。 | `finviz` 選用 | 獨立使用 | 正式版 |
| **Stockbee Exhaustion Hammer Screener** (`stockbee-exhaustion-hammer-screener`) | 透過品質／流動性關卡、先前動能、回檔深度、跌破後收復、槌子線形狀、成交量確認、市場條件與風險距離，篩選 Stockbee 式賣壓衰竭槌子線美股候選。 | `fmp` **必要**, `prices_json` 選用, `profiles_json` 選用, `local_calculation` — | 流程步驟 | 測試版 |
| **Stockbee Momentum Burst Screener** (`stockbee-momentum-burst-screener`) | 透過 4% 突破、美元漲幅突破、振幅擴張、成交量擴張、型態品質與風險距離，篩選 Stockbee 式三至五日動能爆發美股候選。 | `fmp` **必要**, `prices_json` 選用, `local_calculation` — | 流程步驟 | 測試版 |
| **Theme Detector** (`theme-detector`) | 辨識並分析跨產業熱門市場主題。 | `fmp` 選用, `finviz` _建議_ | 流程步驟 | 正式版 |
| **VCP Screener** (`vcp-screener`) | 在 S&P 500 股票中篩選 Mark Minervini 的波動收斂型態（VCP）。 | `fmp` **必要** | 流程步驟 | 正式版 |

### 交易規劃

| Skill | 說明 | 整合需求 | 角色 | 上游狀態 |
|---|---|---|---|---|
| **Contrarian Setup Gate** (`contrarian-setup-gate`) | 離線整合 COT 擁擠程度、消息反應失敗與週線價格確認，透過條件未齊即阻擋的優先順序狀態機，產出單一 setup_status，作為 Jason Shapiro 逆向方法的決策核心。 | `local_calculation` — | 流程步驟 | 正式版 |
| **Drawdown Circuit Breaker** (`drawdown-circuit-breaker`) | 讀取 trader-memory-core 狀態，以每日虧損上限、連敗冷卻與週／月回撤停用條件，判斷當日是否允許新增交易風險。 | `local_calculation` — | 流程步驟 | 正式版 |
| **Futures Position Sizer** (`futures-position-sizer`) | 根據方向、進場與停損價，使用經核對的 23 市場合約規格表（乘數、最小跳動、每跳價值）計算期貨口數，實作 Jason Shapiro 流程第四步。 | `local_calculation` — | 流程步驟 | 正式版 |
| **Position Sizer** (`position-sizer`) | 依風險計算股票多單部位規模。 | `local_calculation` — | 流程步驟 | 正式版 |
| **Pre-Trade Discipline Gate** (`pre-trade-discipline-gate`) | 離線人工執行檢查表，阻擋無計畫、部位過大、報復性交易風險、被市場環境或回撤限制禁止的進場，並記錄結果。 | `local_calculation` — | 流程步驟 | 正式版 |
| **Technical Analyst** (`technical-analyst`) | 分析股票、股價指數、加密貨幣或外匯貨幣對的週線圖。 | `chart_image` **必要**, `fmp` 選用 | 流程步驟 | 正式版 |
| **US Stock Analysis** (`us-stock-analysis`) | 綜合美股基本面（財務指標、企業品質、估值）、技術面（指標、型態、支撐／壓力）、個股比較與投資報告產出。 | `user_input` **必要**, `websearch` **必要** | 獨立使用 | 正式版 |

### 交易紀錄

| Skill | 說明 | 整合需求 | 角色 | 上游狀態 |
|---|---|---|---|---|
| **Signal Postmortem** (`signal-postmortem`) | 記錄並分析優勢研究流程與其他 skills 所產生訊號的交易後結果。 | `local_calculation` —, `fmp` 選用 | 流程步驟 | 正式版 |
| **Stockbee Setup Fluency Trainer** (`stockbee-setup-fluency-trainer`) | 以動能爆發候選建立 Stockbee 型態樣本簿，更新三日／五日後續表現、最大有利／不利波動（MFE／MAE）、停損觸發、結果標籤與群組統計。 | `prices_json` 選用, `fmp` 選用, `local_calculation` — | 流程步驟 | 測試版 |
| **Trade Hypothesis Ideator** (`trade-hypothesis-ideator`) | 從市場資料、交易紀錄與日誌片段提出可否證的策略假說，產出排序後的假說卡片，並可匯出 strategy.yaml。 | `local_calculation` — | 流程步驟 | 正式版 |
| **Trade Performance Coach** (`trade-performance-coach`) | 檢視已平倉交易、分批出場與月度彙總中的流程遵循、風險紀律、執行品質與行為模式，產出下次交易的操作規則。 | `local_calculation` — | 流程步驟 | 測試版 |
| **Trader Memory Core** (`trader-memory-core`) | 追蹤投資論點的完整生命週期，從篩選想法到平倉後檢討。 | `fmp` 選用 | 流程步驟 | 正式版 |
| **Weekly Performance Digest** (`weekly-performance-digest`) | 彙整已平倉交易的每週績效，包括勝率、期望值與型態分析。 | `local_calculation` — | 獨立使用 | 正式版 |

### 策略研究

| Skill | 說明 | 整合需求 | 角色 | 上游狀態 |
|---|---|---|---|---|
| **Backtest Expert** (`backtest-expert`) | 提供系統化交易策略回測的專業指引。 | `user_input` **必要** | 流程步驟 | 正式版 |
| **Edge Candidate Agent** (`edge-candidate-agent`) | 從日終資料提出並排序美股做多優勢研究題目，匯出可供 trade-strategy-pipeline 第一階段使用的候選規格。 | `fmp` 選用 | 流程步驟 | 正式版 |
| **Edge Concept Synthesizer** (`edge-concept-synthesizer`) | 在策略設計／匯出前，將偵測題目與線索整理成一致的優勢概念，包含論點、失效條件與策略操作手冊。 | `local_calculation` — | 內部元件 | 正式版 |
| **Edge Hint Extractor** (`edge-hint-extractor`) | 從每日市場觀察與新聞反應擷取優勢線索，可選擇用 LLM 協助構思，並產出正式 hints.yaml 供後續概念整合與自動偵測。 | `local_calculation` — | 流程步驟 | 正式版 |
| **Edge Pipeline Orchestrator** (`edge-pipeline-orchestrator`) | 串接從偵測、概念整合、策略設計到審查、修訂與匯出的完整優勢研究流程。 | `local_calculation` — | 僅供研究 | 正式版 |
| **Edge Signal Aggregator** (`edge-signal-aggregator`) | 整合並排序 edge-candidate-agent、theme-detector、sector-analyst、institutional-flow-tracker 等訊號，以加權評分、去重及矛盾處理…產出信心排序儀表板。 | `local_calculation` — | 獨立使用 | 正式版 |
| **Edge Strategy Designer** (`edge-strategy-designer`) | 將抽象優勢概念轉為策略草案，並可匯出供 edge-candidate-agent 匯出／驗證流程使用的研究題目 YAML。 | `local_calculation` — | 內部元件 | 正式版 |
| **Edge Strategy Reviewer** (`edge-strategy-reviewer`) | 審查策略草案的優勢合理性、過度擬合風險、樣本充分性與執行可行性。 | `local_calculation` — | 內部元件 | 正式版 |
| **manifoldbt Backtester** (`manifoldbt-backtester`) | 使用 manifoldbt Rust 引擎，對 OHLCV 資料執行宣告式策略規格，產出 backtest-expert 評分所需的八項輸入。 | `manifoldbt` **必要**, `ohlcv_file` **必要** | 僅供研究 | 測試版 |
| **MT5 Robot Tester** (`mt5-robot-tester`) | 以可續跑的三輪本機流程批次測試 MetaTrader 5 EA，排名結果並保留確定性的參數與商品學習紀錄。 | `mt5_local_files` **必要**, `local_calculation` — | 僅供研究 | 測試版 |
| **Residual Edge Analyzer** (`residual-edge-analyzer`) | 使用 HAC 迴歸、滾動穩定性、基準敏感度與市場環境診斷，拆解策略報酬中的基準曝險與殘餘表現。 | `local_calculation` — | 僅供研究 | 測試版 |
| **Scenario Analyzer** (`scenario-analyzer`) | 透過 scenario-analyst agent 分析新聞標題後 18 個月的情境，並由 strategy-reviewer 提供第二意見，產出主要／次要／第三層影響與選股。 | `websearch` **必要** | 流程步驟 | 正式版 |
| **Stanley Druckenmiller Investment** (`stanley-druckenmiller-investment`) | Druckenmiller 策略整合器：整合市場廣度、市場高檔、總經環境、FTD、VCP、主題與 CANSLIM 等八個上游 skill 輸出，形成 0–100 的統一信心分數… | `local_calculation` — | 流程步驟 | 正式版 |
| **Stockbee 20% Study** (`stockbee-20pct-study`) | 建立 Stockbee 式單日漲跌逾 20% 股票事件研究，分類催化因素、型態背景、後續表現與優勢線索，不將觀察結果當成買賣訊號。 | `fmp` **必要**, `prices_json` 選用, `news_events_json` 選用, `websearch` 選用, `local_calculation` — | 流程步驟 | 測試版 |
| **Strategy Pivot Designer** (`strategy-pivot-designer`) | 辨識回測改善停滯，依當前失敗型態設計結構不同的策略轉向候選。 | `local_calculation` — | 僅供研究 | 正式版 |

### 進階衛星策略

| Skill | 說明 | 整合需求 | 角色 | 上游狀態 |
|---|---|---|---|---|
| **Earnings Trade Analyzer** (`earnings-trade-analyzer`) | 以跳空幅度、財報前趨勢、成交量趨勢、MA200 與 MA50 位置五項因素，分析近期財報後股票反應。 | `fmp` **必要** | 流程步驟 | 正式版 |
| **Institutional Flow Tracker** (`institutional-flow-tracker`) | 利用 13F 申報資料分析機構持股變化與投資組合資金流。 | `fmp` **必要** | 獨立使用 | 正式版 |
| **Options Strategy Advisor** (`options-strategy-advisor`) | 提供選擇權策略分析與模擬。 | `fmp` 選用 | 獨立使用 | 正式版 |
| **Pair Trade Screener** (`pair-trade-screener`) | 辨識並分析股票配對交易機會的統計套利工具。 | `fmp` **必要** | 獨立使用 | 正式版 |
| **Parabolic Short Trade Planner** (`parabolic-short-trade-planner`) | 篩選美股拋物線式急漲衰竭型態，產出有條件的盤前放空計畫，再以即時五分鐘 K 線檢查盤中觸發。 | `fmp` **必要**, `alpaca` 選用 | 獨立使用 | 正式版 |
| **PEAD Screener** (`pead-screener`) | 篩選財報後跳空上漲股票的財報後漂移（PEAD）型態。 | `fmp` **必要** | 流程步驟 | 正式版 |
| **Stockbee Episodic Pivot Analyzer** (`stockbee-episodic-pivot-analyzer`) | 依催化因素品質、跳空／振幅擴張、量能衝擊、被忽略程度／重估背景、流動性與事件日低點風險，分析財報、展望、併購、FDA、分析師、合約、產品、軋空及故事／主題帶來的 Stockbee 首日事件轉折候選。 | `catalyst_events_json` **必要**, `fmp` 選用, `local_calculation` — | 流程步驟 | 測試版 |

### 管理與開發工具

| Skill | 說明 | 整合需求 | 角色 | 上游狀態 |
|---|---|---|---|---|
| **Data Quality Checker** (`data-quality-checker`) | 在市場分析文件與部落格文章發布前，驗證資料品質。 | `local_calculation` — | 獨立使用 | 正式版 |
| **Dual Axis Skill Reviewer** (`dual-axis-skill-reviewer`) | 以兩個面向審查任意專案的 skills：確定性的程式檢查（結構、程式、測試、執行安全），以及 LLM 深度審查發現。 | `local_calculation` — | 流程步驟 | 正式版 |
| **Earnings Calendar** (`earnings-calendar`) | 使用 FMP API 取得即將公布財報的美股日曆。 | `fmp` **必要** | 獨立使用 | 正式版 |
| **Economic Calendar Fetcher** (`economic-calendar-fetcher`) | 使用 FMP API 取得即將公布的經濟事件與資料。 | `fmp` **必要** | 獨立使用 | 正式版 |
| **FXMacroData Calendar** (`fxmacrodata-calendar`) | 使用 FXMacroData 取得官方來源的總經公布事件，供交易規劃與事件風險檢查。 | `fxmacrodata` 選用 | 獨立使用 | 測試版 |
| **Skill Designer** (`skill-designer`) | 將結構化想法規格轉成新的 Claude skill。 | `local_calculation` — | 內部元件 | 正式版 |
| **Skill Idea Miner** (`skill-idea-miner`) | 從 Claude Code 工作階段紀錄中挖掘 skill 想法。 | `local_calculation` — | 內部元件 | 正式版 |
| **Skill Integration Tester** (`skill-integration-tester`) | 檢查 skill 是否存在、跨 skill 資料契約（JSON schema）相容性、檔案命名與交接完整性，以驗證 CLAUDE.md 定義的多 skill 流程。 | `local_calculation` — | 獨立使用 | 正式版 |
| **Trading Skills Navigator** (`trading-skills-navigator`) | 從自然語言交易目標推薦適合的流程、skill 組合、API 需求與安裝方式。 | `local_calculation` — | 獨立使用 | 正式版 |

## 更多工作流程範例

上方介紹的是核心＋衛星策略的主要入門流程；以下示範其他 skill 組合，包括進階衛星策略與貢獻者流程。

### 每日市場監控

1. 用 **Economic Calendar Fetcher** 檢查當日重要事件，例如 FOMC、非農就業與 CPI。
2. 用 **Earnings Calendar** 找出當日公布財報的重要公司。
3. 用 **Market News Analyst** 檢視隔夜新聞及其市場影響。
4. 用 **Breadth Chart Analyst** 評估整體市場健康度與位置。

### 每週策略檢視

1. 用 **Sector Analyst** 取得 CSV 並辨識產業輪動，也可提供圖表。
2. 用 **Technical Analyst** 確認主要指數與持股的趨勢。
3. 用 **Market Environment Analysis** 取得完整總經環境摘要。
4. 用 **US Market Bubble Detector** 評估投機過熱與風險程度。

### 個股研究

1. 用 **US Stock Analysis** 進行完整基本面與技術面檢視。
2. 用 **Earnings Calendar** 確認即將公布財報的日期。
3. 用 **Market News Analyst** 檢視公司近期新聞與產業發展。
4. 在計算部位前，用 **Backtest Expert** 驗證進出場策略。

### 策略配置

1. 用 **Stanley Druckenmiller Investment** 辨識總經主題。
2. 用 **Economic Calendar Fetcher** 規劃重要經濟資料公布前後的進場時機。
3. 用 **Breadth Chart Analyst** 與 **Technical Analyst** 進行確認。
4. 用 **US Market Bubble Detector** 協助風險管理與獲利了結規劃。

### 財報動能交易

1. 用 **Earnings Trade Analyzer** 依跳空幅度、趨勢、量能與均線位置評分近期財報反應。
2. 將分析結果交給 **PEAD Screener** 的 Mode B，尋找下跌 K 線回檔後再突破的型態。
3. 用 **Technical Analyst** 確認週線型態、支撐與壓力。
4. 用 PEAD Screener 的 **流動性** 篩選確認部位規模是否可行。
5. 監控 `SIGNAL_READY` 股票的突破進場，先定義停損（下跌 K 線低點）與 2R 目標。

### 收益型投資組合

1. 用 **Value Dividend Screener** 找出股利可持續的優質股票。
2. 用 **Dividend Growth Pullback Screener** 尋找技術進場位置合適的股利成長股。
3. 用 **US Stock Analysis** 深入研究主要候選的基本面。
4. 用 **Earnings Calendar** 追蹤組合持股即將公布的財報。
5. 用 **Market Environment Analysis** 評估股利策略的總經條件。
6. 用 **Backtest Expert** 驗證股利擷取或股利成長策略。

### Kanchi 股利流程（美股）

1. 用 **Kanchi Dividend SOP** 執行五步驟流程，建立包含失效條件的買進計畫。
2. 按每日／每週／每季頻率用 **Kanchi Dividend Review Monitor** 產生 `OK/WARN/REVIEW` 清單。
3. 用 **Kanchi Dividend US Tax Accounting** 檢查合格股利假設與帳戶配置。
4. 加碼前，將 `REVIEW` 發現送回 **Kanchi Dividend SOP**。

### 選擇權策略開發

1. 用 **Options Strategy Advisor** 以 Black–Scholes 定價模擬並比較選擇權策略。
2. 用 **Technical Analyst** 找出合適的進場時機與支撐／壓力。
3. 用 **Earnings Calendar** 規劃財報事件相關策略。
4. 投入資金前，用 **US Stock Analysis** 驗證基本面論點。
5. 檢視 Greeks 與損益情境，選擇備兌買權、價差、跨式等策略。

### 投資組合檢視與再平衡

1. 用 **Portfolio Manager** 透過 Alpaca MCP 取得目前持股並分析組合健康度。
2. 檢視資產配置、產業分散與風險指標，例如 beta、波動率與集中程度。
3. 檢視依論點驗證產生的個別部位標記：HOLD／ADD／TRIM／SELL 候選。
4. 用 **Market Environment Analysis** 與 **US Market Bubble Detector** 評估總經環境。
5. 檢視再平衡計畫，再由人決定是否採取行動。

### 統計套利機會

1. 用 **Pair Trade Screener** 辨識具有共整合關係的股票配對。
2. 分析均值回歸指標，例如半衰期、z-score 與避險比率。
3. 用 **Technical Analyst** 確認兩邊部位的進場型態。
4. 依 z-score 門檻監控進出場訊號。
5. 追蹤價差收斂並管理市場中性部位。

### Skill 品質與自動化

- **Data Quality Checker**（`data-quality-checker`）
  - 在發布前驗證市場分析文件與文章的資料品質。
  - 檢查五類問題：價格尺度不一致（ETF／期貨位數提示）、商品代號格式、日期與星期不符（英文／日文）、配置加總錯誤（限指定區段），以及單位不符。
  - 採建議模式，以警告提示人工檢視；即使有發現，結束碼仍為 0。
  - 支援日文全形符號（％、〜）、區間表示（50-55%），以及未寫年份之日期的年份推定。
  - 不需 API 金鑰，可離線檢查本機 Markdown 檔案。

- **Skill Designer**（`skill-designer`）
  - 根據結構化想法規格，產生用於設計新 skills 的 Claude CLI 提示詞。
  - 提示詞包含儲存庫慣例：結構指南、品質檢查表與 `SKILL.md` 範本。
  - 列出既有 skills 以避免重複；用於每日 skill 自動產生流程。
  - 不需 API 金鑰。

- **Dual-Axis Skill Reviewer**（`dual-axis-skill-reviewer`）
  - 以確定性的自動評分及選用的 LLM 深度審查檢查品質，支援加權混合結果。
  - 自動評分分五類、總分 100：中繼資料與使用情境 20、流程覆蓋 25、執行安全與可重現性 25、配套產物 10、測試健康度 20。
  - 能辨識 `knowledge_only` 類型（沒有程式、僅提供參考資料），調整評分期待，避免不公平扣分。
  - 選用的 LLM 面向評估正確性、風險、缺漏邏輯與可維護性，可設定混合權重。
  - `--all` 可檢查整個儲存庫，`--skip-tests` 用於快速初查，`--project-root` 用於跨專案審查。
  - 不需 API 金鑰。

- **Skill Idea Miner**（`skill-idea-miner`）
  - 從 Claude Code 工作階段紀錄擷取想法，依新穎性、可行性與交易價值評分，維護排序後的待辦清單。
  - 用於每週 skill 自動產生流程，也能手動執行。
  - 不需 API 金鑰。

## 貢獻者自動化

自我改善與 skill 產生流程是維護者工具，不是初學者的交易操作步驟。其行為、副作用、手動指令與 macOS 排程，請見 [Skill 自動化入門](docs/dev/skill-automation.md)（[日文](docs/dev/skill-automation.ja.md)）。

## 自訂與貢獻

- 修改 `SKILL.md` 可調整觸發描述或能力註記；打包時，frontmatter 的名稱須與資料夾一致。
- 可擴充參考文件，或在各 skill 資料夾加入程式以支援新流程。
- 發布更新時，重新產生 `skill-packages/` 內對應的 `.skill`，讓網頁版使用者取得最新版：

```bash
python3 scripts/package_skills.py --skill <skill-name>
```

## API 需求

部分 skills 需要 API 金鑰才能存取資料。

### 需要 API 的 skills

各 skill 對 FMP、FINVIZ Elite 與 Alpaca 的需求，請見由 [skills-index.yaml](skills-index.yaml) 產生的 [API 需求矩陣](docs/en/skill-catalog.md#api-requirements-matrix)。設定憑證前，先讀 [個別 skill 指南](docs/en/skills/index.md)，確認不同模式的先決條件與離線替代方式。

### API 設定

以下方案與額度為英文版記載，請以各服務商最新公告為準；本 fork 的 Yahoo／FinMind 設定請見 [本版安裝與差異](FORK_NOTES.md)。

**Financial Modeling Prep（FMP）API：**

- 免費額度：每日 250 次請求；上游說明認為可滿足多數情境。
- 註冊：<https://financialmodelingprep.com/developer/docs>
- 設定環境變數：`export FMP_API_KEY=your_key_here`
- 或依提示，以命令列參數提供金鑰。

**FINVIZ Elite API：**

- 訂閱費：每月 39.50 美元，或每年 299.50 美元。
- 註冊：<https://elite.finviz.com/>
- 設定環境變數：`export FINVIZ_API_KEY=your_key_here`
- 可用於股利篩選器的快速初篩。

**Alpaca Trading API：**

- 提供免費模擬交易帳號。
- 註冊：<https://alpaca.markets/>
- 需要設定 Alpaca MCP Server。
- 設定環境變數：

```bash
export ALPACA_API_KEY="your_api_key_id"
export ALPACA_SECRET_KEY="your_secret_key"
export ALPACA_PAPER="true"  # 實盤使用 "false"
```

## 支援與延伸閱讀

- Claude Skills 發布介紹：<https://www.anthropic.com/news/skills>
- Claude Code Skills 使用說明：<https://docs.claude.com/en/docs/claude-code/skills>
- Financial Modeling Prep API：<https://financialmodelingprep.com/developer/docs>

有問題或建議，歡迎提出 issue，或在相關 skill 資料夾附上指引，協助後續使用者善用這些交易研究工具。

## 授權

本儲存庫所有 skills 與參考資料均供教育與研究使用。
