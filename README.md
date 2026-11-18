# agent-trading-skills

Trading skills for Codex, Claude, OpenCode, and other AI agents.

本專案是 [tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills)
的 agent 研究版；台股工具涵蓋 TWSE/TPEX 股票與 ETF，全市場掃描另支援美國交易所股票／ETF。保留 MIT 授權與上游研究方法；
[上游 README](UPSTREAM_README.md) 留存供追溯。
目標版本：[world4jason/agent-trading-skills，`codex/taiwan-market`](https://github.com/world4jason/agent-trading-skills/tree/codex/taiwan-market)。

## Codex 預設安裝

在專案根目錄建立 Python 環境並安裝：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python scripts/install_taiwan.py
```

這是預設的 Codex 安裝方式。安裝器把 skills 連結到這份 checkout、備份原連結、保留其他
skills，且不覆蓋非連結資料夾。安裝後請保留 checkout 與 `.venv`。只有所選 FinMind
資料集需要憑證時，才在環境設定 `FINMIND_TOKEN`；不要把憑證貼在對話或寫入 repo。

其他 agent 可將 `skills/<skill-name>/SKILL.md` 標準 skill 檔案放入各自的 skills 目錄；
本 repo 不宣稱已針對其他 agent client 完成測試。

## 選股與價格來源

screen 與 prices 指令接受 `--provider auto|yahoo|finmind`。`auto` 先嘗試 Yahoo 日線，再
嘗試 FinMind。明確指定 provider 時先嘗試該來源；若無法涵蓋所需日期範圍，就改用另一個
provider 取得整段範圍，不拼接不同來源的部分日線。FinMind 可提供台灣股票目錄、交易日曆
與原始財務資料；Yahoo 完整基本面快照可補上目前可取得的欄位，仍缺少的欄位須明確標示。

```bash
.venv/bin/python scripts/taiwan_screen.py --strategy vcp momentum-burst exhaustion-hammer parabolic --symbols 2330 6488 0050 --start 2023-01-01 --end 2024-12-31 --provider auto --output /tmp/taiwan-screen.json
```

上述日期是歷史操作範例。全市場使用 `--all` 取代 `--symbols ...`；`--exchange twse|tpex`、
`--kind stock|etf` 可縮小範圍。報告列出來源、日期、實際處理標的與缺資料原因；部分結果
不代表全市場結果。

- [台股／美股全市場掃描與完整報告](CROSS_MARKET_SCAN.md)
- [各引擎的確切範圍、檢查與限制](TAIWAN_ENGINES.md)
- [Codex 執行環境與預設安裝](CODEX_RUNTIME.md)
- [台股市場與資料口徑](TAIWAN_MARKET.md)
- [Wealthfolio 資料來源分析](WEALTHFOLIO_DATA_SOURCES.md)
- `scripts/taiwan_data.py`：資料取得；`scripts/taiwan_position.py`：台幣倉位計算。
- `$trading-skills-navigator`：從中文研究問題找到合適 skill。

ETF 可使用技術選股；公司 EPS、估值及財報事件條件不套用 ETF。這是研究工具，不會下單，
也不保證獲利。

上游來源版本 `fdfff010e1efe181ebe9c11a0109ef5f8b736147`。
