"""Synthetic Iranian observations through the existing authenticated company backend."""

import asyncio
import copy
import hashlib
import json
from pathlib import Path
from uuid import uuid4, uuid5

import httpx
import pytest
from test_destination_ingestion import destination  # noqa: F401
from test_ingest_http import ingress  # noqa: F401
from test_market_stream import HEADERS, ORIGIN, server, ws_url
from websockets.asyncio.client import connect

from marketdata.domain import Instrument, ProviderInstrument, RegistryEntry
from marketdata.registry import Registry
from marketdata.tsetmc.ingest import router
from marketdata.tsetmc.wire import decode, encode, financial_hash, validate
from marketdata.tsetmc.writer import ordered

FIXTURES = Path(__file__).parent / "fixtures/tsetmc"


def test_optional_routes_advertise_existing_company_authentication():
    from marketdata.api import create_app
    from marketdata.config import Settings
    from marketdata.ingest_api import create_app as create_ingest

    settings = Settings(_env_file=None, company_tsetmc_enabled=True)
    read = create_app(settings).openapi()
    assert read["paths"]["/api/v1/tsetmc/latest"]["get"]["security"] == [{"CompanyBearer": []}]
    ingest = create_ingest(settings.model_copy(update={"application_role": "ingest"})).openapi()
    assert ingest["paths"]["/api/ingest/v1/tsetmc/batches"]["post"]["security"] == [
        {"ProducerBearer": []}
    ]


def fixture(name):
    return decode((FIXTURES / (name + ".json")).read_bytes())


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.json")), ids=lambda p: p.stem)
def test_reviewed_wire_examples(path):
    validate(decode(path.read_bytes()), "Batch")


def test_current_cannot_become_fresh_by_receipt_or_replace_newer_source():
    from datetime import UTC, datetime

    from marketdata.tsetmc.api import freshness

    observation = fixture("current")["records"][0]["observation"]
    assert freshness(observation, datetime(2026, 10, 21, tzinfo=UTC))["freshness"] == "stale"
    changed = copy.deepcopy(observation)
    changed["source_reported_at"] = "2026-03-21T08:59:59Z"
    with pytest.raises(ValueError, match="source_version_conflict"):
        ordered(observation, changed, "current")


@pytest.fixture
async def iran(ingress):  # noqa: F811
    g = ingress
    original = fixture("daily")
    code = original["records"][0]["observation"]["ins_code"]
    instrument = Instrument(
        canonical_symbol="TSETMC:" + code,
        display_name="Synthetic equity",
        asset_class="equity",
        instrument_type="common_stock",
        exchange="SYNTHETIC",
        currency="IRR",
    )
    registry = Registry(
        entries=[
            RegistryEntry(
                instrument=instrument,
                mappings=[
                    ProviderInstrument(
                        provider="tsetmc", provider_symbol=code, realtime_status="unknown"
                    )
                ],
            )
        ]
    )
    await g.d.store.register(registry)
    async with g.d.store.connection() as c:
        await c.execute(
            await asyncio.to_thread(Path("scripts/sql/tsetmc_destination_roles.sql").read_text)
        )
        for stream in ("tsetmc_daily", "tsetmc_current", "tsetmc_coverage", "tsetmc_status"):
            await c.execute(
                """INSERT INTO ingest_source_owners VALUES
              ($1,'tsetmc',$2,$3,$4,1,ARRAY['unknown'])""",
                instrument.id,
                stream,
                g.d.producer,
                g.d.epoch,
            )
    g.app.include_router(router(g.settings, g.app.state.store))

    def batch(name, *, seq=None):
        value = fixture(name)
        value.update(
            producer_id=str(g.d.producer),
            session_id=str(g.d.session),
            source_epoch=str(g.d.epoch),
            batch_id=str(uuid4()),
        )
        for r in value["records"]:
            if seq is not None:
                r["source_position"] = str(seq)
            r["observation_id"] = str(
                uuid5(g.d.epoch, value["stream"] + ":" + r["source_position"])
            )
        return value

    async def upload(value):
        raw = encode(value)
        return await g.client.post(
            "/api/ingest/v1/tsetmc/batches",
            content=raw,
            headers={
                "X-Payload-SHA256": hashlib.sha256(raw).hexdigest(),
                "Content-Type": "application/json",
            },
        )

    g.iran_batch, g.iran_upload, g.iran_code = batch, upload, code
    return g


async def test_atomic_receipts_corrections_auth_and_shared_reads(iran):
    g = iran
    first = g.iran_batch("daily")
    response = await g.iran_upload(first)
    assert response.status_code == 200, response.text
    assert response.json()["counts"]["applied"] == 1
    assert (await g.iran_upload(first)).json() == response.json()
    conflict = copy.deepcopy(first)
    conflict["records"][0]["observation"]["measurements"]["official_close"] = "113"
    assert (await g.iran_upload(conflict)).status_code == 422
    # Valid changed bytes under the same batch are rejected, with no financial mutation.
    o = conflict["records"][0]["observation"]
    o["financial_hash"] = financial_hash(o)
    assert (await g.iran_upload(conflict)).status_code == 409
    corrected = g.iran_batch("correction")
    response = await g.iran_upload(corrected)
    assert response.status_code == 200, response.text
    assert (await g.iran_upload(g.iran_batch("current"))).status_code == 200
    wrong = g.iran_batch("coverage")
    wrong["ownership_generation"] = 2
    assert (await g.iran_upload(wrong)).status_code == 403
    raw = encode(g.iran_batch("coverage"))
    denied = await g.client.post(
        "/api/ingest/v1/tsetmc/batches",
        content=raw,
        headers={"Authorization": "Bearer wrong", "Content-Type": "application/json"},
    )
    assert denied.status_code == 401
    # The independent READ process uses its SELECT-only role; collector is absent.
    async with server(g.reader, company_tsetmc_enabled=True, api_environment="production") as (
        _,
        base,
    ):
        async with httpx.AsyncClient(base_url=base, headers=HEADERS) as client:
            params = dict(ins_code=g.iran_code, start="2026-01-01", end="2027-01-01")
            finalized = await client.get("/api/v1/tsetmc/daily", params=params)
            assert finalized.status_code == 200, finalized.text
            assert finalized.json()["items"] == []
            history = (
                await client.get(
                    "/api/v1/tsetmc/daily", params={**params, "selection": "accepted-unverified"}
                )
            ).json()
            assert (
                history["items"][0]["measurements"]
                == corrected["records"][0]["observation"]["measurements"]
            )
            latest = (
                await client.get("/api/v1/tsetmc/latest", params={"ins_code": g.iran_code})
            ).json()
            assert latest["current"]["realtime_quote_available"] is False
            assert latest["current"]["freshness"] == "stale"
            assert (await client.get("/api/v1/instruments")).status_code == 200
            assert (
                await client.get("/api/v1/prices/latest", params={"provider": "mock"})
            ).status_code == 200
        async with connect(
            ws_url(base).replace("/ws/marketdata", "/ws/tsetmc") + "?ins_code=" + g.iran_code,
            additional_headers=HEADERS,
            origin=ORIGIN,
        ) as ws:
            initial = json.loads(await ws.recv())
            assert initial["type"] == "snapshot"
            # Fixture confirmation describes the original state, so test status publication here.
            status = await g.iran_upload(g.iran_batch("status"))
            assert status.status_code == 200, status.text
            for _ in range(100):
                message = json.loads(await ws.recv())
                if message.get("items"):
                    assert message["items"][0]["type"] == "status.updated"
                    break
            else:
                pytest.fail("committed status did not reach WebSocket")
            replay_cursor = initial["cursor"]
        async with httpx.AsyncClient(base_url=base, headers=HEADERS) as client:
            replay = await client.get(
                "/api/v1/tsetmc/changes", params={"ins_code": g.iran_code, "after": replay_cursor}
            )
            assert replay.status_code == 200 and replay.json()["items"]
    # Reader restart is independent of all source/worker connections.
    async with server(g.reader, company_tsetmc_enabled=True) as (_, base):
        async with httpx.AsyncClient(base_url=base, headers=HEADERS) as client:
            assert (
                await client.get("/api/v1/tsetmc/latest", params={"ins_code": g.iran_code})
            ).json()["current"]
