"""Fail closed before shared fixtures can write to the retained M3B-2 test cluster."""

import asyncio
import json
import os
import re
import struct
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
TASK = "tsetmc-company-m3b2"
OWNER = "801c97e7-784b-4737-b6ca-fa191a8c4373"
SYSTEM_IDENTIFIER = "7698666753214710248"
MARKER = TASK + "/" + OWNER
PROOF = "artifacts/m3b2/remediation/isolation.json"
METADATA = """SELECT current_database() AS database, d.oid::bigint AS database_oid,
    r.rolname AS database_owner, r.oid::bigint AS database_owner_oid,
    shobj_description(d.oid,'pg_database') AS ownership_marker,
    current_user AS connected_role, current_setting('server_version_num') AS version,
    current_setting('data_directory') AS data_directory,
    current_setting('transaction_read_only') AS read_only,
    host(inet_server_addr()) AS address, inet_server_port() AS port,
    pg_postmaster_start_time() AS server_started_at,
    (pg_control_system()).system_identifier::text AS system_identifier
    FROM pg_database d JOIN pg_roles r ON r.oid=d.datdba
    WHERE d.datname=current_database()"""


def evidence(url, root=ROOT):
    """Disk identity is pinned independently of the editable verification report."""
    target = urlsplit(url)
    expected = root.resolve() / "artifacts/m3b2/pgdata"
    if (
        target.scheme != "postgresql"
        or target.hostname != "127.0.0.1"
        or target.port != 4195
        or target.username != "m3b2_admin"
        or target.query
        or target.fragment
    ):
        raise RuntimeError("disposable PostgreSQL endpoint not approved")
    try:
        owner = json.loads((root / "artifacts/m3b2/cluster-owner.json").read_text("utf-8"))
        proof = json.loads((root / PROOF).read_text("utf-8"))
        control = (expected / "global/pg_control").read_bytes()
        pid = (expected / "postmaster.pid").read_text("utf-8").splitlines()
        verified = datetime.fromisoformat(proof["verified_at"])
        started = datetime.fromisoformat(proof["server_started_at"])
        valid = (
            owner["task"] == proof["task"] == TASK
            and owner["owner"] == proof["owner"] == OWNER
            and owner["port"] == proof["port"] == 4195
            and Path(owner["data_directory"]).resolve() == expected
            and Path(proof["data_directory"]).resolve() == expected
            and expected.resolve() == expected
            and (expected / "PG_VERSION").read_text("utf-8").strip() == "16"
            and str(struct.unpack("<Q", control[:8])[0]) == SYSTEM_IDENTIFIER
            and proof["system_identifier"] == SYSTEM_IDENTIFIER
            and proof["server_version_num"] == "160001"
            and target.path == "/" + proof["database"]
            and re.fullmatch(r"m3b2_remediation_[a-z0-9_]+_test", proof["database"])
            and type(proof["database_oid"]) is int
            and proof["database_oid"] > 0
            and type(proof["database_owner_oid"]) is int
            and proof["database_owner_oid"] > 0
            and proof["database_owner"] == "m3b2_admin"
            and proof["ownership_marker"] == MARKER
            and Path(pid[1]).resolve() == expected
            and int(pid[3]) == 4195
            and pid[7].strip() == "ready"
            and proof["postmaster_pid"] == int(pid[0]) > 0
            and proof["postmaster_start_epoch"] == int(pid[2])
            and started.utcoffset() == timedelta(0)
            and started.timestamp() >= int(pid[2])
            and verified.utcoffset() == timedelta(0)
            and timedelta(seconds=-5) <= datetime.now(UTC) - verified < timedelta(hours=8)
            and verified >= started
        )
    except (OSError, ValueError, KeyError, IndexError, TypeError, struct.error):
        raise RuntimeError("disposable PostgreSQL ownership evidence missing or invalid") from None
    if not valid:
        raise RuntimeError("disposable PostgreSQL ownership evidence does not match")
    return proof


async def verify_disposable(url, root=ROOT, *, connection=None):
    profile = os.environ.get("MARKETDATA_TEST_PROFILE", "retained")
    if profile == "github-service":
        from ci_postgres import verify

        return await verify(url, root, connection=connection)
    if profile != "retained":
        raise RuntimeError("disposable PostgreSQL profile not approved")
    proof = await asyncio.to_thread(evidence, url, root)
    # No application pool, DDL, admission function or fixture runs on this connection.
    c = connection or await asyncpg.connect(
        url,
        timeout=5,
        command_timeout=5,
        server_settings={"default_transaction_read_only": "on", "statement_timeout": "5000"},
    )
    try:
        actual = await c.fetchrow(METADATA)
        if (
            not actual
            or any(
                actual[key] != proof[key]
                for key in (
                    "database",
                    "database_oid",
                    "database_owner",
                    "database_owner_oid",
                    "ownership_marker",
                    "system_identifier",
                )
            )
            or (
                actual["version"] != "160001"
                or Path(actual["data_directory"]) != Path(proof["data_directory"])
                or actual["read_only"] != "on"
                or actual["address"] != "127.0.0.1"
                or actual["port"] != 4195
                or actual["connected_role"] != "m3b2_admin"
                or actual["server_started_at"] != datetime.fromisoformat(proof["server_started_at"])
            )
        ):
            raise RuntimeError("live disposable PostgreSQL identity does not match")
    finally:
        if connection is None:
            await c.close()
    return url
