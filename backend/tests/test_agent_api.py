"""The agent sidebar API and its runs, on the scripted provider."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from db.models import Class
from engine.fake import FakeEngine
from main import create_app
from services.agent.llm.fake import FakeProvider, call, reply
from tests.conftest import ADMIN_PASSWORD, TWO_SUBNETS, Classroom, make_settings

V1 = "/api/v1/agent"


@pytest.fixture(autouse=True)
def _fresh_script():
    FakeProvider.reset()
    yield
    FakeProvider.reset()


@pytest.fixture
def agent_client(tmp_path: Path, fake_engine: FakeEngine):
    app = create_app(make_settings(tmp_path, agent_provider="fake"), fake_engine)
    with TestClient(app) as c:
        c.app_ref = app  # type: ignore[attr-defined]
        yield c


@pytest.fixture
def agent_classroom(tmp_path: Path, fake_engine: FakeEngine):
    app = create_app(
        make_settings(tmp_path, admin_password=ADMIN_PASSWORD, agent_provider="fake"), fake_engine
    )
    with TestClient(app) as c:
        yield Classroom(c, app)


def wait_idle(client) -> None:
    client.portal.call(client.app_ref.state.runner.wait_idle)


def new_chat(client, headers=None, **body) -> dict:
    r = client.post(f"{V1}/chats", json=body, headers=headers or {})
    assert r.status_code == 201, r.text
    return r.json()


def send(client, chat_id: str, text: str, headers=None, **extra) -> dict:
    r = client.post(
        f"{V1}/chats/{chat_id}/messages", json={"text": text, **extra}, headers=headers or {}
    )
    assert r.status_code == 202, r.text
    return r.json()


def messages(client, chat_id: str, headers=None) -> list[dict]:
    r = client.get(f"{V1}/chats/{chat_id}", headers=headers or {})
    assert r.status_code == 200, r.text
    return r.json()["messages"]


def wait_for(predicate, timeout: float = 5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = predicate()
        if value:
            return value
        time.sleep(0.02)
    raise AssertionError("timed out")


def test_status_says_off_until_configured(client):
    r = client.get(f"{V1}/status")
    assert r.json()["enabled"] is False and r.json()["reason"] == "agent_off"
    assert client.post(f"{V1}/chats", json={}).status_code == 409


def test_a_reply_without_tools(agent_client):
    c = agent_client
    assert c.get(f"{V1}/status").json()["mode"] == "full"
    FakeProvider.script.append(reply("Hello there."))
    chat = new_chat(c)
    out = send(c, chat["id"], "Hi, what can you do?")
    assert out["queued"] is False
    wait_idle(c)
    rows = messages(c, chat["id"])
    assert [m["role"] for m in rows] == ["user", "assistant"]
    assert rows[1]["content"]["text"] == "Hello there."
    detail = c.get(f"{V1}/chats/{chat['id']}").json()
    assert detail["title"] == "Hi, what can you do?" and detail["active_job_id"] is None
    # The model saw the user's context line, not the system prompt's.
    seen = FakeProvider.calls[0]["history"][0].content["text"]
    assert seen.startswith("<context>") and seen.endswith("Hi, what can you do?")


def test_tools_run_and_their_results_go_back_to_the_model(agent_client):
    c = agent_client
    topo = c.post("/api/v1/topologies", json={"name": "demo", "data": TWO_SUBNETS}).json()
    FakeProvider.script += [
        reply("Looking.", call("get_topology", topology_id=topo["id"])),
        reply("It has two subnets."),
    ]
    chat = new_chat(c, topology_id=topo["id"])
    send(c, chat["id"], "Describe it", context={"topology_id": topo["id"]})
    wait_idle(c)
    rows = messages(c, chat["id"])
    assert [m["role"] for m in rows] == ["user", "assistant", "tool", "assistant"]
    result = rows[2]["content"]["results"][0]
    assert result["name"] == "get_topology" and "Subnet A [subA]" in result["text"]
    second = FakeProvider.calls[1]["history"]
    assert second[-1].role == "tool"
    assert "edit_topology" in FakeProvider.calls[0]["tools"]
    assert c.get(f"{V1}/chats", params={"topology_id": topo["id"]}).json()[0]["id"] == chat["id"]


def test_an_edit_reaches_the_editor_as_a_ui_action(agent_client):
    c = agent_client
    topo = c.post("/api/v1/topologies", json={"name": "demo", "data": TWO_SUBNETS}).json()
    FakeProvider.script += [
        reply(
            "",
            call(
                "edit_topology",
                topology_id=topo["id"],
                ops=[{"op": "add_device", "subnet": "subA", "type": "workstation"}],
            ),
        ),
        reply("Added."),
    ]
    chat = new_chat(c)
    job = send(c, chat["id"], "Add a workstation")["job_id"]
    wait_idle(c)
    with c.websocket_connect(f"{V1}/ws/{chat['id']}/{job}") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello" and hello["job"]["status"] == "succeeded"
        kinds = []
        while True:
            msg = ws.receive_json()
            kinds.append(msg["type"])
            if msg["type"] == "end":
                break
    assert {"run", "message", "tool_start", "tool_end", "end"} <= set(kinds)
    assert c.get(f"/api/v1/topologies/{topo['id']}").json()["version"] == 2


def _pending(c, chat_id: str):
    return c.get(f"{V1}/chats/{chat_id}").json()["pending_approvals"]


@pytest.mark.parametrize("approve", [False, True])
def test_a_risky_call_waits_for_the_owner(agent_client, approve):
    c = agent_client
    topo = c.post("/api/v1/topologies", json={"name": "doomed", "data": TWO_SUBNETS}).json()
    FakeProvider.script += [
        reply("", call("delete_topology", topology_id=topo["id"])),
        reply("Done."),
    ]
    chat = new_chat(c)
    send(c, chat["id"], "Delete it")
    pending = wait_for(lambda: _pending(c, chat["id"]))
    assert pending[0]["name"] == "delete_topology"
    r = c.post(
        f"{V1}/chats/{chat['id']}/approvals/{pending[0]['call_id']}", json={"approve": approve}
    )
    assert r.status_code == 204, r.text
    wait_idle(c)
    result = messages(c, chat["id"])[2]["content"]["results"][0]
    exists = c.get(f"/api/v1/topologies/{topo['id']}").status_code == 200
    if approve:
        assert not result["is_error"] and not exists
    else:
        assert result["is_error"] and "declined" in result["text"] and exists


def test_auto_approve_skips_the_question_but_not_for_deletes(agent_client, fake_engine):
    c = agent_client
    topo = c.post("/api/v1/topologies", json={"name": "lab", "data": TWO_SUBNETS}).json()
    c.post(f"/api/v1/topologies/{topo['id']}/deploy")
    c.portal.call(c.app_ref.state.runner.wait_idle)
    chat = new_chat(c)
    assert c.patch(f"{V1}/chats/{chat['id']}", json={"auto_approve": True}).json()["auto_approve"]
    FakeProvider.script += [reply("", call("destroy", topology_id=topo["id"])), reply("Gone.")]
    send(c, chat["id"], "Tear it down")
    wait_idle(c)
    assert c.get(f"/api/v1/topologies/{topo['id']}/runtime").json()["status"] == "idle"
    FakeProvider.script += [reply("", call("delete_topology", topology_id=topo["id"])), reply("x")]
    send(c, chat["id"], "And delete it")
    assert wait_for(lambda: _pending(c, chat["id"]))[0]["name"] == "delete_topology"


def test_stop_ends_the_run_and_keeps_the_chat_usable(agent_client):
    c = agent_client
    FakeProvider.delay = 2.0
    FakeProvider.script.append(reply("too late"))
    chat = new_chat(c)
    job = send(c, chat["id"], "Think hard")["job_id"]
    time.sleep(0.2)
    assert c.post(f"/api/v1/jobs/{job}/stop").status_code in (200, 202), "stop refused"
    wait_idle(c)
    rows = messages(c, chat["id"])
    assert rows[-1]["role"] == "note" and rows[-1]["content"]["kind"] == "stopped"
    assert c.get(f"/api/v1/jobs/{job}").json()["status"] == "succeeded"
    # The stopped call never got to its reply: it is still queued.
    assert FakeProvider.script.pop(0).text == "too late"
    FakeProvider.delay = 0
    FakeProvider.script.append(reply("Back."))
    send(c, chat["id"], "Continue")
    wait_idle(c)
    assert messages(c, chat["id"])[-1]["content"]["text"] == "Back."


def test_the_step_limit_answers_every_call(tmp_path, fake_engine):
    app = create_app(make_settings(tmp_path, agent_provider="fake", agent_max_steps=2), fake_engine)
    with TestClient(app) as c:
        FakeProvider.script.append(
            reply("", call("read_docs"), call("read_docs"), call("read_docs"))
        )
        chat = c.post(f"{V1}/chats", json={}).json()
        c.post(f"{V1}/chats/{chat['id']}/messages", json={"text": "go"})
        c.portal.call(app.state.runner.wait_idle)
        rows = c.get(f"{V1}/chats/{chat['id']}").json()["messages"]
        results = rows[2]["content"]["results"]
        assert len(results) == 3 and "limit" in results[2]["text"]
        assert rows[-1]["role"] == "note" and rows[-1]["content"]["kind"] == "limit"


def test_a_message_during_a_run_steers_it(agent_client):
    c = agent_client
    FakeProvider.delay = 0.5
    FakeProvider.script += [reply("", call("read_docs")), reply("Noted the change.")]
    chat = new_chat(c)
    first = send(c, chat["id"], "Build a lab")
    second = send(c, chat["id"], "Actually, use three subnets")
    assert second["queued"] is True and second["job_id"] == first["job_id"]
    wait_idle(c)
    texts = [
        m.content.get("text", "") for m in FakeProvider.calls[1]["history"] if m.role == "user"
    ]
    assert any("three subnets" in t for t in texts)


def test_a_refusal_ends_the_turn(agent_client):
    c = agent_client
    from services.agent.llm.base import Turn

    FakeProvider.script.append(Turn(text="", tool_calls=[], stop_reason="refusal", refusal="No."))
    chat = new_chat(c)
    send(c, chat["id"], "something")
    wait_idle(c)
    rows = messages(c, chat["id"])
    assert rows[-1]["content"] == {"kind": "refusal", "text": "No."}


def _tutor_on(classroom: Classroom, teacher: str) -> None:
    r = classroom.client.put(
        "/api/v1/class", json={"tutor_enabled": True}, headers=classroom.teacher(teacher)
    )
    assert r.status_code == 200 and r.json()["tutor_enabled"] is True


def test_students_get_the_tutor_only_once_it_is_on(agent_classroom):
    cr = agent_classroom
    c = cr.client
    alice = cr.student("alice", teacher="tess")
    assert c.get(f"{V1}/status", headers=alice).json() == {
        "enabled": True,
        "provider": "fake",
        "model": None,
        "mode": None,
        "reason": "tutor_off",
        "mcp_path": "/api/v1/mcp",
    }
    assert c.post(f"{V1}/chats", json={}, headers=alice).status_code == 403
    _tutor_on(cr, "tess")
    chat = new_chat(c, alice)
    assert chat["mode"] == "tutor"
    FakeProvider.script += [
        reply("", call("edit_topology", topology_id="x", ops=[{"op": "set_meta", "name": "y"}])),
        reply("I can only explain."),
    ]
    send(c, chat["id"], "Fix my lab for me", alice)
    cr.wait()
    tools = set(FakeProvider.calls[0]["tools"])
    assert "get_topology" in tools and "edit_topology" not in tools
    assert "hints first" in FakeProvider.calls[0]["system"].lower()
    result = messages(c, chat["id"], alice)[2]["content"]["results"][0]
    assert result["is_error"] and "no tool named edit_topology" in result["text"]


def test_staff_read_their_students_chats_but_cannot_drive_them(agent_classroom):
    cr = agent_classroom
    c = cr.client
    alice = cr.student("alice", teacher="tess")
    _tutor_on(cr, "tess")
    FakeProvider.script.append(reply("Hint: check the gateway."))
    chat = new_chat(c, alice)
    send(c, chat["id"], "Why can't I ping?", alice)
    cr.wait()
    tess = cr.teacher("tess")
    listed = c.get(f"{V1}/chats", params={"owner": cr.ids["alice"]}, headers=tess).json()
    assert [x["id"] for x in listed] == [chat["id"]]
    detail = c.get(f"{V1}/chats/{chat['id']}", headers=tess).json()
    assert detail["can_send"] is False and detail["owner"]["username"] == "alice"
    r = c.post(f"{V1}/chats/{chat['id']}/messages", json={"text": "hi"}, headers=tess)
    assert r.status_code == 403
    # Another instructor and another student see nothing.
    sam = cr.teacher("sam")
    assert c.get(f"{V1}/chats/{chat['id']}", headers=sam).status_code == 404
    assert c.get(f"{V1}/chats", params={"owner": cr.ids["alice"]}, headers=sam).status_code == 404
    bob = cr.student("bob", teacher="tess")
    assert c.get(f"{V1}/chats/{chat['id']}", headers=bob).status_code == 404
    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect(f"{V1}/ws/{chat['id']}/x?token={bob['Authorization'][7:]}") as ws:
            ws.receive_json()


def test_a_student_losing_the_tutor_loses_the_run(agent_classroom):
    cr = agent_classroom
    c = cr.client
    alice = cr.student("alice", teacher="tess")
    _tutor_on(cr, "tess")
    chat = new_chat(c, alice)
    with cr.app.state.session_factory() as db:
        db.query(Class).update({"tutor_enabled": False})
        db.commit()
    r = c.post(f"{V1}/chats/{chat['id']}/messages", json={"text": "hi"}, headers=alice)
    assert r.status_code == 403 and r.json()["code"] == "tutor_off"


def test_api_tokens_act_as_their_owner(agent_classroom):
    cr = agent_classroom
    c = cr.client
    tess = cr.teacher("tess")
    r = c.post("/api/v1/auth/tokens", json={"label": "claude code"}, headers=tess)
    assert r.status_code == 201, r.text
    token, info = r.json()["token"], r.json()["info"]
    auth = {"Authorization": f"Bearer {token}"}
    assert c.get("/api/v1/auth/me", headers=auth).json()["user"]["username"] == "tess"
    assert [t["label"] for t in c.get("/api/v1/auth/tokens", headers=tess).json()] == [
        "claude code"
    ]
    assert c.delete(f"/api/v1/auth/tokens/{info['id']}", headers=tess).status_code == 204
    assert c.get("/api/v1/auth/me", headers=auth).status_code == 401
    alice = cr.student("alice", teacher="tess")
    assert c.post("/api/v1/auth/tokens", json={}, headers=alice).status_code == 403
