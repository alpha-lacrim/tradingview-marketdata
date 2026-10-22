# Native instrument expansion - 22 October 2026

## TradingView: 100 source feeds

The native collector now defaults to `config/instruments.tradingview-native100.json`.
Existing 34/99/accuracy-selected registries and stored history are unchanged. Passing
`--registry config/instruments.tradingview-pilot.json` still selects only 34 feeds.
The new list has 50 Binance spot USDT pairs, 21 OANDA forex pairs, the same 21 FXCM
pairs, five precious-metal feeds, and three energy CFDs from OANDA. These are 100
independent feeds, not 100 distinct underlying assets. FXCM uses TradingView's `FX:`
namespace. Never merge broker histories or treat CFD prices as exchange futures.

The owner selected highest trading volume, not market capitalization. Crypto is
ranked by TradingView `24h_vol|5` (reported rolling USD turnover), excluding null or
nonpositive values and sorting exact symbols to break ties. Stablecoin and tokenized
asset spot pairs remain eligible under this existing definition. This is not direct
Binance exchange turnover verification or a claim of underlying product equivalence.
Ranking capture: 2026-10-22T18:04:39.117700+00:00. 516 listed spot USDT pairs were returned.
The selection is frozen until explicitly refreshed; daily turnover rankings change.

Rebuild from private captured scanner responses without network or running changes:

```powershell
uv run python scripts/prepare_native_universe.py --ranking .local/expansion-20261022/ranking.json --directory .local/expansion-20261022/directory.json
```

Both inputs are private evidence, not required for normal installation. Review and
probe a replacement list before switching; never silently rotate a running universe.

## Volume and source validation

OANDA metal/energy feeds were preferred over TVC reference prices because the existing
qualification identifies OANDA volume as tick counts. These are NOT centralized
traded contract/physical-metal volumes. FXCM gold numeric-volume units remain unknown
unless the source metadata verifies them. Binance spot volume is source-reported;
volume never becomes monetary value in the dashboard's `h` field.
[TradingView's volume explanation](https://www.tradingview.com/support/solutions/43000481397-the-volume-indicator-on-my-chart-looks-odd-or-displays-zero-or-n-a-values/)
distinguishes missing trade volume and tick volume. True exchange futures turnover
requires concrete contracts, correct roll handling and available entitlements; no
continuous futures alias was added or represented as spot.

Read-only checks with unchanged provider identity/status gates accepted native 1m
bars from all 100 feeds (2853 bars, 3..29 per feed in the bounded request)
and accepted latest quote observations from all 100. No live data was uploaded or
written into the company DB. Some target minutes were absent; none were synthesized.
Five selected commodity symbols were absent from the current global scanner response
but remained available through the native chart transport with verified identities.
Scanner presence is not a prerequisite for proven native availability, nor sufficient
proof of it. Private reports are under `.local/expansion-20261022/`.
This short check does not guarantee sustained availability, complete history or
permission beyond the existing access gates. The guest protocol remains experimental.

## TSETMC: broad primary-share discovery

The companion native collector discovers primary ordinary-share IDs from the official
`ClosingPrice/GetMarketWatch` response at startup, then verifies each metadata response
and uses the existing per-instrument history/current endpoints. The capture held 3,462
rows across many products; 745 primary-share candidates matched the explicit selection.
Rights, options, funds and secondary lines are excluded rather than misclassified.
The bulk response has zero date/price placeholders, so it is used only for discovery.
Four sampled share families passed metadata, full-history and current parsing; this
is not proof that every candidate has usable complete history. Details live in the
companion `docs/instrument-expansion.md`.

Requests remain paced: hundreds of shares take minutes per latest sweep, especially
during initial metadata/history work. Default full-history refresh is once daily per
instrument. Use repeated `--ins-code` for a faster small watchlist. Keep retry files and
history checkpoints. Stored data remains served during collector outages. No DB reset
or schema migration is required. Restart services to load new code/configuration.

The dashboard can page `/api/instruments?market=tsetmc&limit=1000&offset=0` and read
`display_name`; exact source symbols remain the stable chart/latest keys. No chart
contract changes. Initial broad backfill can take substantial time and disk space;
monitor delivered counts and failed instruments instead of expecting instant coverage.

## Selected TradingView feeds

| Source | Asset class | Product type |
|---|---|---|
| BINANCE:USDCUSDT | crypto | spot |
| BINANCE:BTCUSDT | crypto | spot |
| BINANCE:ETHUSDT | crypto | spot |
| BINANCE:ZECUSDT | crypto | spot |
| BINANCE:SOLUSDT | crypto | spot |
| BINANCE:USD1USDT | crypto | spot |
| BINANCE:XRPUSDT | crypto | spot |
| BINANCE:NEARUSDT | crypto | spot |
| BINANCE:AIUSDT | crypto | spot |
| BINANCE:BNBUSDT | crypto | spot |
| BINANCE:XAUTUSDT | crypto | spot |
| BINANCE:RLUSDUSDT | crypto | spot |
| BINANCE:WLDUSDT | crypto | spot |
| BINANCE:SNDKBUSDT | crypto | spot |
| BINANCE:UNIUSDT | crypto | spot |
| BINANCE:DOGEUSDT | crypto | spot |
| BINANCE:ENAUSDT | crypto | spot |
| BINANCE:SOXLBUSDT | crypto | spot |
| BINANCE:SUIUSDT | crypto | spot |
| BINANCE:SPCXBUSDT | crypto | spot |
| BINANCE:HYPEUSDT | crypto | spot |
| BINANCE:PEPEUSDT | crypto | spot |
| BINANCE:UUSDT | crypto | spot |
| BINANCE:TRXUSDT | crypto | spot |
| BINANCE:ALTUSDT | crypto | spot |
| BINANCE:PUMPUSDT | crypto | spot |
| BINANCE:TAOUSDT | crypto | spot |
| BINANCE:AVAXUSDT | crypto | spot |
| BINANCE:CRCLBUSDT | crypto | spot |
| BINANCE:FDUSDUSDT | crypto | spot |
| BINANCE:QNTUSDT | crypto | spot |
| BINANCE:ADAUSDT | crypto | spot |
| BINANCE:AAVEUSDT | crypto | spot |
| BINANCE:LINKUSDT | crypto | spot |
| BINANCE:LTCUSDT | crypto | spot |
| BINANCE:PAXGUSDT | crypto | spot |
| BINANCE:INJUSDT | crypto | spot |
| BINANCE:STRKUSDT | crypto | spot |
| BINANCE:IOSTUSDT | crypto | spot |
| BINANCE:FILUSDT | crypto | spot |
| BINANCE:ARBUSDT | crypto | spot |
| BINANCE:HBARUSDT | crypto | spot |
| BINANCE:TSLABUSDT | crypto | spot |
| BINANCE:BMTUSDT | crypto | spot |
| BINANCE:MSTRBUSDT | crypto | spot |
| BINANCE:RUNEUSDT | crypto | spot |
| BINANCE:XUSDUSDT | crypto | spot |
| BINANCE:ONDOUSDT | crypto | spot |
| BINANCE:TIAUSDT | crypto | spot |
| BINANCE:FETUSDT | crypto | spot |
| OANDA:EURUSD | forex | otc |
| OANDA:GBPUSD | forex | otc |
| OANDA:USDJPY | forex | otc |
| OANDA:USDCHF | forex | otc |
| OANDA:AUDUSD | forex | otc |
| OANDA:USDCAD | forex | otc |
| OANDA:NZDUSD | forex | otc |
| OANDA:EURGBP | forex | otc |
| OANDA:EURJPY | forex | otc |
| OANDA:EURCHF | forex | otc |
| OANDA:EURAUD | forex | otc |
| OANDA:EURCAD | forex | otc |
| OANDA:EURNZD | forex | otc |
| OANDA:GBPJPY | forex | otc |
| OANDA:GBPCHF | forex | otc |
| OANDA:GBPAUD | forex | otc |
| OANDA:GBPCAD | forex | otc |
| OANDA:GBPNZD | forex | otc |
| OANDA:AUDJPY | forex | otc |
| OANDA:CADJPY | forex | otc |
| OANDA:CHFJPY | forex | otc |
| FX:EURUSD | forex | otc |
| FX:GBPUSD | forex | otc |
| FX:USDJPY | forex | otc |
| FX:USDCHF | forex | otc |
| FX:AUDUSD | forex | otc |
| FX:USDCAD | forex | otc |
| FX:NZDUSD | forex | otc |
| FX:EURGBP | forex | otc |
| FX:EURJPY | forex | otc |
| FX:EURCHF | forex | otc |
| FX:EURAUD | forex | otc |
| FX:EURCAD | forex | otc |
| FX:EURNZD | forex | otc |
| FX:GBPJPY | forex | otc |
| FX:GBPCHF | forex | otc |
| FX:GBPAUD | forex | otc |
| FX:GBPCAD | forex | otc |
| FX:GBPNZD | forex | otc |
| FX:AUDJPY | forex | otc |
| FX:CADJPY | forex | otc |
| FX:CHFJPY | forex | otc |
| OANDA:XAUUSD | metals | otc |
| OANDA:XAGUSD | metals | otc |
| OANDA:XPTUSD | metals | otc |
| OANDA:XPDUSD | metals | otc |
| FX:XAUUSD | metals | otc |
| OANDA:WTICOUSD | energy | cfd |
| OANDA:BCOUSD | energy | cfd |
| OANDA:NATGASUSD | energy | cfd |
