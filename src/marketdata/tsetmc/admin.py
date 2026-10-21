"""Atomic first-install setup over the audited administrative binding interface."""

import argparse
import asyncio
import json
from pathlib import Path
from uuid import UUID

import asyncpg

from marketdata.tsetmc_registry import InstrumentBinding, provision, register
from marketdata.tsetmc_wire import instrument_id


async def setup(dsn_file: Path, plan_file: Path) -> None:
    plan = json.loads(await asyncio.to_thread(plan_file.read_text, encoding="utf8"))
    binding = InstrumentBinding.model_validate(
        {
            k: plan[k]
            for k in (
                "ins_code",
                "display_name",
                "exchange",
                "source_instrument_id",
                "units",
                "approval_evidence",
            )
        }
    )
    identity = str(instrument_id(binding.ins_code))
    streams = plan["producer"]["streams"]
    if len(streams) != 4 or any(s["instrument_id"] != identity for s in streams):
        raise ValueError("single instrument manifest required")
    dsn = (await asyncio.to_thread(dsn_file.read_text)).strip()
    c = await asyncpg.connect(dsn)
    try:
        async with c.transaction():
            if await c.fetchval("SELECT version_num FROM alembic_version") != "0011":
                raise ValueError("audited destination 0011 required")
            if await c.fetchval("SELECT destination_id FROM ingest_destination_state") != UUID(
                plan["destination_id"]
            ):
                raise ValueError("destination identity mismatch")
            await register(c, binding, activate=True)
            await provision(c, plan["producer"])
    finally:
        await c.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn-file", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    try:
        asyncio.run(setup(args.dsn_file, args.plan))
    except Exception as error:
        print(json.dumps({"error": type(error).__name__}))
        return 1
    print('{"producer_created":true}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
