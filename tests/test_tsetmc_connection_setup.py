import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from uuid import uuid4

import pytest


def test_private_handoff_matches_and_never_regenerates_existing_identity(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "connection_setup", "scripts/prepare_tsetmc_connection.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    target = tmp_path / "private"
    args = argparse.Namespace(
        endpoint="https://company.example",
        ins_code="900000000000000001",
        destination_id=str(uuid4()),
        display_name="Synthetic",
        exchange="SYNTHETIC",
        output=target,
    )
    module.prepare(args)

    def read(name):
        return json.loads((target / name).read_text(encoding="utf8"))

    company, worker, source = (
        read("company-plan.json"),
        read("worker.json"),
        read("source-binding.json"),
    )
    assert company["producer"]["producer_id"] == worker["producer_id"] == source["producer_id"]
    assert company["destination_id"] == worker["destination_id"] == source["destination_id"]
    assert {s["source_epoch"] for s in company["producer"]["streams"]} == {source["source_epoch"]}
    assert (
        read("producer-credential.json")[0]["token_sha256"]
        == hashlib.sha256(Path(worker["token_file"]).read_bytes()).hexdigest()
    )
    with pytest.raises(ValueError, match="already exists"):
        module.prepare(args)


@pytest.mark.integration
async def test_generated_plan_provisions_the_company_mapping(store, tmp_path):
    from marketdata.tsetmc.admin import setup

    spec = importlib.util.spec_from_file_location(
        "connection_setup", "scripts/prepare_tsetmc_connection.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    async with store.connection() as c:
        destination = str(await c.fetchval("SELECT destination_id FROM ingest_destination_state"))
    target = tmp_path / "handoff"
    module.prepare(
        argparse.Namespace(
            endpoint="https://company.example",
            ins_code="900000000000000001",
            destination_id=destination,
            display_name="Synthetic",
            exchange="SYNTHETIC",
            output=target,
        )
    )
    dsn = tmp_path / "admin-dsn"
    dsn.write_text(store.settings.database_url.get_secret_value())
    await setup(dsn, target / "company-plan.json")
    async with store.connection() as c:
        assert (
            await c.fetchval("SELECT count(*) FROM ingest_source_owners WHERE provider='tsetmc'")
            == 4
        )
        assert (
            await c.fetchval(
                "SELECT asset_class FROM instruments "
                "WHERE canonical_symbol='TSETMC:900000000000000001'"
            )
            == "equity"
        )
