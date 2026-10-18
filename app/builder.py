"""Merge the topology with live results into the public StatusDocument. Pure: no I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.attach import attach_alerts, attach_checks
from app.document import (
    SCHEMA_VERSION,
    Alert,
    Check,
    Edge,
    Network,
    Node,
    StatusDocument,
    Summary,
    Uptime,
)
from app.live import CheckResult, DailyUptime, FiringAlert
from app.rollup import merge_daily, node_state, posture, window_ratio
from app.topology import Topology, TopologyNode


@dataclass(frozen=True)
class LiveInputs:
    """Everything the sources returned this cycle. A failed source contributes nothing."""

    checks: list[CheckResult] = field(default_factory=list)
    alerts: list[FiringAlert] = field(default_factory=list)
    uptime: DailyUptime = field(default_factory=dict)


@dataclass(frozen=True)
class BuildContext:
    """When, how often, and which beacon built the document."""

    now: datetime
    interval: timedelta
    version: str
    days: int


def _alert(alert: FiringAlert) -> Alert:
    return Alert(name=alert.name, severity=alert.severity, since=alert.since, summary=alert.summary)


def _check(check: CheckResult) -> Check:
    return Check(
        name=check.name,
        group=check.group,
        ok=check.success,
        checked_at=check.checked_at,
        response_ms=check.response_ms,
    )


def _uptime(checks: list[CheckResult], daily: DailyUptime, days: int) -> Uptime | None:
    series = [daily[c.key] for c in checks if c.key in daily]
    if not series:
        return None
    merged = merge_daily(series, days)
    return Uptime(
        days=days,
        daily=merged,
        ratio_30d=window_ratio(merged, 30),
        ratio_90d=window_ratio(merged, 90),
    )


def _node(
    node: TopologyNode,
    checks: list[CheckResult],
    alerts: list[FiringAlert],
    live: LiveInputs,
    days: int,
) -> Node:
    return Node(
        id=node.id,
        name=node.name,
        kind=node.kind,
        parent=node.parent,
        roles=list(node.roles),
        summary=node.summary,
        platform=node.platform,
        hardware=dict(node.hardware),
        addresses=list(node.addresses),
        vlan=node.vlan,
        fqdns=list(node.fqdns),
        state=node_state(checks, alerts),
        checks=[_check(c) for c in checks],
        alerts=[_alert(a) for a in alerts],
        uptime=_uptime(checks, live.uptime, days),
        incident=None,
    )


def build_document(topology: Topology, live: LiveInputs, ctx: BuildContext) -> StatusDocument:
    """The document for this cycle. Orphan checks are the caller's to report."""
    checks_by_node, _ = attach_checks(topology.nodes, live.checks)
    alerts_by_node, unattached = attach_alerts(topology.nodes, live.alerts)
    nodes = [
        _node(n, checks_by_node.get(n.id, []), alerts_by_node.get(n.id, []), live, ctx.days)
        for n in topology.nodes
    ]
    states = [node.state for node in nodes]
    return StatusDocument(
        schema_version=SCHEMA_VERSION,
        generated_at=ctx.now,
        next_expected_at=ctx.now + ctx.interval,
        beacon_version=ctx.version,
        topology_version=topology.source_version,
        posture=posture([(node.kind, node.state) for node in nodes]),
        summary=Summary(
            nodes=len(nodes),
            ok=states.count("ok"),
            degraded=states.count("degraded"),
            down=states.count("down"),
            unknown=states.count("unknown"),
            alerts_firing=len(live.alerts),
        ),
        networks=[Network(**n.model_dump()) for n in topology.networks],
        nodes=nodes,
        edges=[Edge(**e.model_dump()) for e in topology.edges],
        unattached_alerts=[_alert(a) for a in unattached],
    )
