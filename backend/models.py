import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, Text

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
    clab_yaml = Column(Text, nullable=True)
    status = Column(String, default="idle")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class ClassSession(Base):
    __tablename__ = "class_sessions"

    id = Column(String, primary_key=True, default=_new_id)
    name = Column(String, nullable=False)
    template_id = Column(String, ForeignKey("topologies.id"), nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class StudentSlot(Base):
    __tablename__ = "student_slots"

    id = Column(String, primary_key=True, default=_new_id)
    session_id = Column(String, ForeignKey("class_sessions.id"), nullable=False)
    topology_id = Column(String, ForeignKey("topologies.id"), nullable=False)
    join_code = Column(String, unique=True, nullable=False, default=_new_id)
    label = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
