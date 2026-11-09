"""Accounts: the instructor from the environment, student sign-up with the
class join code, sessions, password changes and resets, the class routes."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from db.models import User, UserSession, utcnow
from domain import passwords
from main import create_app
from services.accounts import LoginLimiter
from tests.conftest import (
    INSTRUCTOR_PASSWORD,
    STUDENT_PASSWORD,
    TWO_SUBNETS,
    bearer,
    make_settings,
)


def _login(client, username: str, password: str):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _signup(client, username: str, join_code: str, password: str = STUDENT_PASSWORD):
    return client.post(
        "/api/v1/auth/signup",
        json={"username": username, "password": password, "join_code": join_code},
    )


# ── passwords ───────────────────────────────────────────────────────


def test_password_hashes_verify_and_are_salted():
    a = passwords.hash_password("correct horse")
    b = passwords.hash_password("correct horse")
    assert a != b and a.startswith("scrypt$")
    assert passwords.verify_password("correct horse", a)
    assert not passwords.verify_password("wrong horse", a)
    assert not passwords.verify_password("x", "not-a-hash")
    assert not passwords.needs_rehash(a)
    assert passwords.needs_rehash("scrypt$1024$8$1$abc$def")


def test_join_codes_ignore_case_and_separators():
    code = passwords.new_join_code()
    assert len(code) == 9 and code[4] == "-"
    assert passwords.normalize_join_code(code.upper().replace("-", " ")) == code.replace("-", "")


def test_login_limiter_locks_a_pair_for_a_window():
    now = [0.0]
    limiter = LoginLimiter(max_failures=3, window_s=60, clock=lambda: now[0])
    for _ in range(3):
        limiter.check("alice", "ip")
        limiter.failed("alice", "ip")
    with pytest.raises(Exception) as exc:
        limiter.check("alice", "ip")
    assert exc.value.status_code == 429
    limiter.check("alice", "other-ip")  # another client is not affected
    now[0] = 61
    limiter.check("alice", "ip")  # the window passed


# ── open mode ───────────────────────────────────────────────────────


def test_open_mode_has_no_accounts(client):
    me = client.get("/api/v1/auth/me").json()
    assert me == {
        "user": {"id": None, "username": "instructor", "role": "instructor"},
        "auth_required": False,
    }
    assert _login(client, "instructor", "x").json()["code"] == "accounts_off"
    assert client.get("/api/v1/class").status_code == 200  # everyone is the instructor
    health = client.get("/api/v1/system/health").json()
    assert health["auth_required"] is False and health["signup_open"] is False


# ── the instructor ──────────────────────────────────────────────────


def test_the_instructor_signs_in_with_the_environment_password(classroom):
    c = classroom.client
    assert c.get("/api/v1/auth/me").status_code == 401
    assert _login(c, "instructor", "nope").json()["code"] == "bad_credentials"
    assert _login(c, "nobody", INSTRUCTOR_PASSWORD).status_code == 401
    r = _login(c, " Instructor ", INSTRUCTOR_PASSWORD)  # usernames are case-insensitive
    assert r.status_code == 200
    me = c.get("/api/v1/auth/me", headers=bearer(r.json()["token"])).json()
    assert me["user"]["role"] == "instructor" and me["auth_required"] is True


def test_a_changed_environment_password_signs_the_instructor_out(tmp_path, fake_engine):
    with TestClient(create_app(make_settings(tmp_path, instructor_password="first-pass"))) as c:
        token = _login(c, "instructor", "first-pass").json()["token"]
        assert c.get("/api/v1/auth/me", headers=bearer(token)).status_code == 200
    with TestClient(create_app(make_settings(tmp_path, instructor_password="second-pass"))) as c:
        assert c.get("/api/v1/auth/me", headers=bearer(token)).status_code == 401
        assert _login(c, "instructor", "first-pass").status_code == 401
        assert _login(c, "instructor", "second-pass").status_code == 200


def test_the_static_token_is_the_instructor(tmp_path, fake_engine):
    app = create_app(make_settings(tmp_path, instructor_token="s3cret"), fake_engine)
    with TestClient(app) as c:
        me = c.get("/api/v1/auth/me", headers=bearer("s3cret")).json()
        assert me["user"]["role"] == "instructor"
        # On its own it is also the instructor's password.
        assert _login(c, "instructor", "s3cret").status_code == 200


def test_the_instructor_username_cannot_be_a_students(tmp_path, fake_engine):
    settings = make_settings(tmp_path, instructor_password=INSTRUCTOR_PASSWORD)
    with TestClient(create_app(settings, fake_engine)) as c:
        token = _login(c, "instructor", INSTRUCTOR_PASSWORD).json()["token"]
        code = c.put("/api/v1/class", json={"signup_open": True}, headers=bearer(token))
        assert _signup(c, "teacher", code.json()["join_code"]).status_code == 201
    clash = make_settings(
        tmp_path, instructor_password=INSTRUCTOR_PASSWORD, instructor_username="teacher"
    )
    with pytest.raises(RuntimeError, match="already a student"):
        create_app(clash, fake_engine)


# ── students ────────────────────────────────────────────────────────


def test_sign_up_is_closed_until_the_instructor_opens_it(classroom):
    c = classroom.client
    assert _signup(c, "alice", "whatever").json()["code"] == "signup_closed"
    assert c.get("/api/v1/system/health").json()["signup_open"] is False

    code = classroom.open_signup()
    assert c.get("/api/v1/system/health").json()["signup_open"] is True
    assert _signup(c, "alice", "wrong-code").json()["code"] == "bad_join_code"
    r = _signup(c, "Alice", code.upper())
    assert r.status_code == 201, r.text
    user = r.json()["user"]
    assert user["username"] == "alice" and user["role"] == "student"
    me = c.get("/api/v1/auth/me", headers=bearer(r.json()["token"])).json()
    assert me["user"]["id"] == user["id"]

    assert _signup(c, "alice", code).json()["code"] == "username_taken"
    assert _signup(c, "instructor", code).json()["code"] == "username_taken"
    assert _signup(c, "a b", code).json()["code"] == "invalid_username"
    assert _signup(c, "bob", code, password="short").json()["code"] == "weak_password"

    # Closing sign-up keeps the code; rotating it invalidates the old one.
    c.put("/api/v1/class", json={"signup_open": False}, headers=classroom.instructor)
    assert _signup(c, "carol", code).json()["code"] == "signup_closed"
    new = c.put(
        "/api/v1/class",
        json={"signup_open": True, "rotate_join_code": True},
        headers=classroom.instructor,
    ).json()["join_code"]
    assert new != code
    assert _signup(c, "carol", code).json()["code"] == "bad_join_code"
    assert _signup(c, "carol", new).status_code == 201
    # Signed-up students can still sign in.
    assert _login(c, "alice", STUDENT_PASSWORD).status_code == 200


def test_students_cannot_manage_the_class(classroom):
    alice = classroom.student("alice")
    c = classroom.client
    for method, path in [
        ("get", "/api/v1/class"),
        ("put", "/api/v1/class"),
        ("get", "/api/v1/class/students"),
    ]:
        r = c.request(method, path, headers=alice, json={"signup_open": True})
        assert r.status_code == 403 and r.json()["code"] == "instructor_only"


def test_logout_and_expiry_end_a_session(classroom):
    c = classroom.client
    alice = classroom.student("alice")
    assert c.get("/api/v1/auth/me", headers=alice).status_code == 200
    assert c.post("/api/v1/auth/logout", headers=alice).status_code == 204
    assert c.get("/api/v1/auth/me", headers=alice).status_code == 401

    token = _login(c, "alice", STUDENT_PASSWORD).json()["token"]
    with classroom.app.state.session_factory() as db:
        sess = db.get(UserSession, passwords.token_hash(token))
        sess.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert c.get("/api/v1/auth/me", headers=bearer(token)).status_code == 401


def test_repeated_failed_sign_ins_are_refused_for_a_while(classroom):
    c = classroom.client
    for _ in range(10):
        assert _login(c, "instructor", "guess").status_code == 401
    r = _login(c, "instructor", INSTRUCTOR_PASSWORD)
    assert r.status_code == 429 and r.json()["code"] == "too_many_attempts"


def test_students_change_their_password_and_other_sign_ins_end(classroom):
    c = classroom.client
    alice = classroom.student("alice")
    other = bearer(_login(c, "alice", STUDENT_PASSWORD).json()["token"])
    body = {"current": "wrong", "new": "brand-new-pass"}
    assert c.post("/api/v1/auth/password", json=body, headers=alice).status_code == 403
    body["current"] = STUDENT_PASSWORD
    assert c.post("/api/v1/auth/password", json=body, headers=alice).status_code == 204
    assert c.get("/api/v1/auth/me", headers=alice).status_code == 200  # this one stays
    assert c.get("/api/v1/auth/me", headers=other).status_code == 401
    assert _login(c, "alice", "brand-new-pass").status_code == 200
    r = c.post("/api/v1/auth/password", json=body, headers=classroom.instructor)
    assert r.json()["code"] == "managed_by_env"


def test_the_instructor_resets_a_students_password(classroom):
    c = classroom.client
    alice = classroom.student("alice")
    students = c.get("/api/v1/class/students", headers=classroom.instructor).json()
    assert students["max_labs"] == 1
    (row,) = students["students"]
    assert row["username"] == "alice" and row["topology_count"] == 0 and row["labs"] == []
    r = c.post(f"/api/v1/class/students/{row['id']}/reset-password", headers=classroom.instructor)
    temporary = r.json()["password"]
    assert c.get("/api/v1/auth/me", headers=alice).status_code == 401
    assert _login(c, "alice", temporary).status_code == 200
    assert (
        c.post("/api/v1/class/students/nope/reset-password", headers=classroom.instructor)
    ).status_code == 404


def test_removing_a_student_takes_their_topologies_once_their_labs_are_down(classroom):
    c = classroom.client
    alice = classroom.student("alice")
    mine = classroom.create(alice)
    assert c.post(f"/api/v1/topologies/{mine['id']}/deploy", headers=alice).status_code == 202
    classroom.wait()
    students = c.get("/api/v1/class/students", headers=classroom.instructor).json()["students"]
    (row,) = students
    assert row["topology_count"] == 1
    assert row["labs"] == [{"id": mine["id"], "name": "lab", "status": "deployed"}]

    r = c.delete(f"/api/v1/class/students/{row['id']}", headers=classroom.instructor)
    assert r.status_code == 409 and r.json()["code"] == "student_has_labs"
    # The instructor can destroy a student's lab.
    r = c.post(f"/api/v1/topologies/{mine['id']}/destroy", headers=classroom.instructor)
    assert r.status_code == 202
    classroom.wait()
    r = c.delete(f"/api/v1/class/students/{row['id']}", headers=classroom.instructor)
    assert r.status_code == 204
    assert (
        c.get(f"/api/v1/topologies/{mine['id']}", headers=classroom.instructor).status_code == 404
    )
    assert c.get("/api/v1/auth/me", headers=alice).status_code == 401
    with classroom.app.state.session_factory() as db:
        assert db.query(User).filter(User.role == "student").count() == 0


def test_a_student_creates_owned_topologies(classroom):
    c = classroom.client
    alice = classroom.student("alice")
    rec = classroom.create(alice)
    assert rec["owner"]["username"] == "alice" and rec["published"] is False
    own = classroom.create(classroom.instructor)
    assert own["owner"] is None
    files = {"file": ("x.json", b'{"name": "Imported", "sites": [], "siteConnections": []}')}
    imported = c.post("/api/v1/topologies/import-json", files=files, headers=alice).json()
    assert imported["owner"]["username"] == "alice"
    preset = c.post("/api/v1/presets/two-subnet-demo/load", headers=alice).json()
    assert preset["owner"]["username"] == "alice"
    assert TWO_SUBNETS["sites"][0]["id"] in {s["id"] for s in rec["data"]["sites"]}
