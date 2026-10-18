"""In-lab HTTP surface: health for Gatus and the kubelet, status for previewing the document."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.runner import Beacon

router = APIRouter(prefix="/api")


def get_beacon(request: Request) -> Beacon:
    """The process's Beacon, set on app.state by the lifespan."""
    beacon: Beacon = request.app.state.beacon
    return beacon


BeaconDep = Annotated[Beacon, Depends(get_beacon)]


@router.get("/health", response_model=None)
async def health(beacon: BeaconDep) -> JSONResponse:
    """200 while cycles are succeeding; 503 with a reason when they are not."""
    ok, reason = beacon.healthy(datetime.now(UTC))
    if ok:
        return JSONResponse({"status": "ok", "version": beacon.settings.app_version})
    return JSONResponse({"status": "unhealthy", "reason": reason}, status_code=503)


@router.get("/status")
async def status(beacon: BeaconDep) -> dict[str, Any]:
    """The last good document plus how the last cycle went. Never published as-is."""
    last = beacon.last
    return {
        "target": beacon.publisher.target,
        "last_cycle": None
        if last is None
        else {
            "started_at": last.started_at,
            "finished_at": last.finished_at,
            "published": last.published,
            "error": last.error,
            "source_errors": last.source_errors,
            "orphan_checks": last.orphan_checks,
        },
        "document": None if beacon.document is None else beacon.document.model_dump(mode="json"),
    }


@router.post("/cycle")
async def cycle(beacon: BeaconDep) -> dict[str, Any]:
    """Run one cycle now, for previewing a topology or source change without waiting."""
    report = await beacon.run_once()
    return {"published": report.published, "error": report.error}
