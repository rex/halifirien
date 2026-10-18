"""VictoriaMetrics: daily uptime per Gatus endpoint, from the gatus_results_endpoint_success gauge.

Day N's ratio is the gauge's average over that UTC day. Complete days come from one
query_range (step 1d); today, still in progress, comes from one instant query over the
seconds since midnight. Missing days stay None: no data is not the same as down.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.live import DailyUptime

METRIC = "gatus_results_endpoint_success"
DAY = 86_400


def _midnight(now: datetime) -> datetime:
    return now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


def _series(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("status") != "success":
        raise ValueError(f"query failed: {payload.get('error', 'unknown error')}")
    result = payload.get("data", {}).get("result", [])
    return result if isinstance(result, list) else []


async def _get(client: httpx.AsyncClient, url: str, params: dict[str, str]) -> dict[str, Any]:
    response = await client.get(url, params=params)
    response.raise_for_status()
    body: dict[str, Any] = response.json()
    return body


async def fetch_daily_uptime(
    client: httpx.AsyncClient, base_url: str, days: int, now: datetime
) -> DailyUptime:
    """Gatus key -> `days` ratios, oldest first, the last one being today so far."""
    base = base_url.rstrip("/")
    today = _midnight(now)
    first_end = today - timedelta(days=days - 2)  # the end of the oldest complete day
    out: DailyUptime = {}

    ranged = await _get(
        client,
        f"{base}/api/v1/query_range",
        {
            "query": f"avg_over_time({METRIC}[1d])",
            "start": str(int(first_end.timestamp())),
            "end": str(int(today.timestamp())),
            "step": "1d",
        },
    )
    for series in _series(ranged):
        key = series.get("metric", {}).get("key")
        if not key:
            continue
        by_ts = {int(float(ts)): float(v) for ts, v in series.get("values", [])}
        out[key] = [
            by_ts.get(int((first_end + timedelta(days=i)).timestamp())) for i in range(days - 1)
        ]

    elapsed = max(int((now - today).total_seconds()), 60)
    instant = await _get(
        client,
        f"{base}/api/v1/query",
        {"query": f"avg_over_time({METRIC}[{elapsed}s])", "time": str(int(now.timestamp()))},
    )
    todays = {
        s.get("metric", {}).get("key"): float(s["value"][1])
        for s in _series(instant)
        if s.get("metric", {}).get("key")
    }
    for key in set(out) | set(todays):
        out.setdefault(key, [None] * (days - 1)).append(todays.get(key))
    return out
