from __future__ import annotations

from datetime import UTC, datetime, timedelta

import boto3
import httpx
import pytest
import respx
from moto import mock_aws

from app.config import Settings
from app.main import create_app
from app.publisher import NullPublisher, S3Publisher
from app.runner import Beacon
from tests.conftest import ALERTMANAGER, GATUS, METRICS, gatus_endpoint

EMPTY_QUERY = {"status": "success", "data": {"result": []}}


class RecordingPublisher:
    target = "memory"

    def __init__(self) -> None:
        self.bodies: list[bytes] = []

    async def publish(self, body: bytes) -> None:
        self.bodies.append(body)


def mock_sources(gatus_ok: bool = True) -> None:
    gatus = respx.get(f"{GATUS}/api/v1/endpoints/statuses")
    if gatus_ok:
        gatus.respond(json=[gatus_endpoint("apps_ravenhill", "ravenhill", "apps", "r.test")])
    else:
        gatus.mock(side_effect=httpx.ConnectError("refused"))
    respx.get(f"{ALERTMANAGER}/api/v2/alerts").respond(json=[])
    respx.get(f"{METRICS}/api/v1/query_range").respond(json=EMPTY_QUERY)
    respx.get(f"{METRICS}/api/v1/query").respond(json=EMPTY_QUERY)


@respx.mock
async def test_a_cycle_publishes_the_gated_document(settings: Settings) -> None:
    mock_sources()
    publisher = RecordingPublisher()
    beacon = Beacon(settings, publisher)
    report = await beacon.run_once()
    assert report.published
    assert report.error is None
    assert len(publisher.bodies) == 1
    assert beacon.document is not None
    states = {n.id: n.state for n in beacon.document.nodes}
    assert states == {
        "erebor": "unknown",
        "dale": "unknown",
        "ravenhill": "ok",
        "esgaroth": "unknown",
    }


@respx.mock
async def test_a_dead_source_degrades_to_unknown_but_still_publishes(settings: Settings) -> None:
    mock_sources(gatus_ok=False)
    beacon = Beacon(settings, RecordingPublisher())
    report = await beacon.run_once()
    assert report.published
    assert "gatus" in report.source_errors
    assert beacon.document is not None
    assert beacon.document.summary.unknown == 4


@respx.mock
async def test_a_missing_topology_fails_the_cycle_without_publishing(settings: Settings) -> None:
    mock_sources()
    settings.topology_path.unlink()
    publisher = RecordingPublisher()
    beacon = Beacon(settings, publisher)
    report = await beacon.run_once()
    assert not report.published
    assert report.error is not None
    assert publisher.bodies == []
    later = datetime.now(UTC) + timedelta(hours=1)
    assert beacon.healthy(later) == (False, report.error)


async def test_health_is_ok_during_startup_grace(settings: Settings) -> None:
    beacon = Beacon(settings, NullPublisher())
    assert beacon.healthy(datetime.now(UTC)) == (True, None)


@respx.mock
async def test_routes_report_health_status_and_run_a_cycle(settings: Settings) -> None:
    mock_sources()
    app = create_app(settings, start_loop=False)
    app.state.beacon = Beacon(settings, NullPublisher())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://beacon.test") as client:
        assert (await client.get("/api/health")).json()["status"] == "ok"
        assert (await client.post("/api/cycle")).json() == {"published": True, "error": None}
        status = (await client.get("/api/status")).json()
    assert status["target"] == "dry-run"
    assert status["document"]["posture"] == "ok"
    assert status["last_cycle"]["orphan_checks"] == []


async def test_s3_publisher_puts_json_with_cache_headers() -> None:
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="site")
        publisher = S3Publisher("site", "status/status.json", "public, max-age=60", client=client)
        await publisher.publish(b"{}")
        obj = client.get_object(Bucket="site", Key="status/status.json")
    assert obj["Body"].read() == b"{}"
    assert obj["CacheControl"] == "public, max-age=60"
    assert obj["ContentType"].startswith("application/json")


def test_s3_publisher_refuses_an_empty_bucket() -> None:
    with pytest.raises(ValueError, match="S3_BUCKET"):
        S3Publisher("", "k", "c", client=None)
