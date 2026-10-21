"""Shared dashboard routes over audited storage, using real restricted SQL roles."""

import argparse
import importlib.util
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from test_market_stream import HEADERS, ORIGIN, server, ws_url
from test_tsetmc_http import ingress_tsetmc, upload  # noqa: F401
from tsetmc_helpers import A, tsetmc  # noqa: F401
from websockets.asyncio.client import connect

from marketdata.config import Settings
from marketdata.persistence import Store


@pytest.fixture(autouse=True)
async def clean_disposable_imports(store):
    # store verifies owned disposable SQL identity before any fixture mutation.
    try:
        yield
    finally:
        async with store.connection() as c:
            await c.execute("TRUNCATE instruments,ingest_producers CASCADE")


async def test_generated_setup_is_atomic_and_refuses_reenrollment(store, tmp_path):
    import pytest
    from tsetmc_helpers import example

    from marketdata.tsetmc.admin import setup

    spec = importlib.util.spec_from_file_location(
        "setup_files", "scripts/prepare_tsetmc_connection.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    units = tmp_path / "units.json"
    units.write_text(json.dumps(example("daily.request")["records"][0]["observation"]["units"]))
    async with store.connection() as c:
        destination = str(await c.fetchval("SELECT destination_id FROM ingest_destination_state"))
    target = tmp_path / "connection"
    module.prepare(
        argparse.Namespace(
            endpoint="https://synthetic.example",
            ins_code="900000000000000003",
            destination_id=destination,
            display_name="Synthetic setup",
            exchange="SYNTHETIC",
            source_instrument_id="SYNTHETIC-SETUP",
            approval_evidence="synthetic-test-only",
            units_file=units,
            output=target,
        )
    )
    dsn = tmp_path / "dsn"
    dsn.write_text(store.settings.database_url.get_secret_value())
    await setup(dsn, target / "company-plan.json")
    async with store.connection() as c:
        before = await c.fetch("SELECT * FROM company_tsetmc.instrument_links")
        assert len(before) == 1 and before[0]["enabled"]
        assert (
            await c.fetchval("SELECT count(*) FROM ingest_source_owners WHERE provider='tsetmc'")
            == 4
        )
    with pytest.raises(ValueError, match="binding already exists"):
        await setup(dsn, target / "company-plan.json")
    async with store.connection() as c:
        assert await c.fetch("SELECT * FROM company_tsetmc.instrument_links") == before


async def test_worker_alias_reads_replay_and_retention_floor(ingress_tsetmc):  # noqa: F811
    i = ingress_tsetmc
    batch = i.t.batch()
    receipt = await upload(i, batch, name="batches")
    assert receipt.status_code == 200, receipt.text
    saved = await i.client.get("/api/ingest/v1/tsetmc/receipts/" + batch["batch_id"])
    assert saved.json() == receipt.json()
    assert (await upload(i, batch, name="batches")).json() == receipt.json()
    assert (await upload(i, i.t.batch("current"), name="batches")).status_code == 200
    async with server(
        Store(Settings(_env_file=None, database_url=i.dsn("marketdata_v11_read"))),
        company_tsetmc_enabled=True,
        api_environment="production",
    ) as (_, base):
        async with httpx.AsyncClient(base_url=base, headers=HEADERS) as client:
            instruments = await client.get("/api/v1/tsetmc/instruments")
            assert instruments.status_code == 200, instruments.text
            assert instruments.json()["items"][0]["provider"] == "tsetmc"
            params = dict(ins_code=A, start="2026-01-01", end="2027-01-01")
            history = await client.get(
                "/api/v1/tsetmc/daily",
                params={
                    **params,
                    "selection": "accepted-unverified",
                },
            )
            assert history.status_code == 200, history.text
            assert (
                history.json()["items"][0]["measurements"]
                == batch["records"][0]["observation"]["measurements"]
            )
            latest = await client.get("/api/v1/tsetmc/latest", params={"ins_code": A})
            assert latest.status_code == 200, latest.text
            assert latest.json()["current"]["realtime_quote_available"] is False
        async with connect(
            ws_url(base).replace("/ws/marketdata", "/ws/tsetmc") + "?ins_code=" + A,
            additional_headers=HEADERS,
            origin=ORIGIN,
        ) as ws:
            initial = json.loads(await ws.recv())
            assert initial["type"] == "snapshot"
            status = i.t.batch("status")
            observation = status["records"][0]["observation"]
            now = datetime.now(UTC)
            observation["captured_at"] = (
                (now - timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
            )
            observation["expires_at"] = (
                (now + timedelta(seconds=60)).isoformat().replace("+00:00", "Z")
            )
            response = await upload(i, status, name="batches")
            assert response.status_code == 200, response.text
            for _ in range(100):
                change = json.loads(await ws.recv())
                if change.get("items"):
                    assert change["items"][0]["type"] == "status.updated"
                    break
            else:
                raise AssertionError("missing committed status event")
        async with i.t.store.connection() as c:
            await c.execute("UPDATE company_tsetmc.event_clock SET floor=head")
        async with httpx.AsyncClient(base_url=base, headers=HEADERS) as client:
            expired = await client.get(
                "/api/v1/tsetmc/changes",
                params={
                    "ins_code": A,
                    "after": initial["cursor"],
                },
            )
            assert expired.status_code == 409
