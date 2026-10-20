# M3B-2 disposable CI ownership

The pre-merge review of `bbef28f5` found REVIEW-01: the shared database fixture's
retained Windows ownership profile rejected GitHub's Linux service database.
Actions run `39477219485` recorded 484 passed / 356 fixture setup errors in both
matrix logs. This was a real CI regression; the earlier Windows PG16.1 result
of 827 passed / 9 skipped remains separate historical evidence.

## Two explicit profiles

`tests/disposable_postgres.py` defaults to the original `retained` profile. Its
data directory, task owner, system identifier, exact PG16.1 version, proof and
live checks remain unchanged. Unknown profile names fail closed.

The workflow explicitly selects `MARKETDATA_TEST_PROFILE=github-service`.
That setting selects validation; it is not proof that a database is disposable.
`tests/ci_postgres.py` additionally requires:

- The expected GitHub-hosted repository/job/run/attempt/matrix context.
- The actual service container ID supplied by GitHub, matching Docker inspect.
- Task, repository and run/attempt/matrix ownership labels on that container.
- The approved matrix image and its immutable image ID, no container restart,
  and a newly created anonymous Docker data volume with no host bind mounts.
- Physical PostgreSQL control-file system identifier, data directory, major
  version, PID/start generation, ready status and service port.
- A read-only live connection matching that physical identity, container IP,
  database/owner OIDs, version, startup timestamp and target ownership comment.
- A fresh job-specific proof under ignored `artifacts/ci-postgres.json`.

The initial bootstrap checks an empty, positively owned database before its
first SQL mutation (the ownership comment). It refuses an existing proof.
Every subsequent guarded migration and fixture verifies the proof and live
identity. The shared fixture rechecks its actual pooled connection in a
read-only transaction before TRUNCATE. Container identity snapshots are cached
within a process because Docker IDs/labels/mounts are immutable; every live
connection still checks the saved system identity and server startup timestamp.

No profile approves a database from an environment flag, port or `_test` suffix
alone. No production or retained local service is started or changed by this
workflow. GitHub disposes of its own job services.

## Matrix and verification

The plain PostgreSQL job now uses actual `postgres:16.1`; the separate existing
Timescale job uses `timescale/timescaledb:2.25.1-pg17`. Their version evidence
must be reported separately. The child-death test compares the restricted
connection to its guarded parent's database/version instead of hardcoding the
Windows server version. Financial and crash/receipt assertions are unchanged.

Before bootstrap or migration, the workflow runs fake-only guard tests. New
tests reject absent/stale/incomplete evidence, forged labels, reused volumes,
remote/overridden endpoints, altered live identity and pooled connections.
Instrumented invalid cases cannot issue mutating SQL. Bootstrap tests also
assert validation precedes the first ownership-comment write.

Local first attempt: 139 passed / 1 failed because bootstrap omitted the data
directory from its generated proof; this was corrected. The corrected local
guard/wire run has **140 passed**. Ruff lint/format442 and strict mypy61 pass.
No local database-writing test ran for this CI change. CI results must be
recorded after the actual remote run; local fakes are not Linux/Timescale passes.

The workflow uploads JUnit and job ownership metadata even when it fails.
Application timeouts, financial code, migration 0011, published wire contracts,
collectors/workers and frozen distributions are unchanged by this correction.
