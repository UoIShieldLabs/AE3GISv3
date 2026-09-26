"""Environment snapshots and their fingerprint."""

import copy

from domain.environment import build_environment, fingerprint, plan_sha256


def _env(**over):
    base = dict(
        engine={
            "docker": {"server_version": "28", "kernel": "6.10", "ncpu": 8, "arch": "aarch64"},
            "kathara": {"version": "3.8.3", "network_plugin": {"name": "vde", "id": "p1"}},
        },
        ae3gis={"git_commit": "abc", "mode": "dev"},
        host={"label": "mac", "loadavg": [1.0, 1.0, 1.0]},
        topology={"plan_sha256": plan_sha256([{"collision_domain": "cd0"}], {"a": "img"})},
        nodes=[{"node_id": "b", "image_id": "i2"}, {"node_id": "a", "image_id": "i1"}],
        tool={"image_id": "t1"},
    )
    base.update(over)
    return build_environment(**base)


def test_fingerprint_ignores_load_and_labels_but_not_the_stack():
    a, b = _env(), _env(host={"label": "other", "loadavg": [9, 9, 9]})
    assert a["fingerprint"] == b["fingerprint"]
    assert [n["node_id"] for n in a["nodes"]] == ["a", "b"]
    changed = copy.deepcopy(a)
    changed["nodes"][0]["image_id"] = "i9"
    assert fingerprint(changed) != a["fingerprint"]
    plugin = _env(
        engine={
            **a["engine"],
            "kathara": {"version": "3.8.3", "network_plugin": {"name": "bridge"}},
        }
    )
    assert plugin["fingerprint"] != a["fingerprint"]
    assert _env(ae3gis={"git_commit": "def"})["fingerprint"] != a["fingerprint"]


def test_system_environment_endpoint(client):
    env = client.get("/api/v1/system/environment").json()
    assert env["schema"] == 1 and env["engine"]["engine"] == "fake"
    assert env["ae3gis"]["api_version"] and env["fingerprint"]
