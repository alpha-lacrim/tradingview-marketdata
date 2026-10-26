"""Collector traffic counters count submitted retries and survive restarts."""

import hashlib
import json

import httpx

from marketdata.simple_delivery import PendingUpload
from marketdata.simple_traffic import TrafficMeter


async def test_traffic_counts_upload_retries_and_persists(tmp_path):
    meter = TrafficMeter(tmp_path / "traffic.json")
    meter.frame("source_received", "قیمت")
    meter.frame("source_sent", b"request")
    requests = []

    def respond(request):
        requests.append(request.content)
        if len(requests) == 1:
            return httpx.Response(503, text="retry")
        batch = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "batch_id": batch["batch_id"],
                "sha256": hashlib.sha256(request.content).hexdigest(),
                "accepted": 1,
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        pending = PendingUpload("http://company", tmp_path / "history.json", http, meter)
        pending.stage([{"synthetic": True}])
        try:
            await pending.flush()
        except httpx.HTTPStatusError:
            pass
        assert pending.path.exists()
        await pending.flush()
    assert requests[0] == requests[1]
    assert meter.bytes["api_sent"] == 2 * len(requests[0])
    assert meter.bytes["api_received"] > 0
    assert meter.bytes["source_received"] == len("قیمت".encode())
    meter.report()
    assert TrafficMeter(tmp_path / "traffic.json").bytes == meter.bytes
