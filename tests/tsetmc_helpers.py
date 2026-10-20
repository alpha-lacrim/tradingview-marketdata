"""Invented instrument/data helpers; no source imports, captures or network fetch."""

import copy
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4, uuid5

import pytest

from marketdata.ingest_auth import Principal
from marketdata.tsetmc_permissions import TABLES
from marketdata.tsetmc_registry import InstrumentBinding, provision, register
from marketdata.tsetmc_storage import TsetmcWriter
from marketdata.tsetmc_wire import STREAMS, canonical, decode, financial_hash, instrument_id

DIRECTORY = Path(__file__).parent / "fixtures/tsetmc_v1/examples"
A, B = "900000000000000001", "900000000000000002"


def example(name):
    return decode((DIRECTORY / (name + ".json")).read_bytes())


async def imported_rows(store):
    tables = ["company_tsetmc." + name for name in TABLES] + [
        "ingest_observations",
        "ingest_batches",
        "marketdata_events",
        "marketdata_event_clock",
    ]
    async with store.connection() as c:
        return {
            table: sorted(await c.fetch("SELECT * FROM " + table), key=repr) for table in tables
        }


@pytest.fixture
async def tsetmc(store):
    # The shared database_url guard completes before store can truncate/register anything.
    async with store.connection() as c:
        legacy_head = await c.fetchval("SELECT head FROM marketdata_event_clock")
        units = example("daily.request")["records"][0]["observation"]["units"]
        for code in (A, B):
            await register(
                c,
                InstrumentBinding(
                    ins_code=code,
                    source_instrument_id="SYNTHETIC-EQUITY-" + code,
                    display_name="Synthetic " + code,
                    exchange="SYNTHETIC",
                    units=units,
                    approval_evidence="synthetic-test-only",
                ),
                activate=True,
            )
        producer, session = uuid4(), uuid4()
        epochs = {A: uuid4(), B: uuid4()}
        plan = dict(
            producer_id=str(producer),
            session_id=str(session),
            key_id="synthetic_tsetmc",
            label="synthetic-test-only",
            allowed_statuses=["unknown"],
            streams=[
                dict(
                    instrument_id=str(instrument_id(code)),
                    provider="tsetmc",
                    stream=stream,
                    source_epoch=str(epochs[code]),
                    ownership_generation=1,
                )
                for code in (A, B)
                for stream in STREAMS
            ],
        )
        await provision(c, plan)
        await c.execute(
            """UPDATE ingest_producers SET session_expires_at=clock_timestamp()+interval '1 hour'
            WHERE producer_id=$1""",
            producer,
        )

    def batch(name="daily", *, code=A, position=None, **changes):
        value = copy.deepcopy(example(name + ".request"))
        value.update(
            producer_id=str(producer),
            session_id=str(session),
            source_epoch=str(epochs[code]),
            instrument_id=str(instrument_id(code)),
            batch_id=str(uuid4()),
        )
        for record in value["records"]:
            observation = record["observation"]
            observation.update(
                ins_code=code,
                provider_symbol=code,
                canonical_symbol="TSETMC:" + code,
                instrument_id=str(instrument_id(code)),
                source_instrument_id="SYNTHETIC-EQUITY-" + code,
            )
            if position is not None:
                record["source_position"] = str(position)
                if record["kind"] == "current":
                    observation["state_version"] = str(position)
            record["observation_id"] = str(
                uuid5(epochs[code], value["stream"] + ":" + record["source_position"])
            )
            if "measurements" in observation:
                observation["financial_hash"] = financial_hash(observation)
            if observation.get("review"):
                observation["review"]["reviewed_financial_hash"] = observation["financial_hash"]
            if observation.get("revision_evidence"):
                for side in ("old", "new"):
                    observation["revision_evidence"][side + "_financial_hash"] = financial_hash(
                        observation, observation["revision_evidence"][side + "_measurements"]
                    )
        value.update(changes)
        return value

    return SimpleNamespace(
        store=store,
        writer=TsetmcWriter(store),
        principal=Principal(producer, "synthetic_tsetmc"),
        producer=producer,
        session=session,
        epochs=epochs,
        batch=batch,
        encode=canonical,
        identity=instrument_id,
        legacy_head=legacy_head,
    )
