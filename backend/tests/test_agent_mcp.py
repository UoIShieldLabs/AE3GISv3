"""/api/v1/mcp: the agent's tools over MCP, as the caller behind the bearer token."""

from __future__ import annotations

from db.models import Class
from services.agent import mcp as agent_mcp

HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
    "MCP-Protocol-Version": "2025-06-18",
}


def rpc(client, method: str, params: dict | None = None, headers: dict | None = None):
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    return client.post(agent_mcp.PATH, json=body, headers={**HEADERS, **(headers or {})})


def tool_names(client, headers: dict | None = None) -> set[str]:
    r = rpc(client, "tools/list", headers=headers)
    assert r.status_code == 200, r.text
    return {t["name"] for t in r.json()["result"]["tools"]}


def test_initialize_and_call_a_tool_with_accounts_off(client, topology):
    r = rpc(
        client,
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "t", "version": "1"},
        },
    )
    assert r.status_code == 200, r.text
    assert "tools" in r.json()["result"]["capabilities"]
    names = tool_names(client)
    assert {"get_topology", "edit_topology", "deploy", "purge_lab"} <= names
    assert "open_in_editor" not in names  # browser tools stay in the app
    r = rpc(
        client, "tools/call", {"name": "get_topology", "arguments": {"topology_id": topology["id"]}}
    )
    result = r.json()["result"]
    assert result["isError"] is False
    assert "Host A [hA]" in result["content"][0]["text"]


def test_a_tool_marks_read_only_and_destructive(client):
    r = rpc(client, "tools/list")
    tools = {t["name"]: t for t in r.json()["result"]["tools"]}
    assert tools["get_topology"]["annotations"]["readOnlyHint"] is True
    assert tools["destroy"]["annotations"]["destructiveHint"] is True
    assert "$defs" not in str(tools["edit_topology"]["inputSchema"])


def test_accounts_on_needs_a_token(classroom):
    r = rpc(classroom.client, "tools/list")
    assert r.status_code == 401
    assert r.headers.get("www-authenticate") == "Bearer"
    r = rpc(classroom.client, "tools/list", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


def test_tools_follow_the_callers_role(classroom):
    client = classroom.client
    tess = classroom.teacher("tess")
    alice = classroom.student("alice", teacher="tess")
    assert "purge_lab" in tool_names(client, classroom.admin)
    staff = tool_names(client, tess)
    assert "edit_topology" in staff and "purge_lab" not in staff
    # A student gets nothing until their instructor turns the tutor on…
    assert tool_names(client, alice) == set()
    with classroom.app.state.session_factory() as db:
        cls = db.query(Class).filter(Class.instructor_id == classroom.ids["tess"]).one()
        cls.tutor_enabled = True
        db.commit()
    tutor = tool_names(client, alice)
    assert "get_topology" in tutor and "edit_topology" not in tutor
    # …and cannot call what it doesn't list.
    r = rpc(
        client,
        "tools/call",
        {"name": "deploy", "arguments": {"topology_id": "x"}},
        headers=alice,
    )
    assert r.json()["result"]["isError"] is True
