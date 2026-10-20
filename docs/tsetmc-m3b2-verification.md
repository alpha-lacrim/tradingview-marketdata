# M3B-2 verification — local Windows / PostgreSQL 16.1

Implementation and operations: [tsetmc-m3b2.md](tsetmc-m3b2.md).
This report distinguishes actual execution from future operational gates. No company
connection, source collection, real producer credential, production migration or deployment ran.

## State recovery and isolation

Existing worktree `C:\Users\Pouyan\PycharmProjects\tradingview-m3b2`, branch
`codex/tsetmc-m3b2`, starts and ends at uncommitted base
`e114a25be8679451f6064ad1fb03c0ef6a8aaefe`. It was resumed, not recreated.
Reference HEAD remains `b2b5ae6b7c1602745dc2c99cc6eca0bf124cced7`.
The original consolidation worktree's unrelated modifications remain separate.

The resumed server was stopped; no pytest process remained. Task ownership proof,
absolute data directory, PG_VERSION, pg_control system identifier 7698666753214710248,
process absence, free loopback port, and saved postmaster options were checked before
restarting only that cluster. PostgreSQL recovered the interrupted shutdown. SQL then
independently confirmed server_version_num=160001 and exact data_directory:
`C:/Users/Pouyan/PycharmProjects/tradingview-m3b2/artifacts/m3b2/pgdata`, port 4195.
The binary was read from the reference portable installation; its files were not modified.
No Docker project, existing service, volume or persistent source database was touched.

Initial disposable DB `m3b2_destination_test` and its logs were retained. Aborted tests had
left task-only roles. After checking every database belonged to this task, their grants
were removed within those disposable databases and the two leftover test roles dropped.
A fresh `m3b2_verified_test` was installed from base through the final 0011. Independent
fresh, populated upgrade, and source-worker fixtures used additional uniquely named task DBs.
The `_test` suffix alone was never accepted as isolation evidence.

## Interrupted and failed attempts (retained evidence)

All logs/XML are under ignored `artifacts/m3b2/`. Prior completed evidence was recovered:
wire 48 passed; storage 18 passed; HTTP initial one failure, followed by four passed after
repairing the missing separator in `ON CONFLICT ... DO UPDATE SET` generated SQL.
The interrupted broad run stopped at 576 reported cases: 562 pass, six failures, eight
runtime skips. It had no final JUnit. Ordered progress and unchanged legacy collection
allow recovery of the six failed node IDs; `interrupted-progress-recovered.json` preserves
that mapping. Remaining cases were unexecuted/aborted in that attempt, not passed.

| Original legacy failure | Cause and resolution |
|---|---|
| test_api_production::test_production_refuses_owner_dsn_and_accepts_select_only_role | New permission validation ran before the old owner-DSN rejection and changed its message. Preserve the existing SELECT-only rejection first. |
| test_api_v1::test_production_authentication_cors_and_openapi | New schema-qualified function privilege lookup required namespace USAGE from an old READ principal. Inspect catalog OIDs instead. |
| test_api_v1::test_dashboard_empty_auth_cors_limits_and_readonly | Same READ startup privilege regression; no REST/schema relaxation. |
| test_api_v1_operations::test_real_http_workers_read_stored_broker_candles_without_collector | Same startup regression in a real process; existing stored-candle serving remains unchanged. |
| test_destination_ingestion::test_reader_writer_grants_and_existing_rest_chart_ws | Same old-role startup incompatibility. The exact legacy role SQL is retained and tested. |
| test_market_workers::test_real_uvicorn_two_workers_deliver_same_commits_and_reconcile | Recovered worker log explicitly reports InsufficientPrivilegeError at startup. Fixed by catalog-OID inspection; WS assertions remain intact. |

The first completed recovery diagnostic reported 637 pass / 10 fail / 80 setup errors /
9 skipped. Eighty setup errors cascaded from the interrupted fixed-name test roles already
existing. Other failures included the READ regressions, three new tests incorrectly assuming
legacy journal head zero, a partially updated development task schema, and failed role cleanup
in the new migration fixture. Use a fresh final-schema task DB; compare the legacy head before
and after TSETMC writes. No old financial implementation or legacy assertion was weakened.

The next targeted run reported 188 pass / 2 fail. The new huge-revision case found PostgreSQL
inferring an arithmetic parameter as int32. Explicit BIGINT parameters and bounded neighbor
values now handle the supported position/revision domain, with no proportional range allocation.
The existing API timeout test failed before entering its request assertions: its connection
startup budget is only 50 ms. It passed an unchanged solo rerun. This timing failure is retained,
not relabeled as a pass or silently retried inside a test.

New administrative fence tests initially omitted required replacement-session fields and then
attempted owner/epoch changes without increasing ownership_generation. The existing database
constraints correctly rejected those invalid test setups. Supplying genuine administrative
fences made all five cases pass; no database constraint was relaxed.

A complete intermediate run reported 737 pass / 2 fail / 9 skipped. Its only legacy
failure was that 50 ms startup budget. The new migration test passed its migration/data/grant
assertions but its final DROP DATABASE hit the application's five-second command/statement
budget while a durable Windows checkpoint took about ten seconds. Only this new administrative
cleanup now uses an explicit 60-second DDL timeout; application budgets remain unchanged.
All 32 storage/migration cases passed the focused rerun afterward.

The original frozen rc1 Store was separately exercised on a fresh disposable 0010 database,
with the same dependencies and 50 ms connection setting: 6 of 40 attempts raised TimeoutError.
`frozen-timeout-baseline.json` records actual frozen module provenance and failed iterations.
This proves an existing host timing issue, independently of 0011 or TSETMC. The legacy test
and application timeout implementation remain unchanged. Final suite attempts are all reported.

## Acceptance coverage

| Gate | Executed evidence |
|---|---|
| T01–T02 | All 19 public examples and manifest byte hashes; independent ASCII financial / UTF-8 record / exact-byte payload hashes; strict invalid decimal, identity, key, schema, ordering, finality and body cases |
| T03–T04 | HTTPS/Bearer/Origin/admission, separate namespace grants, disabled defaults, real restricted roles, multi-instrument epochs, shared recovery/replay/fencing, administrative revocation and owner/epoch/generation/key changes |
| T05 | Exact retry receipts, changed-byte conflicts, observation conflicts, retained superseded ACK fields, immutable ledger, receipt lookup and no partial batch commit |
| D01–D03 | Native daily acceptance, confirmation/revocation, corrections, revision seeds, exact previous/successor evidence, reverse delivery, independent instruments, close outside range, null/zero and large exact NUMERIC values |
| D04 | Current A→B→B coalescing, source-clock regression, ambiguous same-clock rejection, explicit correction, durable-head financial comparison |
| D05 | Independent commit-ordered contiguous journal, blocked later transaction, no precommit visibility, rollback, producer-first revocation, response loss and actual child os._exit before/after commit |
| D06 | Fresh base→0011; populated 0010→0011 full public-table snapshots; interruption rollback to0010; disposable downgrade/re-upgrade; new/existing roles and actual forbidden SQL; composite context FK and NUMERIC constraints |
| D07 | Requested keys, ordered page hashes, source fence H with exact prefix, retained old states/revisions, equal-state alias replay, explicit unavailable/incomplete history and huge revision bounds |
| Legacy | Complete existing TradingView READ/INGEST/auth/session/registry/candle/quote/REST/WS/ChartData/source-worker suite; frozen worker actual TLS delivery and session recovery |

Frozen worker test verifies all 105 manifest payload hashes before and after execution. It runs
the exact frozen source with isolated Python import paths and bytecode writing disabled, against
the new destination and a synthetic independently created source DB. Two invented TSETMC registry
bindings are present; native candle/quote delivery and expired-session recovery still work.
It asserts head0011, no TSETMC grants/events, no pending financial source observations and unchanged
frozen bytes. It neither modifies the worker nor connects an actual source installation.

## Results and remaining gates

Final machine-readable counts, hashes and changed-file inventory are recorded alongside this
report when verification finishes. Private wheel installation is a development check, not a
replacement company release. Frozen artifacts and old migration bytes are preserved. Of 373 pre-interruption preservation
hashes, 372 match. The remaining reference AGENTS.md differs only by owner-supplied graphify
instructions and was already dirty at the start of this resumed session; no reference code,
contract or migration changed. Original HANDOFF/README/guide hashes match their saved values.
Graphify AST update ran as instructed; its SQL parser is unavailable (seven SQL files omitted
from that graph), so graph output is navigation evidence, not SQL validation.

Linux/TimescaleDB, production gateway/TLS/WAN, real source transport/ACK/continuity anchors,
physical server restart/restore, real unit/entitlement approval, sustained capacity and public
TSETMC READ/ChartData/WS remain unexecuted. M3B-3 and M3B-4 are not implemented or claimed passed.
Old rc1 cannot be a post-0011 restart target. Production rollback and cutover need separate review.

## Final recorded results

| Run/check | Actual result |
|---|---|
| Complete final PG16.1 suite | **738 passed, 2 failed, 9 skipped**, 838.16 seconds |
| TSETMC cases in that suite | **89 passed**, zero failures/skips |
| Two failed legacy cases, unchanged isolated rerun | **2 passed**, 2.61 seconds |
| Latest focused storage/migration run | **32 passed**, 22.87 seconds |
| Ruff / format / strict mypy | Passed; 437 Python files formatted, 61 source files typed |
| Private wheel | Offline build/install, bundled schema, isolated imports/OpenAPI, restricted production READ lifespan on PG16.1/0011 and pip check (28 packages) passed |

The full-run failures were the unchanged 50 ms startup test and existing fresh-migration
cleanup using a five-second application budget for DROP DATABASE. PostgreSQL explicitly
logged statement timeout on that DROP, after migration assertions. Both tests passed unchanged
on the isolated rerun; **the complete suite is still reported as failed**. No legacy test was
deleted, weakened, xfailed or retried internally. The original six regression tests pass.
No confirmed TradingView behavior regression remains.

Nine skips: optional Databento SDK module; task-container backup/restore and outage cases;
two exact frozen-v1.0/0006 pipelines; three Timescale aggregate cases; Linux production-image
smoke. Exact reasons, all attempt counts and JUnit hashes, complete changed-file inventory
and provenance are in [verification JSON](tsetmc-m3b2-verification.json).

Private package-harness failures are retained: its initial import check omitted the required
INGEST credential-file setting; the first READ call omitted instruments(limit). Only the
harness was corrected. Final installed imports and restricted READ lifespan passed.
The private root wheel retains the development version; no company release export, frozen
regeneration, image build, commit, push, tag or deployment occurred.

Preservation: all 80/106/66 committed distribution payloads match HEAD. Original protected
files match their saved hashes except the owner-supplied reference AGENTS.md instructions
already dirty on resume. The original older manifest uses CRLF, pristine checkout/HEAD LF;
JSON is identical and the original saved hash is unchanged. Generated Ruff caches were
archived under ignored task artifacts; final lint uses RUFF_CACHE_DIR outside distributions.

Recommendation: **ready for independent code review with a non-green complete-suite gate**.
Resolve Windows startup/administrative timing sensitivity in a separately reviewed test setup
or reproduce on target CI before acceptance sign-off. Production, packaging and rollout require
separate review; old rc1 cannot restart against head0011.

## Changed-file inventory

Every path, including all generated graph files and 19 synthetic examples plus manifest,
is listed in the JSON. Hand-edited implementation/configuration/test/documentation files:

- `.gitignore`
- `CODEX.md`
- `HANDOFF.md`
- `README.md`
- `docs/fastapi-tsetmc-ingest-openapi.json`
- `docs/tsetmc-m3b2-verification.json`
- `docs/tsetmc-m3b2-verification.md`
- `docs/tsetmc-m3b2.md`
- `migrations/versions/0011_tsetmc_ingestion.py`
- `pyproject.toml`
- `scripts/sql/tsetmc_destination_roles.sql`
- `src/marketdata/config.py`
- `src/marketdata/contracts/tsetmc.v1.schema.json`
- `src/marketdata/ingest_api.py`
- `src/marketdata/ingest_grants.py`
- `src/marketdata/persistence.py`
- `src/marketdata/release_admin.py`
- `src/marketdata/tsetmc_ingest.py`
- `src/marketdata/tsetmc_permissions.py`
- `src/marketdata/tsetmc_reconciliation.py`
- `src/marketdata/tsetmc_registry.py`
- `src/marketdata/tsetmc_storage.py`
- `src/marketdata/tsetmc_wire.py`
- `tests/conftest.py`
- `tests/test_destination_migrations.py`
- `tests/test_ingest_http.py`
- `tests/test_ingest_migrations.py`
- `tests/test_release_foundation.py`
- `tests/test_session_recovery.py`
- `tests/test_source_capture.py`
- `tests/test_sync_worker.py`
- `tests/test_tsetmc_frozen_worker.py`
- `tests/test_tsetmc_http.py`
- `tests/test_tsetmc_ingestion.py`
- `tests/test_tsetmc_migrations.py`
- `tests/test_tsetmc_wire.py`
- `tests/tsetmc_helpers.py`
- `uv.lock`

Inventory groups: docs: 4, fixtures: 20, generated graph: 547, migrations: 1, root: 6, scripts: 1, src: 12, tests: 14.

Final cleanup: the verified task-owned PG16.1 process was stopped cleanly with zero other
client connections. Final SQL confirmed head0011, nine namespace tables, fsync=on and
synchronous_commit=on. Data directory and all logs/results remain preserved.
