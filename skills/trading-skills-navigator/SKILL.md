---
name: trading-skills-navigator
description: 依中文或英文問題，導覽台灣上市、上櫃股票與 ETF 的研究 skills、資料需求及流程。用於不知道該用哪個 skill、想找台股選股/持股/股利/技術/倉位或免付費資料路徑的請求。只推薦與解釋，不執行交易；期貨、選擇權等範圍外問題明確回報。
---

# 台股研究流程導覽

先讀 [台股執行環境](../../CODEX_RUNTIME.md)。
將使用者原問題交給本版推薦器：

```bash
rtk proxy .venv/bin/python skills/trading-skills-navigator/scripts/recommend.py --query "分析0050與00878 ETF" --format json
```

從 bundle 根目錄執行，或使用腳本絕對路徑。程式預設讀自身 bundle 的台股索引，
不依賴目前工作目錄，也不回退到舊美股快照。

- 依 `routing_diagnostics.status` 解釋結果：`out_of_scope` 不改推薦別的市場；
  `needs_goal` 請使用者描述研究問題；`ambiguous` 說明候選而非假裝精確匹配。
- `suggested_skills` 是本題候選；`related_workflows` 只是背景流程，不能因此自動擴大工作。
  只有明確指定 workflow ID 時 `primary_workflow` 才列完整步驟。
- `--no-api` 沿用「不使用付費資料」的意思，不保證每項資料免費或可得；
  真正離線要求使用者已提供資料，不能暗中呼叫網路。
- `--time-budget` 和 `--experience` 只保存對話偏好，不能據此宣稱任務可在某時間完成。
- skills 已安裝；資料源的 token、額度、資料日期與可得性仍需執行時驗證。
- 回覆使用者語言，列出推薦原因、必要輸入與尚待確認項目；若使用者要求開始分析，
  讀對應 SKILL.md 再執行，導覽器本身不執行研究或下單。
