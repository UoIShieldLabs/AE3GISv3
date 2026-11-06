"""The experiments, identical on both platforms (docs/benchmarks/COMPARE.md).

**A step** (E1, one lab size): restart the platform's VM → raise the ARP
limits → start the monitor (in the VM) and the host sampler → wait for a
quiet VM → 30 s reference → **deploy** (capped) → **network ready** (every
readiness ping answers, capped) → settle 30 s → **hold** 60 s → **teardown**
(until the lab's containers are gone) → 30 s after. Each phase is a window
of the monitor's sweeps and the host's samples.

**E0:** the platform at rest after a restart, no lab.

**E2:** one lab (100 hosts) after a restart: idle ping RTTs, one flat-out TCP
flow, then the load ladder: per pattern and protocol, every flow at a constant
rate, stepping up until delivery falls under ``min_delivered`` or UDP loss
passes ``max_loss``; the last pass and the first failure run again.

**E3:** an E1 step whose hold waits first until the VM's CPU stays quiet
(``quiet_cpu_share`` for ``quiet_for_s``, at most ``max_wait_s``), so the
hold shows a lab at rest once the deploy's aftermath is over (on Docker
Desktop, its UI re-listing the containers can keep the daemon busy for
minutes after a big deploy).

Every result is one JSON file; a file that exists is a step already done, so
a run resumes where it stopped.
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import hostsample, metrics, probes, traffic
from . import labs as labs_mod
from .target import Target, pids


@dataclass
class Platform:
    name: str  # ae3gis | gns3
    vm: Any  # vm.DockerDesktopVm | vm.FusionVm
    adapter: Any  # ae3gis.Ae3gis | gns3.Gns3
    target: Target
    security_opt: list[str] = field(default_factory=list)


class StepFailed(RuntimeError):
    pass


def rate_bps(rate: str) -> float:
    mult = {"K": 1e3, "M": 1e6, "G": 1e9}
    return float(rate[:-1]) * mult[rate[-1]] if rate[-1] in mult else float(rate)


def write_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, indent=1, default=str), newline="\n")
    os.replace(tmp, path)


class Runner:
    def __init__(
        self,
        plan: dict,
        platforms: dict[str, Platform],
        image: str,
        out: Path,
        log=print,
    ) -> None:
        self.plan, self.platforms, self.image, self.out = plan, platforms, image, out
        self.log = log
        self.current: Platform | None = None

    # ── the platform in use ──

    def use(self, p: Platform) -> None:
        """Make ``p`` the only platform running."""
        for other in self.platforms.values():
            if other is not p and other.vm.running():
                self.log(f"stopping {other.name}'s VM")
                other.vm.stop()
            if other is not p and hasattr(other.vm, "quit_app"):
                other.vm.quit_app()
        if not p.vm.running():
            self.log(f"starting {p.name}'s VM")
            p.vm.start()
        elif hasattr(p.vm, "resolve"):
            p.vm.resolve()
        self.current = p

    def vm_info(self, p: Platform, lab: labs_mod.Lab | None = None) -> dict:
        fmt = (
            '{"docker":"{{.ServerVersion}}","kernel":"{{.KernelVersion}}","os":"{{.OperatingSystem}}",'
            '"ncpu":{{.NCPU}},"mem":{{.MemTotal}},"cgroup":"{{.CgroupVersion}}",'
            '"driver":"{{.Driver}}"}'
        )
        info = json.loads(p.target.out(p.target.docker("info", "-f", fmt), timeout=60))
        info["platform"] = p.adapter.version()
        info["vm_disk_bytes"] = p.vm.disk_bytes()
        if lab is not None:
            info["images"] = self.check_images(p, lab)
        return info

    def check_images(self, p: Platform, lab: labs_mod.Lab) -> dict:
        want = {ref: v["digest"] for ref, v in (lab.doc.get("images") or {}).items()}
        got = {}
        for ref, digest in want.items():
            res = p.target.run(
                p.target.docker("image", "inspect", "-f", "{{json .RepoDigests}}", ref), timeout=60
            )
            digests = json.loads(res.stdout or b"[]") if res.returncode == 0 else []
            if not any(d.endswith("@" + digest) for d in digests):
                raise StepFailed(f"{p.name}: {ref} is not {digest} (have {digests})")
            got[ref] = digest
        probe = p.target.out(p.target.docker("image", "inspect", "-f", "{{.Id}}", self.image))
        return {"lab": got, "probe": probe.strip()}

    def sysctls(self, p: Platform) -> dict:
        want = self.plan.get("sysctls") or {}
        if not want:
            return {}
        sets = " ".join(f"{k}={v}" for k, v in want.items())
        script = f"sysctl -q -w {sets} && sysctl {' '.join(want)}"
        root_sh = getattr(p.vm, "root_netns_sh", None)
        argv = root_sh(script) if root_sh else None
        if argv:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                raise RuntimeError(f"{p.name}: sysctls failed: {r.stderr.strip()[:400]}")
            out = r.stdout
        else:
            out = p.target.out(
                p.target.docker(
                    "run",
                    "--rm",
                    "--privileged",
                    "--network",
                    "host",
                    self.image,
                    "sh",
                    "-c",
                    script,
                ),
                timeout=120,
            )
        return dict(line.split(" = ", 1) for line in out.splitlines() if " = " in line)

    # ── probes for one window ──

    def watch(self, p: Platform) -> tuple[probes.Monitor, Any]:
        mon = probes.Monitor(p.target, self.image, interval=self.plan["monitor_interval_s"])
        mon.start()
        hs = hostsample.sampler(p.vm.processes(), interval=self.plan["monitor_interval_s"])
        hs.start()
        mon.wait_first(timeout=120)
        return mon, hs

    def quiet(self, mon: probes.Monitor, share: float, max_s: float, sweeps: int = 3) -> float:
        """Wait until the VM's CPU stays under ``share`` for ``sweeps`` sweeps."""
        t0 = time.monotonic()
        while time.monotonic() - t0 < max_s:
            cpu = metrics.vm_cpu(mon.lines[-(sweeps + 1) :])
            if len(cpu) >= sweeps and all(c[1] < share for c in cpu):
                break
            time.sleep(1)
        return round(time.monotonic() - t0, 1)

    @staticmethod
    def offset(mon: probes.Monitor) -> float:
        """Runner clock minus the VM's clock."""
        return statistics.median(x["rt"] - x["t"] for x in mon.lines) if mon.lines else 0.0

    def summarize(self, mon: probes.Monitor, hs, phases: dict, lab_ids: set[str]) -> dict:
        return {
            name: {
                "t": [t0, t1],
                "vm": metrics.monitor_window(mon.window(t0, t1), lab_ids),
                "host": metrics.host_window(hs.window(t0, t1)),
            }
            for name, (t0, t1) in phases.items()
        }

    def roles_at(self, mon, t0, t1, lab: labs_mod.Lab, containers: dict[str, str]) -> dict:
        """Mean memory per node of each role over a window (the hold)."""
        by_role: dict[str, list[str]] = {}
        for n in lab.nodes:
            if n["id"] in containers:
                by_role.setdefault(n["role"], []).append(containers[n["id"]][:12])
        lines = mon.window(t0, t1)
        out = {}
        for role, ids in by_role.items():
            per = [
                metrics._container_mem(x["c"][c])
                for x in lines
                for c in ids
                if c in (x.get("c") or {})
            ]
            out[role] = {
                "nodes": len(ids),
                "mem_per_node": round(statistics.fmean(per)) if per else None,
            }
        return out

    # ── E0 ──

    def e0(self, p: Platform, rep: int) -> dict:
        cfg = self.plan["e0"]
        rec: dict[str, Any] = {"exp": "e0", "platform": p.name, "rep": rep, "started": time.time()}
        rec["restart"] = restart_vm(p)
        rec["sysctls"] = self.sysctls(p)
        rec["vm"] = self.vm_info(p)
        mon, hs = self.watch(p)
        try:
            t0 = time.time()
            self.log(f"  e0: {cfg['idle_s']} s at rest")
            time.sleep(cfg["idle_s"])
            t1 = time.time()
        finally:
            mon.stop()
            hs.stop()
        phases = {"idle": (t0, t1), "settled": (t1 - min(180, cfg["idle_s"]), t1)}
        rec["phases"] = self.summarize(mon, hs, phases, set())
        rec["series"] = metrics.series(mon.lines, hs.samples, set(), self.offset(mon))
        rec["status"] = "ok"
        return rec

    # ── E1 ──

    def e1(self, p: Platform, size: int, rep: int, long_hold: dict | None = None) -> dict:
        """One E1 step, or with ``long_hold`` (the plan's ``e3``) an E3 step."""
        cfg = self.plan["step"]
        lab = labs_mod.load(size)
        rec: dict[str, Any] = {
            "exp": "e3" if long_hold else "e1",
            "platform": p.name,
            "size": size,
            "rep": rep,
            "lab": lab.name,
            "lab_sha256": lab.sha256,
            "nodes": len(lab.nodes),
            "started": time.time(),
        }
        if long_hold:
            rec["long_hold"] = dict(long_hold)
        rec["restart"] = restart_vm(p)
        rec["sysctls"] = self.sysctls(p)
        rec["vm"] = self.vm_info(p, lab)
        mon, hs = self.watch(p)
        phases: dict[str, tuple[float, float]] = {}
        deployed = None
        containers: dict[str, str] = {}
        try:
            rec["quiet_s"] = self.quiet(mon, cfg["quiet_cpu_share"], cfg["quiet_max_s"])
            t = time.time()
            time.sleep(cfg["reference_s"])
            phases["reference"] = (t, time.time())
            rec["disk_before"] = p.vm.disk_bytes()

            t = time.time()
            self.log(f"  e1: deploying {lab.name} ({len(lab.nodes)} nodes)")
            try:
                deployed = p.adapter.deploy(lab, timeout_s=cfg["deploy_cap_s"], progress=self.log)
            except Exception as e:  # noqa: BLE001 - a failed or capped deploy is a result
                phases["deploy"] = (t, time.time())
                capped = time.time() - t >= cfg["deploy_cap_s"]
                rec["status"] = "capped" if capped else "failed"
                rec["error"] = str(e)[:2000]
                self.log(f"  e1: deploy {rec['status']}: {str(e)[:200]}")
                return self._finish(rec, mon, hs, phases, set())
            phases["deploy"] = (t, time.time())
            rec["deploy"] = dict(deployed.timings)
            containers = p.adapter.containers(deployed)
            node_pids = {
                n: q
                for n, q in ((n, pids(p.target, [c]).get(c)) for n, c in containers.items())
                if q
            }
            rec["containers"] = {
                "expected": len(lab.nodes),
                "found": len(containers),
                "pids": len(node_pids),
            }

            t = time.time()
            rec["ready"] = probes.readiness(
                p.target,
                self.image,
                lab.doc["readiness"],
                node_pids,
                timeout_s=cfg["ready_cap_s"],
                security_opt=p.security_opt,
            )
            rec["ready"]["failed_probes"] = rec["ready"]["failed_probes"][:50]
            phases["ready"] = (t, time.time())
            ok = rec["ready"]["failed"] == 0 and not rec["ready"]["missing"]
            self.log(
                f"  e1: ready {rec['ready']['ok']}/{rec['ready']['ok'] + rec['ready']['failed']} "
                f"in {phases['ready'][1] - phases['ready'][0]:.1f}s"
            )

            t = time.time()
            time.sleep(cfg["settle_s"])
            phases["settle"] = (t, time.time())
            if long_hold:
                t = time.time()
                waited = self.quiet(
                    mon,
                    long_hold["quiet_cpu_share"],
                    long_hold["max_wait_s"],
                    sweeps=max(
                        3, round(long_hold["quiet_for_s"] / self.plan["monitor_interval_s"])
                    ),
                )
                phases["wait"] = (t, time.time())
                rec["quiet_capped"] = waited >= long_hold["max_wait_s"]
                rec["quiet_after_deploy_s"] = round(time.time() - phases["deploy"][1], 1)
                self.log(
                    f"  e3: quiet {rec['quiet_after_deploy_s']:.0f}s after the deploy"
                    + (" (capped)" if rec["quiet_capped"] else "")
                )
            t = time.time()
            time.sleep(long_hold["hold_s"] if long_hold else cfg["hold_s"])
            phases["hold"] = (t, time.time())
            rec["disk_hold"] = p.vm.disk_bytes()
            rec["roles"] = self.roles_at(mon, *phases["hold"], lab, containers)
            rec["status"] = "ok" if ok else "not_ready"
        finally:
            if deployed is not None:
                t = time.time()
                rec["destroy_s"] = p.adapter.destroy(deployed, progress=self.log)
                phases["teardown"] = (t, time.time())
                rec["destroy"] = {
                    k: v for k, v in deployed.timings.items() if k not in (rec.get("deploy") or {})
                }
                self.log(f"  e1: torn down in {rec['destroy_s']}s")
        t = time.time()
        time.sleep(cfg["after_s"])
        phases["after"] = (t, time.time())
        rec["disk_after"] = p.vm.disk_bytes()
        return self._finish(rec, mon, hs, phases, {c[:12] for c in containers.values()})

    def _finish(self, rec, mon, hs, phases, lab_ids) -> dict:
        mon.stop()
        hs.stop()
        rec["phases"] = self.summarize(mon, hs, phases, lab_ids)
        rec["series"] = metrics.series(mon.lines, hs.samples, lab_ids, self.offset(mon))
        rec["retried"] = list(getattr(self.current.adapter, "retried", []) if self.current else [])
        rec["ended"] = time.time()
        return rec

    # ── E2 ──

    def e2(self, p: Platform) -> dict:
        cfg, step = self.plan["e2"], self.plan["step"]
        lab = labs_mod.load(cfg["lab"])
        rec: dict[str, Any] = {
            "exp": "e2",
            "platform": p.name,
            "lab": lab.name,
            "lab_sha256": lab.sha256,
            "started": time.time(),
        }
        rec["restart"] = restart_vm(p)
        rec["sysctls"] = self.sysctls(p)
        rec["vm"] = self.vm_info(p, lab)
        mon, hs = self.watch(p)
        deployed = None
        try:
            rec["quiet_s"] = self.quiet(mon, step["quiet_cpu_share"], step["quiet_max_s"])
            t = time.time()
            time.sleep(step["reference_s"])
            ref = (t, time.time())
            deployed = p.adapter.deploy(lab, timeout_s=step["deploy_cap_s"], progress=self.log)
            containers = p.adapter.containers(deployed)
            node_pids = {
                n: q
                for n, q in ((n, pids(p.target, [c]).get(c)) for n, c in containers.items())
                if q
            }
            rec["ready"] = probes.readiness(
                p.target,
                self.image,
                lab.doc["readiness"],
                node_pids,
                timeout_s=step["ready_cap_s"],
                security_opt=p.security_opt,
            )
            if rec["ready"]["failed"]:
                raise StepFailed(f"not ready: {rec['ready']['failed_probes'][:5]}")
            time.sleep(step["settle_s"])
            lab_ids = {c[:12] for c in containers.values()}
            rec["reference"] = self.summarize(mon, hs, {"reference": ref}, lab_ids)["reference"]
            offset = self.offset(mon)
            run = lambda spec, timeout=900: probes.driver(  # noqa: E731
                p.target, self.image, spec, security_opt=p.security_opt, timeout=timeout
            )

            # a) latency
            pc = cfg["ping"]
            rec["latency"] = {}
            for kind, pairs in lab.doc["pairs"].items():
                ev = run(traffic.ping_spec(pairs, node_pids, pc["count"], pc["interval_s"]))
                rec["latency"][kind] = traffic.ping_summary(ev, pc["count"])
                self.log(f"  e2: ping {kind}: {rec['latency'][kind]}")

            # b) flat-out
            fo = cfg["flatout"]
            rec["flatout"] = []
            for kind, pairs in lab.doc["pairs"].items():
                pair = pairs[0]
                flow = [{**pair, "id": f"flat-{kind}", "port": 5201}]
                for trial in range(fo["trials"]):
                    self.quiet(mon, step["quiet_cpu_share"], 60)
                    time.sleep(fo["between_s"])
                    ev = run(
                        traffic.iperf_spec(
                            flow, node_pids, protocol="tcp", rate=None, duration_s=fo["duration_s"]
                        )
                    )
                    s = traffic.load_summary(
                        ev, n_flows=1, rate_bps=None, window_s=fo["duration_s"] - 1
                    )
                    s.update(kind=kind, trial=trial, **self._cpu(mon, hs, s, offset, lab_ids))
                    rec["flatout"].append(s)
                    self.log(
                        f"  e2: flat-out {kind} #{trial}: {s.get('delivered_bps', 0) / 1e9:.2f} Gb/s"
                    )

            # c) the load ladder
            rec["ladder"] = self.ladder(p, lab, node_pids, mon, hs, offset, lab_ids, run)
            rec["status"] = "ok"
        except Exception as e:  # noqa: BLE001 - recorded, then torn down
            rec["status"] = "failed"
            rec["error"] = str(e)[:2000]
            self.log(f"  e2: failed: {str(e)[:300]}")
        finally:
            if deployed is not None:
                rec["destroy_s"] = p.adapter.destroy(deployed, progress=self.log)
            mon.stop()
            hs.stop()
        rec["series"] = metrics.series(mon.lines, hs.samples, set(), self.offset(mon))
        rec["ended"] = time.time()
        return rec

    def _cpu(self, mon, hs, summary: dict, offset: float, lab_ids: set[str]) -> dict:
        """The VM's and the host's CPU over a traffic window (VM clock)."""
        w = summary.get("window")
        if not w:
            return {}
        lines = [x for x in mon.lines if w[0] <= x["t"] <= w[1]]
        host = hs.window(w[0] + offset, w[1] + offset)
        return {"vm": metrics.monitor_window(lines, lab_ids), "host": metrics.host_window(host)}

    def ladder(self, p, lab, node_pids, mon, hs, offset, lab_ids, run) -> list[dict]:
        cfg, step = self.plan["e2"]["ladder"], self.plan["step"]
        out = []

        def one(pattern: str, proto: str, rate: str, repeat: bool = False) -> dict:
            self.quiet(mon, step["quiet_cpu_share"], step["quiet_max_s"])
            time.sleep(cfg["between_s"])
            flows = lab.doc["flows"][pattern]
            spec = traffic.iperf_spec(
                flows, node_pids, protocol=proto, rate=rate, duration_s=cfg["window_s"] + 5
            )
            ev = run(spec, timeout=cfg["window_s"] + 600)
            s = traffic.load_summary(
                ev, n_flows=len(flows), rate_bps=rate_bps(rate), window_s=cfg["window_s"]
            )
            passed = (s.get("delivered_ratio") or 0) >= cfg["min_delivered"] and (
                proto != "udp" or (s.get("loss") is not None and s["loss"] <= cfg["max_loss"])
            )
            s.update(
                pattern=pattern,
                protocol=proto,
                rate=rate,
                repeat=repeat,
                passed=passed,
                **self._cpu(mon, hs, s, offset, lab_ids),
            )
            self.log(
                f"  e2: {pattern}/{proto} {rate}: delivered {s.get('delivered_ratio')} "
                f"loss {s.get('loss')} -> {'pass' if passed else 'FAIL'}"
            )
            out.append(s)
            return s

        for pattern in cfg["patterns"]:
            for proto in cfg["protocols"]:
                last_pass = None
                for rate in cfg["rates"]:
                    if one(pattern, proto, rate)["passed"]:
                        last_pass = rate
                        continue
                    if last_pass:  # the edge, once more each
                        one(pattern, proto, last_pass, repeat=True)
                    one(pattern, proto, rate, repeat=True)
                    break
        return out

    # ── the whole run ──

    def path(self, p: Platform, name: str) -> Path:
        return self.out / p.name / f"{name}.json"

    def step(self, p: Platform, name: str, fn, *args) -> dict:
        path = self.path(p, name)
        if path.exists():
            self.log(f"{p.name} {name}: done before, skipped")
            return json.loads(path.read_text())
        self.use(p)
        if hasattr(p.adapter, "retried"):
            p.adapter.retried.clear()
        self.log(f"{p.name} {name}: start")
        t0 = time.monotonic()
        try:
            rec = fn(p, *args)
        except Exception as e:  # noqa: BLE001 - a broken step is recorded, the run goes on
            rec = {
                "exp": name.split("-")[0],
                "platform": p.name,
                "status": "error",
                "error": f"{type(e).__name__}: {str(e)[:2000]}",
            }
            self.log(f"{p.name} {name}: ERROR {rec['error'][:300]}")
        rec["wall_s"] = round(time.monotonic() - t0, 1)
        write_json(path, rec)
        self.log(f"{p.name} {name}: {rec.get('status')} in {rec['wall_s']:.0f}s")
        return rec

    def run(self, order: list[str], only: set[str] | None = None) -> None:
        e1 = self.plan["e1"]
        want = only or {"e0", "e1", "e2", "e3"}
        for rep in range(1, e1["reps"] + 1):
            names = order if rep % 2 == 1 else list(reversed(order))
            for name in names:
                p = self.platforms[name]
                if "e0" in want:
                    self.step(p, f"e0-r{rep}", self.e0, rep)
                if "e1" not in want:
                    continue
                stopped = None
                for size in [*e1["sizes"], e1.get("extra_size")]:
                    if size is None:
                        continue
                    label = f"e1-h{size}-r{rep}"
                    if stopped or (size == e1.get("extra_size") and not self.extra_fits(p, rep)):
                        if not self.path(p, label).exists():
                            why = stopped or "the projected memory does not fit"
                            write_json(
                                self.path(p, label),
                                {
                                    "exp": "e1",
                                    "platform": p.name,
                                    "size": size,
                                    "rep": rep,
                                    "status": "skipped",
                                    "reason": why,
                                },
                            )
                            self.log(f"{p.name} {label}: skipped ({why})")
                        continue
                    rec = self.step(p, label, self.e1, size, rep)
                    if rec.get("status") != "ok":
                        stopped = f"h{size} was {rec.get('status')}"
        if "e2" in want:
            for name in order:
                self.step(self.platforms[name], "e2", self.e2)
        e3 = self.plan.get("e3")
        if "e3" in want and e3:
            for size in e3["sizes"]:
                for name in order:
                    self.step(self.platforms[name], f"e3-h{size}-r1", self.e1, size, 1, e3)

    def extra_fits(self, p: Platform, rep: int) -> bool:
        """The extra size runs if doubling the biggest regular size's growth in
        VM memory (hold minus reference) stays under the share of the VM's memory."""
        e1 = self.plan["e1"]
        path = self.path(p, f"e1-h{max(e1['sizes'])}-r{rep}")
        if not path.exists():
            return False
        rec = json.loads(path.read_text())
        try:
            ref = rec["phases"]["reference"]["vm"]["mem_used"]
            hold = rec["phases"]["hold"]["vm"]["mem_used"]
            total = rec["phases"]["hold"]["vm"]["mem_total"]
        except (KeyError, TypeError):
            return False
        factor = e1["extra_size"] / max(e1["sizes"])
        projected = ref + factor * (hold - ref)
        return projected <= e1["extra_max_mem_share"] * total


def restart_vm(p: Platform) -> dict:
    out = {"stop_s": p.vm.stop(), "start_s": p.vm.start()}
    clear = getattr(p.adapter, "clear_leftovers", None)
    if clear:  # after the timed start; the step's quiet wait follows
        out["leftovers"] = clear()
    return out
