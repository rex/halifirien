"""The lab's static shape, as homelab-inventory renders it (tools/render_halifirien_topology.py).

The file arrives through a ConfigMap. It is trusted input from our own renderer, but it is
still validated: unknown fields are ignored (the renderer may grow before the beacon does),
and only the fields modelled here can ever reach the public document.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

HardwareValue = str | int | float | bool | None


class TopologyNetwork(BaseModel):
    """One L3 network: a VLAN and its subnet."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str
    name: str
    cidr: str
    vlan: int | None = None
    purpose: str | None = None


class TopologyNode(BaseModel):
    """A host, guest, device, or service, with what the inventory knows about it."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str
    name: str
    kind: str
    parent: str | None = None
    roles: list[str] = Field(default_factory=list)
    summary: str | None = None
    platform: str | None = None
    hardware: dict[str, HardwareValue] = Field(default_factory=dict)
    addresses: list[str] = Field(default_factory=list)
    vlan: int | None = None
    fqdns: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)


class TopologyEdge(BaseModel):
    """A physical link worth drawing (ethernet, dac, usb, power), from the inventory's cabling."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    source: str
    target: str
    flow: str
    speed_mbps: int | None = None


class Topology(BaseModel):
    """The whole rendered inventory projection. Deterministic: versioned, never timestamped."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    source_version: str | None = None
    networks: list[TopologyNetwork] = Field(default_factory=list)
    nodes: list[TopologyNode] = Field(default_factory=list)
    edges: list[TopologyEdge] = Field(default_factory=list)


def load_topology(path: Path) -> Topology:
    """Read and validate the rendered topology. Raises on a missing or malformed file."""
    return Topology.model_validate(json.loads(path.read_text(encoding="utf-8")))
