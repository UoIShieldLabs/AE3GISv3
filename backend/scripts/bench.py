"""Run one benchmark headless and keep its results.

Posts a benchmark spec (see ``benchmarks/specs/``), follows it step by step,
then saves the export (every file the benchmark recorded) and a Markdown report
in ``--out-dir``. Ctrl-C once: finish the current step and stop; twice: cancel
now (the benchmark still removes what it deployed). To run whole suites on a
host, use ``bench.sh`` / ``scripts/bench_suite.py`` (it builds on this file).

    python scripts/bench.py benchmarks/specs/baseline/idle-sweep.json \\
        [--base-url http://localhost:8000] [--token T] [--label macbook-idle] \\
        [--scale 10,25,50] [--out-dir benchmark-results]

``--attach <benchmark id>`` (no spec) follows a benchmark that is already
running, e.g. after this script was interrupted: the benchmark itself runs in
the backend and does not need it.

Run the backend without auto-reload while a benchmark runs (a reload kills
it): ``docker compose -f docker-compose.yml -f docker-compose.bench.yml up -d``.
Stdlib only (urllib), so it runs from any Python 3.11+ without the venv.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import signal
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RETRIES = 10  # ~4 minutes of backoff


class ApiError(Exception):
    """The backend answered with an error (status, and its JSON envelope)."""

    def __init__(self, method: str, path: str, status: int, detail: str) -> None:
        super().__init__(f"{method} {path}: {status} {detail}")
        self.status = status
        try:
            self.body: dict[str, Any] = json.loads(detail)
        except ValueError:
            self.body = {"detail": detail}


class Api:
    def __init__(self, base: str, token: str | None) -> None:
        self.base = base.rstrip("/") + "/api/v1"
        self.token = token

    def _req(self, method: str, path: str, body: Any = None) -> urllib.request.Request:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        return req

    def raw(self, method: str, path: str, body: Any = None) -> bytes:
        # A loaded host (hundreds of containers starting) can drop a connection
        # now and then: reads are retried for a few minutes, writes never are.
        tries = RETRIES if method == "GET" else 1
        for attempt in range(1, tries + 1):
            try:
                with urllib.request.urlopen(self._req(method, path, body), timeout=120) as res:
                    return res.read()
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode(errors="replace")
                raise ApiError(method, path, exc.code, detail) from None
            except (urllib.error.URLError, OSError) as exc:  # reset, refused, timeout
                if attempt == tries:
                    raise
                print(f"  (retrying {method} {path}: {exc})", file=sys.stderr)
                time.sleep(min(30, 2**attempt))
        raise AssertionError("unreachable")

    def call(self, method: str, path: str, body: Any = None) -> Any:
        raw = self.raw(method, path, body)
        return json.loads(raw) if raw else None

    def ping(self) -> dict[str, Any] | None:
        """The backend's health, asked once (no retries); None when it doesn't answer."""
        try:
            with urllib.request.urlopen(self._req("GET", "/system/health"), timeout=10) as res:
                return json.loads(res.read())
        except (urllib.error.URLError, OSError, ValueError):
            return None


def mb(x: float | None) -> str:
    return "–" if x is None else f"{x / 1e6:.1f}"


def num(x: float | None, digits: int = 1) -> str:
    return "–" if x is None else f"{x:.{digits}f}"


def row_line(r: dict[str, Any]) -> str:
    parts = [
        f"{r['step']:>14}",
        *([] if not r.get("case") or r["case"] in r["step"] else [r["case"]]),
        f"nodes {r.get('nodes', '–'):>5}",
        f"deploy {num(r.get('deploy_s')):>7}s",
        f"ready {num(r.get('ready_s'), 2):>6}s",
        f"destroy {num(r.get('destroy_s')):>6}s",
        f"{mb(r.get('marginal_mem_per_node')):>6} MB/node",
        f"host mem {num(r.get('hold_mem_pct_max')):>5}%",
    ]
    if r.get("delivered_ratio") is not None:
        parts.append(f"delivered {r['delivered_ratio'] * 100:.0f}%")
    parts.append(r["outcome"] + (f" ({r['detail']})" if r.get("detail") else ""))
    return "  ".join(parts)


def describe(bench: dict[str, Any]) -> str:
    """What a benchmark runs, in a few words."""
    spec = bench["spec"]
    kind = bench.get("kind") or ("adaptive" if spec.get("adaptive") else "sweep")
    if kind == "adaptive":
        return f"adaptive from {spec['adaptive']['start']} hosts"
    if kind == "census":
        cases = (spec.get("census") or {}).get("cases") or []
        return f"census of {len(cases)} cases"
    if kind == "matrix":
        return f"traffic matrix on {spec['scale'][0]} hosts"
    return f"scale {spec['scale']}"


def outcome_line(b: dict[str, Any]) -> str:
    result = b.get("result") or {}
    if result.get("census") is not None:
        usable = sum(1 for c in result["census"] if c.get("usable"))
        what = f"{usable} of {len(result['census'])} cases usable"
    elif result.get("matrix") is not None:
        ok = sum(1 for c in result["matrix"] if c.get("outcome") == "ok")
        what = f"{ok} of {len(result['matrix'])} cells passed"
    else:
        what = f"ceiling {result.get('ceiling') or '–'} hosts"
    return (
        f"{b['status']}: {what}"
        + (
            f" · stopped: {result.get('reason')} ({result.get('detail')})"
            if result.get("reason")
            else ""
        )
        + (f" · error: {b['job']['error']}" if b["job"].get("error") else "")
    )


@contextlib.contextmanager
def interruptible(api: Api, bid: str):
    """Ctrl-C once: the benchmark stops after its current step; twice: cancel now."""
    interrupts = 0

    def on_sigint(_sig, _frame) -> None:
        nonlocal interrupts
        interrupts += 1
        if interrupts == 1:
            print("\nstopping after the current step (Ctrl-C again to cancel now)…")
            api.call("POST", f"/jobs/{bid}/stop")
        else:
            print("\ncancelling…")
            api.call("POST", f"/jobs/{bid}/cancel")

    previous = signal.signal(signal.SIGINT, on_sigint)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous)


def follow(api: Api, bid: str, poll: float, out=print) -> dict[str, Any]:
    """Print each new step and phase until the benchmark ends; its final record."""
    shown = 0
    last_phase = None
    while True:
        b = api.call("GET", f"/benchmarks/{bid}")
        rows = (b.get("result") or {}).get("rows") or []
        for r in rows[shown:]:
            out(row_line(r))
            if r.get("next"):  # an adaptive sweep's choice
                out(f"  → {r['next']}")
        shown = len(rows)
        if b["current"] and b["current"] != last_phase:
            out(f"  … {b['current']}")
            last_phase = b["current"]
        if b["status"] not in ("queued", "running"):
            return b
        time.sleep(poll)


def save(api: Api, bid: str, out_dir: Path, stem: str) -> tuple[Path, Path]:
    """The benchmark's report and export as ``<stem>.md`` and ``<stem>.zip``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{stem}.zip"
    zip_path.write_bytes(api.raw("GET", f"/benchmarks/{bid}/export"))
    md_path = out_dir / f"{stem}.md"
    md_path.write_text(api.raw("GET", f"/benchmarks/{bid}/report.md").decode())
    return md_path, zip_path


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("spec", type=Path, nargs="?", help="benchmark spec (JSON)")
    ap.add_argument("--attach", metavar="ID", help="follow a running benchmark instead")
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--token")
    ap.add_argument("--label", help="overrides the spec's label")
    ap.add_argument("--scale", help="overrides the spec's scale, e.g. 10,25,50")
    ap.add_argument("--out-dir", type=Path, default=Path("benchmark-results"))
    ap.add_argument("--poll", type=float, default=5.0, help="seconds between status checks")
    args = ap.parse_args()
    # Progress as it happens, also when piped to a file or `tee`.
    sys.stdout.reconfigure(line_buffering=True)

    api = Api(args.base_url, args.token)
    try:
        if args.attach:
            bench = api.call("GET", f"/benchmarks/{args.attach}")
            spec = dict(bench["spec"])
            if args.label:
                spec["label"] = args.label
        else:
            if args.spec is None:
                ap.error("give a spec, or --attach a running benchmark")
            spec = json.loads(args.spec.read_text())
            if args.label:
                spec["label"] = args.label
            if args.scale:
                spec["scale"] = [int(x) for x in args.scale.split(",") if x.strip()]
                spec.pop("adaptive", None)  # an explicit scale list replaces a climb
            bench = api.call("POST", "/benchmarks", spec)
        bid = bench["id"]
        print(f"benchmark {bid}: {spec.get('label') or 'unnamed'} · {describe(bench)}")
        with interruptible(api, bid):
            b = follow(api, bid, args.poll)
        print("\n" + outcome_line(b))
        stamp = datetime.now(UTC).strftime("%Y-%m-%d")
        label = re.sub(r"[^A-Za-z0-9_-]+", "-", spec.get("label") or bid[:8]).strip("-")
        md_path, zip_path = save(api, bid, args.out_dir, f"{stamp}-{label}")
    except ApiError as exc:
        raise SystemExit(str(exc)) from None
    print(f"saved {md_path} and {zip_path}")
    sys.exit(0 if b["status"] == "succeeded" else 1)


if __name__ == "__main__":
    main()
