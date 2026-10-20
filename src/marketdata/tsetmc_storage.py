"""TSETMC destination transactions; no collector, HTTP client or source database."""

import hashlib
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from marketdata.ingest_auth import Principal
from marketdata.persistence import Store
from marketdata.tsetmc_wire import (
    TsetmcError,
    decode,
    digest,
    record_hash,
    validate,
)


def parsed(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def timestamp(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


class TsetmcWriter:
    def __init__(self, store: Store):
        self.store = store

    async def checkpoint(self, boundary: str) -> None:
        """No-op test seam, never a configurable production fault switch."""

    async def context(
        self, c: Any, principal: Principal, envelope: dict[str, Any], stream: str
    ) -> tuple[Any, Any, datetime]:
        producer = await c.fetchrow(
            """SELECT * FROM ingest_lock_producer($1)""", principal.producer_id
        )
        now = await c.fetchval("""SELECT clock_timestamp()""")
        if (
            not producer
            or not producer["enabled"]
            or producer["credential_key_id"] != principal.key_id
        ):
            raise TsetmcError("producer_not_authorized", 403)
        if (producer["session_id"], producer["session_generation"]) != (
            UUID(envelope["session_id"]),
            envelope["session_generation"],
        ) or producer["session_expires_at"] <= now:
            raise TsetmcError("producer_session_fenced", 409)
        owner = await c.fetchrow(
            """SELECT * FROM ingest_lock_owner($1,'tsetmc',$2)""",
            UUID(envelope["instrument_id"]),
            stream,
        )
        if not owner or (
            owner["producer_id"],
            owner["source_epoch"],
            owner["ownership_generation"],
        ) != (
            principal.producer_id,
            UUID(envelope["source_epoch"]),
            envelope["ownership_generation"],
        ):
            raise TsetmcError("source_not_authorized", 403)
        if await c.fetchval(
            """SELECT EXISTS(SELECT 1 FROM ingest_source_owners WHERE
producer_id=$1 AND stream NOT LIKE
'tsetmc_%')""",
            principal.producer_id,
        ):
            raise TsetmcError("producer_not_authorized", 403)
        link = await c.fetchrow(
            """SELECT l.*,i.payload AS instrument FROM
company_tsetmc.lock_instrument($1) l
JOIN public.instruments i ON i.id=l.instrument_id
""",
            UUID(envelope["instrument_id"]),
        )
        if not link or not link["enabled"]:
            raise TsetmcError("source_not_authorized", 403)
        return producer, link, now

    async def commit(self, principal: Principal, payload: bytes) -> dict[str, Any]:
        batch = decode(payload)
        validate(batch, "Batch")
        if batch["producer_id"] != str(principal.producer_id):
            raise TsetmcError("producer_not_authorized", 403)
        byte_hash = hashlib.sha256(payload).digest()
        async with self.store.connection() as c, c.transaction():
            await c.execute("SET LOCAL synchronous_commit=on")
            producer, link, now = await self.context(c, principal, batch, batch["stream"])
            await c.execute(
                """SELECT pg_advisory_xact_lock(hashtextextended($1,0))""",
                f"marketdata:batch:{principal.producer_id}:{batch['batch_id']}",
            )
            prior = await c.fetchrow(
                """SELECT payload_sha256,receipt FROM ingest_batches WHERE
producer_id=$1 AND batch_id=$2""",
                principal.producer_id,
                UUID(batch["batch_id"]),
            )
            if prior:
                if bytes(prior["payload_sha256"]) != byte_hash:
                    raise TsetmcError("batch_payload_conflict", 409)
                return dict(parsed(prior["receipt"]))
            # Shared observation identities are locked in the same namespace as legacy uploads.
            for oid in sorted(r["observation_id"] for r in batch["records"]):
                await c.execute(
                    """SELECT pg_advisory_xact_lock(hashtextextended($1,0))""",
                    f"marketdata:observation:{principal.producer_id}:{batch['source_epoch']}:{oid}",
                )
            await c.execute(
                """SELECT pg_advisory_xact_lock(hashtextextended($1,0))""",
                f"tsetmc:stream:{batch['instrument_id']}:{batch['stream']}",
            )
            outcomes: list[dict[str, Any]] = []
            cursor = None
            for index, record in enumerate(batch["records"]):
                try:
                    self.binding(record["observation"], link, now)
                    if record["kind"] in {"daily", "current"}:
                        allowed = await c.fetchval(
                            """SELECT 'unknown'=ANY(allowed_statuses) FROM ingest_source_owners
WHERE instrument_id=$1 AND
provider='tsetmc' AND stream=$2""",
                            UUID(batch["instrument_id"]),
                            batch["stream"],
                        )
                        if not allowed:
                            raise TsetmcError("source_status_not_authorized", 403)
                    sha = record_hash(record)
                    previous = await c.fetchrow(
                        """SELECT * FROM ingest_observations WHERE producer_id=$1 AND
source_epoch=$2
AND observation_id=$3""",
                        principal.producer_id,
                        UUID(batch["source_epoch"]),
                        UUID(record["observation_id"]),
                    )
                    canonical_updated = False
                    if previous:
                        if (
                            bytes(previous["observation_sha256"]).hex(),
                            previous["source_position"],
                            previous["stream"],
                            previous["instrument_id"],
                        ) != (
                            sha,
                            int(record["source_position"]),
                            batch["stream"],
                            UUID(batch["instrument_id"]),
                        ):
                            raise TsetmcError("observation_payload_conflict", 409)
                        outcome = "duplicate"
                    else:
                        if await c.fetchval(
                            """SELECT EXISTS(SELECT 1 FROM ingest_observations WHERE producer_id=$1
AND source_epoch=$2
AND instrument_id=$3 AND provider='tsetmc' AND stream=$4 AND
source_position=$5)""",
                            principal.producer_id,
                            UUID(batch["source_epoch"]),
                            UUID(batch["instrument_id"]),
                            batch["stream"],
                            int(record["source_position"]),
                        ):
                            raise TsetmcError("source_version_conflict", 409)
                        outcome, canonical_updated, event = await self.apply(c, batch, record, now)
                        cursor = event or cursor
                        await c.execute(
                            """INSERT INTO
ingest_observations(producer_id,source_epoch,observation_id,batch_id,

instrument_id,provider,stream,source_position,ownership_generation,observation_sha256,payload,outcome)
VALUES($1,$2,$3,$4,$5,'tsetmc',$6,$7,$8,$9,$10::jsonb,$11)""",
                            principal.producer_id,
                            UUID(batch["source_epoch"]),
                            UUID(record["observation_id"]),
                            UUID(batch["batch_id"]),
                            UUID(batch["instrument_id"]),
                            batch["stream"],
                            int(record["source_position"]),
                            batch["ownership_generation"],
                            bytes.fromhex(sha),
                            json.dumps(record),
                            outcome,
                        )
                    observation = record["observation"]
                    outcomes.append(
                        dict(
                            observation_id=record["observation_id"],
                            source_position=record["source_position"],
                            record_sha256=sha,
                            outcome=outcome,
                            stored_state_version=observation.get("state_version"),
                            stored_financial_hash=observation.get("financial_hash"),
                            canonical_updated=canonical_updated,
                        )
                    )
                except TsetmcError as error:
                    raise TsetmcError(error.code, error.status, [index]) from None
            await self.checkpoint("before_receipt")
            now = await c.fetchval("""SELECT clock_timestamp()""")
            if producer["session_expires_at"] <= now:
                raise TsetmcError("producer_session_fenced", 409)
            # SHARE locks keep revocation and handover behind this final lease check.
            result = {
                k: batch[k]
                for k in (
                    "protocol_version",
                    "contract_version",
                    "producer_id",
                    "source_epoch",
                    "batch_id",
                    "instrument_id",
                    "ownership_generation",
                    "stream",
                )
            }
            result.update(
                payload_sha256=byte_hash.hex(),
                destination_id=str(
                    await c.fetchval("""SELECT destination_id FROM ingest_destination_state""")
                ),
                state="committed",
                server_ingested_at=now.isoformat().replace("+00:00", "Z"),
                event_cursor=cursor,
                records=outcomes,
                counts={
                    outcome: sum(r["outcome"] == outcome for r in outcomes)
                    for outcome in ("applied", "recorded_no_change", "superseded", "duplicate")
                },
            )
            validate(result, "Receipt")
            await c.execute(
                """INSERT INTO
ingest_batches(producer_id,batch_id,source_epoch,stream,payload_sha256,receipt,server_ingested_at)
VALUES($1,$2,$3,$4,$5,$6::jsonb,$7)""",
                principal.producer_id,
                UUID(batch["batch_id"]),
                UUID(batch["source_epoch"]),
                batch["stream"],
                byte_hash,
                json.dumps(result),
                now,
            )
            await self.checkpoint("before_commit")
        await self.checkpoint("after_commit")
        return result

    @staticmethod
    def binding(observation: dict[str, Any], link: Any, now: datetime) -> None:
        if (
            observation["ins_code"] != link["ins_code"]
            or observation["source_instrument_id"] != link["source_instrument_id"]
        ):
            raise TsetmcError("source_identity_conflict", 409)
        if "units" in observation and observation["units"] != parsed(link["units"]):
            raise TsetmcError("source_identity_conflict", 409)

        def clocks(item: Any) -> None:
            if isinstance(item, dict):
                for key, value in item.items():
                    if (
                        key
                        in {
                            "captured_at",
                            "received_at",
                            "reviewed_at",
                            "discovered_at",
                            "source_reported_at",
                        }
                        and value
                        and datetime.fromisoformat(value) > now + timedelta(seconds=5)
                    ):
                        raise TsetmcError(
                            "source_clock_ahead"
                            if key == "source_reported_at"
                            else "collector_clock_ahead"
                        )
                    clocks(value)
            elif isinstance(item, list):
                for child in item:
                    clocks(child)

        clocks(observation)

    @staticmethod
    def fields(
        batch: dict[str, Any], record: dict[str, Any], observation: dict[str, Any]
    ) -> dict[str, Any]:
        return dict(
            instrument_id=UUID(batch["instrument_id"]),
            provider="tsetmc",
            producer_id=UUID(batch["producer_id"]),
            source_epoch=UUID(batch["source_epoch"]),
            ownership_generation=batch["ownership_generation"],
            source_position=int(record["source_position"]),
            observation_id=UUID(record["observation_id"]),
            payload=json.dumps(observation),
            state_sha256=digest(observation),
        )

    @staticmethod
    async def insert(
        c: Any, table: str, values: dict[str, Any], keys: list[str] | None = None
    ) -> None:
        columns = list(values)
        placeholders = ",".join(f"${i}" for i in range(1, len(columns) + 1))
        conflict = ""
        if keys:
            conflict = (
                " ON CONFLICT ("
                + ",".join(keys)
                + ") DO UPDATE SET "
                + ",".join(f"{n}=EXCLUDED.{n}" for n in columns if n not in keys)
                + ",server_ingested_at=clock_timestamp()"
            )
        await c.execute(
            f"""INSERT INTO company_tsetmc.{table} ({",".join(columns)})
VALUES({placeholders})"""
            + conflict,
            *values.values(),
        )

    async def revision(self, c: Any, batch: dict[str, Any], record: dict[str, Any]) -> None:
        observation = record["observation"]
        evidence = observation.get("revision_evidence")
        if not evidence:
            return
        number = int(evidence["financial_revision"])
        states = await c.fetch(
            """SELECT financial_revision,financial_hash,payload
            FROM company_tsetmc.daily_states WHERE instrument_id=$1 AND provider='tsetmc'
            AND source_epoch=$2 AND trading_date=$3
            AND financial_revision IN ($4::bigint-1,$4::bigint)""",
            UUID(batch["instrument_id"]),
            UUID(batch["source_epoch"]),
            date.fromisoformat(observation["trading_date"]),
            number,
        )
        for state in states:
            side = "new" if state["financial_revision"] == number else "old"
            if (state["financial_hash"], parsed(state["payload"])["measurements"]) != (
                evidence[side + "_financial_hash"],
                evidence[side + "_measurements"],
            ):
                raise TsetmcError("source_version_conflict", 409)
        rows = await c.fetch(
            """SELECT financial_revision,payload FROM
company_tsetmc.daily_revisions
WHERE instrument_id=$1 AND provider='tsetmc' AND source_epoch=$2 AND
trading_date=$3
AND financial_revision BETWEEN $4 AND $5""",
            UUID(batch["instrument_id"]),
            UUID(batch["source_epoch"]),
            date.fromisoformat(observation["trading_date"]),
            number - 1,
            min(2**63 - 1, number + 1),
        )
        for row in rows:
            prior = parsed(row["payload"])
            if row["financial_revision"] == number:
                if prior != evidence:
                    raise TsetmcError("source_version_conflict", 409)
                return
            older, newer = (
                (prior, evidence) if row["financial_revision"] < number else (evidence, prior)
            )
            if (
                older["new_financial_hash"] != newer["old_financial_hash"]
                or older["new_measurements"] != newer["old_measurements"]
            ):
                raise TsetmcError("source_version_conflict", 409)
        values = self.fields(batch, record, evidence)
        values.update(
            trading_date=date.fromisoformat(observation["trading_date"]), financial_revision=number
        )
        for side in ("old", "new"):
            values.update(
                {
                    side + "_" + k: Decimal(v) if v is not None else None
                    for k, v in evidence[side + "_measurements"].items()
                }
            )
        await self.insert(c, "daily_revisions", values)

    @staticmethod
    def same_context(head: Any, batch: dict[str, Any]) -> bool:
        if head is None:
            return True
        if (head["producer_id"], head["source_epoch"], head["ownership_generation"]) != (
            UUID(batch["producer_id"]),
            UUID(batch["source_epoch"]),
            batch["ownership_generation"],
        ):
            # Replacement epochs need a reviewed baseline operation beyond upload authority.
            raise TsetmcError("source_epoch_conflict", 409)
        return True

    async def event(
        self,
        c: Any,
        batch: dict[str, Any],
        record: dict[str, Any],
        kind: str,
        changed: bool | None = None,
    ) -> tuple[int, str]:
        row = await c.fetchrow(
            """UPDATE company_tsetmc.event_clock SET head=head+1 WHERE singleton
RETURNING head,epoch"""
        )
        values = self.fields(batch, record, record["observation"])
        values.update(
            id=row["head"],
            kind=kind,
            measurements_changed=changed,
            trading_date=date.fromisoformat(record["observation"]["trading_date"])
            if "trading_date" in record["observation"]
            else None,
        )
        await self.insert(c, "events", values)
        await c.execute(
            """SELECT company_tsetmc.prune_events($1)""",
            self.store.settings.tsetmc_event_retention_count,
        )
        import base64

        cursor = base64.urlsafe_b64encode(f"tsetmc1:{row['epoch']}:{row['head']}".encode()).decode()
        return int(row["head"]), cursor

    async def apply(
        self, c: Any, batch: dict[str, Any], record: dict[str, Any], now: datetime
    ) -> tuple[str, bool, str | None]:
        observation = record["observation"]
        kind = record["kind"]
        if kind in {"daily", "daily_revision"}:
            await self.revision(c, batch, record)
            if kind == "daily_revision":
                return "recorded_no_change", False, None
            return await self.daily(c, batch, record)
        table = {
            "current": "current_latest",
            "coverage": "daily_coverage",
            "status": "source_status",
        }[kind]
        if kind == "coverage":
            applied = False
            for row in observation["coverage_rows"]:
                head = await c.fetchrow(
                    """SELECT * FROM company_tsetmc.daily_coverage WHERE instrument_id=$1
AND provider='tsetmc' AND
trading_date=$2""",
                    UUID(batch["instrument_id"]),
                    date.fromisoformat(row["trading_date"]),
                )
                self.same_context(head, batch)
                if head and head["source_position"] >= int(record["source_position"]):
                    continue
                values = self.fields(batch, record, row)
                values.update(
                    trading_date=date.fromisoformat(row["trading_date"]),
                    captured_at=timestamp(observation["captured_at"]),
                )
                await self.insert(c, table, values, ["instrument_id", "provider", "trading_date"])
                applied = True
            if applied:
                _, cursor = await self.event(c, batch, record, "coverage.updated")
                return "applied", False, cursor
            return "superseded", False, None
        head = await c.fetchrow(
            f"""SELECT * FROM company_tsetmc.{table} WHERE instrument_id=$1 AND
provider='tsetmc'""",
            UUID(batch["instrument_id"]),
        )
        self.same_context(head, batch)
        if head and head["source_position"] > int(record["source_position"]):
            return "superseded", False, None
        if kind == "current":
            return await self.current(c, batch, record, head)
        if datetime.fromisoformat(observation["expires_at"]) <= now:
            return "recorded_no_change", False, None
        old = parsed(head["payload"]) if head else None
        if old and datetime.fromisoformat(observation["captured_at"]) < datetime.fromisoformat(
            old["captured_at"]
        ):
            raise TsetmcError("source_version_conflict", 409)
        values = self.fields(batch, record, observation)
        values.update(
            session_id=UUID(batch["session_id"]),
            session_generation=batch["session_generation"],
            captured_at=timestamp(observation["captured_at"]),
            expires_at=timestamp(observation["expires_at"]),
        )
        await self.insert(c, table, values, ["instrument_id", "provider"])

        def semantic(state: dict[str, Any]) -> Any:
            return {
                k: state[k]
                for k in (
                    "process_state",
                    "source_availability",
                    "latest_failure_category",
                    "open_quarantine_count",
                    "historical_revision_count",
                )
            } | {
                "session": {
                    k: state["session"][k]
                    for k in ("expectation", "confidence", "provenance_sha256")
                }
            }

        if old and semantic(old) == semantic(observation):
            return "recorded_no_change", False, None
        _, cursor = await self.event(c, batch, record, "status.updated")
        return "applied", False, cursor

    async def daily(
        self, c: Any, batch: dict[str, Any], record: dict[str, Any]
    ) -> tuple[str, bool, str | None]:
        observation = record["observation"]
        day = date.fromisoformat(observation["trading_date"])
        states = await c.fetch(
            """SELECT
state_version,source_position,financial_revision,financial_hash,payload
FROM
company_tsetmc.daily_states
WHERE instrument_id=$1 AND provider='tsetmc' AND source_epoch=$2 AND
trading_date=$3""",
            UUID(batch["instrument_id"]),
            UUID(batch["source_epoch"]),
            day,
        )
        version, revision, position = (
            int(observation["state_version"]),
            int(observation["financial_revision"]),
            int(record["source_position"]),
        )
        evidence_rows = await c.fetch(
            """SELECT financial_revision,payload FROM company_tsetmc.daily_revisions
            WHERE instrument_id=$1 AND provider='tsetmc' AND source_epoch=$2
            AND trading_date=$3 AND financial_revision BETWEEN $4::bigint AND $5::bigint""",
            UUID(batch["instrument_id"]),
            UUID(batch["source_epoch"]),
            day,
            revision,
            min(2**63 - 1, revision + 1),
        )
        for row in evidence_rows:
            evidence = parsed(row["payload"])
            side = "new" if row["financial_revision"] == revision else "old"
            if (observation["financial_hash"], observation["measurements"]) != (
                evidence[side + "_financial_hash"],
                evidence[side + "_measurements"],
            ):
                raise TsetmcError("source_version_conflict", 409)
        aliases = await c.fetch(
            """SELECT (payload->'observation'->>'state_version')::bigint AS state_version,
            min(source_position) AS first_position,max(source_position) AS last_position
            FROM public.ingest_observations WHERE instrument_id=$1 AND provider='tsetmc'
            AND source_epoch=$2 AND stream='tsetmc_daily' AND payload->>'kind'='daily'
            AND payload->'observation'->>'trading_date'=$3
            GROUP BY (payload->'observation'->>'state_version')::bigint""",
            UUID(batch["instrument_id"]),
            UUID(batch["source_epoch"]),
            day.isoformat(),
        )
        for alias in aliases:
            if (alias["state_version"] < version and alias["last_position"] >= position) or (
                alias["state_version"] > version and alias["first_position"] <= position
            ):
                raise TsetmcError("source_version_conflict", 409)
        for state in states:
            if state["state_version"] == version:
                if parsed(state["payload"]) != observation:
                    raise TsetmcError("source_version_conflict", 409)
                return "recorded_no_change", False, None
            older, newer = (
                (parsed(state["payload"]), observation)
                if state["state_version"] < version
                else (observation, parsed(state["payload"]))
            )
            if int(older["financial_revision"]) > int(newer["financial_revision"]) or (
                older["financial_revision"] == newer["financial_revision"]
                and older["financial_hash"] != newer["financial_hash"]
            ):
                raise TsetmcError("source_version_conflict", 409)
            if int(newer["financial_revision"]) == int(older["financial_revision"]) + 1:
                evidence = newer["revision_evidence"]
                if not evidence or (
                    evidence["old_financial_hash"],
                    evidence["old_measurements"],
                ) != (older["financial_hash"], older["measurements"]):
                    raise TsetmcError("source_version_conflict", 409)
        head = await c.fetchrow(
            """SELECT * FROM company_tsetmc.daily_records WHERE instrument_id=$1
AND provider='tsetmc' AND
trading_date=$2""",
            UUID(batch["instrument_id"]),
            day,
        )
        self.same_context(head, batch)
        applied = not head or version > head["state_version"]
        cursor, event_id = None, None
        if applied:
            event_id, cursor = await self.event(c, batch, record, record["event_type"])
            values = self.fields(batch, record, observation)
            values.update(
                {
                    k: Decimal(v) if v is not None else None
                    for k, v in observation["measurements"].items()
                }
            )
            values.update(
                trading_date=day,
                financial_revision=revision,
                state_version=version,
                **{
                    k: observation[k]
                    for k in (
                        "financial_hash",
                        "acceptance",
                        "upstream_finality",
                        "local_finalization",
                        "publication_state",
                    )
                },
            )
            await self.insert(
                c, "daily_records", values, ["instrument_id", "provider", "trading_date"]
            )
        values = self.fields(batch, record, observation)
        values.update(
            trading_date=day,
            financial_revision=revision,
            state_version=version,
            financial_hash=observation["financial_hash"],
            became_canonical=applied,
            published_event_id=event_id,
        )
        await self.insert(c, "daily_states", values)
        return ("applied" if applied else "superseded"), applied, cursor

    async def current(
        self, c: Any, batch: dict[str, Any], record: dict[str, Any], head: Any
    ) -> tuple[str, bool, str | None]:
        observation = record["observation"]
        old = parsed(head["payload"]) if head else None
        if old:
            same = old["financial_hash"] == observation["financial_hash"]
            old_day, day = old["source_date"], observation["source_date"]
            old_time, clock = old["source_time"], observation["source_time"]
            if old_day and day and day != old_day:
                permitted = day > old_day
            elif None in (old_day, day, old_time, clock):
                permitted = (
                    same and day is not None and clock is not None and old_day in (None, day)
                )
            elif old_time != clock:
                permitted = clock > old_time
            else:
                permitted = same or (
                    observation["accepted_decision"] == "explicit_same_time_correction"
                    and bool(observation["correction_reason_sha256"])
                )
            if not permitted:
                raise TsetmcError("current_source_regression", 409)
        changed = old is None or old["measurements"] != observation["measurements"]
        financial_changed = old is None or old["financial_hash"] != observation["financial_hash"]
        values = self.fields(batch, record, observation)
        values.update(
            {
                k: Decimal(v) if v is not None else None
                for k, v in observation["measurements"].items()
            }
        )
        values.update(
            state_version=int(observation["state_version"]),
            financial_hash=observation["financial_hash"],
            source_date=date.fromisoformat(observation["source_date"])
            if observation["source_date"]
            else None,
            source_time=datetime.strptime(observation["source_time"], "%H:%M:%S").time()
            if observation["source_time"]
            else None,
            source_reported_at=timestamp(observation["source_reported_at"]),
            received_at=timestamp(observation["source"]["received_at"]),
        )
        await self.insert(c, "current_latest", values, ["instrument_id", "provider"])
        event = (
            record["event_type"]
            if record["event_type"] != "current.updated"
            else ("current.updated" if financial_changed else "current.position_updated")
        )
        _, cursor = await self.event(c, batch, record, event, changed)
        return "applied", True, cursor
