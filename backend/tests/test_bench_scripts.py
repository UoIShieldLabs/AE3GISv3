"""The headless benchmark scripts (stdlib only, run from the host) against the
app on the fake engine."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bench = _load("bench")


class ClientApi(bench.Api):
    """bench.Api over a TestClient instead of urllib."""

    def __init__(self, client) -> None:
        super().__init__("http://test", None)
        self.client = client

    def raw(self, method, path, body=None):
        r = self.client.request(method, "/api/v1" + path, json=body)
        if r.status_code >= 400:
            raise bench.ApiError(method, path, r.status_code, r.text)
        return r.content

    def ping(self):
        return self.client.get("/api/v1/system/health").json()


def test_follow_and_save(client, fake_engine, tmp_path):
    fake_engine.monitor_interval = 0.02
    api = ClientApi(client)
    spec = {"label": "t", "scale": [2], "cooldown_s": 0.1, "settle_s": 0.1, "hold_s": 0.1}
    b = api.call("POST", "/benchmarks", spec)
    lines: list[str] = []
    done = bench.follow(api, b["id"], 0.05, out=lines.append)
    assert done["status"] == "succeeded" and any("2 hosts" in line for line in lines)
    assert bench.describe(done) == "scale [2]"
    assert bench.outcome_line(done).startswith("succeeded: ceiling 2 hosts")
    md, z = bench.save(api, b["id"], tmp_path, "run")
    assert md.read_text().startswith("# Benchmark: t") and z.stat().st_size > 0
    try:
        api.call("POST", "/benchmarks", {**spec, "scale": [2, 1]})
    except bench.ApiError as exc:
        assert exc.status == 422
    else:
        raise AssertionError("expected a 422")


# ── the suite runner ──────────────────────────────────────────────────

import json  # noqa: E402

import pytest  # noqa: E402

suites = _load("bench_suite")

FAST = {"cooldown_s": 0.05, "settle_s": 0.1, "hold_s": 0.1, "monitor": {"interval_s": 1}}
POOLS = {
    "hosts": [
        {"type": "workstation", "images": ["kathara/base"]},
        {"type": "web-server", "images": ["httpd:alpine"]},
        {"type": "attacker", "images": ["ae3gis.local/malicious-client"]},
    ]
}


def _write(root, files):
    for name, data in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))


def _suite(tmp_path, items, **extra):
    _write(tmp_path / "suites", {"s.json": {"name": "s", "items": items, **extra}})
    return suites.load_suite(str(tmp_path / "suites" / "s.json"), specs_root=tmp_path / "specs")


def test_load_suite_checks_items(tmp_path):
    _write(
        tmp_path / "specs",
        {
            "census.json": {"census": {}},
            "climb.json": {"adaptive": {"start": 4}, "topology": {"generate": {"random": POOLS}}},
            "sweep.json": {"scale": [2]},
        },
    )
    ok = _suite(
        tmp_path,
        [
            {"id": "c", "spec": "census.json"},
            {
                "id": "r",
                "spec": "climb.json",
                "runs": 2,
                "pool_from": "c",
                "start_from_previous": 0.7,
            },
        ],
    )
    assert ok["restart_docker"] is True and len(ok["_sha"]) == 64
    elsewhere = _suite(tmp_path, [{"id": "a", "spec": str(tmp_path / "specs" / "sweep.json")}])
    assert elsewhere["items"][0]["_spec"] == {"scale": [2]}  # an absolute spec path
    bad = [
        [{"id": "a", "spec": "sweep.json"}, {"id": "a", "spec": "sweep.json"}],
        [{"id": "a", "spec": "nope.json"}],
        [{"id": "a", "spec": "sweep.json"}, {"id": "r", "spec": "climb.json", "pool_from": "a"}],
        [{"id": "r", "spec": "climb.json", "runs": 2, "seeds": [1]}],
        [{"id": "s", "spec": "sweep.json", "start_from_previous": 0.7}],
        [],
    ]
    for items in bad:
        with pytest.raises(suites.SuiteError):
            _suite(tmp_path, items)


def test_plans_and_specs():
    item = {
        "id": "r",
        "runs": 3,
        "seeds": [7, None, 9],
        "pool_from": "c",
        "start_from_previous": 0.7,
        "overrides": {"hold_s": 5, "adaptive": {"confirm": 1}},
        "_spec": {
            "adaptive": {"start": 100, "min_step": 10},
            "topology": {"generate": {"seed": 1, "random": copy_pools()}},
        },
    }
    suite = {"items": [{"id": "c", "_spec": {"census": {}}}, item]}
    runs = suites.plan_runs(suite)
    assert [(r["key"], r["dir"], r["seed"]) for r in runs] == [
        ("c", "01-c", None),
        ("r-run1", "02-r-run1", 7),
        ("r-run2", "03-r-run2", 2),
        ("r-run3", "04-r-run3", 9),
    ]
    assert [r["key"] for r in suites.plan_runs(suite, {"r"})][0] == "r-run1"
    census = [
        {"type": "workstation", "image": "kathara/base", "usable": True},
        {"type": "attacker", "image": "ae3gis.local/malicious-client", "usable": False},
    ]
    spec, notes = suites.build_spec(item, runs[2], "m4", previous_ceiling=375, census=census)
    assert spec["label"] == "m4 · r run 2" and spec["topology"]["generate"]["seed"] == 2
    assert spec["adaptive"] == {"start": 260, "min_step": 10, "confirm": 1} and spec["hold_s"] == 5
    kinds = {e["type"] for e in spec["topology"]["generate"]["random"]["hosts"]}
    assert kinds == {"workstation", "web-server"}  # attacker failed; httpd untested: kept
    assert notes["excluded"] == ["attacker · ae3gis.local/malicious-client"]
    with pytest.raises(suites.SuiteError, match="nothing usable"):
        suites.apply_pool(
            item["_spec"],
            [{**c, "usable": False} for c in census[:1]]
            + [
                {"type": "web-server", "image": "httpd:alpine", "usable": False},
                census[1],
            ],
        )
    assert suites.next_start(20, 0.7, 25) == 25 and suites.deep_merge({"a": [1]}, {"a": [2]}) == {
        "a": [2]
    }


def copy_pools():
    return json.loads(json.dumps(POOLS))


def test_restart_and_keep_awake_commands():
    assert suites.restart_plan("Darwin", None, True) == [["docker", "desktop", "restart"]]
    mac = suites.restart_plan("Darwin", None, False)
    assert (
        mac[0][0] == "osascript"
        and mac[1] == suites.WAIT_DOWN
        and mac[2] == ["open", "-a", "Docker"]
    )
    assert suites.restart_plan("Linux", None, True) is None  # needs root: give a command
    assert suites.restart_plan("Linux", "sudo -n systemctl restart docker", False) == [
        ["sudo", "-n", "systemctl", "restart", "docker"]
    ]
    assert suites.keep_awake_cmd("Darwin", 42) == ["caffeinate", "-dimsu", "-w", "42"]


def test_aggregate_random():
    def result(ceiling, nodes, comp, mem=10e6, deploy=20.0):
        rows = [
            {"scale": ceiling - 10, "outcome": "ok", "nodes": nodes - 10},
            {
                "scale": ceiling,
                "outcome": "ok",
                "nodes": nodes,
                "hold_mem_pct_max": 90.5,
                "marginal_mem_per_node": mem,
                "deploy_s": deploy,
                "composition": comp,
            },
        ]
        return {"ceiling": ceiling, "rows": rows}

    runs = [
        {
            "key": "r1",
            "seed": 1,
            "result": result(200, 220, {"siem · w": 20, "workstation · b": 180}),
        },
        {
            "key": "r2",
            "seed": 2,
            "result": result(300, 330, {"siem · w": 10, "workstation · b": 290}),
        },
        {"key": "r3", "seed": 3, "result": {"ceiling": None, "rows": []}},
    ]
    agg = suites.aggregate_random(runs)
    assert agg["without_ceiling"] == ["r3"] and len(agg["runs"]) == 2
    assert agg["across"]["ceiling"]["mean"] == 250 and agg["across"]["ceiling"][
        "std"
    ] == pytest.approx(70.71, 0.01)
    assert agg["runs"][0]["deploy_s_per_node"] == pytest.approx(20 / 220)
    assert agg["type_shares"]["siem"]["mean"] == pytest.approx((0.1 + 10 / 300) / 2)
    md = suites.summary_markdown(
        {"suite": "s", "host": "m4", "runs": [], "git": {"commit": "abc"}}, {"r": agg}
    )
    assert "## Random climbs: `r` (2 with a ceiling, 1 without: r3)" in md and "| siem |" in md


def test_a_suite_end_to_end_and_resume(client, fake_engine, tmp_path):
    fake_engine.monitor_interval = 0.02
    fake_engine.platform = "linux/arm64"  # malicious-client builds only for amd64
    fake_engine.fake_mem_per_node = 200_000_000  # the fake 8 GiB host fills at ~35 nodes
    cases = [{"type": t["type"], "image": t["images"][0]} for t in POOLS["hosts"][1:]]
    climb = {
        **FAST,
        "topology": {"generate": {"servers": 0, "hosts_per_subnet": 10, "random": POOLS}},
        "adaptive": {"start": 10, "min_step": 2, "confirm": 0, "max_steps": 6},
        "stop": {"max_mem_pct": 95, "project_memory": False},
    }
    _write(
        tmp_path / "specs",
        {"census.json": {**FAST, "census": {"per_image": 2, "cases": cases}}, "climb.json": climb},
    )
    suite = _suite(
        tmp_path,
        [
            {"id": "census", "spec": "census.json"},
            {
                "id": "random",
                "spec": "climb.json",
                "runs": 2,
                "pool_from": "census",
                "start_from_previous": 0.7,
            },
        ],
        rest_wait_s=0,
    )
    out = tmp_path / "results" / "m4" / "run"
    api = ClientApi(client)
    lines: list[str] = []

    class Lines(suites.Log):
        def __call__(self, text: str = "") -> None:
            lines.append(text)

    def make():
        return suites.Runner(
            suite,
            api,
            out,
            host="m4",
            log=Lines(None),
            poll=0.05,
            allow_dirty=True,
            sleep=lambda s: None,
        )

    runner = make()
    runner.preflight()
    assert runner.manifest["prebuild"]["unavailable"] == {
        "ae3gis.local/malicious-client": next(
            i["reason"]
            for i in api.call("GET", "/images")["images"]
            if i["ref"] == "ae3gis.local/malicious-client"
        )
    }
    assert runner.run() == 0, lines
    manifest = json.loads((out / "manifest.json").read_text())
    assert [r["status"] for r in manifest["runs"]] == ["done", "done", "done"]
    census = json.loads((out / "01-census" / "benchmark.json").read_text())["result"]["census"]
    assert {c["case"]: c["usable"] for c in census}[
        "attacker · ae3gis.local/malicious-client"
    ] is False
    run1 = json.loads((out / "02-random-run1" / "spec.json").read_text())
    assert {e["type"] for e in run1["topology"]["generate"]["random"]["hosts"]} == {
        "workstation",
        "web-server",
    }
    assert run1["label"] == "m4 · random run 1" and run1["topology"]["generate"]["seed"] == 1
    ceiling1 = manifest["runs"][1]["ceiling"]
    run2 = json.loads((out / "03-random-run2" / "spec.json").read_text())
    assert ceiling1 and run2["adaptive"]["start"] == suites.next_start(ceiling1, 0.7, 2)
    assert (out / "02-random-run1" / "report.md").is_file() and (
        out / "02-random-run1" / "export.zip"
    ).is_file()
    assert manifest["runs"][1]["rest"]["mem_total"] > 0
    summary = (out / "summary.md").read_text()
    assert "## Random climbs: `random` (2 with a ceiling" in summary
    assert (out / "random-random.json").is_file()
    # Resume: everything is done, nothing runs again.
    before = len(api.call("GET", "/benchmarks"))
    assert make().run() == 0 and len(api.call("GET", "/benchmarks")) == before


# ── traffic limit search ──────────────────────────────────────────────


def test_cell_ids_match_the_backends():
    from domain.benchmark import matrix_cells

    matrix = json.loads(
        (
            Path(__file__).resolve().parents[1] / "benchmarks/specs/traffic/burst-limits.json"
        ).read_text()
    )["matrix"]
    assert [c["id"] for c in suites.matrix_cell_ids(matrix)] == [
        c["id"] for c in matrix_cells(matrix)
    ]


def _search(limit: int | None, estimate: int, cfg: dict) -> tuple[dict, list[int]]:
    """Drive one cell whose traffic gets through up to ``limit`` hosts."""
    state = {"cell": {}, "estimate": estimate, "pass": {}, "fail": {}, "unrun": {}}
    sizes = []
    while (size := suites.next_probe(state, cfg)) is not None:
        sizes.append(size)
        assert len(sizes) < 30
        if limit is None or size <= limit:
            state["pass"][str(size)] = state["pass"].get(str(size), 0) + 1
        else:
            state["fail"][str(size)] = "traffic_short"
    return state, sizes


@pytest.mark.parametrize(
    ("limit", "estimate"),
    [(330, 400), (330, 100), (330, 2000), (75, 85), (20, 300), (None, 500), (970, 900)],
)
def test_the_search_brackets_each_limit_within_a_step(limit, estimate):
    cfg = {**suites.LIMIT_DEFAULTS, "max_hosts": 1000}
    state, sizes = _search(limit, estimate, cfg)
    r = suites.limit_result("c", state, cfg)
    assert r["done"]
    if limit is None or limit >= 1000:
        assert (r["comfortable"], r["fails_at"]) == (1000, None) and r["confirmed"]
    elif limit < 50:
        assert (r["comfortable"], r["fails_at"]) == (None, 50)
    else:
        assert r["comfortable"] == limit // 50 * 50 and r["fails_at"] == r["comfortable"] + 50
        assert r["confirmed"] and sizes.count(r["comfortable"]) == 2
    assert len(sizes) <= 12


def test_record_probe():
    def st():
        return {"cell": {}, "estimate": 100, "pass": {}, "fail": {}, "unrun": {}}

    states = {k: st() for k in ("a", "b", "c", "d")}
    rows = [
        {"case": None, "outcome": "ok"},
        {"case": "a", "cell": {"x": 1}, "outcome": "ok"},
        {"case": "b", "cell": {"x": 1}, "outcome": "degraded", "reason": "traffic_short"},
        {"case": "c", "cell": {"x": 1}, "outcome": "stopped", "reason": "memory"},
    ]
    suites.record_probe(states, 200, ["a", "b", "c", "d"], {"rows": rows})
    assert states["a"]["pass"] == {"200": 1} and states["b"]["fail"] == {"200": "traffic_short"}
    assert states["c"]["fail"] == {"200": "memory"} and states["d"]["unrun"] == {"200": 1}
    suites.record_probe(states, 200, ["d"], {"rows": rows[:1]})
    assert states["d"]["fail"] == {"200": "not_run"}  # asked twice, never reached
    deploy_failed = [{"case": None, "outcome": "stopped", "reason": "memory"}]
    suites.record_probe(states, 900, ["a"], {"rows": deploy_failed})
    assert states["a"]["fail"]["900"] == "memory"
    results = [suites.limit_result(k, s, suites.LIMIT_DEFAULTS) for k, s in states.items()]
    assert results[2]["bound"] == "host" and results[1]["bound"] == "traffic"


def test_a_limit_search_end_to_end(client, fake_engine, tmp_path):
    fake_engine.monitor_interval = 0.02
    fake_engine.traffic_capacity_bps = 25e6  # 1 Mb/s flows: 25 clients get through
    spec = {
        **FAST,
        "hold_s": 0.2,
        "quiet_timeout_s": 0.2,  # the fake host's CPU grows with nodes; don't wait for it
        "topology": {
            "generate": {
                "hosts_per_subnet": 50,
                "server_mix": [{"type": "workstation", "per_hosts": 10}],
            }
        },
        "scale": [10],
        "matrix": {
            "patterns": [
                {
                    "id": "cs",
                    "kind": "clients_to_servers",
                    "servers": {"subnets": ["sub-srv"], "roles": ["host"]},
                }
            ],
            "axes": {"protocol": ["udp"], "bitrate": ["1M", "100K"], "burst_interval_ms": [100]},
            "interval_s": 0.5,
            "ramp_s": 0,
            "gap_s": 0.05,
        },
        "stop": {"min_delivered_ratio": 0.95, "max_loss_pct": 1, "project_memory": False},
    }
    _write(tmp_path / "specs", {"limits.json": spec})
    limits = {
        "step": 10,
        "max_hosts": 60,
        "cost": {"cs": {"udp": [0.0, 25.0]}},  # makes the 1M estimate ~18 hosts
        "flows_per_host": {"cs": 1},
        "mem_per_host": {"cs": 16e6},
    }
    suite = _suite(
        tmp_path, [{"id": "lim", "spec": "limits.json", "limits": limits}], rest_wait_s=0
    )
    out = tmp_path / "results"

    class Lines(suites.Log):
        def __call__(self, text: str = "") -> None:
            pass

    runner = suites.Runner(
        suite,
        ClientApi(client),
        out,
        host="m4",
        log=Lines(None),
        poll=0.05,
        allow_dirty=True,
        sleep=lambda s: None,
        prebuild=False,
    )
    assert runner.run() == 0
    manifest = json.loads((out / "manifest.json").read_text())
    [run] = manifest["runs"]
    assert run["status"] == "done" and run["probes"]
    results = {r["id"]: r for r in json.loads((out / "limits-lim.json").read_text())}
    fast = results["cs·udp·1M·100ms"]
    assert (fast["comfortable"], fast["fails_at"], fast["bound"]) == (20, 30, "traffic")
    assert fast["confirmed"] and fast["reason"] == "traffic_short"
    slow = results["cs·udp·100K·100ms"]
    assert (slow["comfortable"], slow["fails_at"]) == (60, None) and slow["confirmed"]
    summary = (out / "summary.md").read_text()
    assert (
        "## Traffic limits: `lim`" in summary
        and "| 1M | 20 / 30 |" in summary
        and "≥ 60" in summary
    )
    # Each probe ran only the cells that wanted its size.
    first = run["probes"][0]
    b = json.loads((out / first["dir"] / "benchmark.json").read_text())
    assert {r["case"] for r in b["result"]["rows"] if r.get("cell")} == set(first["cells"])
    # Resumed: nothing left to probe.
    again = suites.Runner(
        suite,
        ClientApi(client),
        out,
        host="m4",
        log=Lines(None),
        poll=0.05,
        allow_dirty=True,
        sleep=lambda s: None,
        prebuild=False,
    )
    before = len(run["probes"])
    assert again.run() == 0
    assert len(json.loads((out / "manifest.json").read_text())["runs"][0]["probes"]) == before


def test_sysctl_command_and_parse():
    argv = suites.sysctl_argv({"net.ipv4.neigh.default.gc_thresh3": 16384})
    assert argv[:6] == ["docker", "run", "--rm", "--privileged", "--net=host", suites.SYSCTL_IMAGE]
    assert "sysctl -q -w net.ipv4.neigh.default.gc_thresh3=16384" in argv[-1]
    out = "net.ipv4.neigh.default.gc_thresh3 = 16384\nnoise\n"
    assert suites.parse_sysctls(out) == {"net.ipv4.neigh.default.gc_thresh3": "16384"}


def test_suite_sysctls_are_set_after_every_restart(client, fake_engine, tmp_path):
    fake_engine.monitor_interval = 0.02
    _write(tmp_path / "specs", {"sweep.json": {**FAST, "scale": [2]}})
    suite = _suite(
        tmp_path,
        [{"id": "a", "spec": "sweep.json"}, {"id": "b", "spec": "sweep.json"}],
        rest_wait_s=0,
        sysctls={"net.ipv4.neigh.default.gc_thresh3": 16384},
    )
    calls = []

    def tune(wanted):
        calls.append(dict(wanted))
        return {k: str(v) for k, v in wanted.items()}

    class Lines(suites.Log):
        def __call__(self, text: str = "") -> None:
            pass

    runner = suites.Runner(
        suite,
        ClientApi(client),
        tmp_path / "out",
        host="m4",
        log=Lines(None),
        poll=0.05,
        allow_dirty=True,
        sleep=lambda s: None,
        prebuild=False,
        restart=lambda: None,
        tune=tune,
        kernel_log=lambda: 0,
    )
    runner.preflight()
    assert runner.run() == 0
    assert len(calls) == 3  # preflight, then after each of the 2 restarts
    manifest = json.loads((tmp_path / "out" / "manifest.json").read_text())
    assert manifest["sysctls"] == {"net.ipv4.neigh.default.gc_thresh3": "16384"}
    assert "gc_thresh3=16384" in (tmp_path / "out" / "summary.md").read_text()


def test_a_cancelled_probe_is_asked_again_on_resume(tmp_path):
    class StubApi:
        base = "http://stub/api/v1"

        def call(self, method, path, body=None):
            assert (method, path) == ("GET", "/benchmarks/b1")
            return {"id": "b1", "live": False, "status": "cancelled", "result": None}

    _write(tmp_path / "specs", {"m.json": {"matrix": {"patterns": [{"id": "p", "kind": "mesh"}]}}})
    suite = _suite(tmp_path, [{"id": "lim", "spec": "m.json", "limits": {}}])

    class Lines(suites.Log):
        def __call__(self, text: str = "") -> None:
            pass

    runner = suites.Runner(suite, StubApi(), tmp_path / "out", host="m4", log=Lines(None))
    state = {"cell": {}, "estimate": 900, "pass": {"700": 1}, "fail": {}, "unrun": {}}
    probe = {
        "key": "k",
        "round": 3,
        "size": 900,
        "cells": ["c"],
        "dir": "d",
        "status": "running",
        "benchmark_id": "b1",
    }
    runner.run_probe(
        {"item": "lim", "key": "lim", "dir": "01"}, probe, {}, {"c": state}, resume=True
    )
    assert probe["status"] == "cancelled" and probe["recorded"]
    assert state == {"cell": {}, "estimate": 900, "pass": {"700": 1}, "fail": {}, "unrun": {}}
    assert suites.next_probe(state, suites.LIMIT_DEFAULTS) == 900  # the size is asked again
