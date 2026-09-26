"""SQLAlchemy models.

``Topology.data`` is opaque JSON owned by the frontend; the backend never
strips or reshapes it. ``engine_state`` holds the deployment engine's own
bookkeeping (see ``engine.base.EngineState``). ``version`` increments on every
content change and backs optimistic concurrency on PUT.

Jobs record every long-running operation with ordered steps. A job's
``subject`` is what it serialises on (``topology:<id>``, ``image:<ref>``,
``source:<name>``, ``capture:…``, ``traffic:<id>``); ``topology_id`` is set
for jobs that belong to a topology. Events are
an append-only log per topology that the UI, reconcile, and a future agent can
read.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text

from db.session import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return uuid.uuid4().hex


TOPOLOGY_STATUSES = ("idle", "deploying", "deployed", "destroying", "error")
JOB_KINDS = ("deploy", "destroy", "purge", "build", "sync_source", "capture", "traffic")
JOB_STATUSES = ("queued", "running", "succeeded", "failed", "cancelled")


class Topology(Base):
    __tablename__ = "topologies"

    id = Column(String, primary_key=True, default=new_id)
    name = Column(String, nullable=False)
    data = Column(JSON, nullable=False)
    engine_state = Column(JSON, nullable=True)
    status = Column(String, default="idle", nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=new_id)
    topology_id = Column(String, ForeignKey("topologies.id", ondelete="CASCADE"), nullable=True)
    # What the job serialises on; see the module docstring. Always set by
    # services.jobs.create_job (nullable only for rows older than 0003).
    subject = Column(String, nullable=True)
    kind = Column(String, nullable=False)
    # The job's inputs, e.g. {"ref": ..., "fresh": false} for a build.
    params = Column(JSON, nullable=True)
    status = Column(String, default="queued", nullable=False)
    # [{name, status, message, started_at, ended_at}]
    steps = Column(JSON, default=list, nullable=False)
    error = Column(Text, nullable=True)
    # What the job produced, e.g. a capture's packet counts or a traffic run's
    # summary. Bulk output (pcaps, time series) lives in its artifacts directory.
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_jobs_topology_created", "topology_id", "created_at"),
        Index("ix_jobs_subject_created", "subject", "created_at"),
    )

    @property
    def is_active(self) -> bool:
        return self.status in ("queued", "running")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topology_id = Column(String, nullable=True, index=True)
    job_id = Column(String, nullable=True)
    ts = Column(DateTime, default=utcnow, nullable=False)
    level = Column(String, default="info", nullable=False)  # info | warning | error
    type = Column(String, nullable=False)  # e.g. job.step, deploy.finished, reconcile.stale
    message = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)
