"""GNS3 2.2 adapter: a lab file as a GNS3 project of Docker nodes.

Through the server's REST API (``http://<vm>:3080/v2``):

1. **Project:** create a project.
2. **Nodes:** one Docker node per lab node, created in parallel:
   - the same image;
   - one adapter per interface (adapter *i* is ``eth``\\ *i*);
   - console off;
   - a start command that writes the node's boot commands to
     ``/ae3gis-init.sh``, runs them like Kathara's ``.startup`` does, then
     ``exec``\\ s the same idle process Kathara's machines run.
3. **Links:** one per point-to-point link, created in parallel.
4. **Start:** bulk start, then wait until every node reports ``started``.

Teardown stops the nodes, deletes the project, and waits until the containers
are gone from the VM's Docker.
"""

from __future__ import annotations

import base64
import json
import shlex
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from .labs import INIT_LOG, INIT_PATH, Lab
from .target import Target


class Gns3Error(RuntimeError):
    pass


@dataclass
class Gns3Lab:
    project_id: str
    nodes: dict[str, str]  # lab node id -> GNS3 node id
    timings: dict[str, float] = field(default_factory=dict)


class Gns3:
    def __init__(
        self,
        url: str,
        target: Target,
        *,
        concurrency: int = 8,
        idle: list[str] | None = None,
        extra_properties: dict[str, Any] | None = None,
    ) -> None:
        self.url = url.rstrip("/")
        self.target = target
        self.concurrency = concurrency
        self.idle = idle or ["bash"]  # what Kathara's machines idle on (checked in Phase 0)
        self.extra = dict(extra_properties or {})

    # ── HTTP ──

    def call(self, method: str, path: str, body: Any = None, timeout: float = 120) -> Any:
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(
            f"{self.url}/v2{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if data else {},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            raise Gns3Error(f"{method} {path}: HTTP {e.code}: {detail}") from e
        return json.loads(raw) if raw else None

    def version(self) -> dict[str, Any]:
        return self.call("GET", "/version", timeout=10)

    # ── a node's start command ──

    def start_command(self) -> str:
        """Write ``$AE3GIS_INIT`` (base64) to INIT_PATH, run it, then idle.
        GNS3 splits this with shlex and runs it once the node's interfaces
        exist (its init wrapper waits for them)."""
        script = (
            f'printf %s "$AE3GIS_INIT" | base64 -d > {INIT_PATH}'
            f" && sh {INIT_PATH} > {INIT_LOG} 2>&1; exec {shlex.join(self.idle)}"
        )
        return shlex.join(["sh", "-c", script])

    def node_body(self, lab: Lab, node: dict[str, Any]) -> dict[str, Any]:
        init = lab.init_script(node)
        env = [f"{k}={v}" for k, v in (node.get("env") or {}).items()]
        if init:
            env.append("AE3GIS_INIT=" + base64.b64encode(init.encode()).decode())
        props = {
            "image": node["image"],
            "adapters": max(1, lab.adapters(node)),
            "console_type": "none",
            "start_command": self.start_command() if init else shlex.join(self.idle),
            "environment": "\n".join(env),
            **self.extra,
        }
        return {
            "name": node["machine_name"],
            "node_type": "docker",
            "compute_id": "local",
            "properties": props,
        }

    # ── deploy / destroy ──

    def _parallel(self, fn, items: list) -> list:
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            return list(pool.map(fn, items))

    def deploy(self, lab: Lab, *, timeout_s: float = 2700, progress=print) -> Gns3Lab:
        t0 = time.monotonic()
        project = self.call("POST", "/projects", {"name": f"ae3gis-compare-{lab.name}-{int(time.time())}"})
        pid = project["project_id"]
        nodes: dict[str, str] = {}

        def create(node: dict[str, Any]) -> tuple[str, str]:
            body = self.node_body(lab, node)
            created = self.call("POST", f"/projects/{pid}/nodes", body, timeout=300)
            return node["id"], created["node_id"]

        try:
            nodes = dict(self._parallel(create, lab.nodes))
            t_nodes = time.monotonic()
            progress(f"  gns3: {len(nodes)} nodes created in {t_nodes - t0:.1f}s")

            def link(ends) -> None:
                (a, ai), (b, bi) = ends
                body = {
                    "nodes": [
                        {"node_id": nodes[a], "adapter_number": ai, "port_number": 0},
                        {"node_id": nodes[b], "adapter_number": bi, "port_number": 0},
                    ]
                }
                self.call("POST", f"/projects/{pid}/links", body, timeout=300)

            self._parallel(link, lab.point_to_point())
            t_links = time.monotonic()
            progress(f"  gns3: {len(lab.links)} links in {t_links - t_nodes:.1f}s")
            self.call("POST", f"/projects/{pid}/nodes/start", {}, timeout=timeout_s)
            self.wait_status(pid, "started", len(nodes), t0 + timeout_s)
            t_start = time.monotonic()
            progress(f"  gns3: all nodes started in {t_start - t_links:.1f}s")
        except Exception:
            self.destroy(Gns3Lab(project_id=pid, nodes=nodes), progress=lambda *_: None)
            raise
        return Gns3Lab(
            project_id=pid,
            nodes=nodes,
            timings={
                "create_nodes_s": round(t_nodes - t0, 3),
                "create_links_s": round(t_links - t_nodes, 3),
                "start_s": round(t_start - t_links, 3),
                "deploy_s": round(t_start - t0, 3),
            },
        )

    def wait_status(self, pid: str, status: str, n: int, deadline: float) -> None:
        while True:
            nodes = self.call("GET", f"/projects/{pid}/nodes", timeout=120)
            done = sum(1 for x in nodes if x.get("status") == status)
            if done >= n:
                return
            if time.monotonic() > deadline:
                raise Gns3Error(f"only {done} of {n} nodes {status} by the deadline")
            time.sleep(1.0)

    def containers(self, lab_nodes: Gns3Lab) -> dict[str, str]:
        """Lab node id -> its Docker container id in the GNS3 VM."""
        by_gns3 = {v: k for k, v in lab_nodes.nodes.items()}
        out = {}
        for n in self.call("GET", f"/projects/{lab_nodes.project_id}/nodes", timeout=120):
            cid = (n.get("properties") or {}).get("container_id")
            if cid and n["node_id"] in by_gns3:
                out[by_gns3[n["node_id"]]] = cid
        return out

    def destroy(self, lab_nodes: Gns3Lab, *, timeout_s: float = 2700, progress=print) -> float:
        t0 = time.monotonic()
        before = set(self.containers(lab_nodes).values()) if lab_nodes.nodes else set()
        pid = lab_nodes.project_id
        try:
            self.call("POST", f"/projects/{pid}/nodes/stop", {}, timeout=timeout_s)
        except Gns3Error as e:
            progress(f"  gns3: stop: {e}")
        self.call("DELETE", f"/projects/{pid}", timeout=timeout_s)
        deadline = t0 + timeout_s
        while before:
            alive = set(
                self.target.out(self.target.docker("ps", "-aq", "--no-trunc"), timeout=120).split()
            )
            before = {c for c in before if c in alive}
            if not before or time.monotonic() > deadline:
                break
            time.sleep(1.0)
        return round(time.monotonic() - t0, 3)
