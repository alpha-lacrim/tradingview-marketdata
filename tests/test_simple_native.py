"""Native installation contract, idempotence, corrections and dashboard compatibility."""

import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit
from uuid import uuid4

import asyncpg
import httpx
import pytest
from pydantic import ValidationError

from marketdata.simple_api import chart, create_app
from marketdata.simple_delivery import PendingUpload, single_instance
from marketdata.simple_models import Observation
from marketdata.simple_store import SimpleStore, initialize


def observation(**overrides):
    return dict(
        market="tradingview",
        symbol="TEST:ABC",
        interval="1m",
        time=1784246400,
        received_at="2026-07-17T00:00:00Z",
        open="1.000000000000000001",
        close="2",
        high="3",
        low="1",
        volume="12.5",
        **overrides,
    )


def body(rows):
    return json.dumps({"batch_id": str(uuid4()), "observations": rows}, separators=(",", ":"))


@pytest.mark.parametrize(
    "field,value",
    [
        ("open", 1.5),
        ("close", "NaN"),
        ("received_at", "2026-01-01T00:00:00"),
        ("time", 1784246401),
        ("high", "0"),
        ("count", -1),
    ],
)
def test_invalid_observations(field, value):
    raw = observation()
    raw[field] = value
    with pytest.raises(ValidationError):
        Observation.model_validate(raw)


def test_chart_arrays_exact_mapping_and_partial_metrics():
    a = Observation.model_validate(observation()).model_dump(mode="json")
    b = dict(a, time=a["time"] + 60, open="2", close="2.5", high="4", low="1.5", volume=None)
    result, omitted, placeholders = chart([{"time": r["time"], "data": r} for r in [a, b]], 300)
    assert result == {
        "a": [1784246400],
        "b": [1.0],
        "c": [2.5],
        "d": [4.0],
        "e": [1.0],
        "f": [0],
        "g": [0.0],
        "h": [0.0],
        "i": None,
    }
    assert omitted == 0 and placeholders == 3
    a["open"] = None
    assert chart([{"time": a["time"], "data": a}], 60)[1] == 1


def test_tsetmc_official_close_can_exceed_executed_range():
    raw = observation()
    raw.update(market="tsetmc", symbol="123", interval="1d", close="10")
    Observation.model_validate(raw)
    raw["interval"] = "1m"
    with pytest.raises(ValidationError):
        Observation.model_validate(raw)


async def test_durable_upload_retry_and_receipt_validation(tmp_path):
    uploads = []

    async def respond(request):
        uploads.append(request.content)
        if len(uploads) == 1:
            raise httpx.ReadTimeout("response lost after server commit")
        data = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "batch_id": data["batch_id"],
                "accepted": len(data["observations"]),
                "sha256": hashlib.sha256(request.content).hexdigest(),
            },
        )

    path = tmp_path / "pending.json"
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        pending = PendingUpload("http://company:8000", path, client)
        pending.stage([observation()])
        with pytest.raises(httpx.ReadTimeout):
            await pending.flush()
        assert path.exists()
        with pytest.raises(RuntimeError):
            pending.stage([observation()])
        with pytest.raises(ValueError, match="another API URL"):
            await PendingUpload("http://other", path, client).flush()
        await PendingUpload("http://company:8000", path, client).flush()
        assert uploads[0] == uploads[1] and not path.exists()
        pending.stage([observation()])
        with pytest.raises(ValueError, match="receipt"):
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(lambda _: httpx.Response(200, json={}))
            ) as bad:
                await PendingUpload("http://company:8000", path, bad).flush()
        assert path.exists()


def test_collector_directory_single_owner(tmp_path):
    with single_instance(tmp_path):
        with pytest.raises(OSError), single_instance(tmp_path):
            pass
    with single_instance(tmp_path):
        pass


@pytest.fixture
async def native_store():
    url = os.getenv("SIMPLE_TEST_DATABASE_URL")
    if not url:
        pytest.skip("set SIMPLE_TEST_DATABASE_URL to a disposable native profile database")
    parsed = urlsplit(url)
    assert parsed.hostname in {"127.0.0.1", "localhost"}
    assert parsed.path.startswith("/simple_native_") and parsed.path.endswith("_test")
    conn = await asyncpg.connect(url)
    try:
        marker = await conn.fetchval("""SELECT shobj_description(oid,'pg_database')
            FROM pg_database WHERE datname=current_database()""")
        assert marker == "native-simple-disposable-tests"
    finally:
        await conn.close()
    await initialize(url)
    store = SimpleStore(url)
    await store.connect()
    try:
        await store.pool.execute("""TRUNCATE simple_marketdata.records,
            simple_marketdata.changes,simple_marketdata.receipts RESTART IDENTITY""")
        yield store
    finally:
        await store.close()


async def test_postgres_http_retry_correction_precision_order_and_chart(native_store):
    store = native_store
    app = create_app(store=store)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://company"
    ) as http:
        raw = body([observation()])
        first = await http.post("/api/ingest", content=raw)
        assert first.status_code == 200
        assert (await http.post("/api/ingest", content=raw)).json() == first.json()
        conflicting = json.loads(raw)
        conflicting["observations"][0]["close"] = "2.5"
        assert (await http.post("/api/ingest", json=conflicting)).status_code == 409
        rows = await store.rows("tradingview", "TEST:ABC", "1m", 0, 2000000000, 10)
        assert rows[0]["data"]["open"] == "1.000000000000000001"
        assert await store.pool.fetchval("SELECT count(*) FROM simple_marketdata.changes") == 1
        corrected = observation()
        corrected.update(close="2.5", received_at="2026-07-18T00:00:00Z")
        assert (await http.post("/api/ingest", content=body([corrected]))).status_code == 200
        assert (await http.post("/api/ingest", content=body([observation()]))).status_code == 200
        params = dict(market="tradingview", symbol="TEST:ABC", start=1784246400, end=1784246460)
        chart_result = await http.get("/api/chart", params=params)
        assert chart_result.json() == {
            "a": [1784246400],
            "b": [1.0],
            "c": [2.5],
            "d": [3.0],
            "e": [1.0],
            "f": [0],
            "g": [12.5],
            "h": [0.0],
            "i": None,
        }
        assert chart_result.headers["x-zero-placeholders"] == "2"
        assert await store.pool.fetchval("SELECT count(*) FROM simple_marketdata.changes") == 2
        corrected["received_at"] = "2026-07-19T00:00:00Z"
        await http.post("/api/ingest", content=body([corrected]))
        assert await store.pool.fetchval("SELECT count(*) FROM simple_marketdata.changes") == 2
        assert (await http.get("/api/chart", params=dict(params, market="tsetmc"))).json()[
            "a"
        ] == []
        assert (await http.get("/api/instruments")).json()[0]["symbol"] == "TEST:ABC"
        changes = (
            await http.get("/api/changes", params=dict(market="tradingview", symbol="TEST:ABC"))
        ).json()
        assert changes["cursor"] == 2 and len(changes["items"]) == 2
        preflight = await http.options(
            "/api/chart",
            headers={"Origin": "http://dashboard", "Access-Control-Request-Method": "GET"},
        )
        assert preflight.headers["access-control-allow-origin"] == "*"


async def test_latest_never_regresses_event_time_and_token_is_optional(native_store, monkeypatch):
    monkeypatch.setenv("SIMPLE_UPLOAD_TOKEN", "test-token")
    app = create_app(store=native_store)
    now = datetime.now(UTC)
    quote = dict(
        market="tsetmc",
        symbol="123",
        interval="quote",
        time=0,
        received_at=now.isoformat(),
        event_at=(now - timedelta(days=1)).isoformat(),
        last="42",
        official_close="43",
        status="unknown",
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://company"
    ) as http:
        assert (await http.post("/api/ingest", content=body([quote]))).status_code == 401
        headers = {"Authorization": "Bearer test-token"}
        assert (
            await http.post("/api/ingest", content=body([quote]), headers=headers)
        ).status_code == 200
        quote.update(
            received_at=(now + timedelta(seconds=1)).isoformat(),
            event_at=(now - timedelta(days=2)).isoformat(),
            last="1",
        )
        await http.post("/api/ingest", content=body([quote]), headers=headers)
        latest = (await http.get("/api/latest", params=dict(market="tsetmc", symbol="123"))).json()
        assert latest["data"]["last"] == "42" and latest["data"]["official_close"] == "43"
        quote.update(received_at=(now + timedelta(seconds=2)).isoformat(), event_at=None)
        await http.post("/api/ingest", content=body([quote]), headers=headers)
        preserved = (
            await http.get("/api/latest", params=dict(market="tsetmc", symbol="123"))
        ).json()
        assert preserved["data"]["last"] == "42"
        assert latest["source_age_seconds"] >= 86400
        assert latest["receive_age_seconds"] < 5


async def test_batch_validation_is_atomic(native_store):
    bad = observation()
    bad["open"] = "NaN"
    app = create_app(store=native_store)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://company"
    ) as http:
        result = await http.post("/api/ingest", content=body([observation(), bad]))
        assert result.status_code == 422
    assert await native_store.pool.fetchval("SELECT count(*) FROM simple_marketdata.records") == 0


def test_upload_schema_is_available_to_dashboard_developers():
    app = create_app("postgresql://unused")
    schema = app.openapi()
    body_schema = schema["paths"]["/api/ingest"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert (
        body_schema["properties"]["observations"]["items"]["$ref"]
        == "#/components/schemas/Observation"
    )
    assert "received_at" in schema["components"]["schemas"]["Observation"]["required"]


@pytest.mark.parametrize("permanent", [False, True])
async def test_one_shot_reports_per_source_failure(monkeypatch, tmp_path, permanent):
    from types import SimpleNamespace

    from marketdata import simple_collector as collector

    pair = (
        SimpleNamespace(canonical_symbol="TEST:ABC"),
        SimpleNamespace(provider_symbol="TEST:ABC"),
    )

    class Provider:
        async def subscribe(self, pairs):
            pass

        async def connect(self):
            pass

        async def disconnect(self):
            pass

        async def fetch_many(self, jobs):
            error = collector.PermanentConnectionError if permanent else RuntimeError
            return {"TEST:ABC": error("provider unavailable")}

    monkeypatch.setattr(
        collector.Registry, "load", lambda _: SimpleNamespace(subscriptions=lambda _: [pair])
    )
    monkeypatch.setattr(collector, "TradingViewCandleProvider", lambda *_: Provider())
    args = SimpleNamespace(
        registry=None,
        history_minutes=30,
        api_url="http://localhost:8000",
        state_dir=tmp_path,
        once=True,
    )
    error_type = collector.PermanentConnectionError if permanent else RuntimeError
    match = "provider unavailable" if permanent else "history failed for 1 sources"
    with pytest.raises(error_type, match=match):
        await collector.run(args)


@pytest.mark.parametrize("once", [False, True])
@pytest.mark.parametrize("failure_count", [1, 3])
async def test_history_handshake_eof_retries_without_stopping_collector(
    monkeypatch, tmp_path, once, failure_count
):
    import asyncio
    from types import SimpleNamespace

    from websockets.exceptions import InvalidMessage

    from marketdata import simple_collector as collector

    pair = (
        SimpleNamespace(canonical_symbol="TEST:ABC"),
        SimpleNamespace(provider_symbol="TEST:ABC"),
    )
    recovered = asyncio.Event()
    attempts = []
    closed = []
    sleeps = []
    real_sleep = asyncio.sleep

    class Provider:
        async def subscribe(self, pairs):
            pass

        async def connect(self):
            attempts.append(self)
            if len(attempts) <= failure_count:
                self.effective_concurrency = 1
                raise InvalidMessage("did not receive a valid HTTP response") from EOFError()

        async def disconnect(self):
            closed.append(self)

        async def fetch_many(self, jobs):
            recovered.set()
            return {"TEST:ABC": []}

    class Quotes(Provider):
        async def connect(self):
            pass

        async def disconnect(self):
            pass

        async def stream_ticks(self):
            await asyncio.Event().wait()
            if False:
                yield

    async def sleep(seconds):
        sleeps.append(seconds)
        await real_sleep(0)

    monkeypatch.setattr(
        collector.Registry, "load", lambda _: SimpleNamespace(subscriptions=lambda _: [pair])
    )
    monkeypatch.setattr(collector, "TradingViewCandleProvider", lambda *_: Provider())
    monkeypatch.setattr(collector, "TradingViewGuestProvider", lambda *_: Quotes())
    monkeypatch.setattr(collector.asyncio, "sleep", sleep)
    args = SimpleNamespace(
        registry=None,
        history_minutes=30,
        api_url="http://localhost:8000",
        state_dir=tmp_path,
        once=once,
    )
    if once:
        with pytest.raises(InvalidMessage):
            await collector.run(args)
        assert len(attempts) == len(closed) == 1
    else:
        task = asyncio.create_task(collector.run(args))
        ready = asyncio.create_task(recovered.wait())
        try:
            done, _ = await asyncio.wait(
                [task, ready], timeout=2, return_when=asyncio.FIRST_COMPLETED
            )
            if task in done:
                task.result()
            assert recovered.is_set()
            assert len(attempts) >= 2 and attempts[0] in closed
            assert 60 in sleeps
            assert attempts[-1].effective_concurrency == 1
            if failure_count == 3:
                assert 120 in sleeps and 240 in sleeps
        finally:
            task.cancel()
            ready.cancel()
            await asyncio.gather(task, ready, return_exceptions=True)


@pytest.mark.parametrize("failure", [TimeoutError, OSError, asyncpg.InterfaceError])
async def test_api_database_failures_return_retryable_503(failure):
    from contextlib import asynccontextmanager

    class Unavailable(SimpleStore):
        @asynccontextmanager
        async def connection(self):
            raise failure("private connection detail")
            yield

    store = Unavailable("unused")
    store.pool = object()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(create_app(store=store)), base_url="http://company"
    ) as http:
        for path in [
            "/health",
            "/api/instruments",
            "/api/latest?market=tradingview&symbol=TEST:ABC",
        ]:
            response = await http.get(path)
            assert response.status_code == 503
            assert response.json() == {"detail": "database unavailable"}
            assert response.headers["retry-after"] == "30"
        assert (await http.get("/openapi.json")).status_code == 200


async def test_pool_exhaustion_returns_503_then_recovers(native_store):
    connections = [await native_store.pool.acquire() for _ in range(10)]
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(create_app(store=native_store)), base_url="http://company"
    ) as http:
        try:
            response = await http.get("/health")
            assert response.status_code == 503
        finally:
            for conn in connections:
                await native_store.pool.release(conn)
        assert (await http.get("/health")).status_code == 200


def test_websocket_database_failure_closes_for_reconnect():
    from contextlib import asynccontextmanager

    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    class Unavailable(SimpleStore):
        @asynccontextmanager
        async def connection(self):
            raise TimeoutError()
            yield

    store = Unavailable("unused")
    store.pool = object()
    client = TestClient(create_app(store=store))
    with client.websocket_connect("/api/ws?market=tradingview&symbol=TEST:ABC") as ws:
        with pytest.raises(WebSocketDisconnect) as caught:
            ws.receive_json()
        assert caught.value.code == 1013


@pytest.mark.parametrize(
    "update",
    [
        {"open": "-1"},
        {"last": "-1"},
        {"official_close": "-1"},
        {"open": "4"},
        {"last": "4"},
        {"official_close": "2.5"},
        {"symbol": "1" * 31},
        {"event_at": "2026-07-17T00:06:00Z"},
    ],
)
def test_tsetmc_upload_rejects_invalid_measurements(update):
    row = observation()
    row.update(market="tsetmc", symbol="123", interval="1d", official_close="2")
    row.update(update)
    with pytest.raises(ValidationError):
        Observation.model_validate(row)


def test_tsetmc_upload_preserves_close_semantics_zero_activity_and_staleness():
    row = observation()
    row.update(
        market="tsetmc",
        symbol="123",
        interval="1d",
        close="10",
        official_close="10",
        event_at="2026-07-15T09:00:00Z",
    )
    assert Observation.model_validate(row).close == 10
    row.update(count=0, volume="0", open="0", last="0")
    assert Observation.model_validate(row).open == 0
    row.update(
        open=None,
        close=None,
        high=None,
        low=None,
        last=None,
        official_close=None,
        volume=None,
        count=None,
    )
    with pytest.raises(ValidationError, match="no observed measurements"):
        Observation.model_validate(row)


async def test_tsetmc_bad_upload_is_atomic(native_store):
    row = observation()
    row.update(market="tsetmc", symbol="123", interval="1d")
    bad = dict(row, time=row["time"] + 86400, last="-1")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(create_app(store=native_store)), base_url="http://company"
    ) as http:
        assert (await http.post("/api/ingest", content=body([row, bad]))).status_code == 422
    assert await native_store.pool.fetchval("SELECT count(*) FROM simple_marketdata.records") == 0


async def test_instrument_directory_pages_and_names(native_store):
    rows = [
        dict(observation(), market="tsetmc", symbol=str(10000 + i), interval="1d")
        for i in range(1002)
    ]
    quote = dict(
        rows[0], interval="quote", time=0, last="2", metadata={"display_name": "Synthetic share"}
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(create_app(store=native_store)), base_url="http://company"
    ) as http:
        assert (await http.post("/api/ingest", content=body(rows + [quote]))).status_code == 200
        page = (await http.get("/api/instruments?market=tsetmc")).json()
        assert len(page) == 1000 and page[0]["display_name"] == "Synthetic share"
        tail = (await http.get("/api/instruments?market=tsetmc&offset=1000")).json()
        assert [r["symbol"] for r in tail] == ["11000", "11001"]
        assert (await http.get("/api/instruments?market=tradingview")).json() == []
        assert (await http.get("/api/instruments?offset=-1")).status_code == 422


def test_coverage_reports_absence_without_inventing_market_sessions():
    from marketdata.simple_api import coverage

    result = coverage([{"time": 60}, {"time": 180}], 0, 300, 60)
    assert result["unobserved_ranges"] == [
        {"start": 0, "end": 60},
        {"start": 120, "end": 180},
        {"start": 240, "end": 300},
    ]
    assert result["completeness"] == "unverified"
    assert coverage([], 1, 59, 60)["unobserved_ranges"] == []


async def test_chart_partial_bucket_and_coverage_api(native_store):
    row = observation()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(create_app(store=native_store)), base_url="http://company"
    ) as http:
        assert (await http.post("/api/ingest", content=body([row]))).status_code == 200
        params = dict(
            market=row["market"], symbol=row["symbol"], start=row["time"], end=row["time"] + 300
        )
        response = await http.get("/api/chart", params=dict(params, interval="5m"))
        assert response.status_code == 200
        assert response.headers["X-Partial-Buckets"] == "1"
        response = await http.get("/api/coverage", params=params)
        assert response.status_code == 200
        result = response.json()
        assert result["stored_bars"] == 1
        assert result["unobserved_ranges"] == [
            {"start": row["time"] + 60, "end": row["time"] + 300}
        ]
