"""Native dashboard service: one URL, one PostgreSQL database, optional upload token."""

import asyncio
import hmac
import logging
import os
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any

import asyncpg
from fastapi import FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from marketdata.simple_models import Batch, Market, float64
from marketdata.simple_store import SimpleStore

logger = logging.getLogger(__name__)

STEPS = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "1d": 86400}
Symbol = Annotated[str, Query(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_:.-]+$")]


def chart(rows: list[dict[str, Any]], step: int) -> tuple[dict[str, Any], int, int]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    missing = 0
    for row in rows:
        if any(row["data"][field] is None for field in ("open", "close", "high", "low")):
            missing += 1
            continue
        grouped[row["time"] // step * step].append(row["data"])
    output: dict[str, Any] = {key: [] for key in "abcdefgh"}
    output["i"] = None
    placeholders = 0
    for stamp, items in sorted(grouped.items()):
        values: list[Any] = [
            stamp,
            items[0]["open"],
            items[-1]["close"],
            max(Decimal(i["high"]) for i in items),
            min(Decimal(i["low"]) for i in items),
        ]
        for field in ("count", "volume", "value"):
            if any(i[field] is None for i in items):
                values.append(0)
                placeholders += 1
            else:
                values.append(sum(Decimal(str(i[field])) for i in items))
        for key, value in zip("abcdefgh", values, strict=True):
            if key in "af":
                if not 0 <= int(value) <= 2**63 - 1:
                    raise ValueError("dashboard count exceeds int64")
                output[key].append(int(value))
            else:
                output[key].append(float64(value))
    return output, missing, placeholders


def create_app(database_url: str | None = None, *, store: SimpleStore | None = None) -> FastAPI:
    url = database_url or os.environ.get("DATABASE_URL", "")
    if not url and store is None:
        raise ValueError("set DATABASE_URL to the company PostgreSQL database")
    db = store or SimpleStore(url)
    token = os.environ.get("SIMPLE_UPLOAD_TOKEN", "")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            await db.connect()
            yield
        finally:
            await db.close()

    app = FastAPI(title="Company market data", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Missing-OHLC", "X-Zero-Placeholders"],
    )
    app.state.store = db

    @app.exception_handler(TimeoutError)
    @app.exception_handler(OSError)
    @app.exception_handler(asyncpg.InterfaceError)
    @app.exception_handler(asyncpg.PostgresError)
    async def database_error(request: Request, error: Exception) -> JSONResponse:
        logger.warning(
            "database operation failed: %s path=%s", type(error).__name__, request.url.path
        )
        return JSONResponse(
            {"detail": "database unavailable"}, status_code=503, headers={"Retry-After": "30"}
        )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        assert db.pool is not None
        async with db.connection() as conn:
            await conn.fetchval("SELECT 1")
        return {"ok": True, "profile": "native", "upload_token_required": bool(token)}

    batch_schema = Batch.model_json_schema(ref_template="#/components/schemas/{model}")
    definitions = batch_schema.pop("$defs", {})

    @app.post(
        "/api/ingest",
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": batch_schema}},
            }
        },
    )
    async def ingest(request: Request) -> dict[str, Any]:
        if token and not hmac.compare_digest(
            request.headers.get("authorization", "").encode(), ("Bearer " + token).encode()
        ):
            raise HTTPException(401, "upload token required")
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 16 * 1024 * 1024:
                raise HTTPException(413, "upload exceeds 16 MiB; use smaller batches")
        try:
            batch = Batch.model_validate_json(body)
        except ValidationError:
            raise HTTPException(422, "invalid observation batch; see /docs") from None
        try:
            return await db.ingest(batch, bytes(body))
        except ValueError as error:
            raise HTTPException(409, str(error)) from None

    @app.get("/api/instruments")
    async def instruments() -> list[dict[str, Any]]:
        assert db.pool is not None
        async with db.connection() as conn:
            rows = await conn.fetch("""SELECT market,symbol,
                array_agg(DISTINCT interval) AS intervals,
                max(received_at) AS last_received_at
                FROM simple_marketdata.records
                GROUP BY market,symbol ORDER BY market,symbol LIMIT 1000""")
        return [dict(r) for r in rows]

    async def latest_row(market: str, symbol: str) -> dict[str, Any]:
        rows = await db.rows(market, symbol, "quote", 0, 1, 1)
        if not rows:
            raise HTTPException(404, "no quote received for this source")
        row = rows[0]
        now = datetime.now(UTC)
        event = row["data"].get("event_at")
        row["receive_age_seconds"] = max(
            0.0, (now - datetime.fromisoformat(row["received_at"])).total_seconds()
        )
        row["source_age_seconds"] = (
            (now - datetime.fromisoformat(event)).total_seconds() if event else None
        )
        return row

    @app.get("/api/latest")
    async def latest(market: Market, symbol: Symbol) -> dict[str, Any]:
        return await latest_row(market, symbol)

    @app.get("/api/chart")
    async def history(
        response: Response,
        market: Market,
        symbol: Symbol,
        interval: str | None = None,
        start: int | None = None,
        end: int | None = None,
    ) -> dict[str, Any]:
        interval = interval or ("1d" if market == "tsetmc" else "1m")
        if interval not in STEPS or (market == "tsetmc" and interval != "1d"):
            raise HTTPException(422, "supported intervals: TradingView 1m/5m/15m/1h/1d; TSETMC 1d")
        now = datetime.now(UTC)
        end = end if end is not None else int(now.timestamp()) + 1
        start = start if start is not None else int((now - timedelta(days=30)).timestamp())
        if not 0 <= start < end <= 32503680000:
            raise HTTPException(422, "use start < end in Unix seconds (end exclusive)")
        native = "1d" if market == "tsetmc" else "1m"
        rows = await db.rows(market, symbol, native, start, end, 100001)
        if len(rows) > 100000:
            raise HTTPException(413, "range exceeds 100000 native bars; request a shorter range")
        try:
            result, missing, placeholders = chart(rows, STEPS[interval])
        except ValueError:
            raise HTTPException(
                422, "stored values cannot be represented by dashboard float64/int64"
            ) from None
        response.headers["X-Missing-OHLC"] = str(missing)
        response.headers["X-Zero-Placeholders"] = str(placeholders)
        return result

    @app.get("/api/records")
    async def records(
        market: Market,
        symbol: Symbol,
        interval: str,
        start: int = 0,
        end: int = 32503680000,
        limit: int = Query(1000, ge=1, le=5000),
    ) -> dict[str, Any]:
        if interval not in {"1m", "1d", "quote"} or not 0 <= start < end:
            raise HTTPException(422, "invalid native interval or range")
        rows = await db.rows(market, symbol, interval, start, end, limit + 1)
        return {
            "items": rows[:limit],
            "next_start": rows[limit]["time"] if len(rows) > limit else None,
        }

    @app.get("/api/changes")
    async def changes(
        market: Market, symbol: Symbol, after: int = Query(0, ge=0)
    ) -> dict[str, Any]:
        rows = await db.changes(after, market, symbol)
        return {"items": rows, "cursor": rows[-1]["id"] if rows else after}

    @app.websocket("/api/ws")
    async def websocket(
        ws: WebSocket, market: Market, symbol: str, after: int | None = None
    ) -> None:
        if len(symbol) > 100 or (after is not None and after < 0):
            await ws.close(code=1008)
            return
        await ws.accept()
        assert db.pool is not None
        try:
            async with db.connection() as conn:
                cursor = (
                    after
                    if after is not None
                    else int(
                        await conn.fetchval(
                            "SELECT coalesce(max(id),0) FROM simple_marketdata.changes"
                        )
                    )
                )
            try:
                snapshot = await latest_row(market, symbol)
            except HTTPException:
                snapshot = None
            async with asyncio.timeout(10):
                await ws.send_json({"type": "snapshot", "latest": snapshot, "cursor": cursor})
            while True:
                rows = await db.changes(cursor, market, symbol)
                cursor = rows[-1]["id"] if rows else cursor
                async with asyncio.timeout(10):
                    await ws.send_json({"type": "changes", "items": rows, "cursor": cursor})
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            return
        except (TimeoutError, OSError, asyncpg.PostgresError, asyncpg.InterfaceError):
            try:
                async with asyncio.timeout(5):
                    await ws.close(code=1013, reason="temporarily unavailable; reconnect")
            except (WebSocketDisconnect, TimeoutError, OSError):
                pass

    app.openapi()["components"]["schemas"].update(definitions)
    return app
