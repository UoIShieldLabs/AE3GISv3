"""Accounts: staff (admins, instructors), self-registered students, sessions, classes.

Accounts are on when ``Settings.auth_required`` (an admin password or token is
configured). Then:

- **admins** may do everything: the host (images, registries, labs,
  benchmarks), every topology and lab, and the staff accounts. One admin comes
  from the environment (``env_managed``), kept in step with it at every start
  (``bootstrap_admin``); admins create the other admins and instructors.
- **instructors** have their own topologies, their own class, and their
  students' topologies and labs; they may build images.
- **students** sign themselves up into a class with its join code while that
  class has sign-up open, and see what their instructor published.

Every staff member has one class (``Class``); a student's ``class_id`` names
theirs. With accounts off every caller is an admin (``OPEN_ADMIN``) and none of
this is consulted.

A sign-in is an opaque random bearer token; only its sha256 is stored. A
temporary password (new account, reset) must be replaced at the next sign-in
(``must_change_password``; ``auth.current_identity`` refuses everything else
until then). Who may touch which topology is ``api.access``; this module only
answers "who is it" and manages the accounts.
"""

from __future__ import annotations

import hmac
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import Select, func, select
from sqlalchemy import update as sql_update
from sqlalchemy.orm import Session

from api.errors import Conflict, Forbidden, Invalid, NotFound, TooManyRequests, Unauthorized
from config import Settings
from db.models import STAFF_ROLES, Class, Topology, User, UserSession, utcnow
from domain import passwords

Role = Literal["admin", "instructor", "student"]

USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,31}$")
MIN_PASSWORD = 8
# Topology statuses that hold (or may still hold) containers on this host.
LAB_STATUSES = ("deploying", "deployed", "destroying")
# last_seen is written at most this often per session (not on every request).
_SEEN_EVERY = timedelta(seconds=60)
# The LoginLimiter key for wrong join codes (per client).
_JOIN_CODE_KEY = "#join-code"


@dataclass(frozen=True)
class Identity:
    """Who is calling. ``user_id`` is None only with accounts off."""

    user_id: str | None
    username: str
    role: Role
    # A student's instructor (the staff member whose class they are in).
    instructor_id: str | None = None
    must_change_password: bool = False
    # The environment's admin, whose password only the environment changes.
    env_managed: bool = False

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_staff(self) -> bool:
        return self.role in STAFF_ROLES

    @property
    def is_student(self) -> bool:
        return self.role == "student"

    @property
    def owner_id(self) -> str | None:
        """What ``Topology.owner_id`` holds for things this caller creates."""
        return self.user_id


OPEN_ADMIN = Identity(user_id=None, username="admin", role="admin")


def _aware(dt: datetime | None) -> datetime | None:
    # SQLite hands DateTime columns back naive; they are written in UTC.
    if dt is None or dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=UTC)


def normalize_username(raw: str) -> str:
    return (raw or "").strip().lower()


def identity_of(db: Session, user: User) -> Identity:
    return Identity(
        user_id=user.id,
        username=user.username,
        role=user.role,  # type: ignore[arg-type]
        instructor_id=teacher_of(db, user.id) if user.role == "student" else None,
        must_change_password=bool(user.must_change_password),
        env_managed=bool(user.env_managed),
    )


def env_admin_row(db: Session) -> User | None:
    return db.scalar(select(User).where(User.env_managed.is_(True)))


# ── the environment's admin ─────────────────────────────────────────


def bootstrap_admin(db: Session, settings: Settings) -> None:
    """Create or update the environment's admin row, and settle what has no
    owner yet. A no-op while accounts are off.

    A changed password replaces the hash and signs that admin out everywhere.
    Topologies without an owner (made with accounts off) become theirs, and a
    student without a class joins theirs. Safe at every start.
    """
    password = settings.bootstrap_password
    if not password:
        return
    row = env_admin_row(db)
    username = normalize_username(settings.bootstrap_username) or (
        row.username if row is not None else "admin"
    )
    clash = db.scalar(
        select(User).where(User.username == username, User.id != (row.id if row else ""))
    )
    if clash is not None:
        raise RuntimeError(
            f"The admin username '{username}' (AE3GIS_ADMIN_USERNAME) is already a "
            f"{clash.role}'s; pick another one or remove that account"
        )
    if row is None:
        row = User(
            username=username,
            password_hash=passwords.hash_password(password),
            role="admin",
            env_managed=True,
        )
        db.add(row)
        db.flush()
    else:
        row.username = username
        row.role = "admin"
        row.must_change_password = False
        if not passwords.verify_password(password, row.password_hash) or passwords.needs_rehash(
            row.password_hash
        ):
            row.password_hash = passwords.hash_password(password)
            db.query(UserSession).filter(UserSession.user_id == row.id).delete()
    cls = class_of(db, row.id)
    db.execute(sql_update(Topology).where(Topology.owner_id.is_(None)).values(owner_id=row.id))
    db.execute(
        sql_update(User)
        .where(User.role == "student", User.class_id.is_(None))
        .values(class_id=cls.id)
    )
    db.commit()


def purge_expired_sessions(db: Session) -> int:
    n = db.query(UserSession).filter(UserSession.expires_at < utcnow()).delete()
    db.commit()
    return n


# ── sessions ────────────────────────────────────────────────────────


@dataclass
class SignIn:
    token: str
    expires_at: datetime
    user: User


def start_session(db: Session, user: User, settings: Settings) -> SignIn:
    token = passwords.new_session_token()
    now = utcnow()
    expires = now + timedelta(hours=settings.session_ttl_hours)
    db.add(
        UserSession(
            token_hash=passwords.token_hash(token),
            user_id=user.id,
            created_at=now,
            expires_at=expires,
            last_seen_at=now,
        )
    )
    user.last_seen_at = now
    db.commit()
    return SignIn(token=token, expires_at=expires, user=user)


def resolve_token(db: Session, settings: Settings, token: str | None) -> Identity | None:
    """The identity behind a bearer token, or None if it is not valid."""
    if not token:
        return None
    static = settings.bootstrap_token
    if static and hmac.compare_digest(token.encode(), static.encode()):
        row = env_admin_row(db)
        if row is None:
            return OPEN_ADMIN
        return identity_of(db, row)
    sess = db.get(UserSession, passwords.token_hash(token))
    if sess is None:
        return None
    now = utcnow()
    if _aware(sess.expires_at) <= now:
        db.delete(sess)
        db.commit()
        return None
    user = db.get(User, sess.user_id)
    if user is None:
        return None
    seen = _aware(sess.last_seen_at)
    if seen is None or now - seen >= _SEEN_EVERY:
        sess.last_seen_at = now
        user.last_seen_at = now
        db.commit()
    return identity_of(db, user)


def end_session(db: Session, token: str | None) -> None:
    if not token:
        return
    db.query(UserSession).filter(UserSession.token_hash == passwords.token_hash(token)).delete()
    db.commit()


class LoginLimiter:
    """Refuse sign-ins for a (username, client) pair after too many failures in
    a window: enough to stop a classmate guessing passwords, nothing more."""

    def __init__(
        self,
        max_failures: int = 10,
        window_s: float = 300,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_failures = max_failures
        self.window_s = window_s
        self._clock = clock
        self._failures: dict[tuple[str, str], list[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: tuple[str, str]) -> list[float]:
        cutoff = self._clock() - self.window_s
        times = [t for t in self._failures.get(key, []) if t > cutoff]
        if times:
            self._failures[key] = times
        else:
            self._failures.pop(key, None)
        return times

    def check(self, username: str, client: str) -> None:
        with self._lock:
            times = self._recent((username, client))
            if len(times) >= self.max_failures:
                retry = int(times[0] + self.window_s - self._clock()) + 1
                raise TooManyRequests(
                    "Too many failed sign-ins; try again in a few minutes",
                    code="too_many_attempts",
                    retry_after_s=max(retry, 1),
                )

    def failed(self, username: str, client: str) -> None:
        with self._lock:
            self._recent((username, client))
            self._failures.setdefault((username, client), []).append(self._clock())

    def succeeded(self, username: str, client: str) -> None:
        with self._lock:
            self._failures.pop((username, client), None)


def login(
    db: Session,
    settings: Settings,
    limiter: LoginLimiter,
    *,
    username: str,
    password: str,
    client: str,
) -> SignIn:
    if not settings.auth_required:
        raise Conflict("Accounts are off on this instance; no sign-in needed", code="accounts_off")
    name = normalize_username(username)
    limiter.check(name, client)
    user = db.scalar(select(User).where(User.username == name))
    if user is None or not passwords.verify_password(password, user.password_hash):
        limiter.failed(name, client)
        raise Unauthorized("Wrong username or password", code="bad_credentials")
    limiter.succeeded(name, client)
    if passwords.needs_rehash(user.password_hash):
        user.password_hash = passwords.hash_password(password)
    return start_session(db, user, settings)


def _check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD:
        raise Invalid(f"Passwords need at least {MIN_PASSWORD} characters", code="weak_password")


def signup(
    db: Session,
    settings: Settings,
    limiter: LoginLimiter,
    *,
    username: str,
    password: str,
    join_code: str,
    client: str,
) -> SignIn:
    """A student account in the class whose join code this is, signed in."""
    if not settings.auth_required:
        raise Conflict("Accounts are off on this instance; no sign-up needed", code="accounts_off")
    if not any_signup_open(db):
        raise Forbidden("Sign-up is closed; ask your instructor to open it", code="signup_closed")
    limiter.check(_JOIN_CODE_KEY, client)
    cls = class_by_code(db, join_code)
    if cls is None:
        limiter.failed(_JOIN_CODE_KEY, client)
        raise Forbidden("That join code is not right", code="bad_join_code")
    if not cls.signup_open:
        raise Forbidden(
            "Sign-up for that class is closed; ask your instructor to open it",
            code="signup_closed",
        )
    name = _valid_username(username)
    _check_password(password)
    _ensure_free(db, name)
    user = User(
        username=name,
        password_hash=passwords.hash_password(password),
        role="student",
        class_id=cls.id,
    )
    db.add(user)
    db.commit()
    return start_session(db, user, settings)


def _valid_username(raw: str) -> str:
    name = normalize_username(raw)
    if not USERNAME_RE.match(name):
        raise Invalid(
            "Usernames are 3-32 characters: letters, digits, '.', '_' or '-'",
            code="invalid_username",
        )
    return name


def _ensure_free(db: Session, name: str) -> None:
    if db.scalar(select(User).where(User.username == name)) is not None:
        raise Conflict("That username is taken", code="username_taken")


def change_password(
    db: Session, identity: Identity, *, current: str, new: str, keep_token: str | None
) -> None:
    if identity.env_managed or not identity.user_id:
        raise Conflict(
            "This admin's password is set by AE3GIS_ADMIN_PASSWORD", code="managed_by_env"
        )
    user = db.get(User, identity.user_id)
    if user is None:
        raise NotFound("User")
    if not passwords.verify_password(current, user.password_hash):
        raise Forbidden("The current password is not right", code="bad_credentials")
    _check_password(new)
    if new == current:
        raise Invalid("Choose a password different from the current one", code="same_password")
    user.password_hash = passwords.hash_password(new)
    user.must_change_password = False
    keep = passwords.token_hash(keep_token) if keep_token else ""
    db.query(UserSession).filter(
        UserSession.user_id == user.id, UserSession.token_hash != keep
    ).delete()
    db.commit()


def _temporary_password(db: Session, user: User) -> str:
    """Give ``user`` a temporary password (shown once, to be changed at the
    next sign-in) and sign them out everywhere."""
    temporary = passwords.new_temporary_password()
    user.password_hash = passwords.hash_password(temporary)
    user.must_change_password = True
    db.query(UserSession).filter(UserSession.user_id == user.id).delete()
    db.commit()
    return temporary


# ── classes ─────────────────────────────────────────────────────────


def class_of(db: Session, instructor_id: str) -> Class:
    """The staff member's class, made on first use (sign-up closed, no code)."""
    cls = db.scalar(select(Class).where(Class.instructor_id == instructor_id))
    if cls is None:
        cls = Class(instructor_id=instructor_id, signup_open=False)
        db.add(cls)
        db.flush()
    return cls


def class_by_code(db: Session, join_code: str) -> Class | None:
    """The class whose join code this is (any case, dashes and spaces ignored)."""
    given = passwords.normalize_join_code(join_code or "")
    if not given:
        return None
    found = None
    for cls in db.scalars(select(Class).where(Class.join_code.is_not(None))):
        if hmac.compare_digest(
            given.encode(), passwords.normalize_join_code(cls.join_code).encode()
        ):
            found = cls
    return found


def any_signup_open(db: Session) -> bool:
    return (
        db.scalar(
            select(func.count(Class.id)).where(
                Class.signup_open.is_(True), Class.join_code.is_not(None)
            )
        )
        or 0
    ) > 0


def _class_out(cls: Class | None) -> dict[str, Any]:
    if cls is None:
        return {"signup_open": False, "join_code": None}
    return {"signup_open": bool(cls.signup_open), "join_code": cls.join_code or None}


def _new_join_code(db: Session) -> str:
    taken = {
        passwords.normalize_join_code(c)
        for c in db.scalars(select(Class.join_code).where(Class.join_code.is_not(None)))
    }
    while True:
        code = passwords.new_join_code()
        if passwords.normalize_join_code(code) not in taken:
            return code


def class_settings(db: Session, identity: Identity) -> dict[str, Any]:
    """The caller's class (staff). With accounts off there is none."""
    if not identity.user_id:
        return _class_out(None)
    cls = class_of(db, identity.user_id)
    db.commit()
    return _class_out(cls)


def update_class_settings(
    db: Session,
    identity: Identity,
    *,
    signup_open: bool | None = None,
    rotate_join_code: bool = False,
) -> dict[str, Any]:
    """Open or close sign-up to the caller's class (opening it the first time
    makes a join code), or give it a new code."""
    if not identity.user_id:
        raise Conflict("Accounts are off on this instance; there is no class", code="accounts_off")
    cls = class_of(db, identity.user_id)
    if rotate_join_code or (signup_open and not cls.join_code):
        cls.join_code = _new_join_code(db)
    if signup_open is not None:
        cls.signup_open = bool(signup_open)
    db.commit()
    return _class_out(cls)


# ── students ────────────────────────────────────────────────────────


def teacher_of(db: Session, user_id: str | None) -> str | None:
    """The staff member whose class the student is in (None: not a student)."""
    if not user_id:
        return None
    return db.scalar(
        select(Class.instructor_id)
        .join(User, User.class_id == Class.id)
        .where(User.id == user_id, User.role == "student")
    )


def student_ids_of(instructor_id: str | None) -> Select:
    """A subquery: the ids of the students in the staff member's class."""
    return select(User.id).where(
        User.role == "student",
        User.class_id.in_(select(Class.id).where(Class.instructor_id == instructor_id)),
    )


def _student(db: Session, identity: Identity, user_id: str) -> User:
    """A student the caller may manage: any for an admin, their own for an
    instructor (others are 404)."""
    user = db.get(User, user_id)
    if user is None or user.role != "student":
        raise NotFound("Student")
    if not identity.is_admin and teacher_of(db, user.id) != identity.user_id:
        raise NotFound("Student")
    return user


def lab_topologies(db: Session, owner_id: str) -> list[Topology]:
    """A user's topologies that hold (or may hold) containers on this host."""
    rows = db.scalars(select(Topology).where(Topology.owner_id == owner_id))
    return [t for t in rows if holds_lab(t)]


def holds_lab(topo: Topology) -> bool:
    return topo.status in LAB_STATUSES or (topo.status == "error" and topo.engine_state is not None)


def _ownership(db: Session, owner_ids: list[str]) -> tuple[dict[str, int], dict[str, list[dict]]]:
    """Per owner: how many topologies (not retired), and the labs they hold."""
    counts: dict[str, int] = {}
    labs: dict[str, list[dict]] = {}
    if not owner_ids:
        return counts, labs
    for t in db.scalars(select(Topology).where(Topology.owner_id.in_(owner_ids))):
        if t.retired_at is None:
            counts[t.owner_id] = counts.get(t.owner_id, 0) + 1
        if holds_lab(t):
            labs.setdefault(t.owner_id, []).append({"id": t.id, "name": t.name, "status": t.status})
    return counts, labs


def list_students(db: Session, identity: Identity) -> list[dict[str, Any]]:
    """The caller's students (an admin: every student), each with their instructor."""
    stmt = select(User).where(User.role == "student").order_by(User.username)
    if not identity.is_admin:
        stmt = stmt.where(User.id.in_(student_ids_of(identity.user_id)))
    users = list(db.scalars(stmt))
    teachers = {
        class_id: {"id": uid, "username": name}
        for class_id, uid, name in db.execute(
            select(Class.id, User.id, User.username).join(User, User.id == Class.instructor_id)
        ).all()
    }
    counts, labs = _ownership(db, [u.id for u in users])
    return [
        {
            "id": u.id,
            "username": u.username,
            "created_at": u.created_at,
            "last_seen_at": u.last_seen_at,
            "instructor": teachers.get(u.class_id),
            "topology_count": counts.get(u.id, 0),
            "labs": labs.get(u.id, []),
        }
        for u in users
    ]


def reset_password(db: Session, identity: Identity, user_id: str) -> str:
    """A temporary password (shown once) for one of the caller's students."""
    return _temporary_password(db, _student(db, identity, user_id))


def _refuse_running(user: User, topos: list[Topology]) -> None:
    running = [t for t in topos if holds_lab(t)]
    if running:
        raise Conflict(
            f"Destroy {user.username}'s running lab(s) first",
            code="student_has_labs",
            labs=[t.id for t in running],
        )


def student_for_removal(
    db: Session, identity: Identity, user_id: str
) -> tuple[User, list[Topology]]:
    """The student and their topologies, refusing while any lab is up."""
    user = _student(db, identity, user_id)
    topos = list(db.scalars(select(Topology).where(Topology.owner_id == user.id)))
    _refuse_running(user, topos)
    return user, topos


def delete_user(db: Session, user: User) -> None:
    db.query(UserSession).filter(UserSession.user_id == user.id).delete()
    db.delete(user)
    db.commit()


def owners(db: Session, owner_ids: set[str]) -> dict[str, dict[str, str]]:
    """``{id: {id, username, role}}`` for the given user ids, in one query."""
    if not owner_ids:
        return {}
    rows = db.execute(select(User.id, User.username, User.role).where(User.id.in_(owner_ids)))
    return {uid: {"id": uid, "username": name, "role": role} for uid, name, role in rows.all()}


def owner_out(known: dict[str, dict[str, str]], owner_id: str | None) -> dict[str, str] | None:
    """A topology's ``owner`` in an API summary (None: nobody's, accounts off)."""
    if not owner_id:
        return None
    return known.get(owner_id) or {"id": owner_id, "username": "unknown", "role": "student"}


# ── staff (admins) ──────────────────────────────────────────────────


def _staff(db: Session, user_id: str) -> User:
    user = db.get(User, user_id)
    if user is None or user.role not in STAFF_ROLES:
        raise NotFound("Staff member")
    return user


def _check_staff_role(role: str) -> None:
    if role not in STAFF_ROLES:
        raise Invalid("A staff member is an admin or an instructor", code="invalid_role")


def staff_out(db: Session, user: User) -> dict[str, Any]:
    return list_staff(db, only=user.id)[0]


def list_staff(db: Session, *, only: str | None = None) -> list[dict[str, Any]]:
    """Every admin and instructor, with their class's size and their own
    topologies and labs."""
    stmt = select(User).where(User.role.in_(STAFF_ROLES)).order_by(User.username)
    if only:
        stmt = stmt.where(User.id == only)
    users = list(db.scalars(stmt))
    classes = {
        c.instructor_id: c
        for c in db.scalars(select(Class).where(Class.instructor_id.in_([u.id for u in users])))
    }
    sizes = dict(
        db.execute(
            select(User.class_id, func.count(User.id))
            .where(User.role == "student", User.class_id.is_not(None))
            .group_by(User.class_id)
        ).all()
    )
    counts, labs = _ownership(db, [u.id for u in users])
    out = []
    for u in users:
        cls = classes.get(u.id)
        out.append(
            {
                "id": u.id,
                "username": u.username,
                "role": u.role,
                "env_managed": bool(u.env_managed),
                "must_change_password": bool(u.must_change_password),
                "created_at": u.created_at,
                "last_seen_at": u.last_seen_at,
                "student_count": sizes.get(cls.id, 0) if cls else 0,
                "signup_open": bool(cls.signup_open) if cls else False,
                "topology_count": counts.get(u.id, 0),
                "labs": labs.get(u.id, []),
            }
        )
    return out


def create_staff(db: Session, *, username: str, role: str) -> tuple[User, str]:
    """A new admin or instructor with a temporary password (shown once)."""
    _check_staff_role(role)
    name = _valid_username(username)
    _ensure_free(db, name)
    temporary = passwords.new_temporary_password()
    user = User(
        username=name,
        password_hash=passwords.hash_password(temporary),
        role=role,
        must_change_password=True,
    )
    db.add(user)
    db.flush()
    class_of(db, user.id)
    db.commit()
    return user, temporary


def _admin_count(db: Session) -> int:
    return db.scalar(select(func.count(User.id)).where(User.role == "admin")) or 0


def set_role(db: Session, actor: Identity, user_id: str, role: str) -> User:
    """Make a staff member an admin or an instructor."""
    _check_staff_role(role)
    user = _staff(db, user_id)
    if user.role == role:
        return user
    if user.id == actor.user_id:
        raise Conflict("You cannot change your own role", code="cannot_change_self")
    if user.env_managed:
        raise Conflict("The environment's admin is always an admin", code="managed_by_env")
    if user.role == "admin" and _admin_count(db) <= 1:
        raise Conflict("There must be at least one admin", code="last_admin")
    user.role = role
    db.commit()
    return user


def reset_staff_password(db: Session, actor: Identity, user_id: str) -> str:
    """A temporary password (shown once) for a staff member."""
    user = _staff(db, user_id)
    if user.env_managed:
        raise Conflict(
            "This admin's password is set by AE3GIS_ADMIN_PASSWORD", code="managed_by_env"
        )
    if user.id == actor.user_id:
        raise Conflict("Change your own password from your user menu", code="cannot_change_self")
    return _temporary_password(db, user)


def delete_staff(
    db: Session, actor: Identity, user_id: str, *, transfer_to: str | None = None
) -> User:
    """Remove a staff member; their topologies (labs included) and their
    students go to ``transfer_to`` (default: the caller). Returns the heir."""
    user = _staff(db, user_id)
    if user.id == actor.user_id:
        raise Conflict("You cannot remove your own account", code="cannot_delete_self")
    if user.env_managed:
        raise Conflict("The environment's admin cannot be removed", code="managed_by_env")
    if user.role == "admin" and _admin_count(db) <= 1:
        raise Conflict("There must be at least one admin", code="last_admin")
    heir_id = transfer_to or actor.user_id
    heir = db.get(User, heir_id) if heir_id else None
    if heir is None or heir.role not in STAFF_ROLES or heir.id == user.id:
        raise Invalid("Hand their work to another admin or instructor", code="bad_transfer")
    db.execute(sql_update(Topology).where(Topology.owner_id == user.id).values(owner_id=heir.id))
    old = db.scalar(select(Class).where(Class.instructor_id == user.id))
    if old is not None:
        new = class_of(db, heir.id)
        db.execute(sql_update(User).where(User.class_id == old.id).values(class_id=new.id))
        db.delete(old)
    db.query(UserSession).filter(UserSession.user_id == user.id).delete()
    db.delete(user)
    db.commit()
    return heir


# ── the per-student lab cap ─────────────────────────────────────────


def check_lab_cap(db: Session, identity: Identity, topo: Topology, settings: Settings) -> None:
    """Refuse a student's deploy that would exceed ``student_max_labs``.

    Called under the runner's admission lock (``deployment.start_deploy``'s
    ``admit``), so two deploys by one student cannot both slip under the cap.
    """
    cap = settings.student_max_labs
    if not identity.is_student or cap <= 0 or not identity.user_id:
        return
    # A retired lesson copy's lab is being destroyed; it never blocks the student.
    others = [
        t for t in lab_topologies(db, identity.user_id) if t.id != topo.id and t.retired_at is None
    ]
    if len(others) >= cap:
        names = ", ".join(f"'{t.name}'" for t in others)
        raise Conflict(
            f"You can run {cap} lab(s) at a time; destroy {names} first",
            code="lab_limit",
            limit=cap,
            labs=[{"id": t.id, "name": t.name} for t in others],
        )
