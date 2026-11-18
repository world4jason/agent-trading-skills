# Taiwan runtime for Codex

The default Codex installation uses the repository `.venv/bin/python` and
`scripts/install_taiwan.py`; setup details are in [README.md](README.md).
Other agents can load the standard `SKILL.md` files through their own skills
directories. This repository does not claim client-specific testing for them.

Scope: TWSE/TPEX-listed stocks and ETFs, including Taiwan-listed offshore-exposure
ETFs. No futures/options contracts, brokerage orders, US tax workflows or MT5.

Read [Taiwan market conventions](TAIWAN_MARKET.md). Actual automatic screener
entrypoints and supported checks are documented in [TAIWAN_ENGINES.md](TAIWAN_ENGINES.md).
Use `scripts/taiwan_screen.py` or the mapped legacy entrypoints. Other upstream US
scripts are retained for reference and are not Taiwan executors. Do not run US
market-regime jobs, FMP pipelines or brokerage integrations merely because a file exists.

Screen and price commands accept `--provider auto|yahoo|finmind`. `auto` tries
Yahoo daily prices first, then FinMind. An explicitly selected provider is tried
first; if it cannot cover the requested date range, retry the complete range
with the other provider. Do not splice price ranges from different providers.
FinMind provides Taiwan catalogue, calendar, and raw financial-data capabilities.
Yahoo's full fundamental snapshot can fill available gaps; report fields that
remain unavailable. Set `FINMIND_TOKEN` only when the selected FinMind dataset
requires it. Never put secrets in arguments, reports or commits. All-market runs
may exceed provider limits: preserve incomplete coverage in the report.

Use Asia/Taipei dates, TWD and string tickers. Do not splice different adjustment
bases. Screen results are research candidates, not orders or verified profitable
strategies. FinMind period dates are not public release timestamps; historical
fundamental screens are not point-in-time backtests. Respond in the user's language.
