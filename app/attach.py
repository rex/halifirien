"""Attach live results to topology nodes.

Checks match in order: a key the node declares (the renderer knows every stack's Gatus
key), then the probe's hostname against a node's addresses and FQDNs, then the endpoint
name against a node id. Alerts match on the first of their labels, in ALERT_LABELS
order, whose value is a node id. Anything left over is reported, never guessed at.
"""

from __future__ import annotations

from collections import defaultdict

from app.live import CheckResult, FiringAlert
from app.topology import TopologyNode

ALERT_LABELS: tuple[str, ...] = (
    "target",
    "namespace",
    "job",
    "kubernetes_io_hostname",
    "host",
    "instance",
)


def _host_index(nodes: list[TopologyNode]) -> dict[str, str]:
    index: dict[str, str] = {}
    for node in nodes:
        for name in (*node.addresses, *node.fqdns):
            index.setdefault(name.lower(), node.id)
    return index


def attach_checks(
    nodes: list[TopologyNode], checks: list[CheckResult]
) -> tuple[dict[str, list[CheckResult]], list[CheckResult]]:
    """Node id -> its checks, plus the checks no node claimed."""
    declared = {key: node.id for node in nodes for key in node.checks}
    by_host = _host_index(nodes)
    ids = {node.id for node in nodes}
    attached: dict[str, list[CheckResult]] = defaultdict(list)
    orphans: list[CheckResult] = []
    for check in checks:
        host = (check.hostname or "").lower()
        node_id = (
            declared.get(check.key)
            or by_host.get(host)
            or (check.name if check.name in ids else None)
        )
        if node_id is None:
            orphans.append(check)
        else:
            attached[node_id].append(check)
    return dict(attached), orphans


def _alert_target(alert: FiringAlert, ids: set[str]) -> str | None:
    for label in ALERT_LABELS:
        value = alert.labels.get(label)
        if value is None:
            continue
        value = value.split(":", 1)[0]  # instance labels carry a port
        if value in ids:
            return value
    return None


def attach_alerts(
    nodes: list[TopologyNode], alerts: list[FiringAlert]
) -> tuple[dict[str, list[FiringAlert]], list[FiringAlert]]:
    """Node id -> its alerts, plus the alerts that name no node."""
    ids = {node.id for node in nodes}
    attached: dict[str, list[FiringAlert]] = defaultdict(list)
    unattached: list[FiringAlert] = []
    for alert in alerts:
        target = _alert_target(alert, ids)
        if target is None:
            unattached.append(alert)
        else:
            attached[target].append(alert)
    return dict(attached), unattached
