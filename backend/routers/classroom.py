"""Classroom management: sessions, student slots, and student login."""

from __future__ import annotations

import copy

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import InstructorIdentity, require_instructor
from database import get_db
from models import ClassSession, StudentSlot, Topology
from schemas import (
    ClassSessionCreate,
    ClassSessionRecord,
    InstantiateRequest,
    StudentLoginRequest,
    StudentSlotRecord,
    TokenResponse,
)

router = APIRouter(prefix="/api/classroom", tags=["classroom"])


# ── Student login (public) ────────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
def student_login(body: StudentLoginRequest, db: Session = Depends(get_db)):
    slot = db.query(StudentSlot).filter(StudentSlot.join_code == body.join_code).first()
    if not slot:
        raise HTTPException(401, "Invalid join code")
    return TokenResponse(
        role="student",
        token=slot.join_code,
        topology_id=slot.topology_id,
    )


# ── Class sessions (instructor only) ─────────────────────────────


@router.get("/sessions", response_model=list[ClassSessionRecord])
def list_sessions(
    db: Session = Depends(get_db),
    _: InstructorIdentity = Depends(require_instructor),
):
    return db.query(ClassSession).order_by(ClassSession.created_at.desc()).all()


@router.post("/sessions", response_model=ClassSessionRecord, status_code=201)
def create_session(
    body: ClassSessionCreate,
    db: Session = Depends(get_db),
    _: InstructorIdentity = Depends(require_instructor),
):
    template = db.get(Topology, body.template_id)
    if not template:
        raise HTTPException(404, "Template topology not found")

    session = ClassSession(name=body.name, template_id=body.template_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions/{session_id}", response_model=ClassSessionRecord)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    _: InstructorIdentity = Depends(require_instructor),
):
    session = db.get(ClassSession, session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    _: InstructorIdentity = Depends(require_instructor),
):
    session = db.get(ClassSession, session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    # Delete all student slots for this session
    db.query(StudentSlot).filter(StudentSlot.session_id == session_id).delete()
    db.delete(session)
    db.commit()


# ── Instantiate (clone topology for students) ────────────────────


@router.post(
    "/sessions/{session_id}/instantiate",
    response_model=list[StudentSlotRecord],
    status_code=201,
)
def instantiate(
    session_id: str,
    body: InstantiateRequest,
    db: Session = Depends(get_db),
    _: InstructorIdentity = Depends(require_instructor),
):
    session = db.get(ClassSession, session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    template = db.get(Topology, session.template_id)
    if not template:
        raise HTTPException(404, "Template topology not found")

    slots: list[StudentSlot] = []
    for i in range(1, body.count + 1):
        label = f"{body.label_prefix} {i}"

        # Deep-copy the template topology data
        cloned_data = copy.deepcopy(template.data)
        topo = Topology(
            name=f"{session.name} — {label}",
            data=cloned_data,
        )
        db.add(topo)
        db.flush()  # Populate topo.id before creating the slot

        slot = StudentSlot(
            session_id=session_id,
            topology_id=topo.id,
            label=label,
        )
        db.add(slot)
        slots.append(slot)

    db.commit()
    for slot in slots:
        db.refresh(slot)

    return slots


# ── Student slots ─────────────────────────────────────────────────


@router.get("/sessions/{session_id}/slots", response_model=list[StudentSlotRecord])
def list_slots(
    session_id: str,
    db: Session = Depends(get_db),
    _: InstructorIdentity = Depends(require_instructor),
):
    session = db.get(ClassSession, session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return (
        db.query(StudentSlot)
        .filter(StudentSlot.session_id == session_id)
        .order_by(StudentSlot.created_at)
        .all()
    )


@router.delete("/sessions/{session_id}/slots/{slot_id}", status_code=204)
def delete_slot(
    session_id: str,
    slot_id: str,
    db: Session = Depends(get_db),
    _: InstructorIdentity = Depends(require_instructor),
):
    slot = (
        db.query(StudentSlot)
        .filter(StudentSlot.id == slot_id, StudentSlot.session_id == session_id)
        .first()
    )
    if not slot:
        raise HTTPException(404, "Slot not found")
    db.delete(slot)
    db.commit()
