from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
import respx

from app.sources.alerts import fetch_alerts
from app.sources.gatus import fetch_checks
from app.sources.metrics import fetch_daily_uptime
from tests.conftest import ALERTMANAGER, GATUS, METRICS, gatus_endpoint

NOW = datetime(2026, 10, 18, 18, 0, tzinfo=UTC)
TODAY = int(datetime(2026, 10, 18, tzinfo=UTC).timestamp())
DAY = 86_400


@respx.mock
async def test_gatus_takes_the_newest_result_and_skips_empty_endpoints() -> None:
    endpoint = gatus_endpoint("apps_x", "x", "apps", "x.test")
    endpoint["results"].insert(0, {"success": False, "timestamp": "2026-10-18T00:00:00Z"})
    respx.get(f"{GATUS}/api/v1/endpoints/statuses").respond(
        json=[endpoint, {"name": "y", "group": "apps", "key": "apps_y", "results": []}]
    )
    async with httpx.AsyncClient() as client:
        checks = await fetch_checks(client, GATUS)
    assert len(checks) == 1
    assert checks[0].success is True
    assert checks[0].response_ms == 12.5
    assert checks[0].checked_at is not None


@respx.mock
async def test_alerts_keep_only_warning_and_critical() -> None:
    route = respx.get(f"{ALERTMANAGER}/api/v2/alerts").respond(
        json=[
            {"labels": {"alertname": "Watchdog", "severity": "none"}},
            {"labels": {"alertname": "CPUThrottlingHigh", "severity": "info"}},
            {
                "labels": {"alertname": "PoolUnhealthy", "severity": "critical", "target": "m"},
                "annotations": {"summary": "pool2 DEGRADED"},
                "startsAt": "2026-10-17T16:10:00.000Z",
            },
        ]
    )
    async with httpx.AsyncClient() as client:
        alerts = await fetch_alerts(client, ALERTMANAGER)
    assert [a.name for a in alerts] == ["PoolUnhealthy"]
    assert alerts[0].summary == "pool2 DEGRADED"
    assert route.calls.last.request.url.params["silenced"] == "false"


@respx.mock
async def test_uptime_aligns_days_and_appends_today() -> None:
    respx.get(f"{METRICS}/api/v1/query_range").respond(
        json={
            "status": "success",
            "data": {
                "result": [
                    {
                        "metric": {"key": "apps_x"},
                        # days=4: complete days end at TODAY-2d, TODAY-1d, TODAY; one is missing
                        "values": [[TODAY - 2 * DAY, "1"], [TODAY, "0.5"]],
                    }
                ]
            },
        }
    )
    respx.get(f"{METRICS}/api/v1/query").respond(
        json={
            "status": "success",
            "data": {"result": [{"metric": {"key": "apps_x"}, "value": [0, "0.25"]}]},
        }
    )
    async with httpx.AsyncClient() as client:
        uptime = await fetch_daily_uptime(client, METRICS, 4, NOW)
    assert uptime == {"apps_x": [1.0, None, 0.5, 0.25]}


@respx.mock
async def test_uptime_raises_on_a_failed_query() -> None:
    respx.get(f"{METRICS}/api/v1/query_range").respond(json={"status": "error", "error": "bad"})
    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError, match="bad"):
            await fetch_daily_uptime(client, METRICS, 4, NOW)
