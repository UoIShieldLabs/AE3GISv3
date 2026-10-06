"""Benchmarks end to end on the fake engine: sweeps, criteria, busy hosts, results."""

import io
import time
import zipfile

import pytest

from domain.generator import GeneratorParams, counts

FAST = {"cooldown_s": 0.15, "settle_s": 0.15, "hold_s": 0.2, "monitor": {"interval_s": 1}}


@pytest.fixture
def fast(fake_engine):
    fake_engine.monitor_interval = 0.02
    fake_engine.traffic_interval = 0.02
    return fake_engine


def _start(client, **spec):
    body = {"label": "t", "scale": [2, 4], **FAST, **spec}
    return client.post("/api/v1/benchmarks", json=body)


def _done(client, bid):
    return client.get(f"/api/v1/benchmarks/{bid}").json()


def test_idle_sweep(client, wait_jobs, fast):
    r = _start(client, topology={"generate": {"servers": 1, "hosts_per_subnet": 3}})
    assert r.status_code == 202, r.text
    bench = r.json()
    assert bench["job"]["subject"] == "benchmark" and bench["topology_id"]
    assert bench["kind"] == "sweep" and bench["spec"]["kind"] == "sweep"
    wait_jobs()
    done = _done(client, bench["id"])
    assert done["status"] == "succeeded", done["job"]["error"]
    names = [s["name"] for s in done["job"]["steps"]]
    assert names == ["preflight", "images", "baseline", "2 hosts", "4 hosts"]
    result = done["result"]
    assert result["stopped_by"] == "completed" and result["ceiling"] == 4
    first, second = result["rows"]
    size = {n: counts(GeneratorParams(hosts=n, servers=1, hosts_per_subnet=3)) for n in (2, 4)}
    assert (first["scale"], first["outcome"], first["nodes"]) == (2, "ok", size[2]["nodes"])
    assert second["nodes"] == size[4]["nodes"] and second["links"] == size[4]["links"]
    # The fake engine charges 10 MB per node: what marginal memory must find (a
    # sweep at a window's edge may catch a short-lived 5 MB helper).
    for row in (first, second):
        assert row["marginal_mem_per_node"] == pytest.approx(10_000_000, rel=0.03)
    assert first["deploy_s"] is not None and first["destroy_s"] is not None
    assert first["quiet_wait_s"] is not None and first["quiet_wait_s"] < 5  # the fake host is quiet
    assert first["ready_s"] is not None and first["probes"] > 0 and first["probes_failed"] == 0
    assert set(first["deploy_phases"]) == {"validate", "images", "plan", "deploy", "verify"}
    assert first["node_mem_mean"] > 0 and first["hold_cpu_mean"] is not None
    assert [s["scale"] for s in result["by_scale"]] == [2, 4]

    # Nothing is left running; the topology row stays (its step jobs hang off it).
    assert fast.labs == {} and fast.helpers == {}
    topo = client.get(f"/api/v1/topologies/{bench['topology_id']}").json()
    assert topo["status"] == "idle" and topo["name"] == "bench: t"
    assert len(topo["data"]["sites"][0]["subnets"]) == 3  # the last step: 4 hosts, 3 per subnet

    names = {a["name"] for a in client.get(f"/api/v1/jobs/{bench['id']}/artifacts").json()}
    assert {"benchmark.json", "results.csv", "report.md", "host.csv.gz", "markers.csv.gz"} <= names
    z = zipfile.ZipFile(io.BytesIO(client.get(f"/api/v1/benchmarks/{bench['id']}/export").content))
    assert {"topologies/2-1.json", "topologies/4-1.json", "job.log"} <= set(z.namelist())
    csv_head = client.get(f"/api/v1/jobs/{bench['id']}/artifacts/results.csv").text.splitlines()[0]
    assert "marginal_mem_per_node" in csv_head and "deploy_deploy_s" in csv_head
    md = client.get(f"/api/v1/benchmarks/{bench['id']}/report.md").text
    assert f"| 2 | 1 | {size[2]['nodes']} |" in md and "ceiling 4 hosts" in md
    markers = client.get(f"/api/v1/jobs/{bench['id']}/artifacts").json()
    assert markers  # (gzipped; contents covered by the monitor tests)
    assert [b["id"] for b in client.get("/api/v1/benchmarks").json()] == [bench["id"]]


def test_traffic_sweep_measures_delivery(client, wait_jobs, fast):
    traffic = {
        "patterns": [
            {"id": "cs", "kind": "clients_to_servers", "servers": ["srv-1"], "bitrate": "5M"}
        ],
        "interval_s": 0.5,
        "ramp_s": 0,
    }
    bench = _start(client, scale=[2], traffic=traffic).json()
    wait_jobs()
    done = _done(client, bench["id"])
    assert done["status"] == "succeeded", done["job"]["error"]
    [row] = done["result"]["rows"]
    assert row["outcome"] == "ok" and row["flows"] == 2 and row["traffic_job"]
    assert row["offered_bps"] == 10e6 and row["delivered_ratio"] > 0.8
    run = client.get(f"/api/v1/traffic/runs/{row['traffic_job']}").json()
    assert run["result"]["stopped_by"] == "benchmark"
    # The network side is in the row, the report, and the export (run summaries).
    assert row["slowest_flow"] and row["bytes_received"] > 0 and row["flow_ratio_min"] > 0.8
    md = client.get(f"/api/v1/benchmarks/{bench['id']}/report.md").text
    assert "| Hosts | # | Flows | Asked Mb/s |" in md and "| 2 | 1 | 2 | 10.00 |" in md
    z = zipfile.ZipFile(io.BytesIO(client.get(f"/api/v1/benchmarks/{bench['id']}/export").content))
    assert {"traffic/2-1/run.json", "traffic/2-1/totals.ndjson"} <= set(z.namelist())
    assert "traffic/2-1/flows.ndjson" not in z.namelist()  # keep_samples is off


def test_images_a_small_step_leaves_out_are_prepared_too(client, wait_jobs, fast):
    # 2 hosts at 99:1 place no postgres node, but a larger step would: the
    # images step pulls it up front instead of inside a later deploy.
    fast.present_images = {"kathara/base", "kathara/frr"}
    mix = [
        {"type": "workstation", "weight": 99},
        {"type": "database-server", "image": "postgres:alpine", "weight": 1},
    ]
    bench = _start(client, scale=[2], topology={"generate": {"host_mix": mix}}).json()
    wait_jobs()
    assert _done(client, bench["id"])["status"] == "succeeded"
    assert "postgres:alpine" in fast.present_images


def test_the_host_at_rest_is_recorded(client, wait_jobs, fast):
    bench = _start(client, scale=[2], rest_s=0.3).json()
    wait_jobs()
    done = _done(client, bench["id"])
    rest = done["result"]["rest"]
    assert rest["samples"] > 0 and rest["mem_used"] > 0 and rest["mem_total"] > rest["mem_used"]
    md = client.get(f"/api/v1/benchmarks/{bench['id']}/report.md").text
    assert "**At rest (before the first step):**" in md
    plain = _start(client, scale=[2]).json()  # rest_s 0: not measured
    wait_jobs()
    assert _done(client, plain["id"])["result"]["rest"] is None


def test_repetitions_fold_into_a_spread_table(client, wait_jobs, fast):
    bench = _start(client, scale=[2], repetitions=2).json()
    wait_jobs()
    done = _done(client, bench["id"])
    assert done["result"]["kind"] == "sweep" and len(done["result"]["rows"]) == 2
    md = client.get(f"/api/v1/benchmarks/{bench['id']}/report.md").text
    assert "Per scale over its repetitions (mean ± std):" in md and "| 2 | 2 (2) |" in md
    wrong = _start(client, scale=[2], kind="adaptive")
    assert wrong.status_code == 422


def test_a_random_sweep_records_each_steps_composition(client, wait_jobs, fast):
    pools = {
        "hosts": [
            {"type": "workstation", "images": ["kathara/base"]},
            {"type": "web-server", "images": ["httpd:alpine"]},
            {"type": "router", "images": ["kathara/frr"]},
        ],
        "routers": [{"type": "firewall", "images": ["kathara/frr"]}],
    }
    gen = {"servers": 0, "hosts_per_subnet": 4, "random": pools, "seed": 3}
    bench = _start(client, scale=[6], topology={"generate": gen}).json()
    wait_jobs()
    done = _done(client, bench["id"])
    assert done["status"] == "succeeded", done["job"]["error"]
    [row] = done["result"]["rows"]
    assert sum(row["composition"].values()) == row["nodes"]
    assert row["composition"]["firewall · kathara/frr"] == 3  # core + 2 subnet routers
    md = client.get(f"/api/v1/benchmarks/{bench['id']}/report.md").text
    assert "generated, random (seed 3)" in md and "Hosts (3 types)" in md
    csv_head = client.get(f"/api/v1/jobs/{bench['id']}/artifacts/results.csv").text.splitlines()[0]
    assert "composition" not in csv_head
    bad = {**gen, "random": {"hosts": [{"type": "router", "images": ["httpd:alpine"]}]}}
    assert _start(client, scale=[6], topology={"generate": bad}).json()["code"] == "bad_generator"


def test_an_image_census(client, wait_jobs, fast):
    fast.platform = "linux/arm64"  # malicious-client builds only for amd64
    fast.fail_build = {"ae3gis.local/nginx": "boom"}
    cases = [
        {"type": "web-server", "image": "httpd:alpine"},
        {"type": "web-server", "image": "ae3gis.local/nginx"},
        {"type": "attacker", "image": "ae3gis.local/malicious-client"},
    ]
    body = {"label": "census", **FAST, "census": {"per_image": 3, "cases": cases}}
    r = client.post("/api/v1/benchmarks", json=body)
    assert r.status_code == 202, r.text
    assert r.json()["kind"] == "census" and len(r.json()["spec"]["census"]["cases"]) == 4
    wait_jobs()
    done = _done(client, r.json()["id"])
    assert done["status"] == "succeeded", done["job"]["error"]
    result = done["result"]
    assert result["stopped_by"] == "completed" and result["ceiling"] is None
    rows = {row["case"]: row for row in result["rows"]}
    ref, httpd = rows["workstation · kathara/base"], rows["web-server · httpd:alpine"]
    assert result["rows"][0]["case"] == "workstation · kathara/base"  # the reference first
    assert ref["outcome"] == httpd["outcome"] == "ok" and httpd["nodes"] == 3 + 5
    assert set(httpd["by_image"]) == {"web-server · httpd:alpine"}  # only the case's nodes
    assert httpd["by_image"]["web-server · httpd:alpine"]["count"] == 3
    nginx = rows["web-server · ae3gis.local/nginx"]
    attacker = rows["attacker · ae3gis.local/malicious-client"]
    assert (nginx["outcome"], nginx["reason"]) == ("skipped", "image_failed")
    assert (attacker["outcome"], attacker["reason"]) == ("skipped", "image_unavailable")
    table = {c["case"]: c for c in result["census"]}
    assert table["web-server · httpd:alpine"]["usable"] and not table[nginx["case"]]["usable"]
    # The fake charges 10 MB a node: the estimate takes the base nodes out.
    assert table["web-server · httpd:alpine"]["host_mem_per_node"] == pytest.approx(10e6, rel=0.1)
    md = client.get(f"/api/v1/benchmarks/{r.json()['id']}/report.md").text
    assert "2 of 4 cases usable" in md and "| `web-server · httpd:alpine` | ok |" in md
    names = [st["name"] for st in done["job"]["steps"]]
    assert names[3:] == list(rows)
    assert fast.labs == {}
    bad = client.post(
        "/api/v1/benchmarks",
        json={**body, "census": {"cases": [{"type": "router", "image": "httpd:alpine"}]}},
    )
    assert bad.status_code == 422 and bad.json()["code"] == "bad_census"
    assert client.post("/api/v1/benchmarks", json={**body, "scale": [2]}).status_code == 422


MATRIX = {
    "patterns": [
        {"id": "cs", "kind": "clients_to_servers", "servers": ["srv-1", "srv-2"]},
        {
            "id": "mesh",
            "kind": "mesh",
            "fanout": 2,
            "nodes": {"roles": ["host"], "exclude": ["srv-1", "srv-2"]},
        },
    ],
    "axes": {
        "pattern": ["cs", "mesh"],
        "protocol": ["tcp", "udp"],
        "bitrate": ["50K", "1M"],
        "burst_interval_ms": [100, 2000],
    },
    "interval_s": 0.5,
    "ramp_s": 0,
    "gap_s": 0.05,
    "seed": 1,
}


def test_a_traffic_matrix_runs_every_cell_on_one_deployment(client, wait_jobs, fast):
    gen = {"servers": 2, "hosts_per_subnet": 4}
    r = _start(client, scale=[4], topology={"generate": gen}, matrix=MATRIX)
    assert r.status_code == 202, r.text
    bench = r.json()
    assert bench["kind"] == "matrix"
    wait_jobs()
    done = _done(client, bench["id"])
    assert done["status"] == "succeeded", done["job"]["error"]
    result = done["result"]
    assert result["stopped_by"] == "completed" and result["ceiling"] is None
    deploy, *cells = result["rows"]
    assert deploy["step"] == "deploy" and deploy["deploy_s"] is not None
    assert deploy["destroy_s"] is not None and deploy["marginal_mem_per_node"] is not None
    assert len(cells) == 16 and all(c["outcome"] == "ok" for c in cells), [
        (c["case"], c["outcome"], c.get("detail")) for c in cells
    ]
    ids = [c["case"] for c in cells]
    assert len(set(ids)) == 16 and "cs·tcp·50K·100ms" in ids
    from domain.benchmark import matrix_cells

    assert ids != [c["id"] for c in matrix_cells(MATRIX)]  # run in a shuffled order
    mesh = next(c for c in cells if c["case"] == "mesh·udp·1M·2000ms")
    assert mesh["flows"] == 8 and mesh["cell"]["burst_interval_ms"] == 2000  # 4 hosts × 2
    assert mesh["offered_bps"] == 8e6 and mesh["idle_cpu_mean"] is not None
    run = client.get(f"/api/v1/traffic/runs/{mesh['traffic_job']}").json()
    assert run["result"]["flows"][0]["burst"]["count"] == 179
    names = [st["name"] for st in done["job"]["steps"]]
    assert names[:4] == ["preflight", "images", "baseline", "deploy"]
    assert names[4].startswith("cell 001/16 ") and names[-1] == "teardown"
    # Deployed once for all the cells.
    jobs = client.get(f"/api/v1/topologies/{bench['topology_id']}/jobs").json()
    assert sum(1 for j in jobs if j["kind"] == "deploy") == 1
    assert len(result["matrix"]) == 16
    md = client.get(f"/api/v1/benchmarks/{bench['id']}/report.md").text
    assert "**pattern cs · protocol tcp — Delivered (% of asked)**" in md
    assert "**pattern mesh · protocol udp — Loss %**" in md
    assert "16 of 16 cells passed" in md and "Cells in run order:" in md
    assert md.index("**pattern cs · protocol tcp") < md.index("**pattern mesh · protocol udp")
    assert "| 50K | " in md and "| bitrate \\ burst_interval_ms | 100ms | 2000ms |" in md
    z = zipfile.ZipFile(io.BytesIO(client.get(f"/api/v1/benchmarks/{bench['id']}/export").content))
    assert sum(1 for n in z.namelist() if n.startswith("traffic/") and n.endswith("run.json")) == 16
    assert fast.labs == {}


def test_matrix_refusals(client):
    gen = {"topology": {"generate": {"servers": 2, "hosts_per_subnet": 4}}}
    bad_axis = {**MATRIX, "axes": {"colour": ["red"]}}
    assert _start(client, scale=[4], matrix=bad_axis, **gen).status_code == 422
    assert _start(client, scale=[4, 8], matrix=MATRIX, **gen).status_code == 422
    huge = {
        **MATRIX,
        "axes": {"bitrate": ["1G"], "burst_interval_ms": [10000], "protocol": ["udp"]},
    }
    r = _start(client, scale=[4], matrix=huge, **gen)
    assert r.status_code == 422 and r.json()["code"] == "bad_matrix"
    ghost = {
        **MATRIX,
        "patterns": [{**MATRIX["patterns"][0], "servers": ["ghost"]}, MATRIX["patterns"][1]],
    }
    r = _start(client, scale=[4], matrix=ghost, **gen)
    assert r.status_code == 422 and r.json()["code"] == "bad_matrix"


def test_a_stop_criterion_ends_the_sweep(client, wait_jobs, fast):
    fast.oom_nodes = {"h0-1"}
    bench = _start(client, scale=[2, 4, 8]).json()
    wait_jobs()
    done = _done(client, bench["id"])
    assert done["status"] == "succeeded", done["job"]["error"]
    result = done["result"]
    [row] = result["rows"]
    assert row["outcome"] == "stopped" and row["reason"] == "oom" and "h0-1" in row["detail"]
    assert result["stopped_by"] == "criterion:oom" and result["ceiling"] is None
    assert fast.labs == {}


def test_a_step_that_would_exhaust_memory_is_not_deployed(client, wait_jobs, fast):
    fast.fake_mem_per_node = 300_000_000  # 20 hosts (37 nodes) would need ~12 GB of 8.6
    spec = {"generate": {"servers": 1, "hosts_per_subnet": 3}}
    bench = _start(client, topology=spec, scale=[2, 20]).json()
    wait_jobs()
    done = _done(client, bench["id"])
    assert done["status"] == "succeeded", done["job"]["error"]
    first, second = done["result"]["rows"]
    assert first["outcome"] == "ok"
    assert second["outcome"] == "stopped" and second["reason"] == "projected_memory"
    assert "deploy_job" not in second and done["result"]["ceiling"] == 2


def test_an_adaptive_sweep_climbs_to_the_memory_target(client, wait_jobs, fast):
    # 50 MB a node on the fake 8 GiB host (1 GiB resting): 90% is ~133 nodes,
    # and a few hosts more add ~1% (coarser steps could jump past 95%)
    fast.fake_mem_per_node = 50_000_000
    gen = {"servers": 1, "hosts_per_subnet": 20}
    adaptive = {"start": 20, "min_step": 2, "confirm": 1}
    stop = {"max_mem_pct": 95, "project_memory": False}
    r = _start(client, scale=[], topology={"generate": gen}, adaptive=adaptive, stop=stop)
    assert r.status_code == 202, r.text
    wait_jobs()
    done = _done(client, r.json()["id"])
    assert done["status"] == "succeeded", done["job"]["error"]
    result = done["result"]
    assert done["kind"] == "adaptive" and result["kind"] == "adaptive"
    rows = result["rows"]
    climb, confirm = rows[:-1], rows[-1]
    assert all(r["outcome"] == "ok" for r in rows), [
        (r["scale"], r["outcome"], r.get("detail"), r.get("hold_mem_pct_max")) for r in rows
    ]
    scales = [r["scale"] for r in climb]
    assert scales[0] == 20 and scales == sorted(set(scales)) and len(scales) >= 3
    assert scales[1] == 40  # far from the target: at most ×2
    assert climb[-1]["hold_mem_pct_max"] >= 90 > climb[-2]["hold_mem_pct_max"]
    assert all("next" in r for r in climb)
    assert result["stopped_by"] == "limit_reached" and result["limit"].startswith("memory peaked")
    assert (confirm["scale"], confirm["rep"]) == (scales[-1], 2)
    assert result["ceiling"] == scales[-1]
    names = [s["name"] for s in done["job"]["steps"]]
    assert names[-1] == f"{scales[-1]} hosts #2"
    assert fast.labs == {}


def test_a_climb_steps_down_from_a_start_too_big(client, wait_jobs, fast):
    # 50 MB a node on the fake 8 GiB host: 200 hosts (~230 nodes) can't fit.
    fast.fake_mem_per_node = 50_000_000
    gen = {"servers": 1, "hosts_per_subnet": 20}
    adaptive = {"start": 200, "min_step": 2, "confirm": 0, "descend": 0.5}
    stop = {"max_mem_pct": 95, "project_memory": False}
    r = _start(client, scale=[], topology={"generate": gen}, adaptive=adaptive, stop=stop)
    wait_jobs()
    done = _done(client, r.json()["id"])
    assert done["status"] == "succeeded", done["job"]["error"]
    rows = done["result"]["rows"]
    first = rows[0]
    assert first["scale"] == 200 and first["outcome"] == "stopped"
    assert first["reason"] == "memory" and first["next"].endswith("trying 100 hosts")
    assert rows[1]["scale"] == 100 and rows[1]["outcome"] == "ok"
    assert all(r["scale"] < 200 for r in rows[1:])  # the climb stays below what failed
    ceiling = done["result"]["ceiling"]
    assert ceiling == max(r["scale"] for r in rows if r["outcome"] == "ok") and ceiling >= 100
    assert done["result"]["stopped_by"] in ("limit_reached", "bracketed")
    assert done["result"]["reason"] is None  # the retried step didn't end the climb
    assert fast.labs == {}


def test_a_full_disk_stops_a_step_and_the_climb_retries_lower(client, wait_jobs, fast):
    # The fake disk: 60 GiB, 20 GiB used at rest; 500 MB a node fills it to 90%
    # at ~67 nodes (memory stays low).
    fast.fake_disk_per_node = 500_000_000
    gen = {"servers": 1, "hosts_per_subnet": 20}
    adaptive = {"start": 100, "min_step": 10, "confirm": 0, "descend": 0.5}
    r = _start(client, scale=[], topology={"generate": gen}, adaptive=adaptive)
    wait_jobs()
    done = _done(client, r.json()["id"])
    assert done["status"] == "succeeded", done["job"]["error"]
    first, second, *_ = done["result"]["rows"]
    assert (first["outcome"], first["reason"]) == ("stopped", "disk")
    assert second["scale"] == 50 and second["outcome"] == "ok"
    assert second["disk_per_node"] == pytest.approx(500e6, rel=0.05)
    assert 50 <= second["hold_disk_pct_max"] < 90
    assert done["result"]["ceiling"] >= 50
    md = client.get(f"/api/v1/benchmarks/{r.json()['id']}/report.md").text
    assert "| Disk MB/node | Disk % max |" in md


@pytest.mark.parametrize("confirm", [0, 1])
def test_an_adaptive_sweep_keeps_its_last_lab(client, wait_jobs, fast, confirm):
    # The last step is the climb's last (no confirm runs) or the last confirm run.
    fast.fake_mem_per_node = 50_000_000
    gen = {"servers": 1, "hosts_per_subnet": 20}
    adaptive = {"start": 60, "min_step": 2, "confirm": confirm}
    stop = {"max_mem_pct": 95, "project_memory": False}
    r = _start(
        client, scale=[], topology={"generate": gen}, adaptive=adaptive, stop=stop, keep_last=True
    )
    assert r.status_code == 202, r.text
    wait_jobs()
    done = _done(client, r.json()["id"])
    assert done["status"] == "succeeded", done["job"]["error"]
    rows = done["result"]["rows"]
    assert len(rows) >= 2 and all(r["outcome"] == "ok" for r in rows)
    assert all("destroy_s" in r for r in rows[:-1]) and "destroy_s" not in rows[-1]
    (lab,) = fast.labs.values()
    assert lab.plan is not None and len(lab.plan.nodes) == rows[-1]["nodes"]
    topo = client.get(f"/api/v1/topologies/{done['topology_id']}").json()
    assert topo["status"] == "deployed"


def test_adaptive_needs_a_generated_topology(client, topology):
    bad = [
        {"scale": [2], "adaptive": {"start": 2}},  # one or the other
        {"topology": {"topology_id": topology["id"]}, "adaptive": {"start": 2}},
        {"adaptive": {"start": 2, "reach_mem_pct": 95, "target_mem_pct": 90}},
    ]
    for body in bad:
        r = client.post("/api/v1/benchmarks", json={"label": "t", **FAST, **body})
        assert r.status_code == 422, r.text


def test_unreachable_hosts_fail_the_step(client, wait_jobs, fast):
    fast.unreachable = {"h0-2"}
    bench = _start(client, scale=[2], stop={"ready_timeout_s": 5}).json()
    wait_jobs()
    [row] = _done(client, bench["id"])["result"]["rows"]
    assert row["outcome"] == "failed" and row["reason"] == "not_ready" and "h0-2" in row["detail"]


def test_busy_hosts_and_one_at_a_time(client, wait_jobs, fast, topology):
    client.post(f"/api/v1/topologies/{topology['id']}/deploy")
    wait_jobs()
    busy = _start(client, scale=[2]).json()
    wait_jobs()
    done = _done(client, busy["id"])
    assert done["status"] == "failed" and "host is busy" in done["job"]["error"]

    fast.traffic_interval = 0.02
    allowed = _start(client, scale=[2], allow_busy_host=True, hold_s=1.0).json()
    again = _start(client, scale=[2])
    assert again.status_code == 409 and again.json()["code"] == "benchmark_active"
    wait_jobs()
    done = _done(client, allowed["id"])
    assert done["status"] == "succeeded", done["job"]["error"]
    info = client.get(f"/api/v1/jobs/{allowed['id']}/artifacts/benchmark.json").json()
    assert info["environment"]["busy"]["labs"]  # recorded with the results


def test_existing_topology_and_stop(client, wait_jobs, fast, topology):
    bench = _start(
        client, topology={"topology_id": topology["id"]}, scale=[], repetitions=3, hold_s=0.5
    ).json()
    assert bench["spec"]["scale"] == [6]
    end = time.monotonic() + 5
    while time.monotonic() < end and not (_done(client, bench["id"])["result"] or {}).get("rows"):
        time.sleep(0.05)
    live = client.get(f"/api/v1/benchmarks/{bench['id']}/report.md")
    assert live.status_code == 200 and "still running" in live.text
    client.post(f"/api/v1/jobs/{bench['id']}/stop")
    wait_jobs()
    done = _done(client, bench["id"])
    assert done["status"] == "succeeded" and done["result"]["stopped_by"] == "user"
    assert 1 <= len(done["result"]["rows"]) < 3
    assert client.get(f"/api/v1/topologies/{topology['id']}").json()["status"] == "idle"


def test_refusals(client, topology, wait_jobs):
    assert client.post("/api/v1/benchmarks", json={"scale": [4, 2]}).status_code == 422
    both = {"topology": {"topology_id": topology["id"], "generate": {}}, "scale": [2]}
    assert client.post("/api/v1/benchmarks", json=both).status_code == 422
    assert _start(client, scale=[]).json()["code"] == "no_scale"
    too_big = _start(client, scale=[2, 100_000])
    assert too_big.status_code == 422 and too_big.json()["code"] == "bad_generator"
    client.post(f"/api/v1/topologies/{topology['id']}/deploy")
    wait_jobs()
    deployed = _start(client, topology={"topology_id": topology["id"]})
    assert deployed.status_code == 409 and deployed.json()["code"] == "bad_state"
