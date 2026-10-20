"""Bounded, authenticated comparison of retained imports; never repairs state."""

from datetime import date
from typing import Any
from uuid import UUID

from marketdata.ingest_auth import Principal
from marketdata.tsetmc_storage import TsetmcWriter, parsed
from marketdata.tsetmc_wire import TsetmcError, digest, validate


async def revisions(c: Any, request: dict[str, Any], day: date, fence: int) -> list[Any]:
    # Use the immutable import ledger to determine availability at H, including
    # evidence first imported at a higher position and later replayed below H.
    rows = await c.fetch(
        """SELECT DISTINCT payload->'observation'->'revision_evidence' AS
evidence
FROM public.ingest_observations WHERE instrument_id=$1 AND
provider='tsetmc'
AND source_epoch=$2 AND stream='tsetmc_daily' AND
source_position<=$3
AND payload->'observation'->>'trading_date'=$4
AND payload->'observation'->'revision_evidence' IS NOT NULL
AND payload->'observation'->'revision_evidence'<>'null'::jsonb""",
        UUID(request["instrument_id"]),
        UUID(request["source_epoch"]),
        fence,
        day.isoformat(),
    )
    evidence = sorted(
        (parsed(r["evidence"]) for r in rows), key=lambda r: int(r["financial_revision"])
    )
    for item in evidence:
        retained = await c.fetchval(
            """SELECT payload FROM company_tsetmc.daily_revisions WHERE
instrument_id=$1
AND provider='tsetmc' AND source_epoch=$2 AND trading_date=$3 AND
financial_revision=$4""",
            UUID(request["instrument_id"]),
            UUID(request["source_epoch"]),
            day,
            int(item["financial_revision"]),
        )
        if retained is None or parsed(retained) != item:
            raise TsetmcError("reconciliation_history_unavailable", 409)
    return evidence


async def row(
    c: Any, request: dict[str, Any], stream: str, day: str | None, fence: int
) -> dict[str, Any]:
    if stream == "tsetmc_daily":
        state = await c.fetchrow(
            """SELECT s.*,o.source_position AS imported_position
            FROM company_tsetmc.daily_states s JOIN public.ingest_observations o
            ON o.instrument_id=s.instrument_id AND o.provider=s.provider
            AND o.source_epoch=s.source_epoch AND o.stream='tsetmc_daily'
            AND o.payload->>'kind'='daily' AND o.payload->'observation'=s.payload
            WHERE s.instrument_id=$1 AND s.provider='tsetmc' AND s.source_epoch=$2
            AND s.trading_date=$3 AND o.source_position<=$4
            ORDER BY s.state_version DESC,o.source_position DESC LIMIT 1""",
            UUID(request["instrument_id"]),
            UUID(request["source_epoch"]),
            date.fromisoformat(day or ""),
            fence,
        )
    else:
        table = {
            "tsetmc_current": "current_latest",
            "tsetmc_coverage": "daily_coverage",
            "tsetmc_status": "source_status",
        }[stream]
        values: list[Any] = [UUID(request["instrument_id"]), UUID(request["source_epoch"])]
        condition = ""
        if stream == "tsetmc_coverage":
            values.append(date.fromisoformat(day or ""))
            condition = " AND trading_date=$3"
        state = await c.fetchrow(
            f"""SELECT * FROM company_tsetmc.{table} WHERE instrument_id=$1 AND
provider='tsetmc' AND source_epoch=$2"""
            + condition,
            *values,
        )
    observation = parsed(state["payload"]) if state else None
    evidence = (
        await revisions(c, request, date.fromisoformat(day), fence)
        if stream == "tsetmc_daily" and day
        else []
    )
    revision = (
        int(observation["financial_revision"])
        if observation and "financial_revision" in observation
        else None
    )
    if stream == "tsetmc_coverage" and state:
        full = await c.fetchval(
            """SELECT payload->'observation' FROM ingest_observations WHERE
producer_id=$1 AND
source_epoch=$2 AND observation_id=$3""",
            state["producer_id"],
            state["source_epoch"],
            state["observation_id"],
        )
        if full is None:
            raise TsetmcError("reconciliation_history_unavailable", 409)
        state_digest: str | None = digest(parsed(full))
    else:
        state_digest = digest(observation) if state else None
    return dict(
        stream=stream,
        trading_date=day,
        found=state is not None,
        source_position=str(
            state["imported_position"] if stream == "tsetmc_daily" else state["source_position"]
        )
        if state
        else None,
        state_version=observation.get("state_version") if observation else None,
        financial_revision=str(revision) if revision else None,
        financial_hash=observation.get("financial_hash") if observation else None,
        state_sha256=state_digest,
        upstream_finality="unverified",
        local_finalization=observation.get("local_finalization") if observation else None,
        revision_count=len(evidence),
        revision_sha256=digest(evidence),
        revision_complete=bool(state)
        and (
            revision is None
            or (
                len(evidence) == revision - 1
                and all(int(r["financial_revision"]) == i for i, r in enumerate(evidence, 2))
            )
        ),
    )


async def reconcile(
    writer: TsetmcWriter, principal: Principal, request: dict[str, Any]
) -> dict[str, Any]:
    validate(request, "ReconcileRequest")
    async with writer.store.connection() as c, c.transaction(isolation="repeatable_read"):
        streams = (
            sorted({k["stream"] for k in request["keys"]})
            if request["mode"] == "keys"
            else ["tsetmc_daily"]
        )
        for stream in streams:
            producer, link, _ = await writer.context(c, principal, request, stream)
            if link["ins_code"] != request["ins_code"]:
                raise TsetmcError("source_identity_conflict", 409)
        fence = int(request["source_fence"]) if request["mode"] == "daily_manifest" else 2**63 - 1
        next_date, more = None, False
        if request["mode"] == "daily_manifest":
            count = await c.fetchval(
                """SELECT count(*) FROM ingest_observations WHERE producer_id=$1 AND
source_epoch=$2
AND instrument_id=$3 AND provider='tsetmc' AND stream='tsetmc_daily'
AND
source_position<=$4""",
                principal.producer_id,
                UUID(request["source_epoch"]),
                UUID(request["instrument_id"]),
                fence,
            )
            if count != fence:
                raise TsetmcError("reconciliation_history_unavailable", 409)
            missing = await c.fetchval(
                """SELECT EXISTS(SELECT 1 FROM ingest_observations o LEFT JOIN
company_tsetmc.daily_states s
ON s.instrument_id=o.instrument_id AND s.provider=o.provider
AND s.source_epoch=o.source_epoch AND s.payload=o.payload->'observation' WHERE
o.producer_id=$1 AND
o.source_epoch=$2
AND o.instrument_id=$3 AND o.stream='tsetmc_daily' AND
o.source_position<=$4
AND o.payload->>'kind'='daily' AND s.observation_id IS NULL)""",
                principal.producer_id,
                UUID(request["source_epoch"]),
                UUID(request["instrument_id"]),
                fence,
            )
            if missing:
                raise TsetmcError("reconciliation_history_unavailable", 409)
            days = await c.fetch(
                """SELECT DISTINCT (payload->'observation'->>'trading_date')::date AS trading_date
                FROM public.ingest_observations WHERE instrument_id=$1
                AND provider='tsetmc' AND source_epoch=$2 AND source_position<=$3
                AND stream='tsetmc_daily' AND payload->>'kind'='daily'
                AND (payload->'observation'->>'trading_date')::date BETWEEN $4 AND $5
                AND ($6::date IS NULL OR (payload->'observation'->>'trading_date')::date>$6)
                ORDER BY trading_date LIMIT $7""",
                UUID(request["instrument_id"]),
                UUID(request["source_epoch"]),
                fence,
                date.fromisoformat(request["from_date"]),
                date.fromisoformat(request["through_date"]),
                date.fromisoformat(request["after_date"]) if request["after_date"] else None,
                request["limit"] + 1,
            )
            more = len(days) > request["limit"]
            keys = [
                {"stream": "tsetmc_daily", "trading_date": r["trading_date"].isoformat()}
                for r in days[: request["limit"]]
            ]
            next_date = keys[-1]["trading_date"] if more else None
        else:
            keys = request["keys"]
        rows = [await row(c, request, k["stream"], k["trading_date"], fence) for k in keys]
        now = await c.fetchval("""SELECT clock_timestamp()""")
        if producer["session_expires_at"] <= now:
            raise TsetmcError("producer_session_fenced", 409)
        # Locking functions require a writable transaction, but no application data is modified.
        result = dict(
            protocol_version=1,
            contract_version="tsetmc.v1",
            mode=request["mode"],
            instrument_id=request["instrument_id"],
            ins_code=request["ins_code"],
            source_epoch=request["source_epoch"],
            ownership_generation=request["ownership_generation"],
            destination_id=str(
                await c.fetchval("""SELECT destination_id FROM ingest_destination_state""")
            ),
            server_checked_at=now.isoformat().replace("+00:00", "Z"),
            source_fence=request.get("source_fence"),
            rows=rows,
            next_after_date=next_date,
            has_more=more,
            page_sha256=digest(rows),
        )
        validate(result, "ReconcileResponse")
    return result
