"""Gatus: the latest result of every endpoint the ring probes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.live import CheckResult

STATUSES_PATH = "/api/v1/endpoints/statuses"


def _parse_time(raw: object) -> datetime | None:
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _to_check(endpoint: dict[str, Any]) -> CheckResult | None:
    results = endpoint.get("results") or []
    if not results:
        return None
    last = results[-1]
    duration_ns = last.get("duration")
    return CheckResult(
        key=str(endpoint["key"]),
        name=str(endpoint.get("name", endpoint["key"])),
        group=str(endpoint.get("group", "")),
        hostname=last.get("hostname"),
        success=bool(last.get("success", False)),
        checked_at=_parse_time(last.get("timestamp")),
        response_ms=round(duration_ns / 1_000_000, 1) if isinstance(duration_ns, int) else None,
    )


async def fetch_checks(client: httpx.AsyncClient, base_url: str) -> list[CheckResult]:
    """Every endpoint's most recent result. Endpoints with no results yet are skipped."""
    response = await client.get(f"{base_url.rstrip('/')}{STATUSES_PATH}")
    response.raise_for_status()
    checks = (_to_check(endpoint) for endpoint in response.json())
    return [check for check in checks if check is not None]
