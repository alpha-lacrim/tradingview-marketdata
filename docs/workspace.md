# Workspace and recovery checkpoints

Use `main` in `tradingview-main-consolidation` for the company API and international
collector code, and `main` in `tsetmc-marketdata` for the independent Iranian collector.
The current connection procedure is [unified-dashboard-flow.md](unified-dashboard-flow.md).
`distributions/` contains frozen releases with their own versioned installation guides.

## Checkpoints

Both repositories have annotated `checkpoint/unified-dashboard-2026-10-21` tags for
the verified implementation before workspace cleanup. A checkpoint is a source-code
reference, not a deployed release or a database backup. Inspect it without changing
your current branch:

```powershell
git show checkpoint/unified-dashboard-2026-10-21
git worktree add --detach ../marketdata-checkpoint checkpoint/unified-dashboard-2026-10-21
```

`checkpoint/workspace-clean-2026-10-21` identifies the subsequent organized workspace.
Completed task branches were removed after preserving their commits. The old
incompatible company integration is retained as
`archive/superseded-unified-dashboard-2026-10-21` for historical recovery only.
Use current `main` for development and deployment preparation.

Never apply company migrations to a collector database. Database restore and
collector continuity require their own reviewed procedures.

## Local files

- `.local/notes/`: private operator plans and notes.
- `artifacts/`: private verification evidence and disposable test resources.
- `.venv/`: the checkout's Python environment; recreate with `uv sync --frozen --extra databento`.
- `graphify-out/`: generated navigation graph; its AST cache stays local.
- `docs/history/`: historical context; `HANDOFF.md` describes the current state.

The 2026-10-21 cleanup archived the duplicate nested checkout, conversation history,
older uncommitted rc1 guides and exact local changes outside the active project.
The private `LOCAL_WORKSPACE.md` records the local archive location and recovery
references. The original operator plan remains at `.local/notes/laptop_VM_flow.md`.
The plan and archived guides require review before use for deployment.

Use the standard root `src/`, `tests/`, `scripts/`, `config/`, and `migrations/`
directories. Keep caches, credentials, database files and local copies out of Git
and container build contexts. The existing home-level Git store and unrelated
worktrees are shared historical resources; this cleanup does not remove them.
