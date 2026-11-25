"""Accounts: the admin from the environment, staff accounts (admins and
instructors) made by admins, student sign-up with a class's join code,
sessions, password changes and resets (temporary passwords must be replaced),
the class routes."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from db.models import User, UserSession, utcnow
from domain import passwords
from main import create_app
from services.accounts import LoginLimiter
from tests.conftest import (
    ADMIN_PASSWORD,
    STAFF_PASSWORD,
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
        "user": {
            "id": None,
            "username": "admin",
            "role": "admin",
            "must_change_password": False,
            "env_managed": False,
        },
        "auth_required": False,
    }
    assert _login(client, "admin", "x").json()["code"] == "accounts_off"
    assert client.get("/api/v1/class").json() == {
        "signup_open": False,
        "join_code": None,
        "tutor_enabled": False,
    }
    r = client.put("/api/v1/class", json={"signup_open": True})
    assert r.status_code == 409 and r.json()["code"] == "accounts_off"
    assert client.get("/api/v1/users").json() == {"staff": []}  # everyone is an admin
    health = client.get("/api/v1/system/health").json()
    assert health["auth_required"] is False and health["signup_open"] is False


# ── the admin from the environment ──────────────────────────────────


def test_the_admin_signs_in_with_the_environment_password(classroom):
    c = classroom.client
    assert c.get("/api/v1/auth/me").status_code == 401
    assert _login(c, "admin", "nope").json()["code"] == "bad_credentials"
    assert _login(c, "nobody", ADMIN_PASSWORD).status_code == 401
    r = _login(c, " Admin ", ADMIN_PASSWORD)  # usernames are case-insensitive
    assert r.status_code == 200
    me = c.get("/api/v1/auth/me", headers=bearer(r.json()["token"])).json()
    assert me["user"]["role"] == "admin" and me["auth_required"] is True
    assert me["user"]["env_managed"] is True and me["user"]["must_change_password"] is False


def test_a_changed_environment_password_signs_the_admin_out(tmp_path, fake_engine):
    with TestClient(create_app(make_settings(tmp_path, admin_password="first-pass"))) as c:
        token = _login(c, "admin", "first-pass").json()["token"]
        assert c.get("/api/v1/auth/me", headers=bearer(token)).status_code == 200
    with TestClient(create_app(make_settings(tmp_path, admin_password="second-pass"))) as c:
        assert c.get("/api/v1/auth/me", headers=bearer(token)).status_code == 401
        assert _login(c, "admin", "first-pass").status_code == 401
        assert _login(c, "admin", "second-pass").status_code == 200


def test_the_old_instructor_variables_still_make_the_admin(tmp_path, fake_engine):
    settings = make_settings(tmp_path, instructor_password="old-pass", instructor_username="prof")
    with TestClient(create_app(settings, fake_engine)) as c:
        r = _login(c, "prof", "old-pass")
        assert r.status_code == 200 and r.json()["user"]["role"] == "admin"
    # Unset, the username stays what it was (an upgrade never renames the admin).
    with TestClient(create_app(make_settings(tmp_path, admin_password="old-pass"))) as c:
        assert _login(c, "prof", "old-pass").status_code == 200


def test_the_static_token_is_the_admin(tmp_path, fake_engine):
    app = create_app(make_settings(tmp_path, admin_token="s3cret"), fake_engine)
    with TestClient(app) as c:
        me = c.get("/api/v1/auth/me", headers=bearer("s3cret")).json()
        assert me["user"]["role"] == "admin"
        # On its own it is also the admin's password.
        assert _login(c, "admin", "s3cret").status_code == 200
    app = create_app(make_settings(tmp_path, instructor_token="s3cret"), fake_engine)
    with TestClient(app) as c:
        assert c.get("/api/v1/auth/me", headers=bearer("s3cret")).status_code == 200


def test_the_admin_username_cannot_be_anothers(tmp_path, fake_engine):
    settings = make_settings(tmp_path, admin_password=ADMIN_PASSWORD)
    with TestClient(create_app(settings, fake_engine)) as c:
        token = _login(c, "admin", ADMIN_PASSWORD).json()["token"]
        code = c.put("/api/v1/class", json={"signup_open": True}, headers=bearer(token))
        assert _signup(c, "teacher", code.json()["join_code"]).status_code == 201
    clash = make_settings(tmp_path, admin_password=ADMIN_PASSWORD, admin_username="teacher")
    with pytest.raises(RuntimeError, match="already a student's"):
        create_app(clash, fake_engine)


def test_turning_accounts_on_gives_the_admin_what_open_mode_made(tmp_path, fake_engine):
    with TestClient(create_app(make_settings(tmp_path), fake_engine)) as c:
        made = c.post("/api/v1/topologies", json={"name": "open", "data": TWO_SUBNETS}).json()
        assert made["owner"] is None
    with TestClient(create_app(make_settings(tmp_path, admin_password=ADMIN_PASSWORD))) as c:
        admin = bearer(_login(c, "admin", ADMIN_PASSWORD).json()["token"])
        rec = c.get(f"/api/v1/topologies/{made['id']}", headers=admin).json()
        assert rec["owner"]["username"] == "admin" and rec["owner"]["role"] == "admin"


# ── staff accounts ──────────────────────────────────────────────────


def test_an_admin_makes_staff_who_replace_their_temporary_password(classroom):
    c = classroom.client
    r = c.post(
        "/api/v1/users", json={"username": "Tess", "role": "instructor"}, headers=classroom.admin
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user"]["username"] == "tess" and body["user"]["role"] == "instructor"
    assert body["user"]["must_change_password"] is True
    temporary = body["password"]

    signed = _login(c, "tess", temporary).json()
    assert signed["user"]["must_change_password"] is True
    tess = bearer(signed["token"])
    # Until the password is changed, only /auth works.
    assert c.get("/api/v1/auth/me", headers=tess).status_code == 200
    r = c.get("/api/v1/topologies", headers=tess)
    assert r.status_code == 403 and r.json()["code"] == "password_change_required"
    same = {"current": temporary, "new": temporary}
    assert (
        c.post("/api/v1/auth/password", json=same, headers=tess).json()["code"] == "same_password"
    )
    body = {"current": temporary, "new": STAFF_PASSWORD}
    assert c.post("/api/v1/auth/password", json=body, headers=tess).status_code == 204
    assert c.get("/api/v1/topologies", headers=tess).status_code == 200
    assert c.get("/api/v1/auth/me", headers=tess).json()["user"]["must_change_password"] is False

    r = c.post("/api/v1/users", json={"username": "tess"}, headers=classroom.admin)
    assert r.json()["code"] == "username_taken"
    r = c.post("/api/v1/users", json={"username": "x"}, headers=classroom.admin)
    assert r.json()["code"] == "invalid_username"
    r = c.post(
        "/api/v1/users", json={"username": "sam", "role": "student"}, headers=classroom.admin
    )
    assert r.status_code == 422


def test_only_admins_manage_staff(classroom):
    c = classroom.client
    tess = classroom.teacher("tess")
    alice = classroom.student("alice")
    for headers in (tess, alice):
        for method, path in [
            ("get", "/api/v1/users"),
            ("post", "/api/v1/users"),
            ("patch", f"/api/v1/users/{classroom.ids['tess']}"),
            ("post", f"/api/v1/users/{classroom.ids['tess']}/reset-password"),
            ("delete", f"/api/v1/users/{classroom.ids['tess']}"),
        ]:
            r = c.request(method, path, headers=headers, json={"username": "z1z", "role": "admin"})
            assert r.status_code == 403 and r.json()["code"] == "admin_only", (method, path)


def test_the_staff_list_and_roles(classroom):
    c = classroom.client
    classroom.teacher("tess")
    classroom.student("bob", teacher="tess")
    staff = {
        s["username"]: s for s in c.get("/api/v1/users", headers=classroom.admin).json()["staff"]
    }
    assert set(staff) == {"admin", "tess"}
    assert staff["admin"]["env_managed"] is True and staff["admin"]["role"] == "admin"
    assert staff["tess"]["student_count"] == 1 and staff["tess"]["signup_open"] is True

    tid = classroom.ids["tess"]
    r = c.patch(f"/api/v1/users/{tid}", json={"role": "admin"}, headers=classroom.admin)
    assert r.status_code == 200 and r.json()["role"] == "admin"
    tess = classroom.teacher("tess")
    assert c.get("/api/v1/users", headers=tess).status_code == 200  # now an admin
    r = c.patch(f"/api/v1/users/{tid}", json={"role": "instructor"}, headers=tess)
    assert r.json()["code"] == "cannot_change_self"
    r = c.patch(
        f"/api/v1/users/{classroom.ids['admin']}", json={"role": "instructor"}, headers=tess
    )
    assert r.json()["code"] == "managed_by_env"
    r = c.patch(f"/api/v1/users/{tid}", json={"role": "instructor"}, headers=classroom.admin)
    assert r.json()["role"] == "instructor"
    assert c.get("/api/v1/users", headers=tess).status_code == 403
    r = c.patch(
        f"/api/v1/users/{classroom.ids['bob']}", json={"role": "admin"}, headers=classroom.admin
    )
    assert r.status_code == 404  # a student is not staff


def test_an_admin_resets_a_staff_password(classroom):
    c = classroom.client
    tess = classroom.teacher("tess")
    r = c.post(f"/api/v1/users/{classroom.ids['tess']}/reset-password", headers=classroom.admin)
    temporary = r.json()["password"]
    assert c.get("/api/v1/auth/me", headers=tess).status_code == 401  # signed out
    assert _login(c, "tess", temporary).json()["user"]["must_change_password"] is True
    r = c.post(f"/api/v1/users/{classroom.ids['admin']}/reset-password", headers=classroom.admin)
    assert r.json()["code"] == "managed_by_env"


def test_removing_staff_hands_their_work_on(classroom):
    c = classroom.client
    tess = classroom.teacher("tess")
    classroom.teacher("uma")
    bob = classroom.student("bob", teacher="tess")
    lesson = classroom.create(tess, "lesson")
    assert (
        c.put(
            f"/api/v1/topologies/{lesson['id']}/published", json={"published": True}, headers=tess
        ).status_code
        == 200
    )
    copy = c.post(f"/api/v1/topologies/{lesson['id']}/copy", headers=bob).json()
    assert c.post(f"/api/v1/topologies/{lesson['id']}/deploy", headers=tess).status_code == 202
    classroom.wait()

    tid = classroom.ids["tess"]
    r = c.delete(f"/api/v1/users/{tid}?transfer_to={classroom.ids['bob']}", headers=classroom.admin)
    assert r.status_code == 422 and r.json()["code"] == "bad_transfer"
    r = c.delete(f"/api/v1/users/{tid}?transfer_to={tid}", headers=classroom.admin)
    assert r.json()["code"] == "bad_transfer"
    r = c.delete(f"/api/v1/users/{tid}?transfer_to={classroom.ids['uma']}", headers=classroom.admin)
    assert r.status_code == 204
    assert c.get("/api/v1/auth/me", headers=tess).status_code == 401

    uma = classroom.teacher("uma")
    rec = c.get(f"/api/v1/topologies/{lesson['id']}", headers=uma).json()
    assert rec["owner"]["username"] == "uma" and rec["status"] == "deployed"  # still running
    students = c.get("/api/v1/class/students", headers=uma).json()["students"]
    assert [(s["username"], s["instructor"]["username"]) for s in students] == [("bob", "uma")]
    # bob's lesson copy follows: it is a copy of what is now uma's lesson.
    assert c.get(f"/api/v1/topologies/{copy['id']}", headers=bob).status_code == 200
    listed = {t["id"] for t in c.get("/api/v1/topologies", headers=bob).json()}
    assert lesson["id"] in listed

    r = c.delete(f"/api/v1/users/{classroom.ids['admin']}", headers=uma)
    assert r.json()["code"] == "admin_only"
    r = c.delete(f"/api/v1/users/{classroom.ids['admin']}", headers=classroom.admin)
    assert r.json()["code"] == "cannot_delete_self"


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
    assert _signup(c, "admin", code).json()["code"] == "username_taken"
    assert _signup(c, "a b", code).json()["code"] == "invalid_username"
    assert _signup(c, "bob", code, password="short").json()["code"] == "weak_password"

    # Closing sign-up keeps the code; rotating it invalidates the old one.
    c.put("/api/v1/class", json={"signup_open": False}, headers=classroom.admin)
    assert _signup(c, "carol", code).json()["code"] == "signup_closed"
    new = c.put(
        "/api/v1/class",
        json={"signup_open": True, "rotate_join_code": True},
        headers=classroom.admin,
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
        assert r.status_code == 403 and r.json()["code"] == "staff_only"


def test_each_class_has_its_own_join_code(classroom):
    c = classroom.client
    tess_code = classroom.open_signup("tess")
    admin_code = classroom.open_signup()
    assert tess_code != admin_code
    bob = _signup(c, "bob", tess_code.replace("-", " ").upper())
    assert bob.status_code == 201
    alice = _signup(c, "alice", admin_code)
    assert alice.status_code == 201
    tess = classroom.teacher("tess")
    mine = c.get("/api/v1/class/students", headers=tess).json()["students"]
    assert [s["username"] for s in mine] == ["bob"]
    every = c.get("/api/v1/class/students", headers=classroom.admin).json()["students"]
    assert [(s["username"], s["instructor"]["username"]) for s in every] == [
        ("alice", "admin"),
        ("bob", "tess"),
    ]
    # One class closing does not close the others.
    c.put("/api/v1/class", json={"signup_open": False}, headers=tess)
    assert _signup(c, "carl", tess_code).json()["code"] == "signup_closed"
    assert _signup(c, "carl", admin_code).status_code == 201
    assert c.get("/api/v1/system/health").json()["signup_open"] is True
    # An instructor manages only their own students.
    alice_id = alice.json()["user"]["id"]
    r = c.post(f"/api/v1/class/students/{alice_id}/reset-password", headers=tess)
    assert r.status_code == 404
    assert c.delete(f"/api/v1/class/students/{alice_id}", headers=tess).status_code == 404


def test_wrong_join_codes_are_refused_for_a_while(classroom):
    c = classroom.client
    code = classroom.open_signup()
    for _ in range(10):
        assert _signup(c, "eve", "zzzz-zzzz").json()["code"] == "bad_join_code"
    r = _signup(c, "eve", code)
    assert r.status_code == 429 and r.json()["code"] == "too_many_attempts"


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
        assert _login(c, "admin", "guess").status_code == 401
    r = _login(c, "admin", ADMIN_PASSWORD)
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
    r = c.post("/api/v1/auth/password", json=body, headers=classroom.admin)
    assert r.json()["code"] == "managed_by_env"


def test_staff_reset_a_students_password(classroom):
    c = classroom.client
    alice = classroom.student("alice")
    students = c.get("/api/v1/class/students", headers=classroom.admin).json()
    assert students["max_labs"] == 1
    (row,) = students["students"]
    assert row["username"] == "alice" and row["topology_count"] == 0 and row["labs"] == []
    r = c.post(f"/api/v1/class/students/{row['id']}/reset-password", headers=classroom.admin)
    temporary = r.json()["password"]
    assert c.get("/api/v1/auth/me", headers=alice).status_code == 401
    r = _login(c, "alice", temporary)
    assert r.status_code == 200 and r.json()["user"]["must_change_password"] is True
    assert (
        c.post("/api/v1/class/students/nope/reset-password", headers=classroom.admin)
    ).status_code == 404


def test_removing_a_student_takes_their_topologies_once_their_labs_are_down(classroom):
    c = classroom.client
    alice = classroom.student("alice")
    mine = classroom.create(alice)
    assert c.post(f"/api/v1/topologies/{mine['id']}/deploy", headers=alice).status_code == 202
    classroom.wait()
    students = c.get("/api/v1/class/students", headers=classroom.admin).json()["students"]
    (row,) = students
    assert row["topology_count"] == 1
    assert row["labs"] == [{"id": mine["id"], "name": "lab", "status": "deployed"}]

    r = c.delete(f"/api/v1/class/students/{row['id']}", headers=classroom.admin)
    assert r.status_code == 409 and r.json()["code"] == "student_has_labs"
    # Staff can destroy a student's lab.
    r = c.post(f"/api/v1/topologies/{mine['id']}/destroy", headers=classroom.admin)
    assert r.status_code == 202
    classroom.wait()
    r = c.delete(f"/api/v1/class/students/{row['id']}", headers=classroom.admin)
    assert r.status_code == 204
    assert c.get(f"/api/v1/topologies/{mine['id']}", headers=classroom.admin).status_code == 404
    assert c.get("/api/v1/auth/me", headers=alice).status_code == 401
    with classroom.app.state.session_factory() as db:
        assert db.query(User).filter(User.role == "student").count() == 0


def test_a_student_creates_owned_topologies(classroom):
    c = classroom.client
    alice = classroom.student("alice")
    rec = classroom.create(alice)
    assert rec["owner"]["username"] == "alice" and rec["published"] is False
    own = classroom.create(classroom.admin)
    assert own["owner"] == {"id": classroom.ids["admin"], "username": "admin", "role": "admin"}
    files = {"file": ("x.json", b'{"name": "Imported", "sites": [], "siteConnections": []}')}
    imported = c.post("/api/v1/topologies/import-json", files=files, headers=alice).json()
    assert imported["owner"]["username"] == "alice"
    preset = c.post("/api/v1/presets/two-subnet-demo/load", headers=alice).json()
    assert preset["owner"]["username"] == "alice"
    assert TWO_SUBNETS["sites"][0]["id"] in {s["id"] for s in rec["data"]["sites"]}
