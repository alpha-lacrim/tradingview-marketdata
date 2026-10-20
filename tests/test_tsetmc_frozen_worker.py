"""Exact frozen TradingView worker -> new destination over actual local TLS."""

# Bounded task-owned fixture files; never source acquisition.
# ruff: noqa: ASYNC240

import asyncio
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_destination_ingestion import destination  # noqa: F401
from test_ingest_http import ingress, tls_files  # noqa: F401
from test_native_candles import make_candle
from test_source_capture import quote, source  # noqa: F401
from test_sync_worker import sync  # noqa: F401
from tsetmc_helpers import A, B, example

from marketdata.tsetmc_registry import InstrumentBinding, register

pytestmark = pytest.mark.integration


async def test_exact_frozen_worker_survives_new_head_and_legacy_session_recovery(
    sync,  # noqa: F811
    pair,
    tmp_path,
):
    w, local, capture, i = sync
    frozen = Path("distributions/marketdata-collector-sync-v1.1.0rc1").resolve()
    manifest = {}
    for line in (frozen / "SHA256SUMS").read_text().splitlines():
        checksum, name = line.split("  ", 1)
        assert hashlib.sha256((frozen / name).read_bytes()).hexdigest() == checksum
        manifest[name] = checksum
    async with i.d.store.connection() as c:
        for code in (A, B):
            await register(
                c,
                InstrumentBinding(
                    ins_code=code,
                    source_instrument_id="SYNTHETIC-" + code,
                    display_name="Synthetic frozen-client isolation",
                    exchange="SYNTHETIC",
                    units=example("daily.request")["records"][0]["observation"]["units"],
                    approval_evidence="synthetic-only",
                ),
            )
        await c.execute(
            "UPDATE ingest_producers SET session_expires_at=clock_timestamp()-interval '1 second'"
        )
    await local.write_candles([make_candle(pair, realtime_status="simulated")], [])
    await local.write_quotes([quote(pair, last="100.1234567890123456789")])
    config = tmp_path / "frozen-worker.json"
    config.write_text(w.config.model_dump_json())
    owner = w.local.lock_connection
    await owner.fetchval("SELECT pg_advisory_unlock(hashtextextended('marketdata:source-sync',0))")
    bootstrap = (
        "import sys,asyncio;from pathlib import Path;"
        "sys.path.insert(0,sys.argv[1]);"
        "import marketdata.sync_worker as worker;"
        "assert Path(worker.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve());"
        "from marketdata.sync_config import SyncConfig;"
        "asyncio.run(worker.run(SyncConfig.load(Path(sys.argv[2])),once=True))"
    )
    child = await asyncio.create_subprocess_exec(
        sys.executable,
        "-I",
        "-B",
        "-c",
        bootstrap,
        str(frozen / "src"),
        str(config),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(child.communicate(), 40)
        assert child.returncode == 0, stderr.decode()
        metrics = json.loads(stdout.decode().splitlines()[-1])
        assert metrics["candle_ack"] >= 1
    finally:
        if child.returncode is None:
            child.kill()
            await child.wait()
        assert await owner.fetchval(
            "SELECT pg_try_advisory_lock(hashtextextended('marketdata:source-sync',0))"
        )
        await w.local.claim(owner)
    assert not (await capture.page())["records"]
    assert not (await capture.pending_quotes())["records"]
    async with i.d.store.connection() as c:
        assert await c.fetchval("SELECT version_num FROM alembic_version") == "0011"
        assert await c.fetchval("SELECT count(*) FROM market_candles") == 1
        assert await c.fetchval("SELECT count(*) FROM latest_prices") == 1
        assert await c.fetchval("SELECT session_generation FROM ingest_producers") == 2
        assert (
            await c.fetchval("SELECT count(*) FROM ingest_source_owners WHERE provider='tsetmc'")
            == 0
        )
        assert await c.fetchval("SELECT count(*) FROM company_tsetmc.events") == 0
    for name, checksum in manifest.items():
        assert hashlib.sha256((frozen / name).read_bytes()).hexdigest() == checksum
