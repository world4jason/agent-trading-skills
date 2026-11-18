# agent-trading-skills repository guide

The Taiwan skills cover TWSE/TPEX stocks and ETFs. For Taiwan and US full-market scans, use `scripts/market_scan.py` and read `CROSS_MARKET_SCAN.md`. Use the
relevant standard `skills/<skill-name>/SKILL.md` from an agent's own skills
directory. The default Codex installation is documented in [README.md](README.md);
this repository does not claim client-specific testing for other agents.

Follow [Taiwan market conventions](TAIWAN_MARKET.md) for provider selection,
calendar, units, and source coverage, and [engine scope](TAIWAN_ENGINES.md) for
current screener behavior. For daily prices, `auto` tries Yahoo before FinMind;
an explicit provider is tried first and fallback uses the other provider for
the whole requested range. FinMind supplies Taiwan catalogue, calendar, and raw
financial-data capabilities; Yahoo's fundamental snapshot fills available gaps.

Keep outputs within the user-requested markets; use market-specific directories, currencies and calendars. Preserve source,
dates, units, adjustment basis, and missing-data notes. Treat screening results
as research candidates, not orders or proof of profitability, and keep tokens
out of prompts, reports, and commits.

The original upstream Claude Code repository guide is preserved at
[`references/upstream-CLAUDE.md`](references/upstream-CLAUDE.md).
