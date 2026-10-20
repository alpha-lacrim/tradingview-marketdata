# M3B-2 audit remediation — 2026-10-20

Bounded company-side corrections in the existing uncommitted `codex/tsetmc-m3b2`
worktree, HEAD `e114a25be8679451f6064ad1fb03c0ef6a8aaefe`. The original implementation
and its failed/aborted verification evidence remain preserved. No source collector,
worker, published contract, old migration or frozen release is changed.

## Corrected invariants

- **F01:** Every full daily state checks retained revision evidence at its financial
  revision and successor. Seed-first and state-first delivery enforce identical old/new
  measurement/hash consistency. Missing evidence is not fabricated; contradictions reject
  the whole transaction. Financial revision and public state version remain independent.
- **F03:** Daily ordering uses all retained full-state observation positions, including
  equal-state aliases. Each version's minimum/maximum positions bound neighboring versions.
  The check precedes equal-state return and is instrument/provider/epoch/date scoped.
- **F04:** Independent full-string checks reject noncanonical measurement/count spelling
  before Decimal conversion and hash validation. No trimming or normalization occurs.
- **F05:** Known local times are parsed even without a UTC instant; review evidence IDs
  obey the complete int64 string domain; unpaired surrogates reject before UTF-8 hashing.
  Persian text, the normative schema and all three hash algorithms are unchanged.
- **R01:** `company_tsetmc.lock_instrument(uuid)` takes a SHARE row lock through commit.
  It is SECURITY DEFINER with fixed search_path, revoked PUBLIC execution and INGEST-only
  execution grants. READ startup rejects execution rights. Writer/reader table privileges
  are otherwise unchanged. The uncommitted 0011 defines the function; no old migration changes.

Binding-only administrative UPDATE now serializes against uploads. Upload-first means the
administrator waits for the upload to finish; administrator-first means an upload waits and
then validates the changed binding. Disablement rejects subsequent uploads, and changed
profiles require matching approved evidence. For combined policy/binding administration,
take producer locks first, sorted owner locks second, binding locks next. Do not take a
binding lock and then request a producer/owner lock. No public binding-change route exists.

## F02: prerequisite for every database-writing verification

The shared `database_url` fixture validates ownership before application pool creation.
The shared `store` fixture repeats that verification on its actual pooled connection,
inside a read-only transaction, before any TRUNCATE. A replaced endpoint therefore cannot
inherit authorization from an earlier connection check. Failed setup closes the pool.
Source/migration/role/frozen-worker fixtures depend on this guarded root before creating
their own uniquely named databases in the same verified cluster.

The test-only guard is deliberately pinned to this retained M3B-2 cluster: exact resolved
task data directory, PG16.1, known system identifier 7698666753214710248, original ownership
marker 801c97e7-784b-4737-b6ca-fa191a8c4373, loopback listener and administrator identity.
It checks PG_VERSION, pg_control, postmaster PID/start generation, the separate owner file,
fresh verification evidence and live read-only SQL metadata. Target database name, OID,
owner OID and a durable task ownership comment must all agree. The proof also matches the
actual postmaster start time; stale/restarted/recreated targets fail closed.

Private proof: `artifacts/m3b2/remediation/isolation.json`. The old `isolation-verified.json`
is historical evidence and is not authorization for these tests. Missing proof fails closed;
do not copy an old report or change TEST_DATABASE_URL to bypass it. An expired proof requires
independent read-only re-verification of the known cluster and target. Another cluster needs
a separately reviewed ownership profile; a name, environment variable or port is insufficient.

Before the first database-writing test, fake-only tests proved missing/forged/stale/mismatched
evidence cannot connect or mutate. Further cases verify actual pytest dependency ordering
and rejection when the application pool resolves a different database identity. No invalid
proof case can reach TRUNCATE, migration, DROP or application registration.

## Evidence and failed attempts

All new local evidence is separate under ignored `artifacts/m3b2/remediation/`.

- Initial safety tests: 21 passed, then 22 after adding PID-generation checks.
- First live guard refused setup: shared database comments need `shobj_description`, and
  PID-file creation precedes pg_postmaster_start_time by more than one second. The guard
  remained closed. Both physical and SQL startup identities are now checked explicitly.
- Pure validation run: 109 passed, followed by 110 with actual pytest ordering coverage.
- First PostgreSQL targeted run: 63 passed, 2 failed. The two child-death harnesses still
  loaded the old database proof. They now use the same current proof as the root guard.
- Corrected PostgreSQL targeted run: 65 passed, including all four restricted-role binding
  concurrency cases, migration roundtrips, crash/retry and actual frozen-worker delivery.
- Pooled-connection safety extension initially had a NameError in its fake connection class
  (22 passed, 1 failed); the corrected fake-only safety suite has 24 passed.
- Initial Ruff checks reported ten formatting/import issues; after formatting, three
  async/fixture-annotation issues remained. File checks now use a thread, coordination uses
  an Event, and the fixture annotation is correctly placed. Final lint/format are clean.
- A deliberate pre-fix R01 run loads only the old context method from the retained development
  wheel. The concurrency assertion fails as expected; inspection confirms disabled binding,
  one financial record and one receipt. This is red reproduction evidence, not a failed
  corrected-code acceptance run. The old wheel and its hash are unchanged.
- `before-after.json` reproduces F01/F03/F04 and all three F05 inputs against that same
  pre-remediation development wheel; the corrected methods reject all six scenarios.

The legacy fresh-migration test's administrative DROP now has independent 60-second client
and statement budgets, justified by the retained 25.539-second checkpoint. Migration and
preservation assertions and production/request budgets remain unchanged. The 50ms legacy
startup test remains unchanged. Isolated reruns never replace an original full-suite result.

## Final executed results

| Check | Actual result |
|---|---|
| Complete PG16.1 suite, final application/test code | **827 passed, 0 failed, 9 skipped**, 644.65 seconds |
| TSETMC subset of that full run | **152 passed**: wire87, storage47, HTTP15, migrations2, frozen worker1 |
| F02 fake-only subset of that full run | **24 passed**, including actual pytest ordering and pooled-identity mismatch |
| Corrected targeted PG run | **65 passed**, before the final extra pooled-connection safety check |
| Final Ruff / format | Passed; 440 Python files already formatted |
| Strict mypy | Passed; 61 source files |
| New private wheel | Offline build and fresh offline install; isolated imports/schema/OpenAPI and actual restricted READ startup on PG16.1/0011 passed |
| Installed dependency consistency | Passed; 28 packages |
| Graphify | AST-only update completed; 6673 nodes / 13166 edges; SQL parser unavailable for seven SQL files |

The complete run passed both previously timing-sensitive legacy cases, all six original
TradingView regression cases, and the actual unchanged frozen worker. It contains 651
passing legacy cases in addition to the TSETMC and guard subsets. No legacy application
timeout, financial semantics, response schema or request-level timeout assertion changed.
The old 738/2/9 report is still preserved and is not rewritten as a pass.

Nine skips remain: optional Databento SDK; container backup/restore and outage; two frozen
v1.0/0006 pipelines; three Timescale aggregate cases; Linux image smoke. No skipped case is
claimed passed. Package checks are private development checks, not a versioned company export.

Before shutdown, SQL confirmed PG16.1, head0011, nine provider tables, fsync/on and
synchronous_commit/on, and zero other clients. Actual writer binding-lock execution is
granted; READ execution, writer binding UPDATE, writer immutable-history UPDATE and READ
INSERT are denied. The test-created package principals were removed before stopping only
the known task server. Process/listener checks afterward found no PostgreSQL/4195 process.
The new proof now intentionally fails until a future authorized run revalidates startup.

All eight pre-existing task database names/OIDs/owners remain; only the new remediation
database remains added. Old local 0011 diagnostic databases retain their earlier development
DDL and were not silently altered to add the new function. Tests used a fresh full 0011.

## Preservation and exact inventory

All 252 frozen payload files match HEAD byte for byte (80 company rc1, 106 worker rc1,
66 older distribution). No new cache directories appeared in those distributions. Old
0001–0010 migrations, TradingView collector/worker/control-plane source, reference schema
and all nineteen fixture examples remain unchanged. All fourteen previous JUnit hashes
match the original report. Of the older 373 protected fingerprints, 372 match; the sole
exception remains the previously acknowledged owner Graphify change to reference AGENTS.md.

[Machine-readable report](tsetmc-m3b2-remediation.json) contains complete expanded Git status,
every changed/new path, its category and digest, and the subset changed by this remediation.
The initial 605-entry audit snapshot is preserved separately. Unrelated pre-existing source,
README/CODEX/configuration changes are retained. Graphify's generated changes are listed
separately; no manual graph/cache deletion was performed. Nothing is staged or committed.

New evidence files and their hashes, including every failed and red-baseline attempt, are
listed in the JSON. Private evidence remains under ignored artifacts/m3b2/remediation;
the previous reports, wheels, data directory and logs are preserved.

Recommendation: **ready for another independent read-only audit**. No unresolved audited
defect or local non-green regression gate remains. This does not authorize publication,
production migration, real enrollment, M3B-3 or M3B-4.

## Boundaries and remaining gates

TSETMC ingestion/enrollment remains disabled by default. No real observations, instruments,
credentials, source requests or company connections are used. The old rc1 binary still
rejects destination head0011. This is not a release, deployment or production rollback plan.
Linux/TimescaleDB, production inventory, unit/rights review, sustained load, restore/cutover,
real HTTPS continuity/ACK and M3B-3/M3B-4 remain separate gates. Future packaging requires a
new reviewed export path/version and inclusion of the new function/grants and resources.
