"""Shared fixtures: a small synthetic lab, and settings pointing at fake sources."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.config import Settings

GATUS = "http://gatus.test"
METRICS = "http://metrics.test"
ALERTMANAGER = "http://alertmanager.test"

TOPOLOGY: dict[str, Any] = {
    "generated_at": "2026-10-18T12:00:00Z",
    "source_version": "0.0.0",
    "networks": [
        {"id": "lan", "name": "LAN", "cidr": "10.9.0.0/24", "vlan": 1, "purpose": "hosts"},
        {"id": "ring", "name": "Ring", "cidr": "10.9.30.0/24", "vlan": 30, "purpose": None},
    ],
    "nodes": [
        {
            "id": "erebor",
            "name": "erebor",
            "kind": "host",
            "roles": ["hypervisor"],
            "platform": "Proxmox VE 9.2",
            "hardware": {"model": "PowerEdge R730", "cores": 40},
            "addresses": ["10.9.0.8"],
            "vlan": 1,
            "fqdns": ["erebor.lab.test"],
        },
        {
            "id": "dale",
            "name": "dale",
            "kind": "vm",
            "parent": "erebor",
            "addresses": ["10.9.30.21"],
            "vlan": 30,
        },
        {
            "id": "ravenhill",
            "name": "ravenhill",
            "kind": "service",
            "parent": "dale",
            "summary": "Photo library",
            "fqdns": ["ravenhill.lab.test"],
            "checks": ["apps_ravenhill"],
            "future_field": "ignored by the beacon",
        },
        {"id": "esgaroth", "name": "esgaroth", "kind": "lxc", "parent": "erebor"},
    ],
    "edges": [{"source": "ravenhill", "target": "dale", "flow": "data"}],
}


def gatus_endpoint(
    key: str, name: str, group: str, hostname: str, success: bool = True
) -> dict[str, Any]:
    """One /api/v1/endpoints/statuses entry with a single result."""
    return {
        "name": name,
        "group": group,
        "key": key,
        "results": [
            {
                "hostname": hostname,
                "duration": 12_500_000,
                "success": success,
                "timestamp": "2026-10-18T18:30:34.221151491Z",
            }
        ],
    }


@pytest.fixture
def topology_path(tmp_path: Path) -> Path:
    path = tmp_path / "topology.json"
    path.write_text(json.dumps(TOPOLOGY), encoding="utf-8")
    return path


@pytest.fixture
def settings(topology_path: Path) -> Settings:
    return Settings(
        topology_path=topology_path,
        gatus_url=GATUS,
        metrics_url=METRICS,
        alertmanager_url=ALERTMANAGER,
        uptime_days=5,
        interval_seconds=900,
        app_version="9.9.9",
    )
