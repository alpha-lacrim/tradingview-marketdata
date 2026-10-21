# AGENTS.md

## Purpose

This repository implements a reliable multi-asset market-data ingestion and serving platform.

This file contains durable repository-level instructions.

Keep this file concise. Detailed engineering conventions belong in `CODEX.md`. Current implementation state belongs in `HANDOFF.md`.

## Required context

Before substantive work:

1. Read this file and any applicable nested `AGENTS.md` / `AGENTS.override.md`.
2. Read `/CODEX.md`.
3. Read `/HANDOFF.md`.
4. Inspect relevant source files and tests before modifying them.
5. Inspect Git status and preserve unrelated user changes.

If instructions conflict, follow the most specific applicable `AGENTS.md`/`AGENTS.override.md`, then this file, then `CODEX.md`.

`HANDOFF.md` describes state, not policy. It must never override engineering rules.

## Core invariants

- Never fabricate provider capabilities, symbols, endpoints, timestamps or market-data status.
- Never represent delayed data as real-time.
- Never represent CFDs, spot instruments, indices, perpetuals and exchange-traded futures as the same instrument.
- Persist concrete futures contracts independently.
- Use UTC timezone-aware timestamps.
- Preserve both upstream event time and local receive time where available.
- Use decimal-safe financial representations rather than binary floating-point where precision matters.
- Never commit secrets.
- Never bypass exchange entitlements or access controls.

## Architecture

Maintain clear boundaries between:

provider transport
→ provider parsing
→ normalization
→ ingestion
→ persistence
→ query/API layers

Provider-specific logic must not leak into database or application-level domain logic.

Prefer simple, replaceable abstractions over provider lock-in.

## Change discipline

- Understand before editing.
- Search callers before changing public interfaces.
- Prefer small cohesive changes.
- Avoid unrelated refactors.
- Add or update tests with behavioural changes.
- Do not introduce infrastructure without a demonstrated need.
- Do not claim tests or commands passed unless they were actually run.

## Validation

Before considering work complete, run the relevant:

- unit tests;
- integration tests;
- linting;
- type checking;
- migrations;
- local smoke tests.

Use the project's existing commands defined in `CODEX.md`.

## Documentation

Update documentation when behaviour, architecture, provider coverage, configuration or operational procedures change.

Keep:

- stable rules in `AGENTS.md`;
- detailed engineering procedures in `CODEX.md`;
- live project state in `HANDOFF.md`.

## Handoff

Before ending a meaningful coding session, update `HANDOFF.md`.

It must enable a fresh agent with no conversation history to understand:

- current state;
- decisions already made;
- what was verified;
- unresolved problems;
- next recommended actions.

Remove stale information rather than accumulating an endless log.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.
