"""The class (instructor only): sign-up, the join code, and the students."""

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
from auth import require_instructor
from config import Settings
from domain import saved_state
from engine.base import DeploymentEngine
from services import accounts, topologies

router = APIRouter(
    prefix="/api/v1/class", tags=["class"], dependencies=[Depends(require_instructor)]
)


@router.get("", response_model=ClassSettingsOut)
def get_class(db: Session = Depends(get_db)):
    return accounts.class_settings(db)


@router.put("", response_model=ClassSettingsOut)
def update_class(body: ClassSettingsIn, db: Session = Depends(get_db)):
    """Open or close sign-up (opening the first time makes a join code), or
    rotate the join code (students already signed up are unaffected)."""
    return accounts.update_class_settings(
        db, signup_open=body.signup_open, rotate_join_code=body.rotate_join_code
    )


@router.get("/students", response_model=StudentsOut)
def list_students(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    students = [StudentOut(**s) for s in accounts.list_students(db)]
    return StudentsOut(students=students, max_labs=settings.student_max_labs)


@router.post("/students/{user_id}/reset-password", response_model=TemporaryPasswordOut)
def reset_password(user_id: str, db: Session = Depends(get_db)):
    """A temporary password (shown once) for a student who forgot theirs;
    their current sign-ins end."""
    return TemporaryPasswordOut(password=accounts.reset_password(db, user_id))


@router.delete("/students/{user_id}", status_code=204)
async def remove_student(
    user_id: str,
    db: Session = Depends(get_db),
    engine: DeploymentEngine = Depends(get_engine),
):
    """Remove a student with their topologies and saved lab state. 409
    ``student_has_labs`` while any of their labs is up (destroy them first)."""
    user, topos = accounts.student_for_removal(db, user_id)
    refs: list[str] = []
    for topo in topos:
        refs.extend(saved_state.refs(topo.saved_state))
        topologies.delete(db, topo)
    accounts.delete_user(db, user)
    await engine.remove_images(refs)
    return Response(status_code=204)
