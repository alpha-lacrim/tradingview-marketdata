"""Opt-in two-database HTTPS qualification against the independent TSETMC checkout.

Run with: uv run --with-editable ../tsetmc-marketdata pytest tests/test_unified_delivery.py
Both database URLs must point to the explicitly provisioned disposable test cluster.
"""

import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
from test_destination_ingestion import destination  # noqa: F401
from test_ingest_http import ingress, tls_files, tls_server  # noqa: F401
from test_tsetmc_company import iran  # noqa: F401


async def test_source_to_company_https_restart_and_correction(iran, tls_files, tmp_path):  # noqa: F811
    source_root = os.getenv("TSETMC_TEST_ROOT")
    if not source_root:
        pytest.skip("set TSETMC_TEST_ROOT to the independent source checkout")
    pytest.importorskip("tsetmc_marketdata")
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text
    from tsetmc_marketdata.collection.jobs import Collector
    from tsetmc_marketdata.delivery import DeliveryConfig, DeliveryError, Worker
    from tsetmc_marketdata.storage.config import DatabaseSettings
    from tsetmc_marketdata.storage.database import Database
    from tsetmc_marketdata.storage.outbox import RecoveryFence, SourceOutbox
    from tsetmc_marketdata.storage.repository import Repository

    g = iran
    spec = importlib.util.spec_from_file_location(
        "synthetic_tsetmc", Path(source_root) / "tests/integration/helpers.py"
    )
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    source = helpers.SyntheticSource()
    name = "tsetmc_test_" + uuid4().hex
    from urllib.parse import urlsplit, urlunsplit

    original = urlsplit(g.d.store.settings.database_url.get_secret_value())
    source_url = urlunsplit(original._replace(scheme="postgresql+asyncpg", path="/" + name))
    admin = await asyncpg.connect(g.d.store.settings.database_url.get_secret_value())
    assert await admin.fetchval("SELECT current_setting('server_version_num')") == "160001"
    assert original.path.endswith("_test")
    await admin.execute(f'CREATE DATABASE "{name}"')
    db = Database(DatabaseSettings(source_url))
    try:
        config = Config(str(Path(source_root) / "alembic.ini"))
        config.set_main_option("script_location", str(Path(source_root) / "migrations"))

        def migrate(conn):
            config.attributes["connection"] = conn
            command.upgrade(config, "head")

        async with db.engine.begin() as conn:
            await conn.run_sync(migrate)

        async def collect(job):
            async with db.owner(source.code) as conn:
                return await Collector(Repository(conn, source.code), source, kind="synthetic").run(
                    job
                )

        await collect("backfill-history")
        await collect("observe-current")
        destination_id = await admin.fetchval("SELECT destination_id FROM ingest_destination_state")
        # This worker has its own producer manifest; legacy data/REST remain untouched.
        await admin.execute(
            "DELETE FROM ingest_source_owners WHERE producer_id=$1 AND provider<>'tsetmc'",
            g.d.producer,
        )
        async with db.owner(source.code) as conn:
            repo = Repository(conn, source.code)
            async with repo.atomic():
                box = SourceOutbox(repo)
                await box.configure(
                    source_epoch=g.d.epoch,
                    installation_id=uuid4(),
                    destination_id=destination_id,
                    producer_id=g.d.producer,
                )
                await box.enroll(seed_id=uuid4(), allow_local_publication=True)
        token_file = tmp_path / "producer.token"
        token_file.write_text(g.token)
        async with tls_server(g.app, tls_files) as origin:
            delivery_config = DeliveryConfig(
                endpoint=origin,
                ins_code=source.code,
                producer_id=g.d.producer,
                destination_id=destination_id,
                session_id=g.d.session,
                session_generation=1,
                token_file=token_file,
                anchor_file=tmp_path / "anchor.json",
                ca_file=tls_files[0],
            )
            worker = Worker(db, delivery_config)
            request = worker.request
            lost = False

            async def uncertain(method, path, raw=None):
                nonlocal lost
                result = await request(method, path, raw)
                if method == "POST" and path == "/tsetmc/batches" and not lost:
                    lost = True
                    raise DeliveryError("transport_unavailable", retryable=True)
                return result

            worker.request = uncertain
            assert await worker.run(seconds=60) > 0
            assert lost
            async with db.read() as conn:
                clocks = (
                    await conn.execute(text("SELECT head,acknowledged FROM sync_stream_clocks"))
                ).all()
                assert all(head == ack for head, ack in clocks)
            first = await admin.fetchval(
                "SELECT count(*) FROM ingest_observations WHERE provider='tsetmc'"
            )
            assert await Worker(db, delivery_config).run(seconds=30) == 0
            assert (
                await admin.fetchval(
                    "SELECT count(*) FROM ingest_observations WHERE provider='tsetmc'"
                )
                == first
            )
            source.rows[0]["pClosing"] = "1050.1234567890123456789"
            await collect("backfill-history")
            assert await Worker(db, delivery_config).run(seconds=60) > 0
            assert (
                await admin.fetchval(
                    "SELECT payload->'measurements'->>'official_close' "
                    "FROM company_tsetmc.heads WHERE stream='tsetmc_daily'"
                )
                == "1050.1234567890123456789"
            )
            assert (
                await admin.fetchval(
                    "SELECT count(*) FROM ingest_observations "
                    "WHERE provider='tsetmc' AND stream='tsetmc_daily'"
                )
                == 2
            )
            # Crash before upload, then expire the saved session. Recovery must retain the
            # original bytes and re-envelope exactly the same observations under the new lease.
            source.rows[0]["pClosing"] = "1051.1234567890123456789"
            await collect("backfill-history")
            interrupted = Worker(db, delivery_config)
            normal_request = interrupted.request

            async def stop_before_upload(method, path, raw=None):
                if path == "/tsetmc/batches":
                    raise DeliveryError("injected_stop")
                return await normal_request(method, path, raw)

            interrupted.request = stop_before_upload
            with pytest.raises(DeliveryError, match="injected_stop"):
                await interrupted.run(seconds=30)
            await admin.execute(
                "UPDATE ingest_producers SET session_expires_at="
                "clock_timestamp()-interval '1 second' WHERE producer_id=$1",
                g.d.producer,
            )
            assert await Worker(db, delivery_config).run(seconds=60) > 0
            assert (
                await admin.fetchval(
                    "SELECT session_generation FROM ingest_producers WHERE producer_id=$1",
                    g.d.producer,
                )
                == 2
            )
            async with db.read() as conn:
                saved = (
                    await conn.execute(
                        text(
                            "SELECT request_bytes,phase FROM sync_batches "
                            "WHERE stream='tsetmc_daily' ORDER BY through_position,phase"
                        )
                    )
                ).all()
            from tsetmc_marketdata.storage.publication_wire import decode

            last = [
                decode(bytes(raw))
                for raw, phase in saved
                if decode(bytes(raw))["records"][0]["observation"]["financial_revision"] == "3"
            ]
            assert len(last) == 2 and last[0]["records"] == last[1]["records"]
            # A restored source behind external ACK evidence must fail closed.
            async with db.engine.begin() as conn:
                await conn.execute(
                    text("UPDATE sync_stream_clocks SET acknowledged=0 WHERE stream='tsetmc_daily'")
                )
            with pytest.raises(RecoveryFence, match="behind proven"):
                await Worker(db, delivery_config).run(seconds=30)
    finally:
        await db.aclose()
        await admin.execute(f'DROP DATABASE "{name}" WITH(FORCE)')
        await admin.close()
