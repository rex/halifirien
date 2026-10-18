"""The beacon loop: collect, build, gate, publish, then wait for the next cycle."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx

from app.attach import attach_checks
from app.builder import BuildContext, LiveInputs, build_document
from app.config import Settings
from app.document import StatusDocument
from app.guard import render_public
from app.publisher import Publisher
from app.sources.alerts import fetch_alerts
from app.sources.gatus import fetch_checks
from app.sources.metrics import fetch_daily_uptime
from app.topology import load_topology

log = logging.getLogger("halifirien.runner")


@dataclass
class CycleReport:
    """What the last cycle did, for /api/health and /api/status. In-lab only."""

    started_at: datetime
    finished_at: datetime | None = None
    published: bool = False
    error: str | None = None
    source_errors: dict[str, str] = field(default_factory=dict)
    orphan_checks: list[str] = field(default_factory=list)


class Beacon:
    """Owns the cycle and remembers its outcome."""

    def __init__(self, settings: Settings, publisher: Publisher) -> None:
        self.settings = settings
        self.publisher = publisher
        self.started_at = datetime.now(UTC)
        self.document: StatusDocument | None = None
        self.last: CycleReport | None = None
        self.last_success_at: datetime | None = None
        self._lock = asyncio.Lock()

    async def _collect(self, now: datetime) -> tuple[LiveInputs, dict[str, str]]:
        s = self.settings
        async with httpx.AsyncClient(timeout=s.source_timeout_seconds) as client:
            checks, alerts, uptime = await asyncio.gather(
                fetch_checks(client, s.gatus_url),
                fetch_alerts(client, s.alertmanager_url),
                fetch_daily_uptime(client, s.metrics_url, s.uptime_days, now),
                return_exceptions=True,
            )
        errors: dict[str, str] = {}
        for name, result in (("gatus", checks), ("alertmanager", alerts), ("metrics", uptime)):
            if isinstance(result, BaseException):
                errors[name] = f"{type(result).__name__}: {result}"
                log.warning("source failed", extra={"source": name, "error": errors[name]})
        return (
            LiveInputs(
                checks=[] if isinstance(checks, BaseException) else checks,
                alerts=[] if isinstance(alerts, BaseException) else alerts,
                uptime={} if isinstance(uptime, BaseException) else uptime,
            ),
            errors,
        )

    async def run_once(self) -> CycleReport:
        """One full cycle. Never raises: the outcome is in the returned report."""
        async with self._lock:
            return await self._cycle()

    async def _cycle(self) -> CycleReport:
        now = datetime.now(UTC)
        report = CycleReport(started_at=now)
        try:
            topology = load_topology(self.settings.topology_path)
            live, report.source_errors = await self._collect(now)
            report.orphan_checks = [c.key for c in attach_checks(topology.nodes, live.checks)[1]]
            ctx = BuildContext(
                now=now,
                interval=timedelta(seconds=self.settings.interval_seconds),
                version=self.settings.app_version,
                days=self.settings.uptime_days,
            )
            document = build_document(topology, live, ctx)
            body = render_public(document)
            await self.publisher.publish(body)
            self.document = document
            report.published = True
            self.last_success_at = now
        except Exception as exc:
            report.error = f"{type(exc).__name__}: {exc}"
            log.exception("cycle failed")
        report.finished_at = datetime.now(UTC)
        self.last = report
        return report

    async def run_forever(self) -> None:
        """Cycle every interval_seconds until cancelled."""
        while True:
            report = await self.run_once()
            log.info(
                "cycle done",
                extra={"published": report.published, "target": self.publisher.target},
            )
            await asyncio.sleep(self.settings.interval_seconds)

    def healthy(self, now: datetime) -> tuple[bool, str | None]:
        """Healthy while a cycle has succeeded within two intervals (or we only just started)."""
        grace = timedelta(seconds=2 * self.settings.interval_seconds + 120)
        reference = self.last_success_at or self.started_at
        if now - reference <= grace:
            return True, None
        reason = self.last.error if self.last and self.last.error else "no successful cycle"
        return False, reason
