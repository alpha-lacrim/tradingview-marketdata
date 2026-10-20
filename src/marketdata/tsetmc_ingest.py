"""Additive routes registered in the existing company INGEST factory only."""

import hashlib
import hmac
import re
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request

from marketdata.config import Settings
from marketdata.tsetmc_reconciliation import reconcile
from marketdata.tsetmc_storage import TsetmcWriter
from marketdata.tsetmc_wire import TsetmcError, decode, validate


def register(app: FastAPI, settings: Settings, writer: TsetmcWriter) -> None:
    # Import after ingest_api's definitions exist; body/guard remain the shared boundary.
    from marketdata.ingest_api import body

    def endpoint(stream: str) -> Callable[[Request], Awaitable[dict[str, Any]]]:
        async def upload(request: Request) -> dict[str, Any]:
            if not settings.tsetmc_ingest_enabled:
                raise TsetmcError("source_not_authorized", 403)
            payload = await body(request, settings.ingest_max_body_bytes)
            hashes = request.headers.getlist("x-payload-sha256")
            if len(hashes) != 1 or not re.fullmatch(r"[0-9a-f]{64}", hashes[0]):
                raise TsetmcError("payload_hash_required", 400)
            if not hmac.compare_digest(hashlib.sha256(payload).hexdigest(), hashes[0]):
                raise TsetmcError("payload_hash_mismatch", 400)
            batch = decode(payload)
            validate(batch, "Batch")
            if batch["stream"] != stream:
                raise TsetmcError("stream_mismatch")
            if len(batch["records"]) > settings.ingest_max_records:
                raise TsetmcError("record_limit_exceeded", 413)
            return await writer.commit(request.state.principal, payload)

        return upload

    for name in ("daily", "current", "coverage", "status"):
        app.add_api_route(
            "/api/ingest/v1/tsetmc/" + name, endpoint("tsetmc_" + name), methods=["POST"]
        )

    @app.post("/api/ingest/v1/tsetmc/reconcile")
    async def comparison(request: Request) -> dict[str, Any]:
        if not settings.tsetmc_ingest_enabled:
            raise TsetmcError("source_not_authorized", 403)
        payload = await body(request, min(262144, settings.ingest_max_body_bytes))
        return await reconcile(writer, request.state.principal, decode(payload))
