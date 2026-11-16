# Codex Taiwan runtime

Resolve installed skill symlinks to find this repository root. Use the repository
`.venv/bin/python`; dependencies are in `pyproject.toml`. Commands in the documents
are relative to the repository root. Reports and user input paths can be absolute.

Scope: TWSE/TPEX-listed stocks and ETFs, including Taiwan-listed offshore-exposure
ETFs. No futures/options contracts, brokerage orders, US tax workflows or MT5.

Read [Taiwan market conventions](TAIWAN_MARKET.md). Actual automatic screener
entrypoints and their supported checks are documented in [TAIWAN_ENGINES.md](TAIWAN_ENGINES.md).
Use `scripts/taiwan_screen.py` or the mapped legacy entrypoints. Other upstream US
scripts are retained for reference and are not Taiwan executors. Do not run US
market-regime jobs, FMP pipelines or brokerage integrations merely because a file exists.

FinMind is primary; Yahoo supplements daily prices after a verified FinMind miss.
Set `FINMIND_TOKEN` in the environment if required. Never put secrets in arguments,
reports or commits. Missing financial fields cannot be inferred from Yahoo prices.
All-market runs may exceed a provider quota: preserve the incomplete coverage report.

Use Asia/Taipei dates, TWD and string tickers. Do not splice different adjustment
bases. Screen results are research candidates, not orders or verified profitable
strategies. FinMind period dates are not public release timestamps; historical
fundamental screens are not point-in-time backtests. Respond in the user's language.
