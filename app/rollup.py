"""State rules. Small on purpose: these are the sentences the page will explain.

- down: every probe of the node is failing.
- degraded: some probes fail, or a warning/critical alert is firing on it.
- ok: it has probes and they all pass, and nothing is firing.
- unknown: nothing observes it. Honest grey beats an invented green.

Posture: outage when any machine (host, vm, lxc, device) is down; degraded when
anything is degraded or down; otherwise ok.
"""

from __future__ import annotations

from collections.abc import Sequence
from statistics import fmean

from app.document import Posture, State
from app.live import CheckResult, FiringAlert

MACHINE_KINDS: frozenset[str] = frozenset({"host", "vm", "lxc", "device", "switch"})


def node_state(checks: Sequence[CheckResult], alerts: Sequence[FiringAlert]) -> State:
    """One node's state from its own probes and alerts (children do not roll up)."""
    passing = sum(1 for check in checks if check.success)
    if checks and passing == 0:
        return "down"
    if alerts or passing < len(checks):
        return "degraded"
    return "ok" if checks else "unknown"


def posture(states: Sequence[tuple[str, State]]) -> Posture:
    """The lab in one word, from (kind, state) pairs."""
    if any(state == "down" and kind in MACHINE_KINDS for kind, state in states):
        return "outage"
    if any(state in ("down", "degraded") for _, state in states):
        return "degraded"
    return "ok"


def merge_daily(series: Sequence[Sequence[float | None]], days: int) -> list[float | None]:
    """Average several probes' daily ratios into one; a day with no data stays None."""
    merged: list[float | None] = []
    for i in range(days):
        values: list[float] = []
        for s in series:
            value = s[i] if i < len(s) else None
            if value is not None:
                values.append(value)
        merged.append(round(fmean(values), 4) if values else None)
    return merged


def window_ratio(daily: Sequence[float | None], window: int) -> float | None:
    """Mean of the last `window` days that have data; None when none do."""
    values = [v for v in daily[-window:] if v is not None]
    return round(fmean(values), 5) if values else None
