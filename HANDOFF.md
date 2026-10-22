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
