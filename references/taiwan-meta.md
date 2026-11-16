# 台股 skill 維護、品質與流程驗證

以本 bundle 的 CODEX_RUNTIME.md、TAIWAN_MARKET.md、skills-index.yaml 與
workflows/*.yaml 為操作依據。upstream 文件、原本 .skill 壓縮包和舊美股自動化指令
保留供追溯，不能當作本版台股能力或測試證明。

檢查每個 workflow 需要的 skill 是否已安裝、輸出資料是否存在、日期/代碼/單位/來源是否相容，
缺資料就停止該相依步驟並說明，不捏造成功產物。資料查核分開完整性、正確性與新鮮度。
不需重寫使用者資料或改動原有規則來使檢查通過。

新增或更新 skill 使用本機
`/Users/world4jason/.codex/skills/.system/skill-creator/SKILL.md`，
完成後跑其 `scripts/quick_validate.py`，並測試真正指令和可觀察輸出。
獨立審查時區分程式格式、資料連線、方法論適用性和真實績效驗證，不混稱全部通過。

skill-idea-miner 僅分析使用者指定對話/匯出，從重複需求、失敗及工具使用證據提出候選；
保留來源，以新穎性/可行性/交易研究價值評估，沒有證據不猜頻率。
不跑原版 Claude 日誌 parser、不開背景排程、不讀取無關私人聊天。

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
