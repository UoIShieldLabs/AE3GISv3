#!/usr/bin/env python3
"""AE3GIS vs GNS3 comparison runner (see docs/benchmarks/COMPARE.md).

    python3 backend/scripts/compare.py check              # is this machine ready?
    python3 backend/scripts/compare.py run                # E0, E1, E2 on both; resumes
    python3 backend/scripts/compare.py run --quick --sizes 25,50 --reps 1   # a dry run
    python3 backend/scripts/compare.py smoke --platform gns3   # E2's traffic on 25 hosts
    python3 backend/scripts/compare.py images             # pinned images + probe in both VMs
    python3 backend/scripts/compare.py memcheck --platform gns3   # the host memory metric here
    python3 backend/scripts/compare.py summarize          # the latest run's tables
    python3 backend/scripts/compare.py proto --platform ae3gis --lab 25 --image <tools image>

The machine's settings come from ``backend/benchmarks/compare/compare.local.json``
(see ``host.example.json``), the experiments' from ``plan.json``; results go
to ``backend/benchmark-results/<host>/<date>-compare/<platform>/``.

``proto`` is the Phase 0 check of one platform. It deploys a lab, then checks
that every node has a container, that addresses, routes and bridges are set,
that every readiness ping passes, and that the monitor sees the lab and the
platform's own processes. It records each node role's main process, for parity,
then tears the lab down, and writes a JSON report.
"""

from __future__ import annotations

import argparse
import copy
import datetime
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compare_lib import labs as labs_mod  # noqa: E402
from compare_lib import probes  # noqa: E402
from compare_lib.ae3gis import Ae3gis  # noqa: E402
from compare_lib.gns3 import Gns3  # noqa: E402
from compare_lib.steps import Platform, Runner, write_json  # noqa: E402
from compare_lib.target import Target, pids  # noqa: E402
from compare_lib.vm import DockerDesktopVm, FusionVm, VirtualBoxVm  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
COMPARE = BACKEND / "benchmarks" / "compare"
RESULTS = BACKEND / "benchmark-results"
# --quick: every wait shortened, one ladder rate; for dry runs, never for results.
QUICK = {
    "step": {"quiet_max_s": 30, "reference_s": 5, "settle_s": 5, "hold_s": 10, "after_s": 5},
    "e0": {"idle_s": 30},
    "e2": {
        "ping": {"count": 5},
        "flatout": {"trials": 1, "duration_s": 5, "between_s": 2},
        "ladder": {"rates": ["1M"], "window_s": 10, "between_s": 3},
    },
}


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


# ── the comparison ──


def merged(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        out[k] = merged(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_config(args) -> tuple[dict, dict]:
    host = json.loads(Path(args.config).read_text())
    plan = json.loads(Path(args.plan).read_text())
    if getattr(args, "quick", False):
        plan = merged(plan, QUICK)
    if getattr(args, "sizes", None):
        plan["e1"]["sizes"] = [int(x) for x in args.sizes.split(",")]
        plan["e1"]["extra_size"] = None
    if getattr(args, "reps", None):
        plan["e1"]["reps"] = args.reps
    return host, plan


def platforms(host: dict) -> dict[str, Platform]:
    a, g = host["ae3gis"], host["gns3"]
    dd = DockerDesktopVm(ROOT, a.get("compose_project", "ae3gis-compare"), a["url"])
    # The VM's address can change on every start: FusionVm.resolve() sets it.
    gt = Target("gns3-vm", ssh=None)
    gt.ssh_opts = (*gt.ssh_opts, "-o", "StrictHostKeyChecking=accept-new")
    gns3 = Gns3("http://unresolved", gt, concurrency=int(g.get("concurrency", 16)))
    user = g.get("user", "gns3")
    if g.get("vbox"):  # VirtualBox (Windows): the VM's name in VirtualBox
        gvm = VirtualBoxVm(
            g["vbox"],
            gt,
            user=user,
            adapter=gns3,
            address=g.get("address"),
            nic=int(g.get("nic", 0)),
            api_port=int(g.get("api_port", 80)),
        )
    else:
        gvm = FusionVm(g["vmx"], gt, user=user, adapter=gns3)
    return {
        "ae3gis": Platform("ae3gis", dd, Ae3gis(a["url"], dd.target), dd.target, []),
        "gns3": Platform("gns3", gvm, gns3, gt, list(g.get("security_opt") or [])),
    }


def log(msg: str) -> None:
    print(f"{datetime.datetime.now():%H:%M:%S} {msg}", flush=True)


def checks(host: dict, plan: dict) -> list[tuple[str, bool, str]]:
    """(what, ok, detail) for this machine, before a run."""
    out = [power()]
    plats = platforms(host)
    dd, fv = plats["ae3gis"].vm, plats["gns3"].vm
    st = dd.settings()
    out.append(
        (
            "Docker Desktop: Resource Saver off",
            st.get("UseResourceSaver") is False,
            f"UseResourceSaver={st.get('UseResourceSaver')}",
        )
    )
    out.append(("Docker Desktop: Kubernetes off", not st.get("KubernetesEnabled"), ""))
    a, g = dd.resources(), fv.resources()
    where = ".wslconfig" if sys.platform == "win32" else "Docker"
    out.append(
        (
            "same CPUs",
            a["cpus"] is not None and a["cpus"] == g["cpus"],
            f"{where} {a['cpus']}, GNS3 VM {g['cpus']}",
        )
    )
    out.append(
        (
            "same memory",
            a["memory_mib"] is not None and a["memory_mib"] == g["memory_mib"],
            f"{where} {a['memory_mib']} MiB, GNS3 VM {g['memory_mib']} MiB",
        )
    )
    if sys.platform == "win32":
        others = dd.other_distros()
        out.append(("no other WSL distros running", not others, ", ".join(others)))
    sizes = [*plan["e1"]["sizes"], plan["e1"].get("extra_size"), plan["e2"]["lab"]]
    missing = [n for n in sizes if n and not (COMPARE / "labs" / f"campus-{n}.json").exists()]
    out.append(("lab files", not missing, f"missing {missing}" if missing else ""))
    gb = shutil.disk_usage(BACKEND).free / 2**30
    out.append(("host disk free > 50 GB", gb > 50, f"{gb:.0f} GB"))
    running = [p.name for p in plats.values() if p.vm.running()]
    out.append(("at most one VM running", len(running) <= 1, f"running: {running}"))
    return out


def power() -> tuple[str, bool, str]:
    if sys.platform == "darwin":
        pm = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
        return ("on AC power", "AC Power" in pm, pm.splitlines()[0] if pm else "?")
    try:
        import psutil

        b = psutil.sensors_battery()
    except ImportError:
        return ("on AC power", False, "needs psutil (pip install psutil)")
    if b is None:
        return ("on AC power", True, "no battery")
    return ("on AC power", bool(b.power_plugged), f"battery {b.percent:.0f}%")


def keep_awake():
    """Keeps the machine (and display) awake until this process exits."""
    if sys.platform == "darwin":
        return subprocess.Popen(["caffeinate", "-dimsu", "-w", str(os.getpid())])
    if sys.platform == "win32":
        import ctypes

        # ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x1 | 0x2)
    return None


def cmd_check(args) -> int:
    host, plan = load_config(args)
    bad = 0
    for what, ok, detail in checks(host, plan):
        bad += not ok
        print(f"  [{'ok' if ok else '!!'}] {what}" + (f": {detail}" if detail else ""))
    print("ready" if not bad else f"{bad} check(s) to fix")
    return 1 if bad else 0


def git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()


def cmd_run(args) -> int:
    host, plan = load_config(args)
    if not args.skip_checks:
        bad = [
            (w, d) for w, ok, d in checks(host, plan) if not ok and w != "at most one VM running"
        ]
        if bad and not args.quick:
            for w, d in bad:
                print(f"  [!!] {w}: {d}")
            print("fix these first (or --skip-checks)")
            return 1
    if args.out:
        out = Path(args.out)
    else:
        base = RESULTS / host["host"]
        prior = sorted(base.glob("*-compare" + ("-quick" if args.quick else "")))
        name = f"{datetime.date.today():%Y-%m-%d}-compare" + ("-quick" if args.quick else "")
        out = prior[-1] if (args.resume and prior) else base / name
    out.mkdir(parents=True, exist_ok=True)
    manifest = out / "manifest.json"
    if not manifest.exists():
        write_json(
            manifest,
            {
                "host": host,
                "plan": plan,
                "commit": git_commit(),
                "started": time.time(),
                "labs": {
                    p.name: labs_mod.load(p).sha256
                    for p in sorted((COMPARE / "labs").glob("*.json"))
                },
                "quick": bool(args.quick),
            },
        )
    awake = keep_awake()
    plats = platforms(host)
    order = [host.get("first", "ae3gis"), *[n for n in plats if n != host.get("first", "ae3gis")]]
    log(f"results: {out}")
    try:
        Runner(plan, plats, host["probe_image"], out, log=log).run(
            order, only=set(args.only.split(",")) if args.only else None
        )
    finally:
        if awake is not None:
            awake.terminate()
    log("run finished")
    return 0


def cmd_smoke(args) -> int:
    """E2's code path on a 25-host lab with short timings: latency, one
    flat-out flow, and every pattern and protocol at 1M for 10 s."""
    host, plan = load_config(args)
    plan = merged(merged(plan, QUICK), {"e2": {"lab": 25}})
    plats = platforms(host)
    out = Path(args.out or f"smoke-{args.platform}")
    runner = Runner(plan, plats, host["probe_image"], out, log=log)
    p = plats[args.platform]
    runner.use(p)
    rec = runner.e2(p)
    write_json(out / f"{p.name}-e2.json", rec)
    log(f"smoke: {rec.get('status')} {rec.get('error', '')}")
    return 0 if rec.get("status") == "ok" else 1


def lab_images() -> dict[str, str]:
    """{ref: digest} over every lab file."""
    out: dict[str, str] = {}
    for f in sorted((COMPARE / "labs").glob("*.json")):
        for ref, v in (labs_mod.load(f).doc.get("images") or {}).items():
            out[ref] = v["digest"]
    return out


def probe_context() -> bytes:
    """The tools image's build context as a tar (no caches), for ``docker build -``."""
    import io
    import tarfile

    buf = io.BytesIO()
    src = BACKEND / "tools" / "nettools"
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for f in sorted(src.iterdir()):
            if f.is_file():
                tar.add(f, arcname=f.name)
    return buf.getvalue()


def cmd_images(args) -> int:
    """Puts the labs' images, at their pinned digests, and the probe image in
    each platform's VM: ``docker pull <repo>@<digest>``, tagged as the lab
    files name it, and the probe built from ``backend/tools/nettools``."""
    host, plan = load_config(args)
    plats = platforms(host)
    runner = Runner(plan, plats, host["probe_image"], Path("."), log=log)
    images = lab_images()
    for name in [args.platform] if args.platform else list(plats):
        p = plats[name]
        runner.use(p)
        for ref, digest in images.items():
            pinned = f"{ref.rsplit(':', 1)[0]}@{digest}"
            log(f"{name}: {pinned}")
            p.target.out(p.target.docker("pull", "-q", pinned), timeout=1800)
            p.target.out(p.target.docker("tag", pinned, ref))
        log(f"{name}: building {host['probe_image']}")
        res = p.target.run(
            p.target.docker("build", "-q", "-t", host["probe_image"], "-"),
            input=probe_context(),
            timeout=1800,
        )
        if res.returncode != 0:
            sys.exit(f"{name}: probe build failed: {res.stderr.decode(errors='replace')[-800:]}")
        runner.check_images(p, labs_mod.load(plan["e2"]["lab"]))
        log(f"{name}: images ok")
    return 0


def cmd_memcheck(args) -> int:
    """Which host metric follows the VM's memory here? Samples the platform's
    host processes while a probe container touches ``--gib`` GiB inside its VM,
    then after it exits. The run's footprint should rise by about that much
    (and keep it: both hypervisors hold freed guest memory)."""
    from compare_lib import hostsample

    host, plan = load_config(args)
    plats = platforms(host)
    p = plats[args.platform]
    Runner(plan, plats, host["probe_image"], Path("."), log=log).use(p)
    groups = p.vm.processes()
    log(f"{p.name}: VM {groups['vm']}, {len(groups['helpers'])} helpers")
    hs = hostsample.sampler(groups, interval=2)
    hs.start()
    phases = []

    def mark(name: str) -> None:
        phases.append((time.time(), name))
        log(name)

    mark("before")
    time.sleep(10)
    mark(f"touching {args.gib} GiB")
    code = (
        f"b=bytearray({args.gib}*1024**3); b[::4096]=b'\\x01'*(len(b)//4096); "
        "import time; time.sleep(30)"
    )
    p.target.out(
        p.target.docker(
            "run", "--rm", "--network", "none", host["probe_image"], "python3", "-c", code
        ),
        timeout=300,
    )
    mark("freed")
    time.sleep(30)
    hs.stop()
    t0 = hs.samples[0]["rt"] if hs.samples else time.time()
    for smp in hs.samples:
        ph = [n for t, n in phases if t <= smp["rt"]][-1:] or ["before"]
        vm = smp["g"].get("vm", {})
        line = (
            f"{smp['rt'] - t0:5.0f}s {ph[0]:18s} footprint {vm.get('footprint', 0) / 2**30:6.2f} G"
            f"  rss {vm.get('rss', 0) / 2**30:6.2f} G"
        )
        if "private" in vm:
            line += f"  private {vm['private'] / 2**30:6.2f} G"
        if smp.get("denied"):
            line += f"  unreadable: {smp['denied']}"
        print(line)
    return 0


def cmd_summarize(args) -> int:
    """Tables for one run: ``summary.md`` and ``summary.json`` beside its steps."""
    from compare_lib import summary

    if args.out:
        out = Path(args.out)
    else:
        host = json.loads(Path(args.config).read_text())["host"]
        runs = sorted((RESULTS / host).glob("*-compare" + ("-quick" if args.quick else "")))
        if not runs:
            sys.exit(f"no runs under {RESULTS / host}")
        out = runs[-1]
    s = summary.summarize(out)
    write_json(out / "summary.json", s)
    md = summary.markdown(s)
    (out / "summary.md").write_text(md + "\n")
    print(md)
    print(f"\nwritten: {out / 'summary.md'}")
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

    def common(q):
        q.add_argument("--config", default=str(COMPARE / "compare.local.json"))
        q.add_argument("--plan", default=str(COMPARE / "plan.json"))

    q = sub.add_parser("check", help="is this machine ready for a run?")
    common(q)
    q = sub.add_parser("run", help="E0, E1 and E2 on both platforms (resumable)")
    common(q)
    q.add_argument("--quick", action="store_true", help="short waits: a dry run, not results")
    q.add_argument("--sizes", help="E1 sizes, comma-separated (no extra size)")
    q.add_argument("--reps", type=int)
    q.add_argument("--only", help="e0,e1,e2")
    q.add_argument("--resume", action="store_true", help="continue the latest run of this host")
    q.add_argument("--out")
    q.add_argument("--skip-checks", action="store_true")
    q = sub.add_parser("smoke", help="E2's traffic on a 25-host lab, short timings")
    common(q)
    q.add_argument("--platform", choices=["ae3gis", "gns3"], required=True)
    q.add_argument("--out")
    q = sub.add_parser("images", help="the pinned lab images and the probe, in each VM")
    common(q)
    q.add_argument("--platform", choices=["ae3gis", "gns3"], help="one platform (default: both)")
    q = sub.add_parser("memcheck", help="which host metric follows a VM's memory")
    common(q)
    q.add_argument("--platform", choices=["ae3gis", "gns3"], required=True)
    q.add_argument("--gib", type=int, default=2)
    q = sub.add_parser("summarize", help="one run's tables (summary.md, summary.json)")
    common(q)
    q.add_argument("--out", help="the run's directory (default: this host's latest run)")
    q.add_argument("--quick", action="store_true", help="the latest quick run")
    args = ap.parse_args(argv)
    cmds = {
        "proto": cmd_proto,
        "check": cmd_check,
        "run": cmd_run,
        "smoke": cmd_smoke,
        "images": cmd_images,
        "memcheck": cmd_memcheck,
        "summarize": cmd_summarize,
    }
    return cmds[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
