"""F02: fakes only; these checks must pass before any PostgreSQL-writing test."""

import copy
import json
import struct
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import conftest
import disposable_postgres as guard
import pytest


@pytest.fixture
def owned(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKETDATA_TEST_PROFILE", "retained")
    directory = tmp_path / "artifacts/m3b2/pgdata"
    (directory / "global").mkdir(parents=True)
    (directory / "global/pg_control").write_bytes(struct.pack("<Q", int(guard.SYSTEM_IDENTIFIER)))
    (directory / "PG_VERSION").write_text("16\n")
    now = datetime.now(UTC).replace(microsecond=0)
    started = now - timedelta(minutes=1)
    (directory / "postmaster.pid").write_text(
        f"123\n{directory}\n{int(started.timestamp())}\n4195\n\n127.0.0.1\n0\nready\n"
    )
    owner = dict(task=guard.TASK, owner=guard.OWNER, port=4195, data_directory=str(directory))
    owner_file = tmp_path / "artifacts/m3b2/cluster-owner.json"
    owner_file.write_text(json.dumps(owner))
    proof = dict(
        **owner,
        system_identifier=guard.SYSTEM_IDENTIFIER,
        server_version_num="160001",
        database="m3b2_remediation_fake_test",
        database_oid=456,
        database_owner="m3b2_admin",
        database_owner_oid=789,
        ownership_marker=guard.MARKER,
        postmaster_pid=123,
        postmaster_start_epoch=int(started.timestamp()),
        server_started_at=started.isoformat(),
        verified_at=now.isoformat(),
    )
    proof_file = tmp_path / guard.PROOF
    proof_file.parent.mkdir()
    proof_file.write_text(json.dumps(proof))
    actual = dict(
        **{
            k: proof[k]
            for k in (
                "database",
                "database_oid",
                "database_owner",
                "database_owner_oid",
                "ownership_marker",
                "system_identifier",
                "port",
                "data_directory",
            )
        },
        version="160001",
        read_only="on",
        address="127.0.0.1",
        connected_role="m3b2_admin",
        server_started_at=started,
    )
    trace = []

    class Connection:
        async def fetchrow(self, sql):
            assert sql.lstrip().startswith("SELECT")
            trace.append("metadata_select")
            return actual

        async def close(self):
            trace.append("close")

    async def connect(url, **kwargs):
        assert kwargs["server_settings"]["default_transaction_read_only"] == "on"
        trace.append("readonly_connect")
        return Connection()

    monkeypatch.setattr(guard.asyncpg, "connect", connect)
    return SimpleNamespace(
        root=tmp_path,
        proof=proof,
        actual=actual,
        proof_file=proof_file,
        owner_file=owner_file,
        directory=directory,
        trace=trace,
        url="postgresql://m3b2_admin@127.0.0.1:4195/" + proof["database"],
    )


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "owner",
        "system",
        "disk_system",
        "stale",
        "database",
        "incomplete",
        "directory",
        "pid",
        "pid_generation",
        "remote",
        "query",
    ],
)
async def test_invalid_disk_evidence_never_connects_or_mutates(owned, fault):
    o = owned
    proof = copy.deepcopy(o.proof)
    if fault == "missing":
        o.proof_file.unlink()
    elif fault == "owner":
        proof["owner"] = "forged-owner"
    elif fault == "system":
        proof["system_identifier"] = "1"
    elif fault == "disk_system":
        (o.directory / "global/pg_control").write_bytes(struct.pack("<Q", 1))
    elif fault == "stale":
        proof["verified_at"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    elif fault == "database":
        proof["database"] = "other_test"
    elif fault == "incomplete":
        del proof["database_oid"]
    elif fault == "directory":
        proof["data_directory"] = str(o.root)
    elif fault == "pid":
        (o.directory / "postmaster.pid").write_text("wrong\n")
    elif fault == "pid_generation":
        proof["postmaster_pid"] = 124
    elif fault == "remote":
        o.url = o.url.replace("127.0.0.1", "example.invalid")
    else:
        o.url += "?host=example.invalid"
    if fault != "missing":
        o.proof_file.write_text(json.dumps(proof))
    with pytest.raises(RuntimeError, match="disposable PostgreSQL"):
        await guard.verify_disposable(o.url, o.root)
    assert o.trace == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("system_identifier", "1"),
        ("database_oid", 999),
        ("database_owner_oid", 999),
        ("ownership_marker", "unowned"),
        ("data_directory", "/another"),
        ("version", "160002"),
        ("server_started_at", datetime(2000, 1, 1, tzinfo=UTC)),
        ("read_only", "off"),
    ],
)
async def test_live_identity_mismatch_only_executes_readonly_metadata(owned, field, value):
    o = owned
    o.actual[field] = value
    with pytest.raises(RuntimeError, match="live disposable PostgreSQL"):
        await guard.verify_disposable(o.url, o.root)
    assert o.trace == ["readonly_connect", "metadata_select", "close"]


@pytest.mark.parametrize("valid", [False, True])
async def test_shared_fixture_guard_finishes_before_any_store_write(owned, monkeypatch, valid):
    o = owned
    if not valid:
        o.actual["database_oid"] += 1
    monkeypatch.setenv("TEST_DATABASE_URL", o.url)

    async def verify(url, **kwargs):
        return await guard.verify_disposable(url, o.root, **kwargs)

    monkeypatch.setattr(conftest, "verify_disposable", verify)

    class Store:
        def __init__(self, settings):
            pass

        async def connect(self):
            o.trace.append("application_connect")

        def connection(self):
            return self

        def transaction(self, *, readonly):
            assert readonly
            return self

        async def fetchrow(self, sql):
            assert sql == guard.METADATA
            o.trace.append("pool_metadata_select")
            return o.actual

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def execute(self, sql):
            o.trace.append(sql.split()[0])

        async def register(self, registry):
            o.trace.append("register")

        async def close(self):
            o.trace.append("application_close")

    monkeypatch.setattr(conftest, "Store", Store)

    async def invoke():
        # This is pytest's dependency order: database_url resolves before store starts.
        url = await conftest.database_url.__wrapped__()
        setup = conftest.store.__wrapped__(url, object())
        await anext(setup)
        await setup.aclose()

    if valid:
        await invoke()
        assert o.trace[:4] == [
            "readonly_connect",
            "metadata_select",
            "close",
            "application_connect",
        ]
        assert o.trace.count("TRUNCATE") == 3
    else:
        with pytest.raises(RuntimeError, match="live disposable PostgreSQL"):
            await invoke()
        assert o.trace == ["readonly_connect", "metadata_select", "close"]


@pytest.mark.parametrize("pool_mismatch", [False, True])
def test_actual_pytest_fixture_dependency_order(owned, monkeypatch, request, pool_mismatch):
    o = owned
    monkeypatch.setenv("TEST_DATABASE_URL", o.url)

    async def verify(url, **kwargs):
        return await guard.verify_disposable(url, o.root, **kwargs)

    async def connect(self):
        o.trace.append("application_connect")
        if pool_mismatch:
            o.actual["database_oid"] += 1

    class Connection:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def transaction(self, *, readonly):
            assert readonly
            return self

        async def fetchrow(self, sql):
            assert sql == guard.METADATA
            o.trace.append("pool_metadata_select")
            return o.actual

        async def execute(self, sql):
            o.trace.append(sql.split()[0])

    async def register(self, registry):
        o.trace.append("register")

    async def close(self):
        o.trace.append("application_close")

    monkeypatch.setattr(conftest, "verify_disposable", verify)
    monkeypatch.setattr(conftest.Store, "connect", connect)
    monkeypatch.setattr(conftest.Store, "connection", lambda self: Connection())
    monkeypatch.setattr(conftest.Store, "register", register)
    monkeypatch.setattr(conftest.Store, "close", close)
    if pool_mismatch:
        with pytest.raises(RuntimeError, match="live disposable PostgreSQL"):
            request.getfixturevalue("store")
        assert o.trace == [
            "readonly_connect",
            "metadata_select",
            "close",
            "application_connect",
            "pool_metadata_select",
            "application_close",
        ]
        return
    assert request.getfixturevalue("store") is not None
    assert o.trace == [
        "readonly_connect",
        "metadata_select",
        "close",
        "application_connect",
        "pool_metadata_select",
        "TRUNCATE",
        "TRUNCATE",
        "TRUNCATE",
        "register",
    ]
