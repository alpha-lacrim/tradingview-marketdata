# Current state - native installation, 2026-10-22

The default is now `docs/native-install.md`: one native FastAPI, one new company
PostgreSQL database, and two direct HTTP collectors with durable retry files.
No Docker, TimescaleDB, collector databases or producer registration are required.
The owner explicitly authorized open API/browser access and optional upload tokens.

`marketdata-simple init/serve` owns the separate `simple_marketdata` schema v1.
`tradingview-simple` reuses existing provider parsing and the provisional 99-source
registry. TSETMC's matching `tsetmc-simple` lives in the other repository.
The dashboard contract is `/api/chart` (a..h arrays plus i:null), with latest,
exact records, correction journal and WebSocket endpoints documented in
`docs/native-dashboard.md`. Decimals stay strings in JSONB until chart conversion.
Uploads are atomic and idempotent; pending files survive lost responses. Older
observations cannot replace newer data. Quote event time is preserved separately.

Validation: Ruff, format, strict mypy passed; full pytest 534 passed / 364 skipped.
Native tests use an explicitly marked disposable PostgreSQL 16.1 database.
Legacy PostgreSQL/Timescale and live tests were not requalified for this additive
profile. Both wheels built; the API wheel includes its SQL initialization resource.
Actual loopback HTTP smoke exercised both upload formats, TSETMC fixture parsers,
PostgreSQL chart/latest reads and WebSocket changes using synthetic upstream data.
This is infrastructure verification, not live coverage qualification.

Ubuntu instructions and user systemd units are supplied, not deployed. Automatic
company CI now tests native PostgreSQL on Ubuntu; legacy Docker CI remains manual.
No employer host/access was supplied. Follow the installation guide there, start
collectors, and give the frontend team the API URL and dashboard contract.

Limits: Foolad only for TSETMC, native daily history with unverified finality;
TradingView registry availability is provisional, not 99 proven feeds. Recovery
requests up to 1440 minutes; longer outages can leave gaps. Quote snapshots are
not a full tick archive. Unknown chart metrics use documented zero placeholders.
Stored history remains readable with collectors offline. Monitor database growth.

Existing databases, frozen distributions and legacy pipelines remain intact.
Native initialization refuses legacy databases; no old history is auto-imported.
Retain old archives, especially history beyond TradingView's retrieval horizon.
Previous handoff is `docs/history/handoff-before-native-install.md`; do not use its
superseded deployment recommendations for this profile. Workspace recovery details
remain in LOCAL_WORKSPACE.md. Never push the private local archive branch.

## Native handshake recovery fix

A live laptop run exposed an unhandled websockets InvalidMessage when the remote
connection ended before the HTTP handshake response. The native candle loop now
retries this transport failure after its existing 60-second delay, while --once
still fails visibly. This prevents the history task from cancelling the quote and
upload tasks. The regression reproduces the previous TaskGroup crash, verifies
cleanup/reconnection and preserves one-shot failure behavior. Provider access
rejections still follow their existing permanent-error path. No database/schema
changes; pending files remain intact. This does not establish why the upstream
connection closed, nor solve independent API response timeouts.

Fix validation: regression 14 passed / 3 database skips; full local suite 528
passed / 368 skipped, Ruff/format and strict mypy passed. Database, optional
provider and live tests were not enabled for this transport-only change.

## Native recovery hardening

Both collectors now report upload HTTP/transport causes, pending filenames,
exponential retry delays (30..300 seconds), recovery, and honor HTTP-date/numeric
Retry-After even when longer. Bad/non-object receipts and permanent rejections
retain pending files and fail visibly. The delivery helper copies are identical.
TradingView preserves reduced concurrency across reconnects, backs off repeated
failures (60..300 seconds), reports close/cause codes and actual delivered/empty
bar counts, and stops on provider-wide permanent rejection. Unknown programming
errors are no longer swallowed by the quote reconnect loop.
TSETMC drains staged uploads before identity lookup; transient startup lookup
failures retry while invalid identity/access failures remain fatal.

API database operations have a 20-second budget including a five-second pool
acquire limit; temporary database/network failures return 503 + Retry-After: 30.
WebSockets close with 1013 for reconnect. Per-request console access logs are off
by default (`--access-log` opts in); this reduces Windows terminal traffic but
cannot guarantee recovery from a paused terminal or unresponsive process.
No schema, stored quote semantics or chart contract changed.

Validation: full company suite 551 passed / 365 skipped, followed by all 38 native
recovery tests passing after an additional permanent-rejection case. Ruff/format
and strict mypy passed. Source suite 281 passed / 119 skipped. An isolated native
PostgreSQL outage returned HTTP 503 for health/instruments, kept OpenAPI at 200,
and recovered after DB restart without restarting FastAPI. No live-provider
outage was induced and the user's running laptop processes were not replaced.
Restart the API and collectors to load these changes. Updated ZIPs must be built
from these commits, not the earlier native or handshake-only checkpoints.
