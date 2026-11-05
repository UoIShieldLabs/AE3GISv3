#!/usr/bin/env python3
"""AE3GIS vs GNS3 comparison runner (see docs/benchmarks/COMPARE.md).

    python3 backend/scripts/compare.py proto --platform gns3 --lab 25 \\
        --gns3-url http://<vm> --ssh gns3@<vm> --image <tools image>
    python3 backend/scripts/compare.py proto --platform ae3gis --lab 25 --image <tools image>

``proto`` is the Phase 0 check of one platform. It deploys a lab, then checks
that every node has a container, that addresses, routes and bridges are set,
that every readiness ping passes, and that the monitor sees the lab and the
platform's own processes. It records each node role's main process, for parity,
then tears the lab down, and writes a JSON report.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compare_lib import labs as labs_mod  # noqa: E402
from compare_lib import probes  # noqa: E402
from compare_lib.ae3gis import Ae3gis  # noqa: E402
from compare_lib.gns3 import Gns3  # noqa: E402
from compare_lib.target import Target, pids  # noqa: E402


def adapter(args):
    if args.platform == "gns3":
        if not (args.gns3_url and args.ssh):
            sys.exit("gns3 needs --gns3-url and --ssh")
        target = Target("gns3-vm", ssh=args.ssh)
        idle = args.idle.split() if args.idle else None
        extra = json.loads(args.gns3_props) if args.gns3_props else None
        return target, Gns3(
            args.gns3_url,
            target,
            concurrency=args.concurrency,
            idle=idle,
            extra_properties=extra,
            bulk=args.bulk,
        )
    target = Target("docker-desktop")
    return target, Ae3gis(args.ae3gis_url, target)


def inspect_node(target: Target, cid: str) -> dict:
    def run(*cmd: str) -> str:
        p = target.run(target.docker("exec", cid, *cmd), timeout=60)
        return (p.stdout or p.stderr).decode(errors="replace").strip()

    top = target.run(target.docker("top", cid, "-o", "pid,rss,comm,args"), timeout=60)
    return {
        "top": top.stdout.decode(errors="replace").strip().splitlines(),
        "addr": run("ip", "-br", "addr").splitlines(),
        "route": run("ip", "route").splitlines(),
        "bridge": run("sh", "-c", "ip -br link show type bridge 2>/dev/null || true").splitlines(),
        "init_log": run("sh", "-c", f"cat {labs_mod.INIT_LOG} 2>/dev/null | tail -5").splitlines(),
        "config": json.loads(
            target.out(target.docker("inspect", "-f", "{{json .Config}}", cid)) or "{}"
        ),
    }


def cmd_proto(args) -> int:
    lab = labs_mod.load(args.lab)
    target, plat = adapter(args)
    report: dict = {
        "platform": args.platform,
        "lab": lab.name,
        "lab_sha256": lab.sha256,
        "t": time.time(),
    }
    report["version"] = plat.version()
    print(f"{args.platform}: {json.dumps(report['version'])[:160]}")
    t0 = time.monotonic()
    deployed = plat.deploy(lab)
    report["deploy"] = {**deployed.timings, "wall_s": round(time.monotonic() - t0, 3)}
    report["retried"] = list(getattr(plat, "retried", []))
    try:
        containers = plat.containers(deployed)
        report["containers"] = {"expected": len(lab.nodes), "found": len(containers)}
        node_pids = {
            nid: p for nid, p in ((n, pids(target, [c]).get(c)) for n, c in containers.items()) if p
        }
        report["pids"] = len(node_pids)
        by_role = {}
        for node in lab.nodes:
            by_role.setdefault(node["role"], node)
        report["nodes"] = {
            role: {"id": n["id"], "image": n["image"], **inspect_node(target, containers[n["id"]])}
            for role, n in by_role.items()
            if n["id"] in containers
        }
        t1 = time.monotonic()
        report["ready"] = probes.readiness(
            target,
            args.image,
            lab.doc["readiness"],
            node_pids,
            security_opt=args.security_opt,
            timeout_s=args.ready_timeout,
        )
        report["ready"]["wall_s"] = round(time.monotonic() - t1, 3)
        print(f"  ready: {report['ready']}")
        mon = probes.Monitor(target, args.image, interval=2.0)
        mon.start()
        try:
            mon.wait_first()
            time.sleep(6)
        finally:
            mon.stop()
        last = mon.lines[-1] if mon.lines else {}
        seen = set((last.get("c") or {}).keys())
        report["monitor"] = {
            "sweeps": len(mon.lines),
            "containers_seen": len(seen),
            "lab_containers_seen": sum(1 for c in containers.values() if c[:12] in seen),
            "infra": last.get("infra"),
            "host_mem": (last.get("host") or {}).get("mem"),
            "ncpu": last.get("ncpu"),
            "sweep_ms": last.get("sweep_ms"),
        }
        print(f"  monitor: {json.dumps(report['monitor'])[:300]}")
    finally:
        if args.keep:
            print(f"  kept the lab up: {deployed}")
        else:
            report["destroy_s"] = plat.destroy(deployed)
            report["destroy"] = {
                k: v for k, v in deployed.timings.items() if k not in report["deploy"]
            }
            print(f"  destroyed in {report['destroy_s']}s")
    report["retried"] = list(getattr(plat, "retried", []))
    out = Path(args.out) if args.out else Path(f"proto-{args.platform}-{lab.name}.json")
    out.write_text(json.dumps(report, indent=1, default=str))
    print(f"report: {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("proto", help="Phase 0: deploy one lab on one platform and check it")
    p.add_argument("--platform", choices=["ae3gis", "gns3"], required=True)
    p.add_argument("--lab", default="25", help="lab size (campus-<n>.json) or a path")
    p.add_argument("--image", required=True, help="the tools image (probes)")
    p.add_argument("--ae3gis-url", default="http://localhost:8000")
    p.add_argument(
        "--gns3-url", help="the GNS3 VM's API, e.g. http://<vm> (port 80 in the GNS3 VM)"
    )
    p.add_argument("--ssh", help="user@host of the GNS3 VM")
    p.add_argument("--concurrency", type=int, default=8, help="GNS3's parallel API calls")
    p.add_argument("--bulk", action="store_true", help="GNS3's own bulk start/stop (3 at a time)")
    p.add_argument(
        "--idle",
        help="override the process GNS3 nodes exec into (default: the image's own start command)",
    )
    p.add_argument("--gns3-props", help="extra Docker node properties (JSON)")
    p.add_argument("--security-opt", action="append", default=[])
    p.add_argument("--ready-timeout", type=float, default=300)
    p.add_argument("--keep", action="store_true", help="leave the lab up to look at it")
    p.add_argument("--out")
    args = ap.parse_args(argv)
    return {"proto": cmd_proto}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
