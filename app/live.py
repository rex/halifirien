"""What the live sources report, before it is attached to the topology."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

Severity = Literal["critical", "warning"]


class CheckResult(BaseModel):
    """The latest Gatus result for one endpoint."""

    model_config = ConfigDict(frozen=True)

    key: str
    name: str
    group: str
    hostname: str | None
    success: bool
    checked_at: datetime | None
    response_ms: float | None


class FiringAlert(BaseModel):
    """One active, unsilenced Alertmanager alert worth showing (warning or critical)."""

    model_config = ConfigDict(frozen=True)

    name: str
    severity: Severity
    since: datetime | None
    summary: str | None
    labels: dict[str, str]


DailyUptime = dict[str, list[float | None]]
"""Gatus key -> one success ratio per day, oldest first; None where there is no data."""
