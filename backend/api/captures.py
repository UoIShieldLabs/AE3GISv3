"""Packet capture: start/list captures, the pcap (downloaded or streamed live),
packet summaries, and a WebSocket of live packets. Stop via ``POST /jobs/{id}/stop``."""

from __future__ import annotations

import asyncio
import contextlib
import re
from collections import deque
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.deps import get_artifacts, get_db, get_runner
from api.errors import Conflict, NotFound
from api.live_ws import ClientGone, forward, unless_disconnected
from api.schemas import CaptureOut, CaptureRequest, PacketPageOut
from auth import require_any_auth, require_instructor, valid_ws_token
from db.models import Job, Topology
from domain.packets import summarize
from domain.pcap import PcapSplitter
from services import capture, jobs, live, topologies
from services.artifacts import ArtifactStore
from services.jobs import JobRunner
from services.live import LiveHub

router = APIRouter(prefix="/api/v1", tags=["captures"])

V1 = "/api/v1"


def _get_capture(db: Session, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if not job or job.kind != capture.KIND:
        raise NotFound("Capture")
    return job


def capture_out(job: Job) -> dict[str, Any]:
    params = job.params or {}
    result = job.result or {}
    relay = capture.active_relay(job.id)
    if relay is not None:
        stats = {
            "packets": relay.packets,
            "bytes": relay.wire_bytes,
            "file_bytes": relay.committed,
            "undecoded": relay.undecoded,
        }
    else:
        stats = {
            k: result.get(k)
            for k in (
                "packets",
                "bytes",
                "file_bytes",
                "undecoded",
                "dropped_by_kernel",
                "duration_s",
                "stopped_by",
            )
            if result.get(k) is not None
        }
    return {
        "id": job.id,
        "topology_id": job.topology_id,
        "label": params.get("label") or "",
        "status": job.status,
        "live": job.is_active,
        "target": params.get("target") or {},
        "endpoint": params.get("endpoint") or {},
        "filter": params.get("filter") or "",
        "snaplen": params.get("snaplen") or 0,
        "limits": params.get("limits") or {},
        "stats": stats,
        "job": jobs.job_to_dict(job),
        "pcap_url": f"{V1}/captures/{job.id}/pcap",
        "ws_path": f"{V1}/topologies/ws/{job.topology_id}/captures/{job.id}",
    }


@router.post(
    "/topologies/{topology_id}/captures",
    response_model=CaptureOut,
    status_code=202,
    responses={200: {"model": CaptureOut, "description": "Already capturing there"}},
)
def start_capture(
    topology_id: str,
    body: CaptureRequest,
    response: Response,
    db: Session = Depends(get_db),
    runner: JobRunner = Depends(get_runner),
    _=Depends(require_instructor),
):
    """Start capturing on a link or a node interface of a deployed topology.

    A capture of an interface that is already being captured returns that
    capture (200). Stop it with ``POST /jobs/{id}/stop``: the pcap is kept.
    """
    topo = topologies.get_or_404(db, topology_id)
    job, created = capture.start_capture(db, runner, topo, body.model_dump())
    if not created:
        response.status_code = 200
    return capture_out(job)


@router.get("/topologies/{topology_id}/captures", response_model=list[CaptureOut])
def list_captures(
    topology_id: str,
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_any_auth),
):
    topologies.get_or_404(db, topology_id)
    return [capture_out(j) for j in jobs.list_jobs(db, topology_id, limit, kinds=(capture.KIND,))]


@router.get("/captures/{job_id}", response_model=CaptureOut)
def get_capture(job_id: str, db: Session = Depends(get_db), _=Depends(require_any_auth)):
    return capture_out(_get_capture(db, job_id))


def _filename(topo: Topology | None, job: Job) -> str:
    ep = (job.params or {}).get("endpoint") or {}
    when = (job.started_at or job.created_at or datetime.now(UTC)).strftime("%Y%m%d-%H%M%S")
    parts = [topo.name if topo else "capture", ep.get("machine", ""), ep.get("interface", ""), when]
    slug = "-".join(re.sub(r"[^A-Za-z0-9_.]+", "_", p).strip("_") for p in parts if p)
    return f"{slug or 'capture'}.pcap"


async def _pcap_stream(
    path: Path, job_id: str, follow: bool, is_active: Callable[[], bool]
) -> AsyncIterator[bytes]:
    """The pcap up to what the relay committed; with ``follow``, tail it live
    until the capture ends. Every byte sent is part of a whole record."""
    # A capture still starting (e.g. building its image) has no file yet.
    while not path.exists():
        if not follow or not await asyncio.to_thread(is_active):
            return
        await asyncio.sleep(0.5)
    pos = 0
    with path.open("rb") as fh:
        while True:
            relay = capture.active_relay(job_id)
            limit = relay.committed if relay is not None else path.stat().st_size
            while pos < limit:
                fh.seek(pos)
                chunk = fh.read(min(limit - pos, 1 << 20))
                if not chunk:
                    break
                pos += len(chunk)
                yield chunk
            if relay is None or not follow:
                return
            await asyncio.sleep(0.25)


@router.get(
    "/captures/{job_id}/pcap",
    response_class=StreamingResponse,
    responses={200: {"content": {"application/vnd.tcpdump.pcap": {}}}},
)
def get_pcap(
    job_id: str,
    follow: bool = Query(
        default=False,
        description="Keep streaming new packets until the capture ends "
        "(pipe into `wireshark -k -i -`)",
    ),
    db: Session = Depends(get_db),
    runner: JobRunner = Depends(get_runner),
    store: ArtifactStore = Depends(get_artifacts),
    _=Depends(require_any_auth),
):
    """The capture as a pcap file. Valid at any moment, even mid-capture.
    Accepts ``?token=`` so curl and plain links work with auth on."""
    job = _get_capture(db, job_id)
    path = store.path(job.id, capture.PCAP_NAME)
    if not job.is_active and not path.exists():
        raise NotFound("Pcap")
    if job.is_active and not path.exists() and not follow:
        raise Conflict("The capture has not started yet", code="not_started")

    def is_active() -> bool:
        with runner.session_factory() as s:
            j = s.get(Job, job_id)
            return bool(j and j.is_active)

    topo = db.get(Topology, job.topology_id)
    return StreamingResponse(
        _pcap_stream(path, job.id, follow, is_active),
        media_type="application/vnd.tcpdump.pcap",
        headers={
            "Content-Disposition": f'attachment; filename="{_filename(topo, job)}"',
            "Cache-Control": "no-store",
            # nginx: pass packets through as they arrive.
            "X-Accel-Buffering": "no",
        },
    )


def _read_packets(path: Path, after: int, limit: int) -> tuple[list[dict[str, Any]], int]:
    splitter = PcapSplitter()
    items: list[dict[str, Any]] = []
    n = 0
    with path.open("rb") as fh:
        while chunk := fh.read(1 << 20):
            for rec in splitter.feed(chunk):
                n += 1
                if n > after and len(items) < limit:
                    items.append(
                        summarize(n, rec.ts, rec.data, rec.origlen, splitter.linktype).to_dict()
                    )
    return items, n


def _tail_packets(path: Path, keep: int) -> list[dict[str, Any]]:
    splitter = PcapSplitter()
    tail: deque[tuple[int, Any]] = deque(maxlen=keep)
    n = 0
    with path.open("rb") as fh:
        while chunk := fh.read(1 << 20):
            for rec in splitter.feed(chunk):
                n += 1
                tail.append((n, rec))
    return [summarize(i, r.ts, r.data, r.origlen, splitter.linktype).to_dict() for i, r in tail]


@router.get("/captures/{job_id}/packets", response_model=PacketPageOut)
async def get_packets(
    job_id: str,
    after: int = Query(default=0, ge=0, description="Packet number to start after"),
    limit: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db),
    store: ArtifactStore = Depends(get_artifacts),
    _=Depends(require_any_auth),
):
    """Summaries of the captured packets, read from the pcap (any capture)."""
    job = _get_capture(db, job_id)
    path = store.path(job.id, capture.PCAP_NAME)
    if not path.exists():
        return {"items": [], "next_after": after, "total": 0}
    items, total = await asyncio.to_thread(_read_packets, path, after, limit)
    return {
        "items": items,
        "next_after": items[-1]["n"] if items else after,
        "total": total,
    }


@router.websocket("/topologies/ws/{topology_id}/captures/{job_id}")
async def capture_live(
    websocket: WebSocket,
    topology_id: str,
    job_id: str,
    token: str | None = Query(default=None),
):
    """Live packet summaries. Messages (JSON): ``hello`` {capture, recent},
    ``packets`` {items, undecoded, dropped}, ``status`` {packets, bytes,
    file_bytes, pps, bps}, ``end`` {result}."""
    if not valid_ws_token(websocket, token):
        await websocket.close(code=4003, reason="Forbidden")
        return
    hub: LiveHub = websocket.app.state.live
    store: ArtifactStore = websocket.app.state.artifacts
    session_factory = websocket.app.state.session_factory

    def info() -> dict[str, Any] | None:
        with session_factory() as db:
            job = db.get(Job, job_id)
            if not job or job.kind != capture.KIND or job.topology_id != topology_id:
                return None
            return CaptureOut.model_validate(capture_out(job)).model_dump(mode="json")

    def is_active() -> bool:
        with session_factory() as db:
            job = db.get(Job, job_id)
            return bool(job and job.is_active)

    if await asyncio.to_thread(info) is None:
        await websocket.close(code=4004, reason="Capture not found")
        return
    await websocket.accept()
    try:
        try:
            channel = await unless_disconnected(
                websocket, live.wait_for_channel(hub, job_id, is_active)
            )
        except ClientGone:
            return
        if channel is None:
            # Finished (or from before a restart): the tail of the file, then the end.
            final = await asyncio.to_thread(info)
            path = store.path(job_id, capture.PCAP_NAME)
            recent: list[dict[str, Any]] = []
            if path.exists():
                recent = await asyncio.to_thread(_tail_packets, path, capture.RECENT_KEPT)
            await websocket.send_json({"type": "hello", "capture": final, "recent": recent})
            await websocket.send_json(
                {"type": "end", "result": (final or {}).get("job", {}).get("result")}
            )
            await websocket.close()
            return
        sub, _history = channel.subscribe(maxsize=64)
        # May overlap the first "packets" batch; clients dedupe by packet number.
        relay = capture.active_relay(job_id)  # None while the capture is still starting
        recent = relay.recent_summaries() if relay else []
        hello = await asyncio.to_thread(info)
        await websocket.send_json({"type": "hello", "capture": hello, "recent": recent})
        try:
            await forward(
                websocket,
                sub,
                lambda m: {**m, "dropped": sub.dropped} if m.get("type") == "packets" else m,
            )
        finally:
            channel.unsubscribe(sub)
        with contextlib.suppress(Exception):
            await websocket.close()
    except WebSocketDisconnect:
        pass
