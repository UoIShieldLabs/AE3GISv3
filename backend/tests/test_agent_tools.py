"""The agent's tools: they call the same services as the API, as the caller."""

from __future__ import annotations

from services.accounts import Identity
from services.agent.tools import load_all, tools_for
from tests.agent_helpers import call_tool, identity_of


def test_get_topology_outlines_ids_and_links(client, app, topology):
    r = call_tool(client, app, "get_topology", topology_id=topology["id"])
    assert not r.is_error
    assert "Subnet A [subA] 10.0.1.0/24" in r.text
    assert "Host A [hA] workstation 10.0.1.5" in r.text
    assert "subnet link A — B [c5]" in r.text


def test_edit_topology_saves_a_new_version_and_tells_the_editor(client, app, topology):
    r = call_tool(
        client,
        app,
        "edit_topology",
        topology_id=topology["id"],
        ops=[{"op": "add_device", "subnet": "subA", "type": "attacker", "name": "kali"}],
    )
    assert not r.is_error, r.text
    assert "as v2" in r.text and "10.0.1.3" in r.text
    assert r.ui == [{"type": "topology_changed", "topology_id": topology["id"], "version": 2}]
    stored = client.get(f"/api/v1/topologies/{topology['id']}").json()
    assert stored["version"] == 2
    names = [c["name"] for c in stored["data"]["sites"][0]["subnets"][0]["containers"]]
    assert "kali" in names


def test_a_rejected_edit_changes_nothing(client, app, topology):
    r = call_tool(
        client,
        app,
        "edit_topology",
        topology_id=topology["id"],
        ops=[{"op": "connect", "a": "hA", "b": "hB"}],
    )
    assert r.is_error and "nothing was changed" in r.text
    assert client.get(f"/api/v1/topologies/{topology['id']}").json()["version"] == 1


def test_invalid_input_is_an_error_the_model_can_read(client, app, topology):
    r = call_tool(client, app, "edit_topology", topology_id=topology["id"], ops=[{"op": "nope"}])
    assert r.is_error and r.text.startswith("Invalid input for edit_topology")


def test_deploy_run_a_command_and_destroy(client, app, topology, fake_engine):
    tid = topology["id"]
    fake_engine.exec_results["ip -br addr"] = (0, "eth0 UP 10.0.1.5/24\n")
    r = call_tool(client, app, "deploy", topology_id=tid)
    assert not r.is_error, r.text
    assert "status=succeeded" in r.text
    assert client.get(f"/api/v1/topologies/{tid}/runtime").json()["status"] == "deployed"

    r = call_tool(client, app, "run_in_node", topology_id=tid, node="hA", command="ip -br addr")
    assert not r.is_error and "[exit 0" in r.text and "10.0.1.5/24" in r.text

    r = call_tool(client, app, "run_in_node", topology_id=tid, node="ghost", command="true")
    assert r.is_error and "unknown_node" in r.text

    r = call_tool(client, app, "destroy", topology_id=tid)
    assert not r.is_error and "status=succeeded" in r.text
    assert client.get(f"/api/v1/topologies/{tid}/runtime").json()["status"] == "idle"


def test_a_command_before_deploy_says_so(client, app, topology):
    r = call_tool(client, app, "run_in_node", topology_id=topology["id"], node="hA", command="true")
    assert r.is_error and "bad_state" in r.text


def test_create_from_a_preset(client, app):
    r = call_tool(client, app, "create_topology", name="Demo", preset="two-subnet-demo")
    assert not r.is_error, r.text
    tid = r.data["topology_id"]
    data = client.get(f"/api/v1/topologies/{tid}").json()["data"]
    assert data["name"] == "Demo" and len(data["sites"][0]["subnets"]) == 2


def test_read_docs_lists_and_reads_topics(client, app):
    r = call_tool(client, app, "read_docs")
    assert "topology-model" in r.text and "presets" in r.text
    assert "## Subnets" in call_tool(client, app, "read_docs", topic="topology-model").text
    assert "two-subnet-demo" in call_tool(client, app, "read_docs", topic="presets").text
    assert call_tool(client, app, "read_docs", topic="../../config").is_error


def test_tool_sets_by_role_and_mode():
    load_all()
    student = Identity(user_id="s", username="s", role="student", instructor_id="t")
    teacher = Identity(user_id="t", username="t", role="instructor")
    admin = Identity(user_id="a", username="a", role="admin")
    tutor = {t.name for t in tools_for(student, "tutor")}
    assert "get_topology" in tutor and "open_in_editor" in tutor
    assert not tutor & {"edit_topology", "deploy", "run_in_node", "arrange", "destroy"}
    assert all(t.risk == "read" for t in tools_for(student, "tutor"))
    # A student is never given the full set, even if asked.
    assert {t.name for t in tools_for(student, "full")} <= tutor
    full = {t.name for t in tools_for(teacher, "full")}
    assert {"edit_topology", "deploy", "run_in_node"} <= full and "purge_lab" not in full
    assert "purge_lab" in {t.name for t in tools_for(admin, "full")}
    mcp = {t.name for t in tools_for(teacher, "full", surface="mcp")}
    assert "open_in_editor" not in mcp and "arrange" not in mcp
    names = [t.name for t in tools_for(admin, "full")]
    assert names == sorted(names)


def test_tools_respect_topology_access(classroom):
    app, client = classroom.app, classroom.client
    teacher_h = classroom.teacher("tess")
    classroom.student("alice", teacher="tess")
    private = classroom.create(teacher_h, "private")
    student_lab = classroom.create(classroom.student("alice", teacher="tess"), "alice lab")
    alice = identity_of(app, classroom.ids["alice"])
    tess = identity_of(app, classroom.ids["tess"])

    r = call_tool(client, app, "get_topology", alice, topology_id=private["id"])
    assert r.is_error and "not_found" in r.text
    listed = call_tool(client, app, "list_topologies", alice).text
    assert "private" not in listed and "alice lab" in listed

    # The instructor may work on their student's topology (as through the API).
    r = call_tool(
        client,
        app,
        "edit_topology",
        tess,
        topology_id=student_lab["id"],
        ops=[{"op": "update", "id": "hA", "set": {"name": "fixed"}}],
    )
    assert not r.is_error, r.text
