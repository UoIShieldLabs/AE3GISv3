import asyncio
import copy
import shutil
import subprocess
import time

import pytest
from fastapi.testclient import TestClient

from main import create_app
from tests.conftest import TWO_SUBNETS, make_settings

NGINX = "ae3gis.local/nginx"


@pytest.fixture
def src(tmp_path):
    root = tmp_path / "containers"
    ctx = root / "nginx-server"
    ctx.mkdir(parents=True)
    (ctx / "dockerfile").write_text("FROM ubuntu:24.04\nRUN echo hi\n")
    (ctx / "index.html").write_text("<h1>hi</h1>\n")
    return root


@pytest.fixture
def app(tmp_path, fake_engine, src):
    settings = make_settings(tmp_path, source_overrides={"ae3gis-containers": src})
    return create_app(settings, fake_engine)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def wait_jobs(client, app):
    return lambda: client.portal.call(app.state.runner.wait_idle)


def _image(client, ref, **params):
    report = client.get("/api/v1/images", params=params).json()
    return next(i for i in report["images"] if i["ref"] == ref)


def _topology(client, image=NGINX, name="web"):
    data = copy.deepcopy(TWO_SUBNETS)
    host = data["sites"][0]["subnets"][0]["containers"][2]
    host.update(type="web-server", image=image)
    r = client.post("/api/v1/topologies", json={"name": name, "data": data})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _wait_for(pred, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return
        time.sleep(0.02)
    raise AssertionError("condition never became true")


def test_report_lists_catalog_images_with_status(client, tmp_path):
    report = client.get("/api/v1/images").json()
    assert report["host"] == {
        "platform": "linux/amd64",
        "can_build": True,
        "detail": "fake builder",
    }
    [source] = report["sources"]
    assert source["name"] == "ae3gis-containers" and source["available"]
    assert source["can_sync"] is False and source["detail"] == "Local override"
    by_ref = {i["ref"]: i for i in report["images"]}
    assert by_ref[NGINX]["status"] == "missing" and by_ref[NGINX]["kind"] == "build"
    assert by_ref[NGINX]["expected_fingerprint"]
    assert (
        by_ref["kathara/frr"]["status"] == "ready" and by_ref["kathara/frr"]["kind"] == "registry"
    )
    # the context isn't in this (test) checkout
    assert by_ref["ae3gis.local/apache"]["status"] == "unavailable"
    assert "not found" in by_ref["ae3gis.local/apache"]["reason"]
    assert by_ref["ae3gis.local/scadabr"]["stability"] == "hidden"


def test_build_then_stale_then_fresh_rebuild(client, wait_jobs, fake_engine, src, tmp_path):
    r = client.post("/api/v1/images/builds", json={"refs": [NGINX]})
    assert r.status_code == 202, r.text
    [job] = r.json()
    assert job["kind"] == "build" and job["subject"] == f"image:{NGINX}"
    assert job["topology_id"] is None
    wait_jobs()

    job = client.get(f"/api/v1/jobs/{job['id']}").json()
    assert job["status"] == "succeeded", job
    assert [s["name"] for s in job["steps"]] == ["source", "snapshot", "build", "verify"]
    log = client.get(f"/api/v1/jobs/{job['id']}/log", params={"offset": 0}).json()["text"]
    assert "#2 [1/3] FROM docker.io/library/ubuntu:24.04" in log
    [spec] = fake_engine.builds
    assert spec.dockerfile == "dockerfile" and not spec.no_cache
    assert spec.labels["io.ae3gis.ref"] == NGINX
    assert not spec.context.exists()  # the snapshot is removed after the build
    assert list((tmp_path / "build-ctx").iterdir()) == []

    img = _image(client, NGINX)
    assert img["status"] == "ready"
    assert img["built_fingerprint"] == img["expected_fingerprint"]
    assert img["last_job"]["id"] == job["id"]

    (src / "nginx-server" / "dockerfile").write_text("FROM ubuntu:24.04\nRUN echo changed\n")
    img = _image(client, NGINX)
    assert img["status"] == "stale" and img["built_fingerprint"] != img["expected_fingerprint"]

    client.post("/api/v1/images/builds", json={"refs": [NGINX], "fresh": True})
    wait_jobs()
    assert fake_engine.builds[-1].no_cache and fake_engine.builds[-1].pull
    assert _image(client, NGINX)["status"] == "ready"


def test_builds_are_deduplicated_and_cancellable(client, app, wait_jobs, fake_engine, tmp_path):
    fake_engine.build_gate = asyncio.Event()
    first = client.post("/api/v1/images/builds", json={"refs": [NGINX]}).json()[0]
    again = client.post("/api/v1/images/builds", json={"refs": [NGINX, NGINX]}).json()
    assert [j["id"] for j in again] == [first["id"]]
    _wait_for(lambda: _image(client, NGINX)["status"] == "building")

    def build_step_running():
        steps = client.get(f"/api/v1/jobs/{first['id']}").json()["steps"]
        return any(s["name"] == "build" and s["status"] == "running" for s in steps)

    _wait_for(build_step_running)
    assert client.post(f"/api/v1/jobs/{first['id']}/cancel").status_code == 202
    wait_jobs()
    job = client.get(f"/api/v1/jobs/{first['id']}").json()
    assert job["status"] == "cancelled"
    assert _image(client, NGINX)["status"] == "missing"
    assert list((tmp_path / "build-ctx").iterdir()) == []


def test_failed_build_is_reported(client, wait_jobs, fake_engine):
    fake_engine.fail_build = {NGINX: 'process "/bin/sh -c apt-get install nope" did not complete'}
    job = client.post("/api/v1/images/builds", json={"refs": [NGINX]}).json()[0]
    wait_jobs()
    job = client.get(f"/api/v1/jobs/{job['id']}").json()
    assert job["status"] == "failed" and "apt-get install nope" in job["error"]
    img = _image(client, NGINX)
    assert img["status"] == "failed" and "apt-get install nope" in img["reason"]


def test_only_catalog_build_images_can_be_built(client):
    r = client.post("/api/v1/images/builds", json={"refs": ["kathara/frr"]})
    assert r.status_code == 422 and r.json()["code"] == "not_buildable"


def test_deploy_builds_missing_images_first(client, wait_jobs, fake_engine):
    tid = _topology(client)
    assert _image(client, NGINX, topology_id=tid)["status"] == "missing"
    deploy = client.post(f"/api/v1/topologies/{tid}/deploy").json()
    wait_jobs()
    deploy = client.get(f"/api/v1/jobs/{deploy['id']}").json()
    assert deploy["status"] == "succeeded", deploy
    images_step = next(s for s in deploy["steps"] if s["name"] == "images")
    [build_id] = images_step["jobs"]
    assert "1 built" in images_step["message"]
    assert client.get(f"/api/v1/jobs/{build_id}").json()["status"] == "succeeded"
    assert len(fake_engine.builds) == 1 and len(fake_engine.labs) == 1
    report = client.get("/api/v1/images", params={"topology_id": tid}).json()
    assert {i["ref"] for i in report["images"]} == {NGINX, "kathara/frr", "kathara/base"}


def test_two_deploys_share_one_build(client, wait_jobs, fake_engine):
    fake_engine.build_gate = asyncio.Event()
    a, b = _topology(client, name="a"), _topology(client, name="b")
    ja = client.post(f"/api/v1/topologies/{a}/deploy").json()["id"]
    jb = client.post(f"/api/v1/topologies/{b}/deploy").json()["id"]

    def both_waiting():
        steps = [client.get(f"/api/v1/jobs/{j}").json()["steps"] for j in (ja, jb)]
        return all(any(s["name"] == "images" and s["jobs"] for s in st) for st in steps)

    _wait_for(both_waiting)
    client.portal.call(fake_engine.build_gate.set)
    wait_jobs()
    assert len(fake_engine.builds) == 1
    for j in (ja, jb):
        assert client.get(f"/api/v1/jobs/{j}").json()["status"] == "succeeded"
    assert len(fake_engine.labs) == 2


def test_failed_build_fails_the_deploy_cleanly(client, wait_jobs, fake_engine):
    fake_engine.fail_build = {NGINX: "no space left on device"}
    tid = _topology(client)
    job_id = client.post(f"/api/v1/topologies/{tid}/deploy").json()["id"]
    wait_jobs()
    job = client.get(f"/api/v1/jobs/{job_id}").json()
    assert job["status"] == "failed"
    assert "Building Nginx failed" in job["error"] and "no space left" in job["error"]
    assert fake_engine.labs == {}
    assert client.get(f"/api/v1/topologies/{tid}/runtime").json()["status"] == "error"


def test_stale_images_deploy_with_a_warning(client, wait_jobs, fake_engine, src):
    client.post("/api/v1/images/builds", json={"refs": [NGINX]})
    wait_jobs()
    (src / "nginx-server" / "index.html").write_text("<h1>changed</h1>\n")
    tid = _topology(client)
    job_id = client.post(f"/api/v1/topologies/{tid}/deploy").json()["id"]
    wait_jobs()
    assert client.get(f"/api/v1/jobs/{job_id}").json()["status"] == "succeeded"
    assert len(fake_engine.builds) == 1  # not rebuilt behind the user's back
    events = client.get(f"/api/v1/topologies/{tid}/events").json()
    stale = [e for e in events if e["type"] == "deploy.images_stale"]
    assert stale and stale[0]["data"]["refs"] == [NGINX]


def test_deploy_refuses_images_this_host_cannot_build(client, wait_jobs, fake_engine):
    fake_engine.can_build = False
    tid = _topology(client)
    job_id = client.post(f"/api/v1/topologies/{tid}/deploy").json()["id"]
    wait_jobs()
    job = client.get(f"/api/v1/jobs/{job_id}").json()
    assert job["status"] == "failed" and "Can't build Nginx" in job["error"]
    assert fake_engine.builds == []


def test_sync_refuses_sources_it_does_not_manage(client):
    r = client.post("/api/v1/sources/ae3gis-containers/sync")
    assert r.status_code == 409 and r.json()["code"] == "not_syncable"
    assert client.post("/api/v1/sources/nope/sync").status_code == 422


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_git_source_clones_and_syncs(tmp_path):
    from catalog.models import GitSource
    from config import Settings
    from services.sources import Sources

    upstream = tmp_path / "upstream"
    (upstream / "nginx-server").mkdir(parents=True)
    (upstream / "nginx-server" / "dockerfile").write_text("FROM ubuntu\n")

    def git(*args, cwd=upstream):
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
        )

    git("init", "-q", "-b", "main")
    git("add", ".")
    git("commit", "-q", "-m", "one")
    first = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=upstream, text=True).strip()

    settings = Settings(data_dir=tmp_path / "data")
    settings.ensure_dirs()
    sources = Sources(settings, {"c": GitSource(kind="git", url=str(upstream), ref="main")})
    assert sources.state("c").available is False and sources.state("c").can_sync
    lines: list[str] = []

    root = asyncio.run(sources.ensure("c", lines.append))
    assert (root / "nginx-server" / "dockerfile").read_text() == "FROM ubuntu\n"
    assert sources.state("c").revision == first

    (upstream / "nginx-server" / "dockerfile").write_text("FROM debian\n")
    git("commit", "-q", "-am", "two")
    (root / "stray").write_text("x")  # local changes are discarded by a sync
    second = asyncio.run(sources.sync("c", lines.append))
    assert second != first and sources.state("c").revision == second
    assert (root / "nginx-server" / "dockerfile").read_text() == "FROM debian\n"
    assert not (root / "stray").exists()


def test_build_command_loads_into_the_image_store(tmp_path):
    from engine.base import BuildSpec
    from engine.docker_build import build_command

    cmd = build_command(
        BuildSpec(
            ref=NGINX,
            context=tmp_path,
            dockerfile="dockerfile",
            args={"V": "1"},
            labels={"io.ae3gis.fingerprint": "abc"},
            pull=True,
            no_cache=True,
        )
    )
    assert cmd[:5] == ["docker", "buildx", "build", "--load", "--progress=plain"]
    assert ["-f", str(tmp_path / "dockerfile")] == cmd[5:7]
    assert ["-t", NGINX] == cmd[7:9]
    assert "--label" in cmd and "io.ae3gis.fingerprint=abc" in cmd
    assert "--build-arg" in cmd and "V=1" in cmd
    assert "--pull" in cmd and "--no-cache" in cmd and cmd[-1] == str(tmp_path)


def test_build_failures_are_explained_by_the_step_output():
    from engine.docker_build import explain_failure

    apt = [
        "#5 5.1 Reading package lists...",
        "#5 5.727 E: Package 'aircrack-ng' has no installation candidate",
        '#5 ERROR: process "/bin/sh -c apt-get install aircrack-ng" did not complete successfully: exit code: 100',
        "------",
        "Dockerfile:5",
        'ERROR: failed to build: failed to solve: process "/bin/sh -c apt-get install" did not complete',
    ]
    assert explain_failure(apt) == "E: Package 'aircrack-ng' has no installation candidate"
    compiler = ["#9 12.0 src/x.c:3:1: error: expected ';'", "#9 12.1 make[2]: *** [x.o] Error 1"]
    assert explain_failure(compiler) == "src/x.c:3:1: error: expected ';'"
    only_buildkit = ['#3 ERROR: failed to compute cache key: "/nope" not found']
    assert explain_failure(only_buildkit) == only_buildkit[0]
    assert explain_failure([]) == ""
