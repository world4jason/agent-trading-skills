# Codex 台股選股與研究 skills

本專案是 [tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills)
的台股改版：上市、上櫃股票與 ETF，FinMind 為主，Yahoo Finance 補充日線。
保留 MIT 授權與上游計算方法，支援 Codex 的 67 個研究 skills。

## 安裝

在專案根目錄建立 Python 環境並安裝：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python scripts/install_taiwan.py
```

安裝器把 skills 連結到這份 checkout，備份原連結，保留其他 skills；不覆蓋非連結資料夾。
因此安裝後請保留 checkout 與 Python 環境。開新 Codex 對話即可使用。
FinMind 需要憑證時，在環境設定 `FINMIND_TOKEN`，不要貼在對話或寫入 repo。

## 自動選股

```bash
.venv/bin/python scripts/taiwan_screen.py --strategy vcp momentum-burst exhaustion-hammer parabolic --symbols 2330 6488 0050 --start 2023-01-01 --end 2024-12-31 --output /tmp/taiwan-screen.json
```

上述日期是歷史操作範例。全市場使用 `--all` 取代 `--symbols ...`；
`--exchange twse|tpex`、`--kind stock|etf` 可縮小範圍。報告列出來源、日期、
實際處理數與缺資料原因，不把缺值當作通過，也不把部分股票稱為全市場。
舊選股檔名仍可執行，已轉接同一台股 CLI，參數改用上列介面。

- [各引擎的確切條件、限制與事件格式](TAIWAN_ENGINES.md)
- [Codex 執行環境](CODEX_RUNTIME.md)
- [台股市場與資料口徑](TAIWAN_MARKET.md)
- `scripts/taiwan_data.py`：資料取得；`scripts/taiwan_position.py`：台幣倉位計算。
- `$trading-skills-navigator`：從中文研究問題找到合適 skill。

ETF 可跑技術選股；公司 EPS、估值及財報事件條件不套用 ETF。
FinMind 額度與資料方案可能限制全市場掃描，Yahoo 無法補齊所有基本面。
這是研究工具，沒有下單、期貨／選擇權交易或獲利保證。

來源版本 `fdfff010e1efe181ebe9c11a0109ef5f8b736147`。
[上游文件](UPSTREAM_README.md) 僅供追溯；其他舊美股自動化不是台股執行入口。
