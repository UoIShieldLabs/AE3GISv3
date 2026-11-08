"""Who may do what in classroom mode (``api.access``): students see their own
topologies and the published ones, work on personal copies, run at most
``student_max_labs`` labs; the instructor sees and may do everything."""

from __future__ import annotations

import copy

import pytest
from starlette.websockets import WebSocketDisconnect

from tests.conftest import TWO_SUBNETS

V1 = "/api/v1"


@pytest.fixture
def setup(classroom):
    """The instructor's draft and published topologies, alice's own topology."""
    alice = classroom.student("alice")
    bob = classroom.student("bob")
    data = copy.deepcopy(TWO_SUBNETS)
    data["tutorials"] = [{"id": "t1", "title": "Intro", "cells": []}]
    data["scenarios"] = [{"id": "s1", "name": "Attack", "phases": []}]
    draft = classroom.create(classroom.instructor, "draft")
    published = classroom.create(classroom.instructor, "lesson", data)
    r = classroom.client.put(
        f"{V1}/topologies/{published['id']}/published",
        json={"published": True},
        headers=classroom.instructor,
    )
    assert r.status_code == 200 and r.json()["published"] is True
    mine = classroom.create(alice, "alice-lab")
    return classroom, alice, bob, draft, published, mine


def _ids(rows):
    return {r["id"] for r in rows}


def test_students_see_their_own_and_the_published(setup):
    cls, alice, bob, draft, published, mine = setup
    c = cls.client
    assert _ids(c.get(f"{V1}/topologies", headers=alice).json()) == {published["id"], mine["id"]}
    assert _ids(c.get(f"{V1}/topologies", headers=bob).json()) == {published["id"]}
    everything = c.get(f"{V1}/topologies", headers=cls.instructor).json()
    assert _ids(everything) == {draft["id"], published["id"], mine["id"]}
    owners = {r["id"]: r["owner"] for r in everything}
    assert owners[mine["id"]]["username"] == "alice" and owners[draft["id"]] is None


def test_a_published_topology_is_view_only_for_students(setup):
    cls, alice, bob, draft, published, mine = setup
    c = cls.client
    pid = published["id"]
    assert c.get(f"{V1}/topologies/{pid}", headers=alice).status_code == 200
    assert c.get(f"{V1}/topologies/{pid}/export", headers=alice).status_code == 200
    for method, path in [
        ("put", f"/topologies/{pid}"),
        ("delete", f"/topologies/{pid}"),
        ("post", f"/topologies/{pid}/deploy"),
        ("post", f"/topologies/{pid}/destroy"),
        ("get", f"/topologies/{pid}/runtime"),
        ("get", f"/topologies/{pid}/events"),
        ("get", f"/topologies/{pid}/jobs"),
        ("get", f"/topologies/{pid}/captures"),
    ]:
        r = c.request(method, V1 + path, headers=alice, json={"name": "x"})
        assert r.status_code == 403 and r.json()["code"] == "not_owner", (method, path)


def test_other_peoples_topologies_do_not_exist_for_a_student(setup):
    cls, alice, bob, draft, published, mine = setup
    c = cls.client
    for headers, tid in [(alice, draft["id"]), (bob, mine["id"])]:
        assert c.get(f"{V1}/topologies/{tid}", headers=headers).status_code == 404
        assert (
            c.put(f"{V1}/topologies/{tid}", json={"name": "x"}, headers=headers).status_code == 404
        )
        assert c.post(f"{V1}/topologies/{tid}/copy", headers=headers).status_code == 404
        assert c.get(f"{V1}/images?topology_id={tid}", headers=headers).status_code == 404
    # The instructor may change a student's topology.
    r = c.put(f"{V1}/topologies/{mine['id']}", json={"name": "fixed"}, headers=cls.instructor)
    assert r.status_code == 200 and r.json()["owner"]["username"] == "alice"


def test_opening_a_published_topology_gives_one_personal_copy(setup):
    cls, alice, bob, draft, published, mine = setup
    c = cls.client
    r = c.post(f"{V1}/topologies/{published['id']}/copy", headers=alice)
    assert r.status_code == 201
    copy_ = r.json()
    assert copy_["owner"]["username"] == "alice"
    assert copy_["source_id"] == published["id"] and copy_["published"] is False
    assert copy_["data"]["tutorials"] == published["data"]["tutorials"]
    assert copy_["data"]["scenarios"] == published["data"]["scenarios"]
    again = c.post(f"{V1}/topologies/{published['id']}/copy", headers=alice)
    assert again.status_code == 200 and again.json()["id"] == copy_["id"]
    bobs = c.post(f"{V1}/topologies/{published['id']}/copy", headers=bob).json()
    assert bobs["id"] != copy_["id"]
    # Copying your own topology duplicates it.
    dup = c.post(f"{V1}/topologies/{mine['id']}/copy", headers=alice)
    assert dup.status_code == 201 and dup.json()["source_id"] is None
    assert dup.json()["name"] == "alice-lab (copy)"


def test_a_copy_tracks_its_source_and_resets_to_it(setup):
    cls, alice, bob, draft, published, mine = setup
    c = cls.client
    copy_ = c.post(f"{V1}/topologies/{published['id']}/copy", headers=alice).json()

    def listed():
        rows = c.get(f"{V1}/topologies", headers=alice).json()
        return next(r for r in rows if r["id"] == copy_["id"])

    assert listed()["update_available"] is False
    newer = copy.deepcopy(published["data"])
    newer["tutorials"][0]["title"] = "Intro v2"
    r = c.put(f"{V1}/topologies/{published['id']}", json={"data": newer}, headers=cls.instructor)
    assert r.status_code == 200
    assert listed()["update_available"] is True

    # The student's own edits are replaced by the reset.
    c.put(f"{V1}/topologies/{copy_['id']}", json={"name": "mine now"}, headers=alice)
    r = c.post(f"{V1}/topologies/{copy_['id']}/reset", headers=alice)
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "lesson"
    assert r.json()["data"]["tutorials"][0]["title"] == "Intro v2"
    assert r.json()["update_available"] is False

    # Not while the lab is up; not for a topology that is not a copy.
    assert c.post(f"{V1}/topologies/{copy_['id']}/deploy", headers=alice).status_code == 202
    cls.wait()
    r = c.post(f"{V1}/topologies/{copy_['id']}/reset", headers=alice)
    assert r.status_code == 409 and r.json()["code"] == "bad_state"
    r = c.post(f"{V1}/topologies/{mine['id']}/reset", headers=alice)
    assert r.json()["code"] == "no_source"


def test_unpublishing_and_deleting_the_source_keep_copies(setup):
    cls, alice, bob, draft, published, mine = setup
    c = cls.client
    copy_ = c.post(f"{V1}/topologies/{published['id']}/copy", headers=alice).json()
    c.put(
        f"{V1}/topologies/{published['id']}/published",
        json={"published": False},
        headers=cls.instructor,
    )
    assert _ids(c.get(f"{V1}/topologies", headers=bob).json()) == set()
    assert c.post(f"{V1}/topologies/{copy_['id']}/reset", headers=alice).json()["code"] == (
        "no_source"
    )
    assert c.delete(f"{V1}/topologies/{published['id']}", headers=cls.instructor).status_code == 204
    kept = c.get(f"{V1}/topologies/{copy_['id']}", headers=alice).json()
    assert kept["source_id"] is None


def test_only_the_instructor_publishes(setup):
    cls, alice, bob, draft, published, mine = setup
    c = cls.client
    r = c.put(f"{V1}/topologies/{mine['id']}/published", json={"published": True}, headers=alice)
    assert r.status_code == 403 and r.json()["code"] == "instructor_only"
    c.put(
        f"{V1}/topologies/{draft['id']}/published",
        json={"published": True},
        headers=cls.instructor,
    )
    assert draft["id"] in _ids(c.get(f"{V1}/topologies", headers=bob).json())


def test_a_student_runs_at_most_the_lab_cap(setup):
    cls, alice, bob, draft, published, mine = setup
    c = cls.client
    second = cls.create(alice, "second")
    assert c.post(f"{V1}/topologies/{mine['id']}/deploy", headers=alice).status_code == 202
    cls.wait()
    r = c.post(f"{V1}/topologies/{second['id']}/deploy", headers=alice)
    assert r.status_code == 409 and r.json()["code"] == "lab_limit"
    assert r.json()["labs"] == [{"id": mine["id"], "name": "alice-lab"}]
    # Others are not affected, the instructor has no cap.
    bobs = cls.create(bob, "bob-lab")
    assert c.post(f"{V1}/topologies/{bobs['id']}/deploy", headers=bob).status_code == 202
    assert c.post(f"{V1}/topologies/{draft['id']}/deploy", headers=cls.instructor).status_code == (
        202
    )
    cls.wait()
    assert c.post(f"{V1}/topologies/{mine['id']}/destroy", headers=alice).status_code == 202
    cls.wait()
    assert c.post(f"{V1}/topologies/{second['id']}/deploy", headers=alice).status_code == 202


def test_jobs_follow_their_topology(setup):
    cls, alice, bob, draft, published, mine = setup
    c = cls.client
    job = c.post(f"{V1}/topologies/{mine['id']}/deploy", headers=alice).json()
    cls.wait()
    for path in (f"/jobs/{job['id']}", f"/jobs/{job['id']}/log", f"/jobs/{job['id']}/artifacts"):
        assert c.get(V1 + path, headers=alice).status_code == 200
        assert c.get(V1 + path, headers=cls.instructor).status_code == 200
        assert c.get(V1 + path, headers=bob).status_code == 404
    assert c.post(f"{V1}/jobs/{job['id']}/cancel", headers=bob).status_code == 404


def test_host_administration_is_the_instructors(setup):
    cls, alice, *_ = setup
    c = cls.client
    for method, path, body in [
        ("post", "/images/builds", {"refs": ["x"]}),
        ("post", "/sources/x/sync", None),
        ("post", "/registries", {"url": "tollan"}),
        ("get", "/system/labs", None),
        ("post", "/system/reconcile", None),
        ("post", "/system/labs/abc/purge", None),
        ("get", "/benchmarks", None),
        ("post", "/topologies/generate", {}),
    ]:
        r = c.request(method, V1 + path, headers=alice, json=body)
        assert r.status_code == 403, (method, path, r.text)
    for path in ("/images", "/registries", "/catalog", "/presets", "/system/environment"):
        assert c.get(V1 + path, headers=alice).status_code == 200, path


def test_websockets_need_a_token_and_the_topology(setup):
    cls, alice, bob, draft, published, mine = setup
    c = cls.client
    exec_path = f"{V1}/topologies/ws/{mine['id']}/exec/hA"
    with pytest.raises(WebSocketDisconnect) as exc:
        with c.websocket_connect(exec_path) as ws:
            ws.receive_text()
    assert exc.value.code == 4003
    bob_token = bob["Authorization"].split()[1]
    with c.websocket_connect(f"{exec_path}?token={bob_token}") as ws:
        assert "topology not found" in ws.receive_text()
    alice_token = alice["Authorization"].split()[1]
    with c.websocket_connect(f"{exec_path}?token={alice_token}") as ws:
        assert "not deployed" in ws.receive_text()
    for kind in ("captures", "traffic", "monitors", "scenario"):
        path = f"{V1}/topologies/ws/{mine['id']}/{kind}/job?token={bob_token}"
        with pytest.raises(WebSocketDisconnect) as exc:
            with c.websocket_connect(path) as ws:
                ws.receive_text()
        assert exc.value.code == 4004, kind


def test_tokens_in_urls_only_read(setup):
    cls, alice, bob, draft, published, mine = setup
    c = cls.client
    token = alice["Authorization"].split()[1]
    assert c.get(f"{V1}/topologies/{mine['id']}?token={token}").status_code == 200
    r = c.put(f"{V1}/topologies/{mine['id']}?token={token}", json={"name": "x"})
    assert r.status_code == 401


def test_the_web_ui_cookie_only_opens_the_relay(setup):
    cls, alice, bob, draft, published, mine = setup
    c = cls.client
    r = c.post(f"{V1}/auth/webui-cookie", headers=alice)
    assert r.status_code == 204 and "ae3gis_webui" in r.cookies
    # The relay answers (the lab is not deployed) rather than asking to sign in.
    r = c.get(f"{V1}/topologies/{mine['id']}/webui/hA/")
    assert r.status_code != 401
    assert c.get(f"{V1}/topologies/{mine['id']}").status_code == 401
    c.cookies.clear()
    assert c.get(f"{V1}/topologies/{mine['id']}/webui/hA/").status_code == 401
