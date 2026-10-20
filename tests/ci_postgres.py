"""Positive ownership proof for this workflow's disposable GitHub service, never production."""

import argparse
import asyncio
import json
import os
import re
import struct
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from urllib.parse import urlsplit

import asyncpg
from disposable_postgres import METADATA, ROOT

PROOF = "artifacts/ci-postgres.json"
DATA = "/var/lib/postgresql/data"
TASK = "marketdata-disposable-ci"
IMAGES = {"false": "postgres:16.1", "true": "timescale/timescaledb:2.25.1-pg17"}


def context():
    run, attempt = os.environ.get("GITHUB_RUN_ID", ""), os.environ.get("GITHUB_RUN_ATTEMPT", "")
    mode = os.environ.get("MARKETDATA_CI_TIMESCALE", "")
    if (
        os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
        or os.environ.get("GITHUB_REPOSITORY", "").lower() != "alpha-lacrim/tradingview-marketdata"
        or os.environ.get("GITHUB_JOB") != "verify"
        or not re.fullmatch(r"[1-9][0-9]*", run)
        or not re.fullmatch(r"[1-9][0-9]*", attempt)
        or mode not in IMAGES
    ):
        raise RuntimeError("disposable CI context not approved")
    return f"{run}-{attempt}-{mode}", IMAGES[mode]


def docker(*args):
    return subprocess.check_output(["docker", *args], timeout=10)


@lru_cache(maxsize=4)
def physical(container, owner, image):
    # Container IDs, labels and mounts are immutable. Live SQL below fences every restart.
    if re.fullmatch(r"[a-f0-9]{64}", container) is None:
        raise RuntimeError("disposable CI container ID not approved")
    info = json.loads(docker("inspect", container))[0]
    labels = info["Config"]["Labels"]
    mounts = info["Mounts"]
    created = datetime.fromisoformat(info["Created"])
    valid = (
        info["Id"] == container
        and info["Config"]["Image"] == image
        and labels.get("marketdata.ci.task") == TASK
        and labels.get("marketdata.ci.owner") == owner
        and labels.get("marketdata.ci.repository", "").lower()
        == "alpha-lacrim/tradingview-marketdata"
        and info["State"]["Running"]
        and info["RestartCount"] == 0
        and timedelta(0) <= datetime.now(UTC) - created < timedelta(hours=8)
        and len(mounts) == 1
        and mounts[0]["Type"] == "volume"
        and mounts[0]["Destination"] == DATA
        and re.fullmatch(r"[a-f0-9]{64}", mounts[0]["Name"]) is not None
        and any(p["HostPort"] == "5432" for p in info["NetworkSettings"]["Ports"]["5432/tcp"])
    )
    if not valid:
        raise RuntimeError("disposable CI container ownership does not match")
    volume = json.loads(docker("volume", "inspect", mounts[0]["Name"]))[0]
    if (
        volume["Name"] != mounts[0]["Name"]
        or volume["Driver"] != "local"
        or datetime.fromisoformat(volume["CreatedAt"]) < created - timedelta(seconds=5)
    ):
        raise RuntimeError("disposable CI data volume is not newly owned")
    control = docker("exec", container, "cat", DATA + "/global/pg_control")
    pid = docker("exec", container, "cat", DATA + "/PG_VERSION", DATA + "/postmaster.pid")
    lines = pid.decode("utf-8").splitlines()
    if (
        lines[0] != ("16" if image == IMAGES["false"] else "17")
        or lines[2] != DATA
        or lines[4] != "5432"
        or lines[8].strip() != "ready"
    ):
        raise RuntimeError("disposable CI physical PostgreSQL identity does not match")
    return dict(
        container=container,
        image_id=info["Image"],
        volume=mounts[0]["Name"],
        system_identifier=str(struct.unpack("<Q", control[:8])[0]),
        postmaster_pid=int(lines[1]),
        postmaster_start_epoch=int(lines[3]),
        addresses=[n["IPAddress"] for n in info["NetworkSettings"]["Networks"].values()],
    )


def evidence(url, root=ROOT, *, container=None):
    try:
        owner, image = context()
        target = urlsplit(url)
        if (
            target.scheme != "postgresql"
            or target.hostname != "127.0.0.1"
            or target.port != 5432
            or target.username != "marketdata"
            or target.path != "/marketdata_test"
            or target.query
            or target.fragment
        ):
            raise ValueError("endpoint")
        if container is not None:
            return physical(container, owner, image) | {"ownership_marker": TASK + "/" + owner}
        proof = json.loads((root / PROOF).read_text("utf-8"))
        actual = physical(proof["container"], owner, image)
        if (
            any(proof[k] != v for k, v in actual.items())
            or proof["ownership_marker"] != TASK + "/" + owner
            or proof["database"] != "marketdata_test"
            or proof["database_owner"] != "marketdata"
            or type(proof["database_oid"]) is not int
            or proof["database_oid"] <= 0
            or type(proof["database_owner_oid"]) is not int
            or proof["database_owner_oid"] <= 0
            or proof["data_directory"] != DATA
            or proof["version"] != "160001"
            and not (image == IMAGES["true"] and 170000 <= int(proof["version"]) < 180000)
            or datetime.fromisoformat(proof["server_started_at"]).timestamp()
            < actual["postmaster_start_epoch"]
            or not timedelta(seconds=-5)
            <= datetime.now(UTC) - datetime.fromisoformat(proof["verified_at"])
            < timedelta(hours=8)
        ):
            raise ValueError("proof")
        return proof
    except (
        OSError,
        ValueError,
        KeyError,
        IndexError,
        TypeError,
        struct.error,
        subprocess.SubprocessError,
    ):
        raise RuntimeError("disposable CI ownership evidence missing or invalid") from None


def matching(actual, proof, *, initial=False):
    if not actual:
        return False
    fields = (
        ["system_identifier"]
        if initial
        else [
            "database",
            "database_oid",
            "database_owner",
            "database_owner_oid",
            "ownership_marker",
            "system_identifier",
            "version",
            "server_started_at",
        ]
    )
    return (
        all(str(actual[k]) == str(proof[k]) for k in fields)
        and actual["database"] == "marketdata_test"
        and actual["database_owner"] == actual["connected_role"] == "marketdata"
        and actual["database_oid"] > 0
        and actual["database_owner_oid"] > 0
        and actual["data_directory"] == DATA
        and actual["address"] in proof["addresses"]
        and actual["port"] == 5432
        and actual["read_only"] == "on"
        and actual["server_started_at"].timestamp() >= proof["postmaster_start_epoch"]
        and (
            actual["version"] == "160001"
            if os.environ["MARKETDATA_CI_TIMESCALE"] == "false"
            else 170000 <= int(actual["version"]) < 180000
        )
    )


async def verify(url, root=ROOT, *, connection=None):
    proof = await asyncio.to_thread(evidence, url, root)
    c = connection or await asyncpg.connect(
        url,
        timeout=5,
        command_timeout=5,
        server_settings={"default_transaction_read_only": "on", "statement_timeout": "5000"},
    )
    try:
        if not matching(await c.fetchrow(METADATA), proof):
            raise RuntimeError("live disposable CI PostgreSQL identity does not match")
    finally:
        if connection is None:
            await c.close()
    return url


async def prepare(url, container, root=ROOT):
    if await asyncio.to_thread((root / PROOF).exists):
        raise RuntimeError("disposable CI ownership proof already exists")
    proof = await asyncio.to_thread(evidence, url, root, container=container)
    c = await asyncpg.connect(
        url,
        timeout=5,
        command_timeout=5,
        server_settings={"default_transaction_read_only": "on", "statement_timeout": "5000"},
    )
    try:
        actual = await c.fetchrow(METADATA)
        if not matching(actual, proof, initial=True) or await c.fetchval(
            "SELECT count(*) FROM pg_tables WHERE schemaname='public'"
        ):
            raise RuntimeError("disposable CI database is not a fresh owned target")
        # Identity has passed physical/container/live checks before this first SQL mutation.
        sql = await c.fetchval(
            "SELECT format('COMMENT ON DATABASE %I IS %L',current_database(),$1::text)",
            proof["ownership_marker"],
        )
        await c.execute("SET default_transaction_read_only=off")
        await c.execute(sql)
        for key in [
            "database",
            "database_oid",
            "database_owner",
            "database_owner_oid",
            "version",
            "data_directory",
        ]:
            proof[key] = actual[key]
        proof["server_started_at"] = str(actual["server_started_at"])
        proof["verified_at"] = datetime.now(UTC).isoformat()
    finally:
        await c.close()

    def save():
        path = root / PROOF
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as file:
            json.dump(proof, file)

    await asyncio.to_thread(save)
    await verify(url, root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container")
    parser.add_argument("--alembic", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    url = os.environ["TEST_DATABASE_URL"]
    if os.environ.get("MARKETDATA_TEST_PROFILE") != "github-service" or url != os.environ.get(
        "DATABASE_URL"
    ):
        raise RuntimeError("explicit matching CI database profile required")
    if args.container and args.alembic is None:
        asyncio.run(prepare(url, args.container))
    else:
        asyncio.run(verify(url))
        if args.alembic:
            subprocess.run([sys.executable, "-m", "alembic", *args.alembic], check=True)


if __name__ == "__main__":
    main()
