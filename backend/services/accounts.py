"""Accounts: the instructor, self-registered students, sessions, the class.

Classroom mode is on when ``Settings.auth_required`` (an instructor password or
token is configured). Then there is exactly one instructor, whose row is kept in
step with the environment at every start (``bootstrap_instructor``), and any
number of students, who sign themselves up with the class join code while the
instructor has sign-up open. With accounts off every caller is the instructor
(``OPEN_INSTRUCTOR``) and none of this is consulted.

A sign-in is an opaque random bearer token; only its sha256 is stored. Who may
touch which topology is ``api.access``; this module only answers "who is it".
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

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.errors import Conflict, Forbidden, Invalid, NotFound, TooManyRequests, Unauthorized
from config import Settings
from db.models import AppSetting, Topology, User, UserSession, utcnow
from domain import passwords

Role = Literal["instructor", "student"]

USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,31}$")
MIN_PASSWORD = 8
# Topology statuses that hold (or may still hold) containers on this host.
LAB_STATUSES = ("deploying", "deployed", "destroying")
# last_seen is written at most this often per session (not on every request).
_SEEN_EVERY = timedelta(seconds=60)


@dataclass(frozen=True)
class Identity:
    """Who is calling. ``user_id`` is None for the instructor when accounts are
    off (no rows exist) or when the static API token is used before any row."""

    user_id: str | None
    username: str
    role: Role

    @property
    def is_instructor(self) -> bool:
        return self.role == "instructor"

    @property
    def owner_id(self) -> str | None:
        """What ``Topology.owner_id`` holds for things this caller creates:
        the student's id, None for the instructor."""
        return None if self.is_instructor else self.user_id


OPEN_INSTRUCTOR = Identity(user_id=None, username="instructor", role="instructor")


def _aware(dt: datetime | None) -> datetime | None:
    # SQLite hands DateTime columns back naive; they are written in UTC.
    if dt is None or dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=UTC)


def normalize_username(raw: str) -> str:
    return (raw or "").strip().lower()


def identity_of(user: User) -> Identity:
    return Identity(user_id=user.id, username=user.username, role=user.role)  # type: ignore[arg-type]


def instructor_row(db: Session) -> User | None:
    return db.scalar(select(User).where(User.role == "instructor"))


# ── the instructor (from the environment) ───────────────────────────


def bootstrap_instructor(db: Session, settings: Settings) -> None:
    """Create or update the single instructor row from the environment.

    A changed password replaces the hash and signs the instructor out
    everywhere. A no-op while accounts are off.
    """
    password = settings.instructor_login_password
    if not password:
        return
    username = normalize_username(settings.instructor_username) or "instructor"
    row = instructor_row(db)
    clash = db.scalar(select(User).where(User.username == username, User.role != "instructor"))
    if clash is not None:
        raise RuntimeError(
            f"AE3GIS_INSTRUCTOR_USERNAME '{username}' is already a student's username; "
            "pick another one or remove that student"
        )
    if row is None:
        db.add(
            User(
                username=username,
                password_hash=passwords.hash_password(password),
                role="instructor",
            )
        )
    else:
        row.username = username
        if not passwords.verify_password(password, row.password_hash) or passwords.needs_rehash(
            row.password_hash
        ):
            row.password_hash = passwords.hash_password(password)
            db.query(UserSession).filter(UserSession.user_id == row.id).delete()
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
    static = settings.instructor_token.strip()
    if static and hmac.compare_digest(token.encode(), static.encode()):
        row = instructor_row(db)
        if row is None:
            return OPEN_INSTRUCTOR
        return identity_of(row)
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
    return identity_of(user)


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
    *,
    username: str,
    password: str,
    join_code: str,
) -> SignIn:
    if not settings.auth_required:
        raise Conflict("Accounts are off on this instance; no sign-up needed", code="accounts_off")
    cls = class_settings(db)
    if not cls["signup_open"] or not cls["join_code"]:
        raise Forbidden("Sign-up is closed; ask your instructor to open it", code="signup_closed")
    given = passwords.normalize_join_code(join_code)
    expected = passwords.normalize_join_code(cls["join_code"])
    if not hmac.compare_digest(given.encode(), expected.encode()):
        raise Forbidden("That join code is not right", code="bad_join_code")
    name = normalize_username(username)
    if not USERNAME_RE.match(name):
        raise Invalid(
            "Usernames are 3-32 characters: letters, digits, '.', '_' or '-'",
            code="invalid_username",
        )
    _check_password(password)
    if db.scalar(select(User).where(User.username == name)) is not None:
        raise Conflict("That username is taken", code="username_taken")
    user = User(username=name, password_hash=passwords.hash_password(password), role="student")
    db.add(user)
    db.commit()
    return start_session(db, user, settings)


def change_password(
    db: Session, identity: Identity, *, current: str, new: str, keep_token: str | None
) -> None:
    if identity.is_instructor:
        raise Conflict(
            "The instructor's password is set by AE3GIS_INSTRUCTOR_PASSWORD",
            code="managed_by_env",
        )
    user = db.get(User, identity.user_id) if identity.user_id else None
    if user is None:
        raise NotFound("User")
    if not passwords.verify_password(current, user.password_hash):
        raise Forbidden("The current password is not right", code="bad_credentials")
    _check_password(new)
    user.password_hash = passwords.hash_password(new)
    keep = passwords.token_hash(keep_token) if keep_token else ""
    db.query(UserSession).filter(
        UserSession.user_id == user.id, UserSession.token_hash != keep
    ).delete()
    db.commit()


# ── the class (instructor) ──────────────────────────────────────────

_SIGNUP_OPEN = "class.signup_open"
_JOIN_CODE = "class.join_code"


def _get_setting(db: Session, key: str, default: Any = None) -> Any:
    row = db.get(AppSetting, key)
    return default if row is None else row.value


def _set_setting(db: Session, key: str, value: Any) -> None:
    row = db.get(AppSetting, key)
    if row is None:
        db.add(AppSetting(key=key, value=value))
    else:
        row.value = value


def class_settings(db: Session) -> dict[str, Any]:
    return {
        "signup_open": bool(_get_setting(db, _SIGNUP_OPEN, False)),
        "join_code": _get_setting(db, _JOIN_CODE) or None,
    }


def update_class_settings(
    db: Session, *, signup_open: bool | None = None, rotate_join_code: bool = False
) -> dict[str, Any]:
    current = class_settings(db)
    if rotate_join_code or (signup_open and not current["join_code"]):
        _set_setting(db, _JOIN_CODE, passwords.new_join_code())
    if signup_open is not None:
        _set_setting(db, _SIGNUP_OPEN, bool(signup_open))
    db.commit()
    return class_settings(db)


def _student(db: Session, user_id: str) -> User:
    user = db.get(User, user_id)
    if user is None or user.role != "student":
        raise NotFound("Student")
    return user


def lab_topologies(db: Session, owner_id: str) -> list[Topology]:
    """A student's topologies that hold (or may hold) containers on this host."""
    rows = db.scalars(select(Topology).where(Topology.owner_id == owner_id))
    return [t for t in rows if holds_lab(t)]


def holds_lab(topo: Topology) -> bool:
    return topo.status in LAB_STATUSES or (topo.status == "error" and topo.engine_state is not None)


def list_students(db: Session) -> list[dict[str, Any]]:
    users = list(db.scalars(select(User).where(User.role == "student").order_by(User.username)))
    counts = dict(
        db.execute(
            select(Topology.owner_id, func.count(Topology.id))
            .where(Topology.owner_id.is_not(None), Topology.retired_at.is_(None))
            .group_by(Topology.owner_id)
        ).all()
    )
    return [
        {
            "id": u.id,
            "username": u.username,
            "created_at": u.created_at,
            "last_seen_at": u.last_seen_at,
            "topology_count": counts.get(u.id, 0),
            "labs": [
                {"id": t.id, "name": t.name, "status": t.status} for t in lab_topologies(db, u.id)
            ],
        }
        for u in users
    ]


def reset_password(db: Session, user_id: str) -> str:
    """Give a student a temporary password (shown once) and sign them out."""
    user = _student(db, user_id)
    temporary = passwords.new_temporary_password()
    user.password_hash = passwords.hash_password(temporary)
    db.query(UserSession).filter(UserSession.user_id == user.id).delete()
    db.commit()
    return temporary


def student_for_removal(db: Session, user_id: str) -> tuple[User, list[Topology]]:
    """The student and their topologies, refusing while any lab is up."""
    user = _student(db, user_id)
    topos = list(db.scalars(select(Topology).where(Topology.owner_id == user.id)))
    running = [t for t in topos if holds_lab(t)]
    if running:
        raise Conflict(
            f"Destroy {user.username}'s running lab(s) first",
            code="student_has_labs",
            labs=[t.id for t in running],
        )
    return user, topos


def delete_user(db: Session, user: User) -> None:
    db.query(UserSession).filter(UserSession.user_id == user.id).delete()
    db.delete(user)
    db.commit()


def owner_names(db: Session, owner_ids: set[str]) -> dict[str, str]:
    if not owner_ids:
        return {}
    rows = db.execute(select(User.id, User.username).where(User.id.in_(owner_ids)))
    return dict(rows.all())


# ── the per-student lab cap ─────────────────────────────────────────


def check_lab_cap(db: Session, identity: Identity, topo: Topology, settings: Settings) -> None:
    """Refuse a student's deploy that would exceed ``student_max_labs``.

    Called under the runner's admission lock (``deployment.start_deploy``'s
    ``admit``), so two deploys by one student cannot both slip under the cap.
    """
    cap = settings.student_max_labs
    if identity.is_instructor or cap <= 0 or not identity.user_id:
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
