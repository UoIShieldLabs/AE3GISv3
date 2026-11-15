"""The live lab view (pure): which links carry traffic and what runs in each node.

Both come from the collector's ``--procs`` sweeps (``domain.monitor.Sweep``):
interface counters turn into a per-connection packet rate, the process lists
into "what was started in this node since the lab came up".

A link *carries traffic* once both directions together pass ``ON_PPS`` in
``ON_SWEEPS`` sweeps within ``WINDOW_S`` (a lone ARP exchange is two packets in
one second and nothing after; an HMI polling its RTU every two seconds is a
burst every other sweep), and stops ``OFF_AFTER_S`` after the rate last reached
``OFF_PPS``, so it neither flashes nor flickers. Its direction is where most of
the bytes go, relative to the connection's ``from`` → ``to``.

A node's processes are those started after the lab finished deploying, without
AE3GIS's own terminal shells and without the children of a process already
listed. What a service of the node keeps respawning on its own does not count
(see ``ProcessTracker``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from domain.topology import interfaces_of, iter_containers
from engine.base import IfaceCounters

ON_PPS = 1.5
ON_SWEEPS = 2
WINDOW_S = 5.0
OFF_PPS = 1.0
# Long enough to bridge the gaps of anything that sends at least every WINDOW_S.
OFF_AFTER_S = 5.0
# One direction carries this many times the other's bytes → the link "flows" that way.
DIRECTION_RATIO = 3.0
# Processes started this long after the deploy finished count as started by someone.
DEPLOY_GRACE_S = 3.0
SEEN_SWEEPS = 2
# A child of one of the container's own processes shows once it lived this long.
SETTLED_S = 10.0
MAX_PROCESSES = 12

# The interactive shells a terminal tab runs (``engine/terminal.py``): idle, they
# are not "something running in the node".
TERMINAL_SHELLS = frozenset({"bash -il", "ash -l", "sh -l"})
_SHELLS = frozenset({"sh", "bash", "ash", "dash"})
# Not what a command line is "about" when naming a shell script's process.
_SHELL_WORDS = frozenset(
    "while until for if then else do done in exec nohup setsid sleep cd export true false "
    "wait trap set sh bash ash".split()
)

Counters = dict[str, dict[str, IfaceCounters]]  # node id -> interface -> counters


# ── links ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LinkRate:
    """One connection's traffic, ``fwd`` = from its ``from`` node to its ``to`` node."""

    fwd_pps: float
    rev_pps: float
    fwd_bps: float
    rev_bps: float

    @property
    def pps(self) -> float:
        return self.fwd_pps + self.rev_pps


def keyed_links(links: list[dict[str, Any]], data: dict[str, Any]) -> list[dict[str, Any]]:
    """The deployed links under the ids the editor draws them with: a
    connection's own id, or ``leg:<device>:<subnet>`` for the attachment AE3GIS
    made for an interface leg (no connection was drawn for it). Links that
    match neither are left out."""
    member: dict[str, set[str]] = {}
    legs: dict[str, list[str]] = {}
    for _site, subnet, container in iter_containers(data):
        cid = str(container.get("id") or "")
        legs[cid] = [str(leg.get("subnetId") or "") for leg in interfaces_of(container)]
        member[cid] = {str(subnet.get("id") or ""), *legs[cid]}
    out: list[dict[str, Any]] = []
    for link in links:
        if link.get("connection_id"):
            out.append(link)
            continue
        device, peer = str(link.get("from") or ""), str(link.get("to") or "")
        into = next((sid for sid in legs.get(device, []) if sid in member.get(peer, set())), None)
        if into:
            out.append({**link, "connection_id": f"leg:{device}:{into}"})
    return out


def link_rates(
    links: list[dict[str, Any]], prev: Counters, cur: Counters, dt: float
) -> dict[str, LinkRate]:
    """Connection id → its rate between two sweeps ``dt`` seconds apart.

    Read from one endpoint's interface (its ``from`` side when that node was
    swept both times): what it sent went forward, what it received came back.
    """
    out: dict[str, LinkRate] = {}
    if dt <= 0:
        return out
    for link in links:
        cid = link.get("connection_id")
        if not cid:
            continue
        first = link.get("from")
        endpoints = sorted(link.get("endpoints") or [], key=lambda e: e.get("node") != first)
        for ep in endpoints:
            node, iface = ep.get("node"), ep.get("interface")
            a = (prev.get(node) or {}).get(iface)
            b = (cur.get(node) or {}).get(iface)
            if a is None or b is None:
                continue
            tx_p, rx_p = b.tx_packets - a.tx_packets, b.rx_packets - a.rx_packets
            tx_b, rx_b = b.tx_bytes - a.tx_bytes, b.rx_bytes - a.rx_bytes
            if min(tx_p, rx_p, tx_b, rx_b) < 0:  # counters reset (interface recreated)
                continue
            if node != first:  # read from the far end: what it received went forward
                tx_p, rx_p, tx_b, rx_b = rx_p, tx_p, rx_b, tx_b
            rate = LinkRate(tx_p / dt, rx_p / dt, tx_b * 8 / dt, rx_b * 8 / dt)
            if cid not in out or rate.pps > out[cid].pps:
                out[cid] = rate
            break
    return out


def _direction(fwd_bps: float, rev_bps: float) -> str:
    if fwd_bps > rev_bps * DIRECTION_RATIO:
        return "fwd"
    if rev_bps > fwd_bps * DIRECTION_RATIO:
        return "rev"
    return "both"


@dataclass
class _LinkState:
    hot: list[float] = field(default_factory=list)  # recent sweeps at or above ON_PPS
    active_until: float | None = None
    fwd_bps: float = 0.0  # smoothed, for a direction that doesn't flip per sweep
    rev_bps: float = 0.0


class LinkActivity:
    """Rates sweep by sweep → the connections carrying traffic and which way."""

    def __init__(self) -> None:
        self._state: dict[str, _LinkState] = {}

    def update(self, rates: dict[str, LinkRate], t: float) -> dict[str, str]:
        for cid in [c for c in self._state if c not in rates]:
            del self._state[cid]
        active: dict[str, str] = {}
        for cid, rate in rates.items():
            st = self._state.setdefault(cid, _LinkState())
            st.hot = [h for h in st.hot if t - h <= WINDOW_S]
            if rate.pps >= ON_PPS:
                st.hot.append(t)
            was_active = st.active_until is not None and t <= st.active_until
            if (rate.pps >= ON_PPS and len(st.hot) >= ON_SWEEPS) or (
                was_active and rate.pps >= OFF_PPS
            ):
                if not was_active:
                    st.fwd_bps, st.rev_bps = rate.fwd_bps, rate.rev_bps
                st.active_until = t + OFF_AFTER_S
            if st.active_until is None or t > st.active_until:
                st.active_until = None
                continue
            if rate.pps >= OFF_PPS:
                st.fwd_bps = (st.fwd_bps + rate.fwd_bps) / 2
                st.rev_bps = (st.rev_bps + rate.rev_bps) / 2
            active[cid] = _direction(st.fwd_bps, st.rev_bps)
        return active


# ── processes ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Proc:
    pid: int
    ppid: int
    name: str
    args: str
    started: float  # unix seconds
    # Started from outside the container (a terminal, a setup or background
    # command: a ``docker exec``) or by something that was. False: a child of
    # one of the container's own processes (an sshd session, a service's worker).
    via_exec: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "args": self.args}


def _script(args: str) -> str | None:
    """The script of a ``sh -c '<script>'`` command line, else None."""
    parts = args.split(None, 2)
    if len(parts) == 3 and parts[1] in ("-c", "-lc"):
        return parts[2].strip()
    return None


def display(comm: str, args: str) -> tuple[str, str]:
    """(name, args) to show for a process. A shell running a script is named
    after the first real command in it (``while sleep 2; do breaker status;
    done`` → ``breaker``) and shows the script, not the ``sh -lc`` around it."""
    script = _script(args) if comm in _SHELLS else None
    if script is None:
        return comm, args or comm
    # Shell words, then the first that names a program: not a keyword, not an
    # assignment (``FOO=1 cmd``, ``export FOO=1``), not an option or a number.
    for word in re.split(r"[\s;&|()<>`'\"]+", script):
        base = word.rsplit("/", 1)[-1]
        if not base or base in _SHELL_WORDS or "=" in word or not base[0].isalpha():
            continue
        return base, script
    return comm, script


def node_processes(
    parent: int, rows: list[list[Any]], *, btime: float, clk_tck: int, since: float
) -> list[Proc]:
    """One container's ``--procs`` item → what was started in it after ``since``
    (unix seconds), oldest first: no idle terminal shells, and only the top of
    each process tree. ``parent`` is the parent of the container's first
    process: its other children were started from outside (``docker exec``)."""
    by_pid = {int(r[0]): r for r in rows}

    def via_exec(pid: int) -> bool:
        for _ in range(64):  # up the tree, as far as the sweep saw it
            row = by_pid.get(pid)
            if row is None:
                return False
            if int(row[1]) == parent:
                return True
            pid = int(row[1])
        return False

    kept: dict[int, Proc] = {}
    for row in rows:
        pid, ppid, start, comm = int(row[0]), int(row[1]), int(row[2]), str(row[3])
        cmdline = str(row[4]) if len(row) > 4 else ""
        started = btime + start / max(clk_tck, 1)
        if started < since:
            continue
        if ppid == parent and cmdline in TERMINAL_SHELLS:
            continue
        name, args = display(comm, cmdline)
        kept[pid] = Proc(pid, ppid, name, args, started, via_exec(pid))
    tops = [p for p in kept.values() if p.ppid not in kept]
    tops.sort(key=lambda p: (p.started, p.pid))
    return tops[:MAX_PROCESSES]


@dataclass
class ProcessTracker:
    """Which of a node's processes to show, sweep by sweep.

    Shown by what they are (parent, name, command line), not by pid, so a loop's
    ``sleep 1`` is one steady entry. Something started through a ``docker exec``
    shows once it was there ``SEEN_SWEEPS`` sweeps in a row. A child of one of
    the container's own processes has to prove it is not that service's routine:
    alive for ``SETTLED_S`` and never respawned (an sshd session stays; a
    switch's own ``sleep 5`` loop never shows).
    """

    _seen: dict[tuple[str, int, str, str], int] = field(default_factory=dict)
    _pids: dict[tuple[str, int, str, str], set[int]] = field(default_factory=dict)

    def update(self, nodes: dict[str, list[Proc]], now: float) -> dict[str, list[Proc]]:
        seen: dict[tuple[str, int, str, str], int] = {}
        out: dict[str, list[Proc]] = {}
        for node, procs in nodes.items():
            shown: set[tuple[str, str]] = set()
            for p in procs:
                key = (node, p.ppid, p.name, p.args)
                seen[key] = self._seen.get(key, 0) + 1 if key not in seen else seen[key]
                if p.via_exec:
                    show = seen[key] >= SEEN_SWEEPS
                else:
                    pids = self._pids.setdefault(key, set())
                    if len(pids) < 3:
                        pids.add(p.pid)
                    show = len(pids) == 1 and now - p.started >= SETTLED_S
                if show and (p.name, p.args) not in shown:
                    shown.add((p.name, p.args))
                    out.setdefault(node, []).append(p)
        self._seen = seen
        return out


def payload(links: dict[str, str], nodes: dict[str, list[Proc]]) -> dict[str, Any]:
    """The message a subscriber gets: active links and busy nodes, nothing else."""
    return {
        "type": "pulse",
        "links": dict(sorted(links.items())),
        "nodes": {n: [p.to_dict() for p in ps] for n, ps in sorted(nodes.items()) if ps},
    }
