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
