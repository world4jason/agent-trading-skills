# Taiwan stock and ETF conventions

## Identity and universe

Resolve stock IDs as strings against a Taiwan stock/ETF catalogue; FinMind
TaiwanStockInfo can provide this catalogue. Yahoo symbols use verified venue
suffixes `.TW` (TWSE) or `.TWO` (TPEX); preserve IDs such as
`0050`, `00679B`, and active-ETF codes. Do not infer venue from digits or query
a US ticker when Taiwan resolution fails. Exclude emerging-board instruments,
warrants, ETNs and non-stock/non-ETF securities from this edition's universe.
Delisted symbols and survivorship bias require an explicit historical universe;
a current list is not a historical constituent database.

## Price, quantity and calendars

Values are TWD per share/unit; normalized volume is shares/units, not lots.
Ordinary domestic stocks and ETFs generally use 1,000 shares/units per board
lot; odd lots use integer shares/units. Confirm instrument-specific exceptions,
including offshore ETFs; pass their verified unit with `--lot-size` instead of
the default 1000. Never permit US-style fractional shares.

Stock tick sizes: below 10: .01; [10,50): .05; [50,100): .10;
[100,500): .50; [500,1000): 1; 1000 and above: 5 TWD.
ETF ticks: below 50: .01; 50 and above: .05 TWD.
The sizing CLI validates prices without silently rounding the user's levels.
Ordinary sessions generally run 09:00–13:30 Asia/Taipei, with special handling
for odd lots and delayed auctions. Use FinMind or official Taiwan trading dates,
not a US NYSE calendar or a simple weekday check. Historical observed price
dates do not guarantee that an absent symbol traded or that a future date is open.

Screen and price commands accept `--provider auto|yahoo|finmind`. `auto` tries
Yahoo daily prices first, then FinMind. An explicitly selected provider is tried
first; if it cannot cover the requested date range, retry the entire range with
the other provider. Never splice partial price ranges from different providers.
FinMind provides Taiwan catalogue, calendar, and raw financial-data capabilities;
Yahoo's full fundamental snapshot fills available gaps. Field availability and
semantics vary, so report unavailable fields instead of inferring values.

Daily price limits are instrument-specific. Do not apply a blanket 10% rule
to every ETF, leveraged fund, IPO or special instrument. Use the published
reference price and current exchange rules. Limit-down conditions, suspension,
and price gaps can prevent a stop execution; stop-distance risk is an estimate.

Source checked 2026-11-16:
https://www.twse.com.tw/zh/products/system/trading.html
For TPEX-specific instruments check the current TPEX trading rules as well:
https://www.tpex.org.tw/zh-tw/mainboard/trading/rules/system.html

## Financial and ETF interpretation

Financial statements are issuer reports with fiscal periods, publication dates
and units. Do not treat a reporting-period end as a release timestamp or use
later restatements in a historical signal. Inspect row `type` and `origin_name`
before mapping FinMind values to ratios. Month revenue is a distinct series,
not quarterly EPS. Report unavailable consensus estimates as unavailable.
Do not reinterpret a Taiwan EPS surprise as US earnings-calendar data.

ETFs do not have operating-company EPS, enterprise value, company revenue or
CANSLIM earnings scores. Evaluate exposures, holdings, NAV/premium-discount,
tracking, liquidity and distributions only when the corresponding data exists.
Distribution yield is not total return. Issuer disclosures are needed for
holdings, NAV, distribution composition and leveraged/inverse product terms.
Taiwan institutional buy/sell data is trading flow, not US 13F ownership.

FinMind dataset and access documentation:
https://finmind.github.io/tutor/TaiwanMarket/Technical/
https://finmind.github.io/tutor/TaiwanMarket/Fundamental/
https://finmind.github.io/tutor/TaiwanMarket/Chip/
Yahoo client semantics:
https://ranaroussi.github.io/yfinance/reference/api/yfinance.PriceHistory.history.html

## Costs and execution planning

Require the user's/broker's fee rate, per-side minimum commission and applicable
sell-tax rate for cost-inclusive sizing. The CLI accepts decimal rates, not
percent numbers, and rounds costs upward to whole TWD conservatively. Verify
stock/ETF/bond-ETF/day-trade treatment and effective dates before suggesting a
rate; no universal tax rate is hardcoded. It assumes one buy and one sell fill,
excludes slippage and may understate costs for multiple fills. It checks cash
and estimated stop-loss budgets but does not submit orders, guarantee fills,
model margin, or perform tax advice.

## Coverage and provenance

Save source, retrieval time, as-of date, requested/evaluated symbols, unavailable
inputs, units and adjustment basis with every output. Do not forward-fill
suspended/no-trade bars or manufacture zero volume. Keep raw trading-price
analysis separate from adjusted-price or total-return analysis. For breadth,
state universe and denominator, minimum history, missing observations and
whether ETFs were excluded or reported separately from operating companies.
Use actual benchmark data and declare the benchmark; never relabel SPY as TAIEX.
