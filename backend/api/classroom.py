"""The caller's class (staff): sign-up, the join code, and the students.

An instructor manages their own class and students; an admin also sees and
manages every student (each listed with their instructor).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from api.deps import get_db, get_engine, get_settings
from api.schemas import (
    ClassSettingsIn,
    ClassSettingsOut,
    StudentOut,
    StudentsOut,
    TemporaryPasswordOut,
)
from auth import require_staff
from config import Settings
from domain import saved_state
from engine.base import DeploymentEngine
from services import accounts, topologies
from services.accounts import Identity

router = APIRouter(prefix="/api/v1/class", tags=["class"])


@router.get("", response_model=ClassSettingsOut)
def get_class(db: Session = Depends(get_db), identity: Identity = Depends(require_staff)):
    return accounts.class_settings(db, identity)


@router.put("", response_model=ClassSettingsOut)
def update_class(
    body: ClassSettingsIn,
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_staff),
):
    """Open or close sign-up to your class (opening it the first time makes a
    join code), rotate its join code (students already signed up are
    unaffected), or switch the agent's tutor on or off for your students."""
    return accounts.update_class_settings(
        db,
        identity,
        signup_open=body.signup_open,
        rotate_join_code=body.rotate_join_code,
        tutor_enabled=body.tutor_enabled,
    )


@router.get("/students", response_model=StudentsOut)
def list_students(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    identity: Identity = Depends(require_staff),
):
    """Your students (an admin: every student, with their instructor)."""
    students = [StudentOut(**s) for s in accounts.list_students(db, identity)]
    return StudentsOut(students=students, max_labs=settings.student_max_labs)


@router.post("/students/{user_id}/reset-password", response_model=TemporaryPasswordOut)
def reset_password(
    user_id: str, db: Session = Depends(get_db), identity: Identity = Depends(require_staff)
):
    """A temporary password (shown once) for a student who forgot theirs: their
    current sign-ins end, and they choose a new one when they next sign in."""
    return TemporaryPasswordOut(password=accounts.reset_password(db, identity, user_id))


@router.delete("/students/{user_id}", status_code=204)
async def remove_student(
    user_id: str,
    db: Session = Depends(get_db),
    engine: DeploymentEngine = Depends(get_engine),
    identity: Identity = Depends(require_staff),
):
    """Remove a student with their topologies and saved lab state. 409
    ``student_has_labs`` while any of their labs is up (destroy them first)."""
    user, topos = accounts.student_for_removal(db, identity, user_id)
    refs: list[str] = []
    for topo in topos:
        refs.extend(saved_state.refs(topo.saved_state))
        topologies.delete(db, topo)
    accounts.delete_user(db, user)
    await engine.remove_images(refs)
    return Response(status_code=204)
