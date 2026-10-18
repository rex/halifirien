"""Alertmanager: active, unsilenced, uninhibited alerts at warning or critical."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

import httpx

from app.live import FiringAlert, Severity

ALERTS_PATH = "/api/v2/alerts"
SHOWN: frozenset[str] = frozenset({"critical", "warning"})


def _to_alert(raw: dict[str, Any]) -> FiringAlert | None:
    labels = {str(k): str(v) for k, v in (raw.get("labels") or {}).items()}
    severity = labels.get("severity", "")
    if severity not in SHOWN or "alertname" not in labels:
        return None
    started = raw.get("startsAt")
    annotations = raw.get("annotations") or {}
    return FiringAlert(
        name=labels["alertname"],
        severity=cast(Severity, severity),
        since=datetime.fromisoformat(started) if isinstance(started, str) else None,
        summary=annotations.get("summary"),
        labels=labels,
    )


async def fetch_alerts(client: httpx.AsyncClient, base_url: str) -> list[FiringAlert]:
    """Alerts a human would act on. Watchdog, info and none severities are left out."""
    response = await client.get(
        f"{base_url.rstrip('/')}{ALERTS_PATH}",
        params={"active": "true", "silenced": "false", "inhibited": "false"},
    )
    response.raise_for_status()
    alerts = (_to_alert(raw) for raw in response.json())
    return [alert for alert in alerts if alert is not None]
