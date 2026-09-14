"""Persisted jobs for long-running operations, run in-process.

A job's handler is a coroutine ``handler(runner, job_id)``. ``runner.step(...)``
records ordered steps on the job row and mirrors each transition into the
event log, so the UI (polling ``/runtime``) and later an agent see progress.
One job runs at a time per topology.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import copy
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from db.models import Job, utcnow
from engine.base import DeploymentEngine
from services import events

log = logging.getLogger(__name__)

Handler = Callable[["JobRunner", str], Awaitable[None]]


def create_job(db: Session, topology_id: str, kind: str) -> Job:
    job = Job(topology_id=topology_id, kind=kind, status="queued", steps=[])
    db.add(job)
    db.flush()
    return job


def active_job(db: Session, topology_id: str) -> Job | None:
    stmt = (
        select(Job)
        .where(Job.topology_id == topology_id, Job.status.in_(["queued", "running"]))
        .order_by(Job.created_at.desc())
    )
    return db.scalars(stmt).first()


def list_jobs(db: Session, topology_id: str, limit: int = 20) -> list[Job]:
    stmt = (
        select(Job)
        .where(Job.topology_id == topology_id)
        .order_by(Job.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def job_to_dict(job: Job) -> dict:
    return {
        "id": job.id,
        "topology_id": job.topology_id,
        "kind": job.kind,
        "status": job.status,
        "steps": list(job.steps or []),
        "error": job.error,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


def recover_stale_jobs(session_factory: sessionmaker[Session]) -> int:
    """After a restart, nothing is running any more: fail leftover jobs."""
    with session_factory() as db:
        stale = list(db.scalars(select(Job).where(Job.status.in_(["queued", "running"]))))
        for job in stale:
            job.status = "failed"
            job.error = "Server restarted while the job was running"
            job.finished_at = utcnow()
            events.record(
                db,
                type="job.failed",
                level="warning",
                message=job.error,
                topology_id=job.topology_id,
                job_id=job.id,
            )
        db.commit()
        return len(stale)


class JobRunner:
    def __init__(self, session_factory: sessionmaker[Session], engine: DeploymentEngine) -> None:
        self.session_factory = session_factory
        self.engine = engine
        self._handlers: dict[str, Handler] = {}
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._tasks: set[asyncio.Task] = set()
        self._futures: set[concurrent.futures.Future] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def register(self, kind: str, handler: Handler) -> None:
        self._handlers[kind] = handler

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Remember the app's event loop so sync request handlers (threadpool) can schedule jobs."""
        self._loop = loop

    # ── scheduling ──
    def submit(self, job_id: str, topology_id: str) -> None:
        coro = self.run(job_id, topology_id)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            task = loop.create_task(coro, name=f"job:{job_id}")
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            return
        if self._loop is None:
            coro.close()
            raise RuntimeError("JobRunner has no event loop; the app has not started")
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        self._futures.add(fut)
        fut.add_done_callback(self._futures.discard)

    async def wait_idle(self) -> None:
        """Await every scheduled job (tests and shutdown)."""
        while self._tasks or self._futures:
            pending = [*self._tasks, *(asyncio.wrap_future(f) for f in self._futures)]
            await asyncio.gather(*pending, return_exceptions=True)

    async def run(self, job_id: str, topology_id: str) -> None:
        async with self._locks[topology_id]:
            with self.session_factory() as db:
                job = db.get(Job, job_id)
                if not job or job.status != "queued":
                    return
                kind = job.kind
                job.status = "running"
                job.started_at = utcnow()
                events.record(
                    db,
                    type="job.started",
                    message=f"{kind} started",
                    topology_id=topology_id,
                    job_id=job_id,
                )
                db.commit()
            handler = self._handlers.get(kind)
            try:
                if handler is None:
                    raise RuntimeError(f"No handler for job kind '{kind}'")
                await handler(self, job_id)
            except Exception as exc:
                log.exception("Job %s (%s) failed", job_id, kind)
                self._finish(job_id, "failed", f"{type(exc).__name__}: {exc}")
            else:
                self._finish(job_id, "succeeded", None)

    def _finish(self, job_id: str, status: str, error: str | None) -> None:
        with self.session_factory() as db:
            job = db.get(Job, job_id)
            if not job:
                return
            job.status = status
            job.error = error
            job.finished_at = utcnow()
            events.record(
                db,
                type=f"job.{status}",
                level="error" if status == "failed" else "info",
                message=error or f"{job.kind} {status}",
                topology_id=job.topology_id,
                job_id=job_id,
            )
            db.commit()

    # ── steps ──
    @contextmanager
    def _job(self, job_id: str) -> Iterator[tuple[Session, Job]]:
        with self.session_factory() as db:
            job = db.get(Job, job_id)
            if job is None:
                raise RuntimeError(f"Job {job_id} vanished")
            yield db, job
            db.commit()

    def _set_step(self, job_id: str, name: str, **patch) -> None:
        with self._job(job_id) as (db, job):
            # Deep-copy: mutating the stored list in place leaves old == new at
            # flush time and SQLAlchemy would skip the UPDATE for the JSON column.
            steps = copy.deepcopy(job.steps or [])
            for s in steps:
                if s["name"] == name:
                    s.update(patch)
                    break
            else:
                steps.append(
                    {
                        "name": name,
                        "status": "pending",
                        "message": None,
                        "started_at": None,
                        "ended_at": None,
                        **patch,
                    }
                )
            job.steps = steps

    @asynccontextmanager
    async def step(self, job_id: str, name: str, message: str | None = None):
        now = datetime.now(UTC).isoformat()
        self._set_step(job_id, name, status="running", message=message, started_at=now)
        self.event(job_id, "job.step", f"{name}: started")
        try:
            yield
        except Exception as exc:
            self._set_step(
                job_id,
                name,
                status="failed",
                message=f"{type(exc).__name__}: {exc}",
                ended_at=datetime.now(UTC).isoformat(),
            )
            self.event(job_id, "job.step", f"{name}: failed — {exc}", level="error")
            raise
        else:
            self._set_step(job_id, name, status="succeeded", ended_at=datetime.now(UTC).isoformat())
            self.event(job_id, "job.step", f"{name}: done")

    def progress(self, job_id: str, name: str, message: str) -> None:
        """Update a running step's message (safe to call from worker threads)."""
        self._set_step(job_id, name, message=message)

    def event(
        self, job_id: str, type: str, message: str, level: str = "info", data: dict | None = None
    ) -> None:
        with self._job(job_id) as (db, job):
            events.record(
                db,
                type=type,
                message=message,
                level=level,
                topology_id=job.topology_id,
                job_id=job_id,
                data=data,
            )
