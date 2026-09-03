"""SQLAlchemy models.

Classroom tables (ClassSession/StudentSlot) are intentionally omitted in this
foundation pass — classroom mode is deferred and will be reintroduced on the
engine abstraction later.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, JSON, String

from database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class Topology(Base):
    __tablename__ = "topologies"

    id = Column(String, primary_key=True, default=_new_id)
    name = Column(String, nullable=False)
    data = Column(JSON, nullable=False)
    # Opaque per-engine deployment state (e.g. Kathara lab name + node map).
    engine_state = Column(JSON, nullable=True)
    status = Column(String, default="idle")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
