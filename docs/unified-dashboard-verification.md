# Unified dashboard verification — 2026-10-21

This qualification used invented observations and a newly initialized, loopback-only
PostgreSQL 16.1 cluster on port 56031. Source and company data occupied separate
databases. No original collector database, persistent Foolad pilot, live provider,
company deployment, or frozen distribution was modified.

## Executed checks

- Company full regression suite against PostgreSQL: **663 passed, 10 skipped**.
  The four failures from the first run were resolved: one compatibility boundary
  rejected the new revision, and three migration tests expected the old head.
- Final focused setup/API/frontend run: **14 passed**. This includes generated
  connection files provisioning the actual company instrument and four stream
  grants, advertised bearer authentication, the new REST/WebSocket behavior and
  the one-origin JavaScript client routing.
- Independent TSETMC full suite with PostgreSQL enabled: **365 passed, 5 skipped**.
  The skips were three explicitly opt-in live probes and two optional dump/restore
  integrations requiring a selected PostgreSQL binary or Docker container.
- A subsequent source recovery run with the portable PostgreSQL binaries enabled:
  **2 passed**, including actual disposable `pg_dump`/`pg_restore`, exact staged
  bytes preserved, and newer continuity evidence fencing the restored database.
- Cross-repository HTTPS test: **1 passed** using an editable source checkout,
  verified local TLS, the company's authenticated INGEST application and its
  restricted database role. It creates and drops only its own synthetic source DB.
  It tests source enrollment, transmission, exact decimal correction, lost response
  after commit, duplicate-free restart, interruption before upload followed by
  session expiry/recovery, preservation of original staged observations, and a
  restored-source regression rejected using the external continuity anchor.
- Company tests exercise separate READ credentials, history selection, source
  freshness, authentication/ownership rejection, WebSocket updates/replay and READ
  restart while the source is absent. The existing international suites also run.
- Both Python packages built as wheels and source archives. The company wheel
  contains its independent `tsetmc/schema.json`; the source wheel includes delivery.
- `docker compose -f compose.company-unified.yaml config --quiet` passed with
  synthetic configuration values. This validates configuration, not a container
  image build or deployed gateway.
- Ruff and mypy checks ran for both projects. Graphify AST updates generated local
  graphs; SQL extraction reported its optional parser missing. Graph outputs remain
  local because the workspace contains unrelated private conversation artifacts.

Raw local logs/XML are in
`artifacts/unified-flow/`; the source report is `.local/unified-tests.xml` in its
own checkout. These paths are ignored, not release payloads.

Reproduce against explicitly created disposable databases, never a production DB:

```powershell
# Company checkout; TEST_DATABASE_URL must end in _test and be migrated to 0011.
uv run --offline pytest -q
# The opt-in two-database test imports the matching sibling source checkout.
$env:TSETMC_TEST_ROOT = 'C:/Users/Pouyan/PycharmProjects/tsetmc-marketdata'
uv run --offline --with-editable ../tsetmc-marketdata pytest tests/test_unified_delivery.py -q
# Source checkout; TSETMC_TEST_ADMIN_URL must refer to an isolated PG 16.1 cluster.
uv run --offline pytest --postgres -q
```

The cross-repository test deliberately requires PostgreSQL 16.1 and creates its own
source database. All credentials in the test observations are synthetic. A Windows
temporary-directory ACL issue required a fresh task-local `--basetemp`; no user
temporary directories or ACLs were changed. Existing dependency deprecation
warnings remain; they did not fail the tests.

## What these checks do not establish

This is an implemented and locally qualified integration, not proof of sustained
genuine coverage. Earlier artifacts distinguish a short genuine TradingView BTC
test, a synthetic 99-feed pipeline test, and a differing 100-source accuracy
registry. The intended 99-feed universe still needs an explicit choice and genuine
provider qualification. Foolad's preceding real pilot evidence does not establish
broader Iranian coverage or real-time delivery.

Actual company DNS/TLS, user login/BFF, secret provisioning, approved database
upgrade, producer rollout and restore rehearsal remain deployment work. No
unattended service was enabled. The TSETMC worker currently uses the local trusted
collector principal, audits at most 10,000 retained batches, and has no automatic
evidence pruning. Company event retention also needs an operational policy before
unattended scale. Default finalized daily history can legitimately be empty.

Use [the setup and frontend guide](unified-dashboard-flow.md) with matching commits
from both repositories. Existing v1.0/v1.1.0rc1 archives do not contain this work.
