"""TSETMC routes inside the existing guarded company INGEST application."""

import hashlib
import hmac
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request

from marketdata.config import Settings
from marketdata.persistence import Store
from marketdata.replication import DestinationWriter, ReplicationError
from marketdata.tsetmc.wire import decode, validate
from marketdata.tsetmc.writer import Writer


def router(settings: Settings, store: Store) -> APIRouter:
    from marketdata.ingest_api import Rejection, body

    result = APIRouter(prefix="/api/ingest/v1/tsetmc")
    writer = Writer(store)

    @result.post("/batches", openapi_extra={"security": [{"ProducerBearer": []}]})
    async def upload(request: Request) -> dict[str, Any]:
        raw = await body(request, min(2097152, settings.ingest_max_body_bytes))
        hashes = request.headers.getlist("x-payload-sha256")
        if len(hashes) != 1 or not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), hashes[0]):
            raise Rejection(400, "payload_hash_mismatch")
        try:
            parsed = decode(raw)
            validate(parsed, "Batch")
            if len(parsed["records"]) > settings.ingest_max_records:
                raise Rejection(413, "record_limit_exceeded")
            return await writer.commit(request.state.principal, raw)
        except ReplicationError:
            raise
        except (ValueError, RecursionError):
            raise Rejection(422, "invalid_tsetmc_batch") from None

    @result.get("/receipts/{batch_id}", openapi_extra={"security": [{"ProducerBearer": []}]})
    async def receipt(request: Request, batch_id: UUID) -> dict[str, Any]:
        saved = await DestinationWriter(store).receipt(
            request.state.principal.producer_id, batch_id
        )
        if not saved or saved.get("contract_version") != "tsetmc.v1":
            raise Rejection(404, "receipt_not_found")
        return saved

    return result
