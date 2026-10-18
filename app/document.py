"""The public status document: the only shape that ever leaves the lab.

Every model forbids extra fields, so the JSON Schema generated from them
(`schema/status.schema.json`, `make schema`) sets additionalProperties: false
everywhere, and app.guard validates every document against that committed file
before it is published. A field that is not modelled here cannot be published.
"""

from __future__ import annotations

from datetime import datetime
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.topology import HardwareValue

SCHEMA_VERSION: Final = 1

State = Literal["ok", "degraded", "down", "unknown"]
Posture = Literal["ok", "degraded", "outage"]


class _Public(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Check(_Public):
    """One health probe attached to a node."""

    name: str
    group: str
    ok: bool
    checked_at: datetime | None
    response_ms: float | None


class Alert(_Public):
    """One firing warning or critical alert."""

    name: str
    severity: Literal["critical", "warning"]
    since: datetime | None
    summary: str | None


class Uptime(_Public):
    """Daily success ratios from the node's probes, oldest first."""

    days: int
    daily: list[float | None]
    ratio_30d: float | None
    ratio_90d: float | None


class Node(_Public):
    """A host, guest, device, or service, with its live state."""

    id: str
    name: str
    kind: str
    parent: str | None
    roles: list[str]
    summary: str | None
    platform: str | None
    hardware: dict[str, HardwareValue]
    addresses: list[str]
    vlan: int | None
    fqdns: list[str]
    state: State
    checks: list[Check]
    alerts: list[Alert]
    uptime: Uptime | None
    incident: str | None = Field(description="A /postmortems slug, when one explains the state")


class Network(_Public):
    """One VLAN and its subnet."""

    id: str
    name: str
    cidr: str
    vlan: int | None
    purpose: str | None


class Edge(_Public):
    """A directed relationship worth drawing."""

    source: str
    target: str
    flow: str


class Summary(_Public):
    """Counts the page can show without walking the node list."""

    nodes: int
    ok: int
    degraded: int
    down: int
    unknown: int
    alerts_firing: int


class StatusDocument(_Public):
    """The whole document, published as status/status.json."""

    schema_version: Literal[1]
    generated_at: datetime
    next_expected_at: datetime
    beacon_version: str
    topology_generated_at: str | None
    posture: Posture
    summary: Summary
    networks: list[Network]
    nodes: list[Node]
    edges: list[Edge]
    unattached_alerts: list[Alert]
