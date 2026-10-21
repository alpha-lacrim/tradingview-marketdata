"""Atomic tsetmc.v1 destination writes using the company's existing producer fences."""

import base64
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from marketdata.ingest_auth import Principal
from marketdata.persistence import Store
from marketdata.replication import ReplicationError
from marketdata.tsetmc.wire import decode, record_sha, validate


def cursor(epoch: Any, position: int) -> str:
    return base64.urlsafe_b64encode(f"tsetmc1:{epoch}:{position}".encode()).decode()


def position(token: str, epoch: Any) -> int:
    try:
        prefix, namespace, number = (
            base64.b64decode(token, altchars=b"-_", validate=True).decode().split(":")
        )
        if prefix != "tsetmc1" or namespace != str(epoch) or not number.isdigit():
            raise ValueError()
        return int(number)
    except (ValueError, UnicodeError):
        raise ValueError("resync_required") from None


def ordered(old: dict[str, Any], new: dict[str, Any], kind: str) -> None:
    if kind == "daily":
        if int(new["state_version"]) <= int(old["state_version"]):
            raise ReplicationError("source_version_conflict")
        previous, revision = int(old["financial_revision"]), int(new["financial_revision"])
        if revision < previous or (
            revision == previous and new["financial_hash"] != old["financial_hash"]
        ):
            raise ReplicationError("source_version_conflict")
        if new["financial_hash"] != old["financial_hash"]:
            proof = new["revision_evidence"]
            if (
                not proof
                or proof["old_financial_hash"] != old["financial_hash"]
                or revision != previous + 1
            ):
                raise ReplicationError("source_version_conflict")
            if new["local_finalization"] != "source_unverified":
                raise ReplicationError("source_version_conflict")
    elif kind == "current":
        before, after = old.get("source_reported_at"), new.get("source_reported_at")
        if before and (not after or datetime.fromisoformat(after) < datetime.fromisoformat(before)):
            raise ReplicationError("source_version_conflict")
        if (
            not before
            or not after
            or datetime.fromisoformat(before) == datetime.fromisoformat(after)
        ) and old["financial_hash"] != new["financial_hash"]:
            if (
                new["accepted_decision"] != "explicit_same_time_correction"
                or not new["correction_reason_sha256"]
            ):
                raise ReplicationError("source_version_conflict")


class Writer:
    def __init__(self, store: Store):
        self.store = store

    async def commit(self, principal: Principal, raw: bytes) -> dict[str, Any]:
        batch = decode(raw)
        validate(batch, "Batch")
        if batch["producer_id"] != str(principal.producer_id):
            raise ReplicationError("producer_not_authorized")
        producer_id, epoch, batch_id, instrument = (
            UUID(batch[k]) for k in ("producer_id", "source_epoch", "batch_id", "instrument_id")
        )
        digest = hashlib.sha256(raw).digest()
        async with self.store.connection() as c, c.transaction():
            await c.execute("SET LOCAL synchronous_commit=on")
            producer = await c.fetchrow("SELECT * FROM ingest_lock_producer($1)", producer_id)
            now = await c.fetchval("SELECT clock_timestamp()")
            if (
                not producer
                or not producer["enabled"]
                or producer["credential_key_id"] != principal.key_id
            ):
                raise ReplicationError("producer_not_authorized")
            if (str(producer["session_id"]), producer["session_generation"]) != (
                batch["session_id"],
                batch["session_generation"],
            ) or producer["session_expires_at"] <= now:
                raise ReplicationError("producer_session_fenced")
            await c.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
                f"marketdata:batch:{producer_id}:{batch_id}",
            )
            previous = await c.fetchrow(
                "SELECT payload_sha256,receipt FROM ingest_batches WHERE producer_id=$1 "
                "AND batch_id=$2",
                producer_id,
                batch_id,
            )
            if previous:
                if previous["payload_sha256"] != digest:
                    raise ReplicationError("batch_payload_conflict")
                return dict(json.loads(previous["receipt"]))
            owner = await c.fetchrow(
                "SELECT * FROM ingest_lock_owner($1,'tsetmc',$2)", instrument, batch["stream"]
            )
            if (
                not owner
                or (owner["producer_id"], owner["source_epoch"], owner["ownership_generation"])
                != (producer_id, epoch, batch["ownership_generation"])
                or "unknown" not in owner["allowed_statuses"]
            ):
                raise ReplicationError("source_not_authorized")
            source = await c.fetchrow(
                """SELECT i.canonical_symbol,i.asset_class,i.instrument_type,p.provider_symbol
              FROM instruments i JOIN provider_instruments p ON p.instrument_id=i.id
              WHERE i.id=$1 AND p.provider='tsetmc'""",
                instrument,
            )
            if (
                not source
                or source["asset_class"] != "equity"
                or source["instrument_type"] != "common_stock"
            ):
                raise ReplicationError("source_identity_conflict")
            await c.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended($1,0))", "tsetmc:" + str(instrument)
            )
            results = []
            for record in sorted(batch["records"], key=lambda r: int(r["source_position"])):
                observation, oid, seq = (
                    record["observation"],
                    UUID(record["observation_id"]),
                    int(record["source_position"]),
                )
                if (
                    observation["canonical_symbol"] != source["canonical_symbol"]
                    or observation["provider_symbol"] != source["provider_symbol"]
                ):
                    raise ReplicationError("source_identity_conflict")
                for stamp in (
                    observation.get("source", {}).get("received_at"),
                    observation.get("captured_at"),
                    observation.get("source_reported_at"),
                ):
                    if stamp and datetime.fromisoformat(stamp) > now + timedelta(seconds=60):
                        raise ReplicationError("source_clock_ahead")
                sha = bytes.fromhex(record_sha(record))
                prior = await c.fetchrow(
                    "SELECT observation_sha256,source_position FROM ingest_observations "
                    "WHERE producer_id=$1 AND source_epoch=$2 AND observation_id=$3",
                    producer_id,
                    epoch,
                    oid,
                )
                changed = False
                if prior:
                    if (prior["observation_sha256"], prior["source_position"]) != (sha, seq):
                        raise ReplicationError("observation_payload_conflict")
                    outcome = "duplicate"
                else:
                    changed = await self.apply(c, batch, record)
                    outcome = "applied" if changed else "recorded_no_change"
                    await c.execute(
                        """INSERT INTO ingest_observations
                      (producer_id,source_epoch,observation_id,batch_id,instrument_id,
                       provider,stream,
                       source_position,ownership_generation,observation_sha256,payload,outcome)
                      VALUES($1,$2,$3,$4,$5,'tsetmc',$6,$7,$8,$9,$10,$11)""",
                        producer_id,
                        epoch,
                        oid,
                        batch_id,
                        instrument,
                        batch["stream"],
                        seq,
                        batch["ownership_generation"],
                        sha,
                        json.dumps(record),
                        outcome,
                    )
                results.append(
                    dict(
                        observation_id=str(oid),
                        source_position=str(seq),
                        record_sha256=sha.hex(),
                        outcome=outcome,
                        canonical_updated=changed,
                        stored_state_version=observation.get("state_version"),
                        stored_financial_hash=observation.get("financial_hash"),
                    )
                )
            clock = await c.fetchrow("SELECT * FROM company_tsetmc.clock")
            destination = await c.fetchval("SELECT destination_id FROM ingest_destination_state")
            if producer["session_expires_at"] <= await c.fetchval("SELECT clock_timestamp()"):
                raise ReplicationError("producer_session_fenced")
            receipt = {
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
            receipt.update(
                destination_id=str(destination),
                payload_sha256=digest.hex(),
                state="committed",
                server_ingested_at=now.isoformat().replace("+00:00", "Z"),
                event_cursor=cursor(clock["epoch"], clock["head"]),
                records=results,
                counts={
                    name: sum(r["outcome"] == name for r in results)
                    for name in ("applied", "recorded_no_change", "superseded", "duplicate")
                },
            )
            validate(receipt, "Receipt")
            await c.execute(
                "INSERT INTO ingest_batches "
                "(producer_id,batch_id,source_epoch,stream,payload_sha256,receipt) "
                "VALUES($1,$2,$3,$4,$5,$6)",
                producer_id,
                batch_id,
                epoch,
                batch["stream"],
                digest,
                json.dumps(receipt),
            )
        return receipt

    async def apply(self, c: Any, batch: dict[str, Any], record: dict[str, Any]) -> bool:
        o, kind = record["observation"], record["kind"]
        # Revision seeds are retained in the immutable shared ledger only.
        if record["event_type"] == "daily.revision_seed":
            return False
        entities = [(o["trading_date"], o)] if kind == "daily" else [("latest", o)]
        if kind == "coverage":
            entities = [
                (day["trading_date"], {**o, "coverage_rows": [day]}) for day in o["coverage_rows"]
            ]
        changed = False
        for entity, payload in entities:
            old = await c.fetchrow(
                "SELECT * FROM company_tsetmc.heads WHERE instrument_id=$1 AND stream=$2 "
                "AND entity=$3 FOR UPDATE",
                UUID(batch["instrument_id"]),
                batch["stream"],
                entity,
            )
            if old:
                # Handover needs reviewed reconciliation, never automatic epoch replacement.
                if (
                    str(old["source_epoch"]),
                    str(old["producer_id"]),
                    old["ownership_generation"],
                ) != (batch["source_epoch"], batch["producer_id"], batch["ownership_generation"]):
                    raise ReplicationError("source_version_conflict")
                if int(record["source_position"]) <= old["source_position"]:
                    raise ReplicationError("source_version_conflict")
                ordered(json.loads(old["payload"]), payload, kind)
            await c.execute(
                """INSERT INTO company_tsetmc.heads VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)
              ON CONFLICT(instrument_id,stream,entity) DO UPDATE SET
                source_position=EXCLUDED.source_position,
              observation_id=EXCLUDED.observation_id,payload=EXCLUDED.payload""",
                UUID(batch["instrument_id"]),
                batch["stream"],
                entity,
                UUID(batch["producer_id"]),
                UUID(batch["source_epoch"]),
                batch["ownership_generation"],
                int(record["source_position"]),
                UUID(record["observation_id"]),
                json.dumps(payload),
            )
            changed = True
        if changed:
            event_id = await c.fetchval(
                "UPDATE company_tsetmc.clock SET head=head+1 RETURNING head"
            )
            await c.execute(
                "INSERT INTO company_tsetmc.events(id,instrument_id,stream,event_type,payload) "
                "VALUES($1,$2,$3,$4,$5)",
                event_id,
                UUID(batch["instrument_id"]),
                batch["stream"],
                record["event_type"],
                json.dumps(o),
            )
        return changed
