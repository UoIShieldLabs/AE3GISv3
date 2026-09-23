"""Persisted jobs for long-running operations, run in-process.

A job's handler is a coroutine ``handler(runner, job_id)``. ``runner.step(...)``
records ordered steps on the job row and mirrors each transition into the
event log, so the UI (polling ``/runtime``) and later an agent see progress.
Every job also gets an append-only log file (``runner.log``).

A job serialises on its *subject* (``topology:<id>``, ``image:<ref>``,
``source:<name>``): one job runs at a time per subject. Jobs can wait on each
other (``runner.wait``) and, where their kind allows it, be cancelled.
"""

from __future__ import annotations

import asyncio
import copy
import logging
import threading
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from db.models import Job, Topology, utcnow
from engine.base import DeploymentEngine
from services import events
from services.joblogs import JobLogStore

if TYPE_CHECKING:
    from services.images import ImageManager

log = logging.getLogger(__name__)

Handler = Callable[["JobRunner", str], Awaitable[None]]

ACTIVE = ("queued", "running")


def topology_subject(topology_id: str) -> str:
    return f"topology:{topology_id}"


def create_job(
    db: Session,
    kind: str,
    *,
    subject: str,
    topology_id: str | None = None,
    params: dict | None = None,
) -> Job:
    job = Job(
        topology_id=topology_id,
        subject=subject,
        kind=kind,
        params=params,
        status="queued",
        steps=[],
    )
    db.add(job)
    db.flush()
    return job


def active_for_subject(db: Session, subject: str) -> Job | None:
    stmt = (
        select(Job)
        .where(Job.subject == subject, Job.status.in_(ACTIVE))
        .order_by(Job.created_at.desc())
    )
    return db.scalars(stmt).first()


def active_job(db: Session, topology_id: str) -> Job | None:
    return active_for_subject(db, topology_subject(topology_id))


def last_for_subject(db: Session, subject: str) -> Job | None:
    stmt = select(Job).where(Job.subject == subject).order_by(Job.created_at.desc())
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
        "subject": job.subject,
        "kind": job.kind,
        "status": job.status,
        "steps": list(job.steps or []),
        "error": job.error,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


def recover_stale_jobs(session_factory: sessionmaker[Session]) -> int:
    """After a restart, nothing is running any more: fail leftover jobs.

    A topology caught mid-deploy or mid-destroy would otherwise stay in that
    state forever (deploy and destroy both refuse it), so it moves to ``error``,
    from which the user can destroy or redeploy.
    """
    with session_factory() as db:
        stale = list(db.scalars(select(Job).where(Job.status.in_(ACTIVE))))
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
        stuck = db.scalars(select(Topology).where(Topology.status.in_(["deploying", "destroying"])))
        for topo in stuck:
            events.record(
                db,
                type="topology.recovered",
                level="warning",
                message=f"Server restarted while {topo.status}; status set to error",
                topology_id=topo.id,
            )
            topo.status = "error"
        db.commit()
        return len(stale)


class JobRunner:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        engine: DeploymentEngine,
        logs: JobLogStore,
    ) -> None:
        self.session_factory = session_factory
        self.engine = engine
        self.logs = logs
        # Set by the app (main.create_app); deploys use it to prepare images.
        self.images: ImageManager | None = None
        self._handlers: dict[str, Handler] = {}
        self._cancellable_kinds: set[str] = set()
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._tasks: dict[str, asyncio.Task] = {}
        self._pending = 0
        self._pending_lock = threading.Lock()
        self._in_handler: set[str] = set()
        self._cancel_requested: set[str] = set()
        self._uncancellable: set[str] = set()
        self._done: dict[str, asyncio.Event] = {}
        self._last_progress: dict[tuple[str, str], float] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        # Serialises "is a job active? no → create one" across request threads.
        self.admission = threading.Lock()

    def register(self, kind: str, handler: Handler, *, cancellable: bool = False) -> None:
        self._handlers[kind] = handler
        if cancellable:
            self._cancellable_kinds.add(kind)

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Remember the app's event loop so sync request handlers (threadpool) can schedule jobs."""
        self._loop = loop

    # ── scheduling ──
    def submit(self, job_id: str) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            if self._loop is None:
                raise RuntimeError("JobRunner has no event loop; the app has not started") from None
            with self._pending_lock:
                self._pending += 1
            self._loop.call_soon_threadsafe(self._spawn_pending, job_id)
            return
        self._spawn(job_id)

    def _spawn(self, job_id: str) -> None:
        task = asyncio.get_running_loop().create_task(self.run(job_id), name=f"job:{job_id}")
        self._tasks[job_id] = task
        task.add_done_callback(lambda _t, jid=job_id: self._tasks.pop(jid, None))

    def _spawn_pending(self, job_id: str) -> None:
        try:
            self._spawn(job_id)
        finally:
            with self._pending_lock:
                self._pending -= 1

    async def wait_idle(self) -> None:
        """Await every scheduled job (tests and shutdown)."""
        while self._tasks or self._pending:
            if self._tasks:
                await asyncio.gather(*list(self._tasks.values()), return_exceptions=True)
            else:
                await asyncio.sleep(0)

    async def shutdown(self, cancel_kinds: tuple[str, ...] = ()) -> None:
        """Cancel jobs of the given kinds (long builds), then wait for the rest."""
        if cancel_kinds:
            with self.session_factory() as db:
                ids = list(
                    db.scalars(
                        select(Job.id).where(Job.status.in_(ACTIVE), Job.kind.in_(cancel_kinds))
                    )
                )
            for job_id in ids:
                self.cancel(job_id, reason="Server shutting down")
        await self.wait_idle()

    async def run(self, job_id: str) -> None:
        with self.session_factory() as db:
            job = db.get(Job, job_id)
            if not job:
                return
            subject = job.subject or topology_subject(job.topology_id)
        async with self._locks[subject]:
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
                    topology_id=job.topology_id,
                    job_id=job_id,
                )
                db.commit()
            self.log(job_id, f"{kind} started")
            handler = self._handlers.get(kind)
            self._in_handler.add(job_id)
            try:
                if handler is None:
                    raise RuntimeError(f"No handler for job kind '{kind}'")
                # A cancel requested before this point surfaces at the handler's
                # first step (see ``step``), so the handler can still clean up.
                await handler(self, job_id)
            except asyncio.CancelledError:
                requested = job_id in self._cancel_requested
                self._finish(job_id, "cancelled", "Cancelled")
                if not requested:
                    raise
            except Exception as exc:
                log.exception("Job %s (%s) failed", job_id, kind)
                self._finish(job_id, "failed", f"{type(exc).__name__}: {exc}")
            else:
                self._finish(job_id, "succeeded", None)
            finally:
                self._in_handler.discard(job_id)
                self._cancel_requested.discard(job_id)
                self._uncancellable.discard(job_id)

    def _finish(self, job_id: str, status: str, error: str | None) -> None:
        with self.session_factory() as db:
            job = db.get(Job, job_id)
            if not job:
                return
            job.status = status
            job.error = error
            job.finished_at = utcnow()
            level = {"failed": "error", "cancelled": "warning"}.get(status, "info")
            events.record(
                db,
                type=f"job.{status}",
                level=level,
                message=error or f"{job.kind} {status}",
                topology_id=job.topology_id,
                job_id=job_id,
            )
            db.commit()
        self.log(job_id, f"{status}" + (f": {error}" if error else ""))
        self.logs.close(job_id)
        done = self._done.pop(job_id, None)
        if done is not None:
            done.set()

    async def wait(self, job_id: str) -> Job | None:
        """Wait for a job to finish and return its final row (must run on the app loop)."""
        done = self._done.setdefault(job_id, asyncio.Event())
        with self.session_factory() as db:
            job = db.get(Job, job_id)
            if job is None or not job.is_active:
                if not done.is_set():
                    self._done.pop(job_id, None)
                return job
        await done.wait()
        with self.session_factory() as db:
            return db.get(Job, job_id)

    # ── cancellation ──
    def cancellable(self, job: Job) -> bool:
        return (
            job.is_active
            and job.kind in self._cancellable_kinds
            and job.id not in self._uncancellable
        )

    def cancel(self, job_id: str, reason: str = "Cancelled") -> bool:
        """Request cancellation; False if the job is finished or past its point of no return.

        Must be called on the app loop so it cannot interleave with the job's own
        progress. A job that has not reached its handler yet is flagged and
        stops before its first step, so its handler still gets to clean up.
        """
        with self.session_factory() as db:
            job = db.get(Job, job_id)
            if job is None or not self.cancellable(job):
                return False
        self._cancel_requested.add(job_id)
        self.log(job_id, reason)
        task = self._tasks.get(job_id)
        if task is not None and job_id in self._in_handler:
            task.cancel()
        return True

    def point_of_no_return(self, job_id: str) -> None:
        """From here on the job can no longer be cancelled (e.g. engine.deploy started)."""
        self._uncancellable.add(job_id)

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
        if job_id in self._cancel_requested:
            raise asyncio.CancelledError
        now = datetime.now(UTC).isoformat()
        self._set_step(job_id, name, status="running", message=message, started_at=now)
        self.event(job_id, "job.step", f"{name}: started")
        self.log(job_id, f"── {name}" + (f": {message}" if message else ""))
        try:
            yield
        except BaseException as exc:
            cancelled = isinstance(exc, asyncio.CancelledError)
            if not cancelled and not isinstance(exc, Exception):
                raise
            text = "cancelled" if cancelled else f"{type(exc).__name__}: {exc}"
            self._set_step(
                job_id,
                name,
                status="cancelled" if cancelled else "failed",
                message=text,
                ended_at=datetime.now(UTC).isoformat(),
            )
            level = "warning" if cancelled else "error"
            self.event(job_id, "job.step", f"{name}: {text}", level=level)
            raise
        else:
            self._set_step(job_id, name, status="succeeded", ended_at=datetime.now(UTC).isoformat())
            self.event(job_id, "job.step", f"{name}: done")
        finally:
            self._last_progress.pop((job_id, name), None)

    def progress(self, job_id: str, name: str, message: str, *, min_interval: float = 0.0) -> None:
        """Update a running step's message and log it (safe to call from worker threads).

        With ``min_interval``, the step message (a DB write) is only updated that
        often; every message still goes to the log.
        """
        self.log(job_id, message)
        if min_interval:
            now = time.monotonic()
            key = (job_id, name)
            if now - self._last_progress.get(key, 0.0) < min_interval:
                return
            self._last_progress[key] = now
        self._set_step(job_id, name, message=message)

    def patch_step(self, job_id: str, name: str, **patch) -> None:
        """Set extra fields on a step (e.g. the build jobs it is waiting on)."""
        self._set_step(job_id, name, **patch)

    def log(self, job_id: str, line: str) -> None:
        stamp = datetime.now(UTC).strftime("%H:%M:%S")
        try:
            self.logs.append(job_id, f"[{stamp}] {line}")
        except OSError as exc:  # pragma: no cover - disk full etc.; never fail a job over its log
            log.warning("Could not write log for job %s: %s", job_id, exc)

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
