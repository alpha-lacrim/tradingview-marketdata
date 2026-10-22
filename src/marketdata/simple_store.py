"""One PostgreSQL database, atomic uploads, retry receipts and correction history."""

import hashlib
import json
from importlib.resources import files
from typing import Any

import asyncpg

from marketdata.simple_models import Batch

UPSERT = """
INSERT INTO simple_marketdata.records AS old(market,symbol,interval,time,received_at,data)
VALUES($1,$2,$3,$4,$5,$6::jsonb)
ON CONFLICT(market,symbol,interval,time) DO UPDATE
SET received_at=excluded.received_at, data=excluded.data, stored_at=clock_timestamp()
WHERE excluded.received_at > old.received_at
AND (excluded.interval <> 'quote' OR excluded.data->>'event_at' IS NULL
     OR old.data->>'event_at' IS NULL
     OR (excluded.data->>'event_at')::timestamptz >= (old.data->>'event_at')::timestamptz)
"""


async def initialize(url: str) -> None:
    conn = await asyncpg.connect(url)
    try:
        async with conn.transaction():
            # Initialization is explicit and refuses legacy storage, including source databases.
            legacy = await conn.fetchval("""SELECT EXISTS(SELECT FROM information_schema.tables
                WHERE table_schema='public' AND table_name IN
                ('alembic_version','instruments','daily_observations','sync_dataset'))""")
            if legacy:
                raise ValueError("use a new empty database for the native profile")
            await conn.execute(files("marketdata").joinpath("simple_schema.sql").read_text())
    finally:
        await conn.close()


class SimpleStore:
    def __init__(self, url: str):
        self.url = url
        self.pool: asyncpg.Pool[Any] | None = None

    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(self.url, min_size=1, max_size=10, command_timeout=30)
        if await self.pool.fetchval("SELECT version FROM simple_marketdata.version") != 1:
            raise RuntimeError("run marketdata-simple init for this database")

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()

    async def ingest(self, batch: Batch, raw: bytes) -> dict[str, Any]:
        assert self.pool is not None
        digest = hashlib.sha256(raw).hexdigest()
        async with self.pool.acquire() as conn, conn.transaction():
            # One transaction order also makes WebSocket change IDs safe replay cursors.
            await conn.execute("SELECT pg_advisory_xact_lock(18617432,1)")
            existing = await conn.fetchrow(
                "SELECT * FROM simple_marketdata.receipts WHERE batch_id=$1", batch.batch_id
            )
            if existing:
                if existing["sha256"] != digest:
                    raise ValueError("batch_id already used for different bytes")
            else:
                values = []
                for o in batch.observations:
                    data = o.model_dump(
                        mode="json", exclude={"market", "symbol", "interval", "time", "received_at"}
                    )
                    values.append(
                        (
                            o.market,
                            o.symbol,
                            o.interval,
                            o.time,
                            o.received_at,
                            json.dumps(data, allow_nan=False),
                        )
                    )
                await conn.executemany(UPSERT, values)
                await conn.execute(
                    "INSERT INTO simple_marketdata.receipts VALUES($1,$2,$3,DEFAULT)",
                    batch.batch_id,
                    digest,
                    len(values),
                )
        return {
            "batch_id": str(batch.batch_id),
            "sha256": digest,
            "accepted": len(batch.observations),
        }

    async def rows(
        self, market: str, symbol: str, interval: str, start: int, end: int, limit: int
    ) -> list[dict[str, Any]]:
        assert self.pool is not None
        records = await self.pool.fetch(
            """SELECT * FROM simple_marketdata.records
            WHERE market=$1 AND symbol=$2 AND interval=$3 AND time >= $4 AND time < $5
            ORDER BY time LIMIT $6""",
            market,
            symbol,
            interval,
            start,
            end,
            limit,
        )
        return [unpack(r) for r in records]

    async def changes(self, after: int, market: str, symbol: str) -> list[dict[str, Any]]:
        assert self.pool is not None
        rows = await self.pool.fetch(
            """SELECT id,market,symbol,interval,time,received_at,
            stored_at,data FROM simple_marketdata.changes WHERE id>$1 AND market=$2 AND symbol=$3
            ORDER BY id LIMIT 500""",
            after,
            market,
            symbol,
        )
        return [unpack(r) for r in rows]


def unpack(row: Any) -> dict[str, Any]:
    result = dict(row)
    result["data"] = json.loads(result["data"])
    for key in ("received_at", "stored_at"):
        result[key] = result[key].isoformat()
    return result
