"""The committed lab files (``benchmarks/compare/labs/campus-<n>.json``)."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LABS = Path(__file__).resolve().parents[2] / "benchmarks" / "compare" / "labs"
INIT_PATH = "/ae3gis-init.sh"  # where both platforms put a node's boot commands
INIT_LOG = "/var/log/ae3gis-init.log"


def eth_index(name: str) -> int:
    m = re.fullmatch(r"eth(\d+)", name)
    if not m:
        raise ValueError(f"not an ethN interface: {name!r}")
    return int(m.group(1))


@dataclass
class Lab:
    path: Path
    doc: dict[str, Any]
    sha256: str

    @property
    def name(self) -> str:
        return self.doc["name"]

    @property
    def hosts(self) -> int:
        return self.doc["hosts"]

    @property
    def nodes(self) -> list[dict[str, Any]]:
        return self.doc["labspec"]["nodes"]

    @property
    def links(self) -> list[dict[str, Any]]:
        return self.doc["labspec"]["links"]

    @property
    def images(self) -> list[str]:
        return self.doc["labspec"]["images"]

    def adapters(self, node: dict[str, Any]) -> int:
        """Interfaces a node needs: ethN for the highest N, plus one."""
        return max((eth_index(i["name"]) for i in node["interfaces"]), default=-1) + 1

    def run(self, node: dict[str, Any]) -> list[str]:
        """The node image's own start command (entrypoint + cmd), which Kathara
        runs as the machine's main process (recorded in the lab file)."""
        info = (self.doc.get("images") or {}).get(node["image"]) or {}
        return list(info.get("run") or ["bash"])

    def init_script(self, node: dict[str, Any]) -> str:
        """The node's boot commands, as AE3GIS writes them to ``INIT_PATH``."""
        return "#!/bin/sh\n" + "\n".join(node["startup"]) + "\n" if node["startup"] else ""

    def point_to_point(self) -> list[tuple[tuple[str, int], tuple[str, int]]]:
        """Each link as ((node id, adapter), (node id, adapter))."""
        out = []
        for link in self.links:
            eps = link["endpoints"]
            if len(eps) != 2:
                raise ValueError(f"{link['collision_domain']}: {len(eps)} endpoints, not 2")
            a, b = eps
            out.append(
                ((a["node"], eth_index(a["interface"])), (b["node"], eth_index(b["interface"])))
            )
        return out


def load(hosts: int | str) -> Lab:
    path = Path(hosts) if str(hosts).endswith(".json") else LABS / f"campus-{hosts}.json"
    raw = path.read_bytes()
    return Lab(path=path, doc=json.loads(raw), sha256=hashlib.sha256(raw).hexdigest())
