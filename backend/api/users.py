"""Staff accounts (admins only): the admins and instructors of this instance.

An admin creates an account with a role; it gets a temporary password, shown
once, which its owner replaces at their first sign-in. Removing a staff member
hands their topologies (running labs included) and their students to another
staff member, the caller by default; nothing is destroyed.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas import (
    RoleIn,
    StaffCreatedOut,
    StaffIn,
    StaffListOut,
    StaffOut,
    TemporaryPasswordOut,
)
from auth import require_admin
from services import accounts
from services.accounts import Identity

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=StaffListOut)
def list_staff(db: Session = Depends(get_db), _: Identity = Depends(require_admin)):
    return StaffListOut(staff=[StaffOut(**s) for s in accounts.list_staff(db)])


@router.post("", response_model=StaffCreatedOut, status_code=201)
def create_staff(
    body: StaffIn, db: Session = Depends(get_db), _: Identity = Depends(require_admin)
):
    """A new admin or instructor. 409 ``username_taken``; 422
    ``invalid_username``."""
    user, password = accounts.create_staff(db, username=body.username, role=body.role)
    return StaffCreatedOut(user=StaffOut(**accounts.staff_out(db, user)), password=password)


@router.patch("/{user_id}", response_model=StaffOut)
def set_role(
    user_id: str,
    body: RoleIn,
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_admin),
):
    """Make a staff member an admin or an instructor. 409 ``last_admin``,
    ``managed_by_env`` (the environment's admin), ``cannot_change_self``."""
    user = accounts.set_role(db, identity, user_id, body.role)
    return StaffOut(**accounts.staff_out(db, user))


@router.post("/{user_id}/reset-password", response_model=TemporaryPasswordOut)
def reset_password(
    user_id: str, db: Session = Depends(get_db), identity: Identity = Depends(require_admin)
):
    """A temporary password (shown once): their sign-ins end, and they choose a
    new one when they next sign in."""
    return TemporaryPasswordOut(password=accounts.reset_staff_password(db, identity, user_id))


@router.delete("/{user_id}", status_code=204)
def delete_staff(
    user_id: str,
    transfer_to: str | None = Query(default=None),
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_admin),
):
    """Remove a staff member. Their topologies and students go to
    ``transfer_to`` (default: you). 409 ``cannot_delete_self``,
    ``managed_by_env``, ``last_admin``; 422 ``bad_transfer``."""
    accounts.delete_staff(db, identity, user_id, transfer_to=transfer_to)
    return Response(status_code=204)
