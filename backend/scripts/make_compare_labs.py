"""Write the AE3GIS vs GNS3 comparison's lab files.

    cd backend && .venv/bin/python scripts/make_compare_labs.py

One JSON file per size under ``benchmarks/compare/labs/``, the single source
both platforms deploy from:

- ``topology``: the generated plain campus (workstation hosts, one server per
  50 hosts, FRR routers, switches), which AE3GIS imports;
- ``labspec``: AE3GIS's own plan of it (nodes, images, interfaces with
  addresses, point-to-point links, boot commands), which the GNS3 adapter
  turns into Docker nodes and links;
- ``readiness``: the ping targets both platforms check before a lab counts as
  ready (every host: its gateway and a host of another subnet);
- ``flows``: per traffic pattern, every flow's client, server, address and port;
- ``pairs``: host pairs for the latency and flat-out tests, in the same LAN and
  across the core.

Deterministic: the same code writes the same bytes, so a run's recorded sha256
names the lab exactly.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
sys.path.insert(0, str(BACKEND))

from domain import selectors  # noqa: E402
from domain.export.labspec import to_labspec  # noqa: E402
from domain.generator import GeneratorParams, generate  # noqa: E402
from domain.plan import build_lab_plan  # noqa: E402
from domain.traffic.patterns import assign_ports, expand  # noqa: E402
from services.benchmark import readiness_probes  # noqa: E402

SIZES = [25, 50, 100, 200, 400, 800]
OUT = BACKEND / "benchmarks" / "compare" / "labs"
STAMP = datetime(2026, 11, 5, tzinfo=UTC)  # fixed, so files are byte-stable
PAIRS = 10
# The traffic suite's two patterns: clients -> servers (north-south through the
# routers and the core) and mesh (each host to its next two neighbours, east-west).
PATTERNS = [
    {"id": "cs", "kind": "clients_to_servers", "servers": {"subnets": ["sub-srv"], "roles": ["host"]}},
    {
        "id": "mesh",
        "kind": "mesh",
        "fanout": 2,
        "nodes": {"roles": ["host"], "subnets": [f"sub-{i}" for i in range(16)]},
    },
]


def params(hosts: int) -> GeneratorParams:
    return GeneratorParams(
        hosts=hosts,
        hosts_per_subnet=200,
        hosts_per_switch=48,
        host_type="workstation",
        server_mix=[{"type": "workstation", "per_hosts": 50}],
        name=f"campus-{hosts}",
    )


def lab(hosts: int) -> dict:
    p = params(hosts)
    topology = generate(p)
    plan = build_lab_plan(topology, f"campus{hosts}")
    index = selectors.node_index(topology)
    node_ids = [n.id for n in plan.nodes]
    readiness = [
        {"node": r["node"], "target": r["target"]}
        for r in readiness_probes(topology, {nid: 0 for nid in node_ids})
    ]

    def pick(selector):
        return selectors.resolve(topology, node_ids, selector or "all")

    flows = {}
    for pattern in PATTERNS:
        fs = expand([pattern], pick)
        assign_ports(fs)
        flows[pattern["id"]] = [
            {
                "id": f["id"],
                "client": f["client"],
                "server": f["server"],
                "server_address": index[f["server"]]["ip"],
                "port": f["port"],
            }
            for f in fs
        ]

    hosts_by_subnet: dict[str, list[str]] = {}
    for nid, info in index.items():
        if info["role"] == "host" and info["ip"]:
            hosts_by_subnet.setdefault(info["subnets"][0], []).append(nid)
    lan = next(v for k, v in hosts_by_subnet.items() if k != "sub-srv")
    servers = hosts_by_subnet.get("sub-srv") or []
    same_lan = [[lan[2 * i], lan[2 * i + 1]] for i in range(min(PAIRS, len(lan) // 2))]
    cross = [[lan[-(i + 1)], servers[i % len(servers)]] for i in range(min(PAIRS, len(lan)))]
    pair = lambda a, b: {"client": a, "server": b, "server_address": index[b]["ip"]}  # noqa: E731
    return {
        "version": 1,
        "name": p.name,
        "hosts": hosts,
        "nodes": len(plan.nodes),
        "links": len(plan.links()),
        "generator": {k: v for k, v in vars(p).items() if v is not None},
        "topology": topology,
        "labspec": to_labspec(
            plan, topology_id=p.name, topology_name=p.name, generated_at=STAMP
        ),
        "readiness": readiness,
        "flows": flows,
        "pairs": {
            "same_lan": [pair(a, b) for a, b in same_lan],
            "cross_core": [pair(a, b) for a, b in cross],
        },
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for n in SIZES:
        doc = lab(n)
        path = OUT / f"campus-{n}.json"
        path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
        print(
            f"{path.relative_to(BACKEND)}: {doc['nodes']} nodes, {doc['links']} links, "
            f"{len(doc['readiness'])} readiness pings, "
            + ", ".join(f"{k} {len(v)} flows" for k, v in doc["flows"].items())
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
