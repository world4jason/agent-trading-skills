# 台股事件、新聞與總經研究

先取得研究期間及實際事件來源。公司訊息優先 MOPS 與公司 IR，台灣總經日曆
優先央行、主計總處與經濟部，相關海外事件查其官方發布機構。
全部保留原時區並轉 Asia/Taipei。日期未知則標未確認，不從季度截止日推算財報日期。
FinMind 月營收的資料月份不是公告可得時點，`create_time` 也不是已驗證公開發布時間。

事件反應：以真正公告時間判斷能使用哪個台股收盤/開盤價格，再比較適當窗口。
先定義預期方向、對照和原方法要求的統計條件；不得因事件後上漲就斷言事件造成上漲。
PEAD 需要可驗證的盈餘預期/驚喜；缺少預期僅能研究公告後價格反應。
營收超預期需真實預期來源，不能用自己推估的數字假裝市場共識。

市場新聞按台股實際曝險與證據整理，不固定只看美國。外匯與全球因素只作相關
台股風險背景，不啟動外匯/期貨交易。宏觀原模型缺台灣成分時不可偷換指標維持同分數。
情境分析分開事實、推論、假設與反證，無校準不給偽精確概率。

價量從共享 CLI 取得；交易日用 `dataset --name TaiwanStockTradingDate`，此指令不帶
`--symbol`。歷史日曆資料未來範圍空白不代表當天休市，未來時段查正式交易所行事曆。

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
