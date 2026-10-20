"""Real restricted principals and the existing authenticated INGEST boundary."""

import asyncio
import hashlib
import json
import secrets
import ssl
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import asyncpg
import httpx
import pytest
from disposable_postgres import PROOF
from test_ingest_http import tls_files  # noqa: F401
from test_sync_worker import worker_tls_server
from tsetmc_helpers import A, B, imported_rows, tsetmc  # noqa: F401

from marketdata.api import create_app as read_app
from marketdata.config import Settings
from marketdata.ingest_api import create_app
from marketdata.ingest_grants import GrantRecoveryRequest
from marketdata.persistence import Store
from marketdata.session_recovery import RecoveryRequest, recover_session
from marketdata.tsetmc_permissions import validate_permissions
from marketdata.tsetmc_wire import canonical, financial_hash

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("case", ["time", "review_id", "surrogate", "decimal_newline"])
async def test_invalid_scalar_http_requests_are_422_with_no_import_writes(ingress_tsetmc, case):
    i = ingress_tsetmc
    name = "current" if case in {"time", "surrogate"} else "daily"
    value = i.t.batch("confirmation" if case == "review_id" else name)
    observation = value["records"][0]["observation"]
    if case == "time":
        observation.update(source_time="99:99:99", source_reported_at=None)
    elif case == "review_id":
        observation["review"]["evidence_observation_ids"] = ["1", str(2**63)]
    elif case == "surrogate":
        observation["instrument_state_title"] = "\ud800"
        observation["financial_hash"] = financial_hash(observation)
    else:
        observation["measurements"]["official_close"] += "\n"
        observation["financial_hash"] = financial_hash(observation)
    before = await imported_rows(i.t.store)
    body = json.dumps(value, ensure_ascii=True).encode("utf-8")
    response = await i.client.post(
        "/api/ingest/v1/tsetmc/" + name,
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Payload-SHA256": hashlib.sha256(body).hexdigest(),
        },
    )
    assert response.status_code == 422, response.text
    assert set(response.json()["error"]) == {"code", "retryable", "record_indexes"}
    assert response.json()["error"]["retryable"] is False
    assert response.headers["cache-control"] == "no-store"
    assert await imported_rows(i.t.store) == before


@pytest.mark.parametrize("first", ["upload", "admin"])
@pytest.mark.parametrize("change", ["disable", "profile"])
async def test_binding_changes_serialize_with_restricted_ingest(ingress_tsetmc, first, change):
    i = ingress_tsetmc
    entered, release, admin_started = asyncio.Event(), asyncio.Event(), asyncio.Event()
    admin_pid = None

    async def pause(boundary):
        if boundary == "before_commit" and first == "upload":
            entered.set()
            await release.wait()

    async def administrator():
        nonlocal admin_pid
        async with i.t.store.connection() as c, c.transaction():
            admin_pid = c.get_server_pid()
            admin_started.set()
            assignment = (
                "enabled=FALSE"
                if change == "disable"
                else "units=jsonb_set(units,'{evidence_ref}','\"synthetic-reviewed-profile\"')"
            )
            await c.execute(
                "UPDATE company_tsetmc.instrument_links SET "
                + assignment
                + " WHERE instrument_id=$1",
                i.t.identity(A),
            )
            if first == "admin":
                entered.set()
                await release.wait()

    async def blocked():
        async with i.t.store.connection() as c, asyncio.timeout(5):
            while True:
                waiting = await c.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE datname=current_database() "
                    "AND wait_event_type='Lock' AND (pid=$1 OR $1=ANY(pg_blocking_pids(pid))))",
                    admin_pid,
                )
                if waiting:
                    return
                await asyncio.sleep(0.01)

    i.app.state.tsetmc_writer.checkpoint = pause
    tasks = []
    try:
        if first == "upload":
            upload_task = asyncio.create_task(upload(i, i.t.batch()))
            tasks.append(upload_task)
            await asyncio.wait_for(entered.wait(), 5)
            admin_task = asyncio.create_task(administrator())
            tasks.append(admin_task)
            await asyncio.wait_for(admin_started.wait(), 5)
        else:
            admin_task = asyncio.create_task(administrator())
            tasks.append(admin_task)
            await asyncio.wait_for(entered.wait(), 5)
            upload_task = asyncio.create_task(upload(i, i.t.batch()))
            tasks.append(upload_task)
        await blocked()
        assert not upload_task.done() and not admin_task.done()
        release.set()
        response = await upload_task
        await admin_task
        expected = 403 if change == "disable" else 409
        assert response.status_code == (200 if first == "upload" else expected), response.text
        assert (await upload(i, i.t.batch(position=2))).status_code == expected
        async with i.t.store.connection() as c:
            for table in ("daily_records", "daily_states", "events"):
                assert await c.fetchval("SELECT count(*) FROM company_tsetmc." + table) == (
                    first == "upload"
                )
            assert await c.fetchval("SELECT count(*) FROM ingest_batches") == (first == "upload")
            assert await c.fetchval("SELECT count(*) FROM ingest_observations") == (
                first == "upload"
            )
            assert await c.fetchval("SELECT head FROM marketdata_event_clock") == i.t.legacy_head
    finally:
        release.set()
        await asyncio.gather(*tasks, return_exceptions=True)


@pytest.fixture
async def ingress_tsetmc(tsetmc, tmp_path):  # noqa: F811
    t = tsetmc
    token = "synthetic_tsetmc." + secrets.token_urlsafe(32)
    credentials = tmp_path / "synthetic-credentials.json"
    await asyncio.to_thread(
        credentials.write_text,
        json.dumps(
            [
                dict(
                    producer_id=str(t.producer),
                    key_id="synthetic_tsetmc",
                    token_sha256=hashlib.sha256(token.encode()).hexdigest(),
                )
            ]
        ),
    )
    async with t.store.connection() as c:
        await c.execute(
            await asyncio.to_thread(Path("scripts/sql/v11_destination_roles.sql").read_text)
        )
        await c.execute(
            await asyncio.to_thread(Path("scripts/sql/tsetmc_destination_roles.sql").read_text)
        )
        # These are task-cluster roles only, not real company credentials.
        for role in ("marketdata_v11_read", "marketdata_v11_ingest"):
            await c.execute(f"ALTER ROLE {role} PASSWORD 'disposable_test'")
    original = urlsplit(t.store.settings.database_url.get_secret_value())

    def dsn(role):
        return urlunsplit(
            original._replace(netloc=f"{role}:disposable_test@{original.hostname}:{original.port}")
        )

    config = Settings(
        _env_file=None,
        application_role="ingest",
        api_environment="production",
        database_url=dsn("marketdata_v11_ingest"),
        ingest_credentials_file=credentials,
        tsetmc_ingest_enabled=True,
    )
    app = create_app(config)
    try:
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="https://ingest.test",
                headers={"Authorization": "Bearer " + token},
            ) as client,
        ):
            yield SimpleNamespace(t=t, app=app, client=client, config=config, dsn=dsn, token=token)
    finally:
        async with t.store.connection() as c:
            for role in ("marketdata_v11_read", "marketdata_v11_ingest"):
                await c.execute(f"DROP OWNED BY {role}")
                await c.execute(f"DROP ROLE {role}")


async def upload(i, value, *, name="daily", **headers):
    body = canonical(value)
    return await i.client.post(
        "/api/ingest/v1/tsetmc/" + name,
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Payload-SHA256": hashlib.sha256(body).hexdigest(),
            **headers,
        },
    )


async def test_authenticated_upload_receipt_lookup_and_safe_errors(ingress_tsetmc):
    i = ingress_tsetmc
    value = i.t.batch()
    response = await upload(i, value)
    assert response.status_code == 200, response.text
    first = response.json()
    assert (await upload(i, value)).json() == first
    assert (await i.client.get("/api/ingest/v1/receipts/" + value["batch_id"])).json() == first
    assert (
        await i.client.post(
            "/api/ingest/v1/tsetmc/reconcile",
            content=canonical(
                dict(
                    protocol_version=1,
                    contract_version="tsetmc.v1",
                    session_id=str(i.t.session),
                    session_generation=1,
                    instrument_id=str(i.t.identity(A)),
                    ins_code=A,
                    source_epoch=str(i.t.epochs[A]),
                    ownership_generation=1,
                    mode="keys",
                    keys=[dict(stream="tsetmc_daily", trading_date="2026-03-21")],
                )
            ),
            headers={"Content-Type": "application/json"},
        )
    ).status_code == 200
    for headers, expected in [
        ({"Origin": "https://browser.test"}, 403),
        ({"Authorization": "Bearer invalid"}, 401),
        ({"X-Payload-SHA256": "0" * 64}, 400),
    ]:
        result = await upload(i, value, **headers)
        assert result.status_code == expected
        assert set(result.json()["error"]) == {"code", "retryable", "record_indexes"}
        assert result.headers["cache-control"] == "no-store"
    invalid = i.t.batch("confirmation")
    invalid["records"][0]["event_type"] = "daily.review_revoked"
    result = await upload(i, invalid)
    assert result.status_code == 422 and result.json()["error"]["record_indexes"] == [0]
    result = await i.client.get("/api/ingest/v1/receipts/" + str(uuid4()))
    assert result.status_code == 404 and set(result.json()["error"]) == {"code", "retryable"}


async def test_disabled_default_and_https_origin_boundaries(ingress_tsetmc):
    i = ingress_tsetmc
    app = create_app(i.config.model_copy(update={"tsetmc_ingest_enabled": False}))
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="https://ingest.test",
            headers={"Authorization": "Bearer " + i.token},
        ) as client,
    ):
        response = await client.post("/api/ingest/v1/tsetmc/daily")
        assert response.status_code == 403
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=i.app), base_url="http://ingest.test"
    ) as client:
        result = await client.post("/api/ingest/v1/tsetmc/daily")
        assert result.status_code == 400
        assert result.json()["error"]["record_indexes"] == []


async def test_multi_epoch_shared_session_recovery_and_legacy_worker_models_stay_closed(
    ingress_tsetmc,
):
    i = ingress_tsetmc
    async with i.t.store.connection() as c:
        grants = await c.fetch(
            "SELECT instrument_id,provider,stream,source_epoch,ownership_generation "
            "FROM ingest_source_owners WHERE producer_id=$1 "
            "ORDER BY instrument_id,provider,stream",
            i.t.producer,
        )
        await c.execute(
            "UPDATE ingest_producers SET session_expires_at=clock_timestamp()-interval '1 second' "
            "WHERE producer_id=$1",
            i.t.producer,
        )
    manifest = [
        {k: str(v) if k in {"instrument_id", "source_epoch"} else v for k, v in dict(g).items()}
        for g in grants
    ]
    value = dict(
        protocol_version=1,
        recovery_id=str(uuid4()),
        previous_session_id=str(i.t.session),
        previous_session_generation=1,
        streams=manifest,
    )
    with pytest.raises(ValueError):
        RecoveryRequest.model_validate(value)
    parsed = GrantRecoveryRequest.model_validate(value)
    first = await recover_session(i.app.state.store, i.t.principal, parsed)
    assert (
        first["session_generation"] == 2 and len({s["source_epoch"] for s in first["streams"]}) == 2
    )
    assert await recover_session(i.app.state.store, i.t.principal, parsed) == first
    response = await upload(i, i.t.batch())
    assert (
        response.status_code == 409
        and response.json()["error"]["code"] == "producer_session_fenced"
    )
    current = i.t.batch(session_id=first["session_id"], session_generation=2)
    assert (await upload(i, current)).status_code == 200
    async with i.t.store.connection() as c:
        await c.execute(
            "UPDATE ingest_producers SET enabled=FALSE WHERE producer_id=$1", i.t.producer
        )
    assert (await upload(i, current)).status_code == 401


async def test_real_restricted_roles_and_new_read_disabled_legacy_routes(ingress_tsetmc):
    i = ingress_tsetmc
    async with i.app.state.store.connection() as c:
        await validate_permissions(c, read_only=False)
        for sql in [
            "UPDATE company_tsetmc.daily_states SET payload=payload",
            "DELETE FROM company_tsetmc.events",
            "UPDATE company_tsetmc.instrument_links SET enabled=TRUE",
            "CREATE TABLE company_tsetmc.forbidden(id int)",
            "UPDATE ingest_source_owners SET ownership_generation=2",
            "TRUNCATE company_tsetmc.daily_records",
        ]:
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await c.execute(sql)
    settings = Settings(
        _env_file=None,
        database_url=i.dsn("marketdata_v11_read"),
        api_environment="production",
        api_key="r" * 40,
    )
    reader = Store(settings, read_only=True)
    await reader.connect()
    try:
        async with reader.connection() as c:
            assert await c.fetchval("SHOW default_transaction_read_only") == "on"
            await c.execute("SET default_transaction_read_only=off")
            for sql in [
                "SELECT * FROM ingest_producers",
                "INSERT INTO company_tsetmc.event_clock(singleton) VALUES(FALSE)",
                "SELECT company_tsetmc.prune_events(1)",
                "SELECT * FROM company_tsetmc.lock_instrument(gen_random_uuid())",
                "CREATE TABLE company_tsetmc.forbidden(id int)",
            ]:
                with pytest.raises(asyncpg.InsufficientPrivilegeError):
                    await c.execute(sql)
    finally:
        await reader.close()
    app = read_app(settings)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="https://read.test",
            headers={"Authorization": "Bearer " + "r" * 40},
        ) as client,
    ):
        assert (await client.get("/api/v1/instruments")).status_code == 200
        assert (await client.get("/api/v1/tsetmc/instruments")).status_code == 404


@pytest.mark.parametrize("boundary", ["before_commit", "after_commit"])
async def test_actual_child_process_death_and_replay(ingress_tsetmc, tmp_path, boundary):
    i = ingress_tsetmc
    value = i.t.batch()
    config = tmp_path / "private-child.json"
    proof = json.loads(await asyncio.to_thread(Path(PROOF).read_text))
    await asyncio.to_thread(
        config.write_text,
        json.dumps(
            dict(
                dsn=i.dsn("marketdata_v11_ingest"),
                proof=proof,
                producer_id=str(i.t.producer),
                key_id="synthetic_tsetmc",
                payload=value,
                boundary=boundary,
            )
        ),
    )
    program = tmp_path / "crash_destination.py"
    await asyncio.to_thread(
        program.write_text,
        """import asyncio,json,os,sys
from pathlib import Path
from uuid import UUID
import asyncpg
from marketdata.config import Settings
from marketdata.persistence import Store
from marketdata.ingest_auth import Principal
from marketdata.tsetmc_storage import TsetmcWriter
from marketdata.tsetmc_wire import canonical
async def main():
    config=json.loads(Path(sys.argv[1]).read_text())
    c=await asyncpg.connect(config['dsn'])
    assert await c.fetchval('SHOW server_version_num')=='160001'
    # Restricted writer cannot SHOW data_directory; parent verified the endpoint.
    assert await c.fetchval('SELECT current_database()')==config['proof']['database']
    await c.close()
    store=Store(Settings(_env_file=None,database_url=config['dsn']))
    await store.connect()
    writer=TsetmcWriter(store)
    async def point(boundary):
        if boundary==config['boundary']:os._exit(81)
    writer.checkpoint=point
    principal=Principal(UUID(config['producer_id']),config['key_id'])
    await writer.commit(principal,canonical(config['payload']))
asyncio.run(main())
""",
    )
    result = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, str(program), str(config)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 81, result.stderr
    async with i.t.store.connection() as c:
        assert await c.fetchval("SELECT count(*) FROM ingest_batches") == (
            boundary == "after_commit"
        )
    receipt = await upload(i, value)
    assert receipt.status_code == 200
    async with i.t.store.connection() as c:
        assert await c.fetchval("SELECT count(*) FROM ingest_batches") == 1
        assert await c.fetchval("SELECT count(*) FROM company_tsetmc.events") == 1


async def test_actual_tls_upload_and_untrusted_certificate_rejected(ingress_tsetmc, tls_files):  # noqa: F811
    i = ingress_tsetmc
    async with worker_tls_server(create_app(i.config), tls_files) as origin:
        async with httpx.AsyncClient(
            verify=ssl.create_default_context(), trust_env=False
        ) as client:
            with pytest.raises(httpx.ConnectError):
                await client.post(origin + "/api/ingest/v1/tsetmc/daily")
        context = ssl.create_default_context(cafile=str(tls_files[0]))
        async with httpx.AsyncClient(
            verify=context, trust_env=False, headers={"Authorization": "Bearer " + i.token}
        ) as client:
            body = canonical(i.t.batch())
            result = await client.post(
                origin + "/api/ingest/v1/tsetmc/daily",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Payload-SHA256": hashlib.sha256(body).hexdigest(),
                },
            )
            assert result.status_code == 200, result.text
