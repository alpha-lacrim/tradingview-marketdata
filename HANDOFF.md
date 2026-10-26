# Current state - native installation, 2026-10-22

One FastAPI/company PostgreSQL, two direct HTTP collectors, durable retry files.
No Docker or source database required. Open API/CORS and optional upload token are
owner-authorized. Use docs/native-install.md and docs/native-dashboard.md.
Frozen distributions, old databases, and legacy pipelines remain untouched. Native
schema v1 refuses legacy initialization; existing native users need no migration.
Keep LOCAL_WORKSPACE.md and docs/workspace.md recovery guidance; never push the
private local archive branch or prune the shared Git store.

## Current coverage and expansion

The owner approved expansion and Binance ranking by highest trading volume.
Native TradingView default is config/instruments.tradingview-native100.json:
50 Binance spot USDT pairs ranked by captured TradingView 24h_vol|5 USD turnover,
42 forex feeds (21 pairs from both OANDA and FXCM), five metals and three OANDA
energy CFDs. FXCM provider namespace is FX:. Tick/unknown volume is not exchange
traded volume. Read docs/native-instruments.md for selection, all symbols and limits.
Existing pilot34/business99/accuracy100 configurations are unchanged. An explicit
--registry pilot argument still restricts the collector to 34 sources.

Read-only bounded native probes accepted bars and quotes for all 100 selected feeds.
Some minute slots were absent; no bars were synthesized. Five commodities absent
from the global scanner still passed native chart identity/status checks. Ranking
is a frozen snapshot, not automatic rotation. Raw ranking/directory/probe outputs
are ignored under .local/expansion-20261022/. scripts/prepare_native_universe.py
rebuilds the list from private snapshots. Previous identity UUIDs are preserved.

Companion TSETMC now defaults to a fixed packaged top100 share watchlist, selected
by reported traded value from a dated market-watch snapshot. Startup does not depend
on market watch. --all-shares explicitly selects the older broad discovery mode.
Remove that flag from laptop commands. See source docs/top100.md for the named list
and live checks. Source identity validation, durable retries and daily full-history
completion checkpoints remain. A100-share latest sweep takes at least100 seconds
with one request start/second pacing, longer during metadata/history work or failures.
No company schema/API change was required for this default-watchlist correction.

/api/instruments now accepts market, limit (1..5000, default1000), offset and adds
latest quote metadata display_name (otherwise symbol). Paging prevents silent loss
beyond 1000 instruments. Source ID is still the chart/latest key. Chart a..h/i:null
and exact Decimal storage, correction history and receipt contracts are unchanged.

## Recovery and integrity retained

TradingView reconnects on ConnectionClosed/InvalidMessage/InvalidStatus and network
timeouts with 60..300s backoff; reduced request concurrency survives reconnect.
Permanent access errors stop. Uploads in both collectors preserve exact bytes until
a matching receipt, retry transient errors with 30..300s backoff and honor longer
Retry-After. Permanent failures/malformed receipts retain files and fail visibly.
API operations have 20s budgets and 5s pool acquisition; transient DB failures return
503/Retry-After30, WebSockets close1013. Access logs are off unless --access-log.

TSETMC validation rejects bad identity types/nested conflicts, empty measurements,
negative prices, inconsistent closes and clocks >5min ahead of receipt. Stale quotes,
zero activity and official close outside trade high/low remain valid. Earlier
qualification: source docs/validation-review-2026-10-22.md. Do not erase pending
files. After intentional company DB replacement use a new archived/separate collector
state directory: a same-URL database reset cannot invalidate source checkpoints.

## Verification and next operation

Company full suite with disposable native PostgreSQL: 565 passed / 365 skipped.
Source suite: 306 passed / 119 skipped. Ruff/format/mypy and both builds passed.
Tests cover >1000 directory paging/names, source isolation, malformed-instrument
continuation, exact receipts and acknowledged history resume after restart.
Legacy PG/live tests are opt-in; no old DB writes, no employer deployment or live
company uploads were performed. Short source probes are not sustained qualification.

Refresh ZIPs from committed heads, including the new native100 config and both
coverage guides. Restart API and collectors with the same state directories to load
changes. Ubuntu units use defaults automatically; laptop pilot commands must change
registry. Do not reset the native DB. Monitor source failures, freshness, pending
uploads and DB disk while broad history fills. Quote snapshots are not a tick archive;
TradingView recovery is limited to available history (up to4999 minutes requested).

## Reliability follow-up (2026-10-25)

Undated incoming quotes no longer replace dated stored quotes. New /api/coverage
reports unobserved native slots without inferring sessions; chart adds exposed
partial-bucket and unverified-coverage headers, preserving its JSON body.
TradingView recovery now defaults to 4999 minutes; backfill beyond available
provider history is not solved. Owner accepts paced TSETMC latest observations rather than instantaneous
provider snapshots. Companion collector now retries empty history next sweep
instead of checkpointing it for a day. No schema migration required.

Verification: company full suite 567 passed, 365 skipped (opt-in legacy/live
paths); native API/store suite 38 passed against disposable PostgreSQL 16.1 on
port 56052, including quote ordering and coverage response tests. Ruff and mypy
passed. Graph rebuilt (SQL extraction unavailable: missing optional parser).
This does not qualify employer deployment or prove uninterrupted live feeds.

## Extended native history (2026-10-25)

The old 1440-minute cap was local, not a measured upstream boundary. Native CLI
now defaults to 4999 minutes and requests at most 5000 bars (one may be forming).
Legacy Settings default stays 300; its validated maximum is now 4999. Quote frame
limits stay 256 KiB; candle WebSocket/decoder buffers are bounded at 2 MiB.
Native requests allow 30 seconds and process ten sources per batch, retaining the
existing two-request concurrency, identity/status checks and receipt handling.
API coverage reports the updated maximum, not the active collector configuration.

Evidence: an initial larger BTC request failed with local close1009 (frame exceeded
262144 bytes), explaining the earlier apparently upstream disconnect. After fixing
both transport and decoder bounds, BTC yielded 4999 completed bars, from
2026-10-22T03:57Z through 2026-10-25T15:15Z using a 30s budget. A 15s trial timed out.
OANDA/FX EURUSD each supplied >2400 bars including data older than one day; weekend
closure accounts for a shorter observed window. These bounded probes do not prove
continuous access or all100 expanded-history completeness. Raw outputs/scripts are
ignored in .local; no live company uploads or production DB changes were made.

Restart tradingview-simple without an explicit smaller --history-minutes to enable
it. Stored history is retained indefinitely by this native path. No migration.
Pending API uploads still pause acquisition, so outages beyond available source
history can still leave gaps. Coverage exposes absence without manufacturing bars.

Verification for extended history: full deterministic suite 562 passed / 372
skipped; separate native PostgreSQL suite 39 passed on disposable port56052.
Ruff and mypy passed. Large-frame acceptance/rejection, 4999-minute bounds and
23-source grouping (10/10/3) have regression tests. Graph rebuilt; optional SQL
parser is still absent. No changes were needed in the TSETMC repository.

## Native higher timeframes (2026-10-26)

Native collector now defaults to 1m/5m/15m/1d, separately persisted by interval.
--intervals selects a subset; --history-bars (old --history-minutes alias) is
30..4999 bars per interval. One chart connection at a time, sequential interval
sweeps; quote connection independent. Full refresh hourly, overlap30 bars.
Large first sweeps may delay minute history updates; quote delivery is independent.
No schema change; API must restart before collector to accept new intervals.

Chart source=auto prefers native rows for the requested range, falling back to
minute aggregation only if none exist. No mixed source within one response.
source=native and source=aggregate are explicit overrides; X-Bar-Source exposed.
1h remains aggregated. Native daily source timestamps preserved (FX observed21Z),
not rounded to UTC midnight. Conservative daily filter excludes last provider bar
and requires start+24h <= cutoff; exact session finality remains unverified.
/api/coverage still measures only native minute TradingView rows.

Live small read-only probes accepted 5m/15m/1d for BTC, OANDA EURUSD, FX EURUSD.
No HTML scraping: direct guest chart/quote WebSocket messages, as documented in
docs/tradingview.md. Guest protocol remains experimental; no account access bypass.
TSETMC diagnostic capture is implemented in companion repo; native history now
uploads valid rows from partial snapshots with explicit validation metadata.

Verification: company full suite575 passed365 skipped against disposable native
PostgreSQL; after final scheduler/parameterized checks, targeted suite132 passed10
skipped. Ruff/mypy/format passed. Source suite318 passed119 skipped. Live interval
probes were read-only and bounded, not all100 long-duration qualification.


## Companion partial-history update

TSETMC native collector no longer rejects thousands of valid dates because a few
rows are invalid. Existing parser rules and conflict-date quarantine retained;
valid uploads carry metadata.history_validation counts/status, raw flags remain in
rotating source diagnostics. No company API/schema changes needed. Chart remains
unchanged; /api/records exposes partial status. Restart source collector with its
existing state directory. Previously failed histories are retried; acknowledged
snapshots refresh on their ordinary daily schedule. No user DB writes performed
by this change; bounded live source proof checked against company upload contract.


## Company bulk history investigation

Remote API at212.33.202.29 is now updated (native intervals and source parameter).
Both active laptop collectors targeted the company URL correctly; pending history
was valid500-row batches. Stored history existed for8 instruments per market at
snapshot, quotes for100 each. Some TSETMC partial uploads contained only old dates,
so last30days charts were empty despite records existing. No evidence of incorrect
DB wiring; query/storage and matching upload receipts were verified remotely.

Measured genuine pending batch replay: TSETMC500rows28.73s (~551KB), TradingView
500rows19.72s (~381KB); old30s timeout had little margin. Smaller100row batch
3.41s (~106KB), matching receipt. Added history_batches helper mirrored in both
repos: newest100 first, ascending within each, every row once. HTTP timeout60s in
both collectors. Pending bytes/receipts remain unchanged. Root cause of path
slowness cannot be assigned to network/server without employer telemetry.
User must stop/restart both laptop collectors using their company state dirs.
No server/API migration required. Full company suite575passed375skipped; source
329passed119skipped, lint/mypy passed. Tests verify batch bounds/order/no row loss.
Server history fill across all100 feeds remains unqualified and may take hours.


Recent-first startup: in normal continuous operation TradingView first requests
up to30 recent bars per instrument/timeframe across the universe, then does deep
recovery. This preview does not set full-refresh markers. TSETMC uploads the
newest100 valid daily rows per unfinished instrument before starting its deep
backfill; preview uploads never set history-completed.json. Their records carry
history_delivery.scope=recent_preview and full_upload_pending=true. The next full
snapshot replaces that metadata on rows it redelivers. --once bypasses preview and
still requests a full pass. Existing pending files drain first unchanged, including
old500row batches. Normal full history may still take hours over a slow path;
recent preview is not proof of complete provider coverage or minute freshness.
Regression tests verify recent-first order, eventual full pass and no premature
completion checkpoint. Source full suite330passed119skipped; company full suite576passed375skipped. No live all100 recovery qualification is claimed.

## Local traffic visibility (2026-10-26)

Native collectors now persist cumulative application payload byte counters under
their selected state directories (`traffic.json`) and print totals/deltas every
minute. TradingView measures WebSocket message payloads; both collectors count API
upload attempts/retries and response bodies. TSETMC measures decoded source HTTP
response bodies. This is an estimate, not NIC/billed traffic. Telemetry save failure
does not stop collection. Restart existing collectors to load the change; keep their
state and pending files. No API/database migration is required. Local API and both
collectors were observed running; local API had BTC1m/5m history and TSETMC daily
history for Foolad and another symbol. This does not prove all source slots complete.
Offline full suites: company 577 passed / 375 skipped, source 331 passed /
119 skipped; Ruff, format and mypy passed in both repositories. Local API had
native TradingView history and quotes for all 100 configured symbols at one
snapshot; existing processes predate this telemetry change and need restart.
