from __future__ import annotations

from datetime import UTC, datetime

from app.attach import attach_alerts, attach_checks
from app.live import CheckResult, FiringAlert
from app.rollup import merge_daily, node_state, posture, window_ratio
from app.topology import Topology
from tests.conftest import TOPOLOGY

NODES = Topology.model_validate(TOPOLOGY).nodes


def check(key: str, name: str, hostname: str | None, success: bool = True) -> CheckResult:
    return CheckResult(
        key=key,
        name=name,
        group="g",
        hostname=hostname,
        success=success,
        checked_at=datetime(2026, 10, 18, tzinfo=UTC),
        response_ms=1.0,
    )


def alert(severity: str = "critical", **labels: str) -> FiringAlert:
    return FiringAlert(
        name="X",
        severity="critical" if severity == "critical" else "warning",
        since=None,
        summary=None,
        labels={"alertname": "X", **labels},
    )


def test_checks_attach_by_declared_key_then_host_then_name() -> None:
    checks = [
        check("apps_ravenhill", "whatever", "elsewhere.test"),
        check("hosts_e", "erebor-proxmox", "10.9.0.8"),
        check("services_esgaroth", "esgaroth", "esgaroth.svc"),
        check("ring_api", "ring-api", "10.9.30.20"),
    ]
    attached, orphans = attach_checks(NODES, checks)
    assert [c.key for c in attached["ravenhill"]] == ["apps_ravenhill"]
    assert [c.key for c in attached["erebor"]] == ["hosts_e"]
    assert [c.key for c in attached["esgaroth"]] == ["services_esgaroth"]
    assert [c.key for c in orphans] == ["ring_api"]


def test_alerts_attach_by_label_priority_and_strip_ports() -> None:
    attached, unattached = attach_alerts(
        NODES,
        [
            alert(target="erebor", host="observer"),
            alert(namespace="ravenhill"),
            alert(instance="dale:9100"),
            alert(instance="nowhere:80"),
        ],
    )
    assert set(attached) == {"erebor", "ravenhill", "dale"}
    assert len(unattached) == 1


def test_node_state_rules() -> None:
    up, down = check("a", "a", None), check("b", "b", None, success=False)
    assert node_state([up], []) == "ok"
    assert node_state([down], []) == "down"
    assert node_state([up, down], []) == "degraded"
    assert node_state([up], [alert()]) == "degraded"
    assert node_state([], []) == "unknown"
    assert node_state([], [alert(severity="warning")]) == "degraded"


def test_posture_only_calls_an_outage_for_machines() -> None:
    assert posture([("host", "ok"), ("service", "ok")]) == "ok"
    assert posture([("host", "ok"), ("service", "down")]) == "degraded"
    assert posture([("host", "down"), ("service", "ok")]) == "outage"
    assert posture([("host", "unknown")]) == "ok"


def test_merge_daily_and_windows() -> None:
    merged = merge_daily([[1.0, None, 0.5], [0.5, None]], 3)
    assert merged == [0.75, None, 0.5]
    assert window_ratio(merged, 2) == 0.5
    assert window_ratio([None, None], 2) is None
