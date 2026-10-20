"""CI ownership and fixture dispatch checks use only instrumented fake connections."""

import copy
import json
import struct
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import ci_postgres as ci
import disposable_postgres as guard
import pytest


@pytest.fixture
def service(tmp_path, monkeypatch):
    for key, value in dict(
        GITHUB_ACTIONS="true",
        RUNNER_ENVIRONMENT="github-hosted",
        GITHUB_REPOSITORY="alpha-lacrim/tradingview-marketdata",
        GITHUB_JOB="verify",
        GITHUB_RUN_ID="123",
        GITHUB_RUN_ATTEMPT="1",
        MARKETDATA_CI_TIMESCALE="false",
        MARKETDATA_TEST_PROFILE="github-service",
    ).items():
        monkeypatch.setenv(key, value)
    now = datetime.now(UTC).replace(microsecond=0)
    started = now - timedelta(minutes=1)
    container, volume = "a" * 64, "b" * 64
    info = dict(
        Id=container,
        Image="sha256:" + "c" * 64,
        Created=started.isoformat(),
        Config=dict(
            Image=ci.IMAGES["false"],
            Labels={
                "marketdata.ci.task": ci.TASK,
                "marketdata.ci.owner": "123-1-false",
                "marketdata.ci.repository": "alpha-lacrim/tradingview-marketdata",
            },
        ),
        State=dict(Running=True),
        RestartCount=0,
        Mounts=[dict(Type="volume", Destination=ci.DATA, Name=volume)],
        NetworkSettings=dict(
            Ports={"5432/tcp": [dict(HostPort="5432")]},
            Networks={"task": dict(IPAddress="172.18.0.2")},
        ),
    )
    disk = dict(Name=volume, Driver="local", CreatedAt=started.isoformat())
    actual = dict(
        database="marketdata_test",
        database_oid=42,
        database_owner="marketdata",
        database_owner_oid=10,
        ownership_marker=ci.TASK + "/123-1-false",
        connected_role="marketdata",
        version="160001",
        data_directory=ci.DATA,
        read_only="on",
        address="172.18.0.2",
        port=5432,
        server_started_at=started,
        system_identifier="1234567890",
    )
    trace = []

    def docker(*args):
        trace.append("docker:" + args[0])
        if args == ("inspect", container):
            return json.dumps([info]).encode()
        if args == ("volume", "inspect", volume):
            return json.dumps([disk]).encode()
        if args == ("exec", container, "cat", ci.DATA + "/global/pg_control"):
            return struct.pack("<Q", 1234567890)
        assert args == (
            "exec",
            container,
            "cat",
            ci.DATA + "/PG_VERSION",
            ci.DATA + "/postmaster.pid",
        )
        return f"16\n123\n{ci.DATA}\n{int(started.timestamp())}\n5432\n\n*\n0\nready\n".encode()

    class Connection:
        async def fetchrow(self, sql):
            assert sql == guard.METADATA
            trace.append("metadata_select")
            return actual

        async def fetchval(self, sql, *args):
            assert sql.lstrip().startswith("SELECT")
            trace.append("select")
            if "pg_tables" in sql:
                return 0
            return "COMMENT ON DATABASE marketdata_test IS 'owned'"

        async def execute(self, sql):
            trace.append(sql)
            if sql.startswith("COMMENT"):
                actual["ownership_marker"] = ci.TASK + "/123-1-false"

        async def close(self):
            trace.append("close")

    async def connect(url, **kwargs):
        assert kwargs["server_settings"]["default_transaction_read_only"] == "on"
        trace.append("readonly_connect")
        return Connection()

    monkeypatch.setattr(ci, "docker", docker)
    monkeypatch.setattr(ci.asyncpg, "connect", connect)
    ci.physical.cache_clear()
    physical = ci.physical(container, *ci.context())
    proof = physical | {k: str(v) if isinstance(v, datetime) else v for k, v in actual.items()}
    proof["verified_at"] = now.isoformat()
    path = tmp_path / ci.PROOF
    path.parent.mkdir()
    path.write_text(json.dumps(proof))
    ci.physical.cache_clear()
    trace.clear()
    yield SimpleNamespace(
        root=tmp_path,
        info=info,
        disk=disk,
        actual=actual,
        proof=proof,
        path=path,
        trace=trace,
        container=container,
        connection=Connection(),
        url="postgresql://marketdata:marketdata@127.0.0.1:5432/marketdata_test",
    )
    ci.physical.cache_clear()


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "stale",
        "incomplete",
        "owner",
        "container_id",
        "container_label",
        "repository",
        "bind_mount",
        "old_volume",
        "wrong_image",
        "stopped",
        "remote",
        "query",
        "context_only",
        "unknown_profile",
    ],
)
async def test_invalid_ci_proof_cannot_connect_or_write(service, monkeypatch, fault):
    s = service
    proof = copy.deepcopy(s.proof)
    if fault == "missing":
        s.path.unlink()
    elif fault == "stale":
        proof["verified_at"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    elif fault == "incomplete":
        del proof["database_oid"]
    elif fault == "owner":
        proof["ownership_marker"] = "forged"
    elif fault == "container_id":
        proof["container"] = "not-a-container"
    elif fault == "container_label":
        s.info["Config"]["Labels"]["marketdata.ci.owner"] = "another-job"
    elif fault == "repository":
        s.info["Config"]["Labels"]["marketdata.ci.repository"] = "another/repo"
    elif fault == "bind_mount":
        s.info["Mounts"][0]["Type"] = "bind"
    elif fault == "old_volume":
        s.disk["CreatedAt"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    elif fault == "wrong_image":
        s.info["Config"]["Image"] = "postgres:latest"
    elif fault == "stopped":
        s.info["State"]["Running"] = False
    elif fault == "remote":
        s.url = s.url.replace("127.0.0.1", "example.invalid")
    elif fault == "query":
        s.url += "?host=example.invalid"
    elif fault == "context_only":
        monkeypatch.setenv("RUNNER_ENVIRONMENT", "self-hosted")
    else:
        monkeypatch.setenv("MARKETDATA_TEST_PROFILE", "bypass")
    if fault != "missing":
        s.path.write_text(json.dumps(proof))
    with pytest.raises(RuntimeError, match="disposable"):
        await guard.verify_disposable(s.url, s.root)
    assert "readonly_connect" not in s.trace
    assert not any(x.startswith(("TRUNCATE", "DROP", "COMMENT", "SET")) for x in s.trace)


@pytest.mark.parametrize(
    "field,value",
    [
        ("database_oid", 999),
        ("database_owner_oid", 999),
        ("ownership_marker", "other"),
        ("system_identifier", "1"),
        ("server_started_at", datetime(2000, 1, 1, tzinfo=UTC)),
        ("data_directory", "/other"),
        ("version", "170007"),
        ("read_only", "off"),
        ("address", "172.18.0.3"),
    ],
)
async def test_ci_live_mismatch_permits_only_metadata_select(service, field, value):
    s = service
    s.actual[field] = value
    with pytest.raises(RuntimeError, match="live disposable CI"):
        await guard.verify_disposable(s.url, s.root)
    assert [x for x in s.trace if not x.startswith("docker:")] == [
        "readonly_connect",
        "metadata_select",
        "close",
    ]


async def test_ci_actual_pooled_connection_is_verified_without_reconnect(service):
    s = service
    assert await guard.verify_disposable(s.url, s.root, connection=s.connection) == s.url
    assert [x for x in s.trace if not x.startswith("docker:")] == ["metadata_select"]
    s.actual["database_oid"] += 1
    with pytest.raises(RuntimeError, match="live disposable CI"):
        await guard.verify_disposable(s.url, s.root, connection=s.connection)
    assert "readonly_connect" not in s.trace


@pytest.mark.parametrize("fault", ["label", "live", "existing_proof", "valid"])
async def test_ci_bootstrap_fences_first_mutation(service, fault):
    s = service
    if fault != "existing_proof":
        s.path.unlink()
    s.actual["ownership_marker"] = None
    if fault == "label":
        s.info["Config"]["Labels"]["marketdata.ci.owner"] = "other"
    elif fault == "live":
        s.actual["system_identifier"] = "other"
    if fault == "valid":
        await ci.prepare(s.url, s.container, s.root)
        assert s.path.exists()
        assert any(x.startswith("COMMENT") for x in s.trace)
        assert s.trace.index("metadata_select") < s.trace.index(
            "SET default_transaction_read_only=off"
        )
        assert await guard.verify_disposable(s.url, s.root) == s.url
    else:
        with pytest.raises(RuntimeError, match="disposable CI"):
            await ci.prepare(s.url, s.container, s.root)
        assert not any(x.startswith(("SET", "COMMENT", "TRUNCATE", "DROP")) for x in s.trace)
