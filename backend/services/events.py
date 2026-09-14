"""Append-only event log per topology (deploy steps, reconcile findings…)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Event


def record(
    db: Session,
    *,
    type: str,
    message: str,
    topology_id: str | None = None,
    job_id: str | None = None,
    level: str = "info",
    data: dict[str, Any] | None = None,
) -> Event:
    """Add an event to the session (caller commits)."""
    ev = Event(
        topology_id=topology_id, job_id=job_id, level=level, type=type, message=message, data=data
    )
    db.add(ev)
    return ev


def list_events(
    db: Session, topology_id: str, *, after_id: int = 0, limit: int = 200
) -> list[Event]:
    stmt = (
        select(Event)
        .where(Event.topology_id == topology_id, Event.id > after_id)
        .order_by(Event.id.desc())
        .limit(max(1, min(limit, 1000)))
    )
    rows = list(db.scalars(stmt))
    rows.reverse()
    return rows
