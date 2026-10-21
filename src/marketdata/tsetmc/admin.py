"""Explicit first-install equity mapping and producer provisioning (no collection)."""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from pydantic import SecretStr

from marketdata.config import Settings
from marketdata.domain import (
    AssetClass,
    DataStatus,
    Instrument,
    InstrumentType,
    ProviderInstrument,
    RegistryEntry,
)
from marketdata.persistence import Store
from marketdata.registry import Registry
from marketdata.release_admin import provision


async def setup(dsn_file: Path, plan_file: Path) -> None:
    plan = json.loads(await asyncio.to_thread(plan_file.read_text, encoding="utf8"))
    options: dict[str, Any] = {
        "_env_file": None,
        "database_url": SecretStr((await asyncio.to_thread(dsn_file.read_text)).strip()),
    }
    store = Store(Settings(**options))
    try:
        await store.connect()
        async with store.connection() as c:
            if await c.fetchval("SELECT version_num FROM alembic_version") != "0011":
                raise ValueError("destination 0011 required")
            if (
                str(await c.fetchval("SELECT destination_id FROM ingest_destination_state"))
                != plan["destination_id"]
            ):
                raise ValueError("destination identity mismatch")
        instrument = Instrument(
            canonical_symbol="TSETMC:" + plan["ins_code"],
            display_name=plan["display_name"],
            asset_class=AssetClass.EQUITY,
            instrument_type=InstrumentType.COMMON_STOCK,
            exchange=plan["exchange"],
            currency="IRR",
            metadata={"units_confidence": "unverified"},
        )
        if not plan["ins_code"].isdigit() or not 1 <= len(plan["ins_code"]) <= 20:
            raise ValueError("invalid ins_code")
        producer = plan["producer"]
        if producer["allowed_statuses"] != ["unknown"]:
            raise ValueError("TSETMC delivery status must remain unknown")
        if (
            len(producer["streams"]) != 4
            or {s["stream"] for s in producer["streams"]}
            != {"tsetmc_daily", "tsetmc_current", "tsetmc_coverage", "tsetmc_status"}
            or any(
                s["instrument_id"] != str(instrument.id) or s["provider"] != "tsetmc"
                for s in producer["streams"]
            )
        ):
            raise ValueError("single-instrument TSETMC manifest required")
        await store.register(
            Registry(
                [
                    RegistryEntry(
                        instrument=instrument,
                        mappings=[
                            ProviderInstrument(
                                provider="tsetmc",
                                provider_symbol=plan["ins_code"],
                                realtime_status=DataStatus.UNKNOWN,
                            )
                        ],
                    )
                ]
            )
        )
        async with store.connection() as c:
            await provision(c, producer)
        print(json.dumps({"instrument_id": str(instrument.id), "producer_created": True}))
    finally:
        await store.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn-file", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    try:
        asyncio.run(setup(args.dsn_file, args.plan))
        return 0
    except Exception as error:
        print(json.dumps({"error": type(error).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
