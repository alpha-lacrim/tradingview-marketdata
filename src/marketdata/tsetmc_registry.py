"""Explicit administrative additions to a populated company registry.

These functions require administrator SQL permissions. Runtime INGEST cannot call
them successfully. No existing identity, ownership, credential or epoch is replaced.
"""

import json
import re
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from marketdata.ingest_grants import Grant
from marketdata.tsetmc_wire import STREAMS, instrument_id, validate


class InstrumentBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    ins_code: str = Field(pattern=r"^[1-9][0-9]{0,19}$")
    source_instrument_id: str | None = Field(max_length=64)
    display_name: str = Field(min_length=1, max_length=256)
    exchange: str = Field(min_length=1, max_length=100)
    units: dict[str, Any]
    approval_evidence: str = Field(min_length=1, max_length=256)
    asset_class: str = Field(default="equity", pattern="^equity$")
    instrument_type: str = Field(default="common_stock", pattern="^common_stock$")

    @model_validator(mode="after")
    def unit_profile(self) -> Self:
        validate(self.units, "Units")
        if self.units["confidence"] == "verified" and not self.units["evidence_ref"]:
            raise ValueError("verified units require explicit evidence")
        return self


async def register(c: Any, binding: InstrumentBinding, *, activate: bool = False) -> None:
    identity = instrument_id(binding.ins_code)
    symbol = "TSETMC:" + binding.ins_code
    async with c.transaction():
        await c.execute(
            """SELECT pg_advisory_xact_lock(hashtextextended($1,0))""",
            "tsetmc:registry:" + binding.ins_code,
        )
        if await c.fetchval(
            """SELECT EXISTS(SELECT 1 FROM instruments WHERE id=$1 OR
canonical_symbol=$2)""",
            identity,
            symbol,
        ):
            raise ValueError("binding already exists; administrative comparison required")
        payload = dict(
            canonical_symbol=symbol,
            display_name=binding.display_name,
            asset_class="equity",
            instrument_type="common_stock",
            exchange=binding.exchange,
            currency="IRR",
            active=activate,
            metadata={},
            base_asset=None,
            quote_asset=None,
            root_symbol=None,
            contract_code=None,
            contract_month=None,
            expiry=None,
            roll_at=None,
            tick_size=None,
            multiplier=None,
        )
        await c.execute(
            """INSERT INTO
instruments(id,canonical_symbol,display_name,asset_class,instrument_type,exchange,currency,active,metadata,payload)
VALUES($1,$2,$3,'equity','common_stock',$4,'IRR',$5,'{}'::jsonb,$6::jsonb)""",
            identity,
            symbol,
            binding.display_name,
            binding.exchange,
            activate,
            json.dumps(payload),
        )
        await c.execute(
            """INSERT INTO
provider_instruments(instrument_id,provider,provider_symbol,realtime_status,metadata)
VALUES($1,'tsetmc',$2,'unknown','{}'::jsonb)""",
            identity,
            binding.ins_code,
        )
        await c.execute(
            """INSERT INTO
company_tsetmc.instrument_links(instrument_id,ins_code,source_instrument_id,units,approval_evidence,enabled)
VALUES($1,$2,$3,$4::jsonb,$5,$6)""",
            identity,
            binding.ins_code,
            binding.source_instrument_id,
            json.dumps(binding.units),
            binding.approval_evidence,
            activate,
        )


async def provision(c: Any, plan: dict[str, Any]) -> None:
    required = {"producer_id", "label", "key_id", "session_id", "streams", "allowed_statuses"}
    if set(plan) != required or plan["allowed_statuses"] != ["unknown"]:
        raise ValueError("explicit unknown-only TSETMC policy required")
    grants = [Grant.model_validate(s) for s in plan["streams"]]
    if not 1 <= len(grants) <= 1000 or any(
        g.provider != "tsetmc" or g.stream not in STREAMS or g.ownership_generation != 1
        for g in grants
    ):
        raise ValueError("initial TSETMC grants required; no handover")
    scopes = {(g.instrument_id, g.stream) for g in grants}
    by_instrument: dict[UUID, UUID] = {}
    for grant in grants:
        if (
            grant.instrument_id in by_instrument
            and by_instrument[grant.instrument_id] != grant.source_epoch
        ):
            raise ValueError("one approved epoch per instrument required")
        by_instrument[grant.instrument_id] = grant.source_epoch
    if len(scopes) != len(grants) or len(set(by_instrument.values())) != len(by_instrument):
        raise ValueError("distinct instrument epochs and unique grants required")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", plan["key_id"]):
        raise ValueError("invalid key ID")
    async with c.transaction():
        for identity in by_instrument:
            if not await c.fetchval(
                """SELECT EXISTS(SELECT 1 FROM company_tsetmc.instrument_links WHERE
instrument_id=$1)""",
                identity,
            ):
                raise ValueError("approved TSETMC binding required")
        await c.execute(
            """INSERT INTO
ingest_producers(producer_id,label,credential_key_id,session_id,session_generation,session_expires_at)
VALUES($1,$2,$3,$4,1,clock_timestamp()+interval '120 seconds')""",
            UUID(plan["producer_id"]),
            plan["label"],
            plan["key_id"],
            UUID(plan["session_id"]),
        )
        for grant in grants:
            await c.execute(
                """INSERT INTO
ingest_source_owners(instrument_id,provider,stream,producer_id,source_epoch,ownership_generation,allowed_statuses)
VALUES($1,'tsetmc',$2,$3,$4,1,ARRAY['unknown'])""",
                grant.instrument_id,
                grant.stream,
                UUID(plan["producer_id"]),
                grant.source_epoch,
            )
