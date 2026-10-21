"""Bounded database-only Iranian equity reads on the shared company application."""

import asyncio
import json
from datetime import UTC, date, datetime
from typing import Annotated, Any, Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.routing import APIRoute

from marketdata.config import Settings
from marketdata.persistence import Store
from marketdata.tsetmc.cursors import cursor, position

Code = Annotated[str, Query(pattern=r"^[0-9]{1,20}$")]
Limit = Annotated[int, Query(ge=1, le=1000)]
Selection = Literal["finalized", "accepted-unverified"]


def freshness(o: dict[str, Any], now: datetime) -> dict[str, Any]:
    source = o.get("source_reported_at")
    received = o["source"]["received_at"]
    age = (now - datetime.fromisoformat(source)).total_seconds() if source else None
    return dict(
        observation=o,
        source_age_seconds=age,
        receipt_age_seconds=(now - datetime.fromisoformat(received)).total_seconds(),
        freshness="unknown" if age is None else "fresh" if 0 <= age <= 120 else "stale",
        delivery_status="unknown",
        realtime_quote_available=False,
    )


async def snapshot(store: Store, code: str) -> dict[str, Any]:
    async with store.connection() as c, c.transaction(isolation="repeatable_read", readonly=True):
        clock = await c.fetchrow("SELECT * FROM company_tsetmc.event_clock")
        rows = await c.fetch(
            """SELECT h.stream,h.payload FROM (
          SELECT instrument_id,payload,'tsetmc_current' AS stream
          FROM company_tsetmc.current_latest UNION ALL
          SELECT instrument_id,payload,'tsetmc_status' AS stream
          FROM company_tsetmc.source_status) h
          JOIN instruments i ON i.id=h.instrument_id WHERE i.canonical_symbol=$1
          AND h.stream IN ('tsetmc_current','tsetmc_status')""",
            "TSETMC:" + code,
        )
        now = datetime.now(UTC)
        items = {r["stream"]: json.loads(r["payload"]) for r in rows}
        current = items.get("tsetmc_current")
        status = items.get("tsetmc_status")
        return dict(
            type="snapshot",
            contract_version="tsetmc.v1",
            cursor=cursor(clock["epoch"], clock["head"]),
            current=freshness(current, now) if current else None,
            status=status,
            status_expired=status is None or datetime.fromisoformat(status["expires_at"]) <= now,
            server_timestamp=now.isoformat(),
        )


async def changes(store: Store, token: str, code: str, limit: int) -> dict[str, Any]:
    async with store.connection() as c, c.transaction(isolation="repeatable_read", readonly=True):
        clock = await c.fetchrow("SELECT * FROM company_tsetmc.event_clock")
        after = position(token, clock["epoch"])
        if after > clock["head"] or after < clock["floor"]:
            raise ValueError("resync_required")
        rows = await c.fetch(
            """SELECT e.* FROM company_tsetmc.events e JOIN instruments i
          ON i.id=e.instrument_id WHERE e.id>$1 AND i.canonical_symbol=$2 ORDER BY e.id LIMIT $3""",
            after,
            "TSETMC:" + code,
            limit + 1,
        )
        more = len(rows) > limit
        rows = rows[:limit]
        return dict(
            items=[
                dict(
                    event_id=str(r["id"]),
                    cursor=cursor(clock["epoch"], r["id"]),
                    type=r["kind"],
                    observation=json.loads(r["payload"]),
                )
                for r in rows
            ],
            cursor=cursor(clock["epoch"], rows[-1]["id"] if more else clock["head"]),
            has_more=more,
        )


def router(settings: Settings) -> APIRouter:
    result = APIRouter(tags=["Iranian equity tsetmc.v1"])
    clients = 0

    def page_capacity(limit: Limit = 100) -> int:
        if limit > settings.api_max_rows:
            raise HTTPException(422, "page capacity exceeded")
        return limit

    PageLimit = Annotated[int, Depends(page_capacity)]

    @result.get("/api/v1/tsetmc/instruments")
    async def instruments(request: Request, limit: PageLimit, after: Code = "0") -> dict[str, Any]:
        async with request.app.state.store.connection() as c:
            rows = await c.fetch(
                "SELECT l.ins_code,i.display_name,i.exchange,l.enabled FROM "
                "company_tsetmc.instrument_links l JOIN instruments i ON i.id=l.instrument_id "
                "WHERE l.ins_code>$1 ORDER BY l.ins_code LIMIT $2",
                after,
                limit + 1,
            )
        return dict(
            items=[
                dict(
                    canonical_symbol="TSETMC:" + r["ins_code"],
                    provider="tsetmc",
                    provider_symbol=r["ins_code"],
                    display_name=r["display_name"],
                    exchange=r["exchange"],
                    active=r["enabled"],
                    asset_class="equity",
                    instrument_type="common_stock",
                    supported_historical_intervals=["1d"],
                    realtime_status="unknown",
                )
                for r in rows[:limit]
            ],
            next_after=rows[limit - 1]["ins_code"] if len(rows) > limit else None,
        )

    @result.get("/api/v1/tsetmc/latest")
    async def latest(request: Request, ins_code: Code) -> dict[str, Any]:
        return await snapshot(request.app.state.store, ins_code)

    @result.get("/api/v1/tsetmc/daily")
    async def daily(
        request: Request,
        ins_code: Code,
        start: date,
        end: date,
        limit: PageLimit,
        selection: Selection = "finalized",
        after: date | None = None,
    ) -> dict[str, Any]:
        """Inclusive start, exclusive end. Midnight date labels are not trading instants."""
        if end <= start or (end - start).days > 36600:
            raise HTTPException(422, "invalid date range (maximum 100 years)")
        store: Store = request.app.state.store
        async with (
            store.connection() as c,
            c.transaction(isolation="repeatable_read", readonly=True),
        ):
            clock = await c.fetchrow("SELECT * FROM company_tsetmc.event_clock")
            rows = await c.fetch(
                """SELECT h.payload FROM company_tsetmc.daily_records h JOIN instruments i ON
                  i.id=h.instrument_id
              WHERE i.canonical_symbol=$1 AND h.trading_date::text >= $2 AND
                h.trading_date::text < $3
              AND ($4::text IS NULL OR h.trading_date::text>$4)
              AND ($5 OR h.payload->>'local_finalization'='operator_finalized') ORDER BY
                h.trading_date LIMIT $6""",
                "TSETMC:" + ins_code,
                start.isoformat(),
                end.isoformat(),
                after.isoformat() if after else None,
                selection == "accepted-unverified",
                limit + 1,
            )
            items = [json.loads(r["payload"]) for r in rows[:limit]]
        return dict(
            contract_version="tsetmc.v1",
            items=items,
            next_after=items[-1]["trading_date"] if len(rows) > limit else None,
            snapshot_cursor=cursor(clock["epoch"], clock["head"]),
            selection=selection,
            upstream_finality="unverified",
        )

    @result.get("/api/v1/tsetmc/coverage")
    async def coverage(
        request: Request, ins_code: Code, limit: PageLimit, after: str = ""
    ) -> dict[str, Any]:
        if len(after) > 10:
            raise HTTPException(422, "invalid coverage cursor")
        async with request.app.state.store.connection() as c:
            rows = await c.fetch(
                """SELECT h.trading_date::text AS entity,h.payload
          FROM company_tsetmc.daily_coverage h
          JOIN instruments i ON
                  i.id=h.instrument_id
              WHERE i.canonical_symbol=$1 AND h.trading_date::text>$2 ORDER
                BY h.trading_date LIMIT $3""",
                "TSETMC:" + ins_code,
                after,
                limit + 1,
            )
        return dict(
            items=[json.loads(r["payload"]) for r in rows[:limit]],
            next_after=rows[limit - 1]["entity"] if len(rows) > limit else None,
            absent_dates="unknown",
            archive_completeness="unproven",
        )

    @result.get("/api/v1/tsetmc/changes")
    async def events(
        request: Request,
        ins_code: Code,
        after: Annotated[str, Query(max_length=200)],
        limit: PageLimit,
    ) -> dict[str, Any]:
        try:
            return await changes(request.app.state.store, after, ins_code, limit)
        except ValueError:
            raise HTTPException(409, "resync_required") from None

    @result.websocket("/api/v1/ws/tsetmc")
    async def socket(
        ws: WebSocket, ins_code: Code, after: Annotated[str | None, Query(max_length=200)] = None
    ) -> None:
        from marketdata.api import authorized

        nonlocal clients
        if (
            not authorized(ws.headers.get("authorization"), settings)
            or ws.headers.get("origin") not in settings.websocket_allowed_origins
        ):
            await ws.close(code=1008)
            return
        if clients >= settings.websocket_max_clients:
            await ws.close(code=1013)
            return
        clients += 1
        try:
            await ws.accept()

            async def send(value: Any) -> None:
                async with asyncio.timeout(settings.websocket_send_timeout_seconds):
                    await ws.send_json(value)

            store: Store = ws.app.state.store
            if after is None:
                initial = await snapshot(store, ins_code)
                await send(initial)
                after = initial["cursor"]
            while True:
                assert after is not None
                page = await changes(
                    store, after, ins_code, min(100, settings.marketdata_event_batch_size)
                )
                await send(
                    dict(
                        type="changes" if page["items"] else "heartbeat",
                        contract_version="tsetmc.v1",
                        **page,
                    )
                )
                after = page["cursor"]
                if not page["has_more"]:
                    await asyncio.sleep(settings.marketdata_poll_seconds)
        except (WebSocketDisconnect, OSError):
            pass
        except ValueError:
            await ws.close(code=1008, reason="resync_required")
        except Exception:
            await ws.close(code=1013, reason="retry with last received cursor")
        finally:
            clients -= 1

    for route in result.routes:
        if isinstance(route, APIRoute):
            route.openapi_extra = {"security": [{"CompanyBearer": []}]}
    return result
