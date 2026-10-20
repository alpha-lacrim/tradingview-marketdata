"""D06: actual disposable PG16.1 DDL, interrupted transaction and populated upgrade."""

# These bounded test-only files and child processes are outside application request IO.
# ruff: noqa: ASYNC240

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import asyncpg
import pytest
from disposable_postgres import verify_disposable
from test_destination_ingestion import candle, destination, record  # noqa: F401

from marketdata.tsetmc_permissions import TABLES

pytestmark = pytest.mark.integration


async def migrate(url, *arguments):
    result = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "alembic", *arguments],
        env={**os.environ, "DATABASE_URL": url},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


async def snapshot(c):
    names = await c.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' "
        "AND tablename<>'alembic_version' ORDER BY tablename"
    )
    return {
        r["tablename"]: sorted(
            [dict(row) for row in await c.fetch('SELECT * FROM public."' + r["tablename"] + '"')],
            key=repr,
        )
        for r in names
    }


async def test_fresh_and_populated_upgrade_interruption_and_disposable_roundtrip(
    destination,  # noqa: F811
    pair,
    tmp_path,
):
    d = destination
    await verify_disposable(d.store.settings.database_url.get_secret_value())
    await d.writer.commit(d.producer, d.batch([record(candle(pair))]))
    async with d.store.connection() as c:
        source = await snapshot(c)
    parsed = urlsplit(d.store.settings.database_url.get_secret_value())
    name = "m3b2_migration_" + uuid4().hex + "_test"
    url = urlunsplit(parsed._replace(path="/" + name))
    async with d.store.connection() as admin:
        await admin.execute(f'CREATE DATABASE "{name}"')
    c = None
    try:
        await migrate(url, "upgrade", "0010")
        c = await asyncpg.connect(url)
        # Preserve actual synthetic financial/receipt/ownership rows from the existing
        # regression fixture; this is a copy inside the verified disposable cluster.
        order = [
            "instruments",
            "provider_instruments",
            "market_ticks",
            "latest_prices",
            "market_candles",
            "latest_candles",
            "candle_coverage",
            "candle_revisions",
            "collector_status",
            "marketdata_event_clock",
            "marketdata_events",
            "ingest_producers",
            "ingest_source_owners",
            "ingest_batches",
            "ingest_observations",
            "ingest_candle_heads",
            "ingest_coverage_heads",
            "ingest_source_status",
            "candle_observation_heads",
            "ingest_request_budgets",
            "ingest_session_recoveries",
            "ingest_quote_heads",
            "ingest_destination_state",
        ]
        await c.execute("DELETE FROM marketdata_event_clock; DELETE FROM ingest_destination_state")
        for table in order:
            if source[table]:
                await c.copy_records_to_table(
                    table,
                    records=[tuple(row.values()) for row in source[table]],
                    columns=list(source[table][0]),
                )
        before = await snapshot(c)
        assert before == source
        # Install actual legacy principals before the migration, then upgrade grants
        # afterward without re-creating accounts or provisioning passwords.
        await c.execute(Path("scripts/sql/v11_destination_roles.sql").read_text())
        child = tmp_path / "interrupt_migration.py"
        child.write_text("""import os
from alembic import command
from alembic.config import Config
from alembic.operations import Operations
original=Operations.execute
def interrupted(self,sql,*args,**kwargs):
    result=original(self,sql,*args,**kwargs)
    if isinstance(sql,str) and "CREATE SCHEMA company_tsetmc" in sql:
        os._exit(71)
    return result
Operations.execute=interrupted
command.upgrade(Config("alembic.ini"),"head")
""")
        result = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, str(child)],
            env={**os.environ, "DATABASE_URL": url},
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 71, result.stderr
        assert await c.fetchval("SELECT version_num FROM alembic_version") == "0010"
        assert await c.fetchval("SELECT to_regnamespace('company_tsetmc')") is None
        assert await snapshot(c) == before
        await migrate(url, "upgrade", "head")
        assert await c.fetchval("SELECT version_num FROM alembic_version") == "0011"
        assert await snapshot(c) == before
        assert {
            r["tablename"]
            for r in await c.fetch(
                "SELECT tablename FROM pg_tables WHERE schemaname='company_tsetmc'"
            )
        } == set(TABLES)
        assert await c.fetchval("SELECT count(*) FROM company_tsetmc.instrument_links") == 0
        await c.execute(Path("scripts/sql/tsetmc_destination_roles.sql").read_text())
        await c.execute(Path("scripts/sql/tsetmc_destination_roles.sql").read_text())
        assert await c.fetchval(
            "SELECT has_table_privilege('marketdata_v11_ingest',"
            "'company_tsetmc.daily_states','INSERT')"
        )
        assert not await c.fetchval(
            "SELECT has_table_privilege('marketdata_v11_ingest',"
            "'company_tsetmc.daily_states','UPDATE')"
        )
        assert await snapshot(c) == before
        await migrate(url, "downgrade", "0010")
        assert await snapshot(c) == before
        await migrate(url, "upgrade", "head")
        assert await snapshot(c) == before
    finally:
        if c:
            for role in ("marketdata_v11_read", "marketdata_v11_ingest"):
                if await c.fetchval("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=$1)", role):
                    await c.execute(f"DROP OWNED BY {role}")
                    await c.execute(f"DROP ROLE {role}")
            await c.close()
        async with d.store.connection() as admin:
            await admin.execute("SET statement_timeout=60000")
            await admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)', timeout=60)


async def test_empty_fresh_0001_to_0011_installs_no_policy_or_source_track(store):
    parsed = urlsplit(store.settings.database_url.get_secret_value())
    name = "m3b2_fresh_" + uuid4().hex + "_test"
    url = urlunsplit(parsed._replace(path="/" + name))
    async with store.connection() as c:
        await verify_disposable(store.settings.database_url.get_secret_value())
        await c.execute(f'CREATE DATABASE "{name}"')
    try:
        await migrate(url, "upgrade", "head")
        c = await asyncpg.connect(url)
        try:
            assert await c.fetchval("SELECT version_num FROM alembic_version") == "0011"
            for table in (
                "instruments",
                "ingest_producers",
                "ingest_source_owners",
                "ingest_batches",
            ):
                assert await c.fetchval(f"SELECT count(*) FROM {table}") == 0
            assert await c.fetchval("SELECT to_regclass('source_capture_version')") is None
            assert await c.fetchval("SELECT count(*) FROM company_tsetmc.events") == 0
            assert await c.fetchval("SELECT head FROM company_tsetmc.event_clock") == 0
        finally:
            await c.close()
        await migrate(url, "downgrade", "0010")
        await migrate(url, "upgrade", "head")
    finally:
        async with store.connection() as c:
            await c.execute("SET statement_timeout=60000")
            await c.execute(f'DROP DATABASE "{name}" WITH (FORCE)', timeout=60)
