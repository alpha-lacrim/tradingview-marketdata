"""Read capacity is enforced before any database access."""

import httpx
import pytest
from fastapi import FastAPI

from marketdata.config import Settings
from marketdata.tsetmc.api import router


@pytest.mark.parametrize(
    "path,params",
    [
        ("instruments", {}),
        ("daily", {"start": "2026-01-01", "end": "2026-02-01"}),
        ("coverage", {}),
        ("changes", {"after": "unused"}),
    ],
)
async def test_tsetmc_respects_configured_page_capacity_before_sql(path, params):
    app = FastAPI()
    app.include_router(router(Settings(_env_file=None, api_max_rows=10)))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/tsetmc/" + path,
            params={"ins_code": "900000000000000001", "limit": 11, **params},
        )
    assert response.status_code == 422
    assert response.json()["detail"] == "page capacity exceeded"
