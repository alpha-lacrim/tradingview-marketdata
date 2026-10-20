# TSETMC M3B-2 company INGEST and storage

This is an uncommitted company-side development change in `tradingview-m3b2`,
branch `codex/tsetmc-m3b2`, based on `e114a25be8679451f6064ad1fb03c0ef6a8aaefe`.
The read-only reference is TSETMC `b2b5ae6b7c1602745dc2c99cc6eca0bf124cced7`.
See [verification](tsetmc-m3b2-verification.md) for actual results and limitations.
Subsequent audit fixes and current verification are in
[M3B-2 remediation](tsetmc-m3b2-remediation.md); the earlier report remains historical.
No company deployment or real producer enrollment is included.

## Boundaries and defaults

There is one company FastAPI product. Its existing READ and INGEST factories remain
independent processes. TradingView source capture and synchronization remain independent
of TSETMC collection and its future worker. Neither worker nor either source database
is installed or changed by this destination migration. TSETMC availability cannot stop
TradingView READ. There are no public TSETMC REST, ChartData or WebSocket endpoints here.

`TSETMC_INGEST_ENABLED` defaults to false. Migration seeds no instrument, producer,
owner, credential, source epoch or financial history. A binding is disabled and inactive
unless an administrator explicitly requests activation. New registry DTOs use
`equity`/`common_stock`; the old TradingView enums and original decoder stay closed.

## Modules and shared components

- `tsetmc_wire.py` validates the bundled exact published JSON Schema and cross-field
  invariants independently of the collector. Public synthetic examples are copied unchanged.
- `tsetmc_storage.py` owns TSETMC SQL transactions. It never calls the legacy
  `DestinationWriter._apply()` candle/quote branches or constructs a `Tick`.
- `tsetmc_reconciliation.py` compares retained imports; it performs no application DML.
- `ingest_grants.py` extends server-side recovery models; original worker models stay closed.
- `tsetmc_registry.py`, `tsetmc_permissions.py` and the additive role SQL provide explicit
  administrative enrollment and restricted runtime checks.
- Existing HTTPS/Bearer guard, admission budgets, credential lookup, producer/owner locks,
  session renewal/recovery, durable receipt lookup, destination identity and observation
  ledger are reused. No separate authentication system or FastAPI product was introduced.

## Destination migration 0011

`down_revision="0010"`. Migrations 0001 through 0010 are unchanged. Namespace
`company_tsetmc` contains exactly nine logical tables:

| Table | Responsibility |
|---|---|
| instrument_links | Approved exact TEXT ins_code, shared registry identity, units/source binding, disabled default |
| daily_records | Accepted canonical daily head with nine exact NUMERIC measurements |
| daily_states | Immutable imported public states, including valid superseded versions |
| daily_revisions | Immutable old/new evidence, hashes and eighteen exact NUMERIC measurements |
| current_latest | Polled current snapshot, independent last trade/official close and source/receive clocks |
| daily_coverage | Per-date coverage; absence of a date does not delete it |
| source_status | Captured and expiring status evidence |
| event_clock | Independent transactional journal epoch/head/floor |
| events | TSETMC journal, independent of TradingView journal and cursors |

Provider/instrument/source identity uses composite foreign keys. Retained observations
also bind producer, epoch, observation ID, instrument, provider, position and ownership
generation through a deferred composite FK. Its additive public-table unique index is
logically redundant with the existing observation PK; populated legacy rows are preserved.
Review index size and migration lock duration before an eventual production cutover.

The three shared stream CHECKs admit the four new `tsetmc_*` names while retaining
`candles`, `quotes`, `coverage`, `status`. The replacement recovery SQL preserves
producer-first locking, full sorted grant manifests, immutable recovery receipts, expired
session recovery and old-generation fencing. Migration 0009 is unchanged.

NUMERIC constraints reject negative/nonfinite values and fractional trade counts.
Official close is allowed outside the executed high/low range. History UPDATE/DELETE
triggers and runtime grants protect immutable evidence. The journal counter is transactional,
so rollback does not consume a visible event ID. Pruning uses a narrowly granted SECURITY
DEFINER function with a fixed search path; it does not prune market history or receipts.

Downgrade refuses when a TSETMC binding, grant or imported observation/receipt exists.
Empty disposable namespace rollback and re-upgrade are tested. This is not a production
rollback procedure: frozen FastAPI 1.1.0rc1 rejects head 0011. Production restore/cutover
requires separately reviewed backups, data continuity and a compatible binary.

## Wire and financial semantics

INGEST-only POST routes are `/api/ingest/v1/tsetmc/{daily,current,coverage,status,reconcile}`.
Uploads require exact `X-Payload-SHA256`. All use the existing HTTPS/Bearer/admission guard.
Body cap is 2 MiB; published schema caps daily at 100 and other streams at one record.
Reconciliation is bounded by its schema and 256 KiB request cap. Unknown fields, duplicate
JSON keys, numeric JSON floats, noncanonical UUID/decimal spelling and invalid identities
are rejected. The original ins_code is nonzero-leading, 1 to 20 decimal digits, kept as TEXT;
unsupported source-local identifiers fail explicitly, without normalization.

Financial decimals are canonical strings, parsed directly to Decimal/NUMERIC without rounding
or float conversion. Null and zero stay distinct. Positions/versions fit signed positive
BIGINT; financial measurements retain the schema's full decimal-string domain. Financial
hashes use the source algorithm (ASCII JSON with integral trade_count), record hashes use
UTF-8 canonical kind/event/observation JSON, and batch hashes cover exact original bytes.
These hashes are deliberately different algorithms/inputs.

Daily acceptance, financial revision and public state version are separate. Confirmation
requires hash-bound sanitized review evidence; revocation cannot carry confirmed state.
Corrections reset local confirmation and prove exact previous/successor measurements and
hashes. Revision seeds import evidence without moving canonical values. Adjacent retained
states/revisions must agree; missing historical evidence remains explicitly incomplete.
Unresolved candidates never become accepted canonical data. Upstream finality always remains
unverified, including operator-confirmed records. No dates, prices, closures or timestamps
are invented. Native daily records never become fabricated one-minute candles.

Current updates obey source date/time and explicit same-clock correction evidence, not
transport position alone. Financial change is recomputed against the company durable head:
A -> B -> B with incoming financial_change=false still updates a company holding A.
Last traded price and official close remain distinct. Source reported instant, actual HTTP
receipt, company ingestion instant, uncertainty and provenance remain separate. Future
capture/review/revision evidence is rejected; expiry is never moved to delivery time.
Unchanged status polls do not create false financial events. Coverage pages update only
listed dates and cannot establish an exchange calendar or complete archive.

## Transactions, retries, ownership and recovery

A complete batch is validated independently. Producer is locked before the owner, immutable
batch/observation identities and stream state. Context includes enabled producer/key, live
session ID/generation, approved binding/epoch and ownership generation. Different instruments
have independent approved epochs. TradingView and TSETMC grants do not confer each other's
permissions. Ownership/epoch replacement cannot silently overwrite an existing canonical
head; a reviewed handover/baseline remains an operator action.

Financial/state/revision writes, observation ledger, TSETMC events and receipt commit together
with `synchronous_commit=on`. One invalid record rolls back all. Context locks are held until
a final lease check and commit. Exact byte retries return the immutable receipt; changed bytes
under an existing batch identity conflict. New batch IDs may refer to retained observations
without rewriting history. Superseded receipts report the submitted retained state/version/hash
needed by source ACK validation, rather than substituting the newer canonical head.

Renewal, recovery and receipt lookup use shared existing routes. Recovery requires the complete
manifest, supports multiple per-instrument epochs, and fences the prior session generation.
No source ACK or future-worker continuity anchor is implemented here. Restore uncertainty is
not permission to rotate epochs or fabricate receipts. Reconciliation never transfers ownership,
repairs records, creates epochs or approves unresolved financial conflicts.

## Reconciliation and legacy READ isolation

Requested keys return retained state hashes, revisions and explicit absence. Daily manifests
at source fence H require the entire imported prefix, compare approved full state and ordered
revision evidence as of H, and hash each ordered bounded page. Equal-state re-delivery aliases
are resolved through the immutable observation ledger, including a lower position imported later.
Revision completeness is checked without allocating an array proportional to a claimed revision
number. Unavailable import history returns `reconciliation_history_unavailable`; counts alone
never establish parity. No future public TSETMC READ API is exposed.

Shared registry queries filter unsupported TSETMC/equity rows before legacy model construction
and before pagination. Existing REST, instrument discovery, latest, WS and ChartData retain their
TradingView contracts. The new provider journal never advances the legacy event clock.

## Explicit administration and role upgrades (future operator action)

Only a reviewed future company package may run administrative commands. No command below
was used against a company server, and no real credentials were generated in this milestone.
The new `release_admin` options require an explicit company release root, private DSN file,
matching database and verified migration boundary:

- `--tsetmc-register <reviewed-binding.json>` adds a new binding to a nonempty registry;
  duplicate identities fail for manual comparison. `--tsetmc-activate` is an explicit opt-in
  on that new binding, not an implicit policy change.
- `--tsetmc-provision <reviewed-policy.json>` creates a distinct initial producer with exact
  per-instrument epochs and unknown-only TSETMC grants. It does not transfer existing grants,
  generate credentials, rotate an epoch or import history.
- `--tsetmc-upgrade-grants` applies additive namespace grants to existing restricted company
  principals after 0011. `--roles` is first-install only and still refuses existing roles.

`scripts/sql/tsetmc_destination_roles.sql` creates no login/password. READ gets SELECT and
USAGE, default read-only, no control-plane secrets/DML/DDL/pruning. INGEST gets the narrow
canonical/history/journal privileges, no registry/policy/history mutation/DDL. Startup rejects
unsafe privilege sets; the upgrade script does not silently revoke unreviewed existing rights.
Legacy READ principals without namespace access can still start with TSETMC disabled.

Enrollment of the real Foulad instrument is deferred. An operator must independently approve
its exact ins_code and original source identity, equity type, data rights, instrument epoch,
unit/corporate-action evidence (currently unverified), producer grants and continuity baseline.
No real pilot binding or activation was performed. Migration alone authorizes none of these.

## Release prerequisites

Existing rc1 distributions and source-sync code are immutable. The root project version is
still 1.1.0rc1 for development; a private wheel installation test is not a release. A future
version such as 1.2.0rc1 needs separate review, a new explicit export path/manifest, inclusion
of new modules/schema/role SQL/0011, lockfile parity, independent company-only installs and
compatibility evidence. Do not run the old hardcoded v1.1 release exporter unchanged.

Actual company database/version, backups, principal privileges, gateway/TLS, unit approval,
restore/cutover and production rollback remain unverified. Linux, TimescaleDB, sustained load,
real TSETMC worker transport/ACK/anchor and public READ features are separate gates.
