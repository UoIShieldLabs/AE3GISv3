"""AE3GIS adapter: a lab file deployed through AE3GIS's own REST API.

The backend runs in bench mode in Docker Desktop (compose project
``ae3gis-compare``), and the lab goes through the same path a user's deploy
does:

1. ``POST /topologies``: the lab file's topology;
2. ``POST /topologies/{id}/deploy``: a deploy job (validate → images → plan →
   deploy → verify), followed until it ends;
3. ``POST /topologies/{id}/destroy``, then delete the topology.

Timings are wall clock from the first request until the lab is up, or gone,
matching how the GNS3 adapter measures. The containers are found by Kathara's
labels (``app=kathara``, ``lab_hash``, ``name``).
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bench  # noqa: E402  (the stdlib API client the benchmark scripts use)

from .labs import Lab  # noqa: E402
from .target import Target  # noqa: E402

TERMINAL = ("succeeded", "failed", "cancelled")


@dataclass
class Ae3gisLab:
    topology_id: str
    lab_hash: str = ""
    machines: dict[str, str] = field(default_factory=dict)  # node id -> machine name
    timings: dict[str, float] = field(default_factory=dict)


class Ae3gis:
    def __init__(self, base: str, target: Target, token: str | None = None) -> None:
        self.api = bench.Api(base.rstrip("/") + "/api/v1", token)
        self.target = target

    def version(self) -> dict[str, Any]:
        return self.api.call("GET", "/system/health")

    def wait_job(self, job_id: str, deadline: float) -> dict[str, Any]:
        while True:
            job = self.api.call("GET", f"/jobs/{job_id}")
            if job["status"] in TERMINAL:
                return job
            if time.monotonic() > deadline:
                self.api.call("POST", f"/jobs/{job_id}/cancel")
                raise RuntimeError(f"job {job_id} still {job['status']} at the deadline")
            time.sleep(1.0)

    def deploy(self, lab: Lab, *, timeout_s: float = 2700, progress=print) -> Ae3gisLab:
        t0 = time.monotonic()
        topo = self.api.call(
            "POST", "/topologies", {"name": f"compare-{lab.name}", "data": lab.doc["topology"]}
        )
        tid = topo["id"]
        job = self.api.call("POST", f"/topologies/{tid}/deploy")
        job = self.wait_job(job["id"], t0 + timeout_s)
        t_done = time.monotonic()
        if job["status"] != "succeeded":
            self.destroy(Ae3gisLab(topology_id=tid), progress=lambda *_: None)
            raise RuntimeError(f"deploy {job['status']}: {job.get('error')}")
        state = self.api.call("GET", f"/topologies/{tid}").get("engine_state") or {}
        steps = {s["name"]: _seconds(s) for s in job.get("steps") or []}
        progress(f"  ae3gis: deployed in {t_done - t0:.1f}s ({json.dumps(steps)})")
        return Ae3gisLab(
            topology_id=tid,
            lab_hash=state.get("lab_hash", ""),
            machines=dict(state.get("nodes") or {}),
            timings={"deploy_s": round(t_done - t0, 3), **{f"job_{k}_s": v for k, v in steps.items() if v is not None}},
        )

    def containers(self, lab: Ae3gisLab) -> dict[str, str]:
        """Lab node id -> its Docker container id in Docker Desktop's VM."""
        text = self.target.out(
            self.target.docker(
                "ps", "-a", "--no-trunc",
                "--filter", "label=app=kathara", "--filter", f"label=lab_hash={lab.lab_hash}",
                "--format", '{{.ID}}\t{{.Label "name"}}',
            )
        )
        by_machine = {}
        for line in text.splitlines():
            cid, _, mname = line.partition("\t")
            by_machine[mname] = cid
        return {nid: by_machine[m] for nid, m in lab.machines.items() if m in by_machine}

    def destroy(self, lab: Ae3gisLab, *, timeout_s: float = 2700, progress=print) -> float:
        t0 = time.monotonic()
        try:
            job = self.api.call("POST", f"/topologies/{lab.topology_id}/destroy")
            job = self.wait_job(job["id"], t0 + timeout_s)
            if job["status"] != "succeeded":
                progress(f"  ae3gis: destroy {job['status']}: {job.get('error')}")
        except bench.ApiError as e:
            progress(f"  ae3gis: destroy: {e}")
        if lab.lab_hash:  # gone from Docker, not only from the backend's view
            while time.monotonic() - t0 < timeout_s:
                left = self.target.out(
                    self.target.docker("ps", "-aq", "--filter", f"label=lab_hash={lab.lab_hash}")
                ).split()
                if not left:
                    break
                time.sleep(1.0)
        took = round(time.monotonic() - t0, 3)
        try:
            self.api.call("DELETE", f"/topologies/{lab.topology_id}")
        except bench.ApiError:
            pass
        return took


def _seconds(step: dict[str, Any]) -> float | None:
    from datetime import datetime

    a, b = step.get("started_at"), step.get("ended_at")
    if not (a and b):
        return None
    return round((datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds(), 3)
