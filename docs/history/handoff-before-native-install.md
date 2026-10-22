# Current state — 2026-10-21

Both active project folders now use `main`. Read `docs/unified-dashboard-flow.md`
for connection setup and `docs/workspace.md` for repository/checkpoint navigation.
The original TradingView folder now contains audited company main, replacing its
superseded integration checkout. No production is active.

## Implemented

- Independently deployed company READ/INGEST share a separate destination database.
- Company destination schema: `0011`; TradingView source: `0006` plus `sc0002`;
  independent TSETMC source: `0005_delivery`.
- Optional COMPANY_TSETMC_ENABLED exposes Iranian discovery, exact daily/latest/
  coverage reads, REST replay and WebSockets. INGEST also requires TSETMC_INGEST_ENABLED.
- Audited Iranian storage retains immutable evidence, revisions, corrections,
  source time/receive time, numeric precision, fencing and journal retention.
- Iranian reads enforce API_MAX_ROWS. The dashboard client preserves source identity
  and documents international subscriptions and REST replay.
- Source worker runtime `9bee3ce` supports delivery during collector ownership,
  full saved-receipt checks and durable continuity evidence.

## Verified runtime checkpoints

Company runtime `f94b4c5`, documented in main `417388b4`, passed CI39597362733:
PostgreSQL16.1 **875 passed / 8 skipped**; TimescalePG17.7 **878 passed / 5 skipped**.
Both included lint, strict mypy, ownership safeguards, upgrade, downgrade and re-upgrade.
https://github.com/alpha-lacrim/tradingview-marketdata/actions/runs/39597362733

Source main `092f1e3` records runtime `9bee3ce`: local **372 passed / 5 skipped**,
final targeted **19 passed**, portable restore checks **2 passed**, and green
Windows/Linux/PostgreSQL CI39597489566. Source PR #1 is merged.
https://github.com/alpha-lacrim/tsetmc-marketdata/actions/runs/39597489566

Both repositories preserve annotated tag `checkpoint/unified-dashboard-2026-10-21`.
Cleanup changes documentation, ignore/build-context rules and Git organization only.
Application code, migrations and frozen distribution payloads are unchanged.
Cleanup validation: `uv sync --frozen --extra databento`, pytest **519 passed /
364 skipped**, Ruff, formatting and strict mypy passed. Database/live tests were
not rerun for documentation/configuration cleanup; the database CI above covers
the unchanged runtime. One upstream Starlette/httpx deprecation warning remains.
Both navigation graphs were refreshed with `graphify update .`; SQL extraction
is unavailable in the local graph tool, not a database validation result.

## Workspace cleanup

Private operator plans are in `.local/notes/`. Duplicate checkout, conversation
history, legacy uncommitted guides and exact earlier local edits were archived with
file hashes outside the project. `LOCAL_WORKSPACE.md` records the private location.
The local Git branch `archive/local-work-before-cleanup-2026-10-21` retains the
tracked local edits. It is private and must not be pushed without review.
Graph outputs remain available; generated AST caches are excluded from Git.
Merged task branches were removed. The incompatible old integration is preserved
as `archive/superseded-unified-dashboard-2026-10-21`, for historical recovery only.
The task-created detached worktree was removed after its private evidence was
archived and verified. Other worktrees and the shared home Git store are untouched.
The finished workspace is tagged `checkpoint/workspace-clean-2026-10-21`.
Earlier handoff details are in `docs/history/handoff-before-2026-10-21-cleanup.md`.
Historical docs describe earlier code and must not override this file.

## Remaining work

Qualify the approved staging host, company TLS/login/BFF, genuine international
feed registry and coverage, source rights and restore/cutover procedures. The
TSETMC worker still has a 10,000-retained-batch startup audit ceiling and uses the
trusted collector SQL principal. Resolve retention and dedicated worker permissions
before unattended operation. Only Foolad has earlier genuine Iranian pilot evidence.
No live provider, service, original pilot, database or volume was changed by cleanup.
