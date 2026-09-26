"""Job artifacts: the store (names, listing, gc) and the download endpoints."""

import os
import time

import pytest

from services import jobs
from services.artifacts import ArtifactStore


def test_store_rejects_names_outside_the_job_dir(tmp_path):
    store = ArtifactStore(tmp_path)
    for bad in ("../x", "a/b", ".hidden", "", "x" * 80):
        with pytest.raises(ValueError):
            store.path("abc123", bad)
    with pytest.raises(ValueError):
        store.path("../etc", "passwd")
    p = store.path("abc123", "capture.pcap", create_dir=True)
    p.write_bytes(b"x")
    [a] = store.list("abc123")
    assert (a.name, a.size, a.content_type) == ("capture.pcap", 1, "application/vnd.tcpdump.pcap")


def test_gc_removes_only_old_job_dirs(tmp_path):
    store = ArtifactStore(tmp_path)
    old = store.path("old1", "run.json", create_dir=True)
    old.write_text("{}")
    past = time.time() - 40 * 86400
    os.utime(old, (past, past))
    os.utime(old.parent, (past, past))
    store.path("new1", "run.json", create_dir=True).write_text("{}")
    assert store.gc(30) == 1
    assert not old.parent.exists() and store.list("new1")


def test_download_and_list_artifacts(app, client):
    runner = app.state.runner
    with runner.session_factory() as db:
        job = jobs.create_job(db, "capture", subject="capture:x")
        job.status = "succeeded"
        db.commit()
        job_id = job.id
    app.state.artifacts.path(job_id, "capture.pcap", create_dir=True).write_bytes(
        b"\xd4\xc3\xb2\xa1"
    )
    listed = client.get(f"/api/v1/jobs/{job_id}/artifacts").json()
    assert [(a["name"], a["size"]) for a in listed] == [("capture.pcap", 4)]
    r = client.get(f"/api/v1/jobs/{job_id}/artifacts/capture.pcap")
    assert r.status_code == 200 and r.content == b"\xd4\xc3\xb2\xa1"
    assert r.headers["content-type"] == "application/vnd.tcpdump.pcap"
    assert "capture.pcap" in r.headers["content-disposition"]
    assert client.get(f"/api/v1/jobs/{job_id}/artifacts/missing.pcap").status_code == 404
    assert client.get(f"/api/v1/jobs/{job_id}/artifacts/..%2Fx").status_code == 404
    assert client.get("/api/v1/jobs/nope/artifacts").status_code == 404
