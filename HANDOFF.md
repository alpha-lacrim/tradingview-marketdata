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

Companion TSETMC native default discovers primary shares (745 candidates in a
3,462-row market-watch snapshot), qualifies metadata individually and uses the
existing daily/current endpoints. Four sampled families passed source parsing;
not all 745 are live-qualified. The bulk endpoint has zero date/price placeholders
and is used only for discovery. Pacing means broad latest sweeps take minutes,
not 15 seconds. Per-instrument full-history refresh is daily, with durable success
checkpoints; a smaller explicit --ins-code watchlist has better freshness.

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
TradingView recovery is limited to available history (up to1440 minutes requested).
