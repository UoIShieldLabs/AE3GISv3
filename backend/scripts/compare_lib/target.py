"""Where a platform's containers run, and how to reach its Docker.

AE3GIS's containers run in Docker Desktop's VM, reached with the local
``docker`` CLI. GNS3's run in the GNS3 VM, reached over SSH (``ssh <vm> docker
…``). Everything the runner does inside a VM goes through a ``Target``, so both
platforms are probed the same way.
"""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from typing import IO


@dataclass(frozen=True)
class Target:
    name: str
    ssh: str | None = None  # "user@host" for the GNS3 VM; None: this machine
    ssh_opts: tuple[str, ...] = ("-o", "BatchMode=yes", "-o", "ConnectTimeout=10")

    def argv(self, cmd: list[str]) -> list[str]:
        if self.ssh is None:
            return list(cmd)
        return ["ssh", *self.ssh_opts, self.ssh, shlex.join(cmd)]

    def run(
        self, cmd: list[str], *, input: bytes | None = None, timeout: float = 120
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            self.argv(cmd), input=input, capture_output=True, timeout=timeout, check=False
        )

    def out(self, cmd: list[str], *, timeout: float = 120) -> str:
        """``cmd``'s stdout; raises with its stderr when it fails."""
        p = self.run(cmd, timeout=timeout)
        if p.returncode != 0:
            raise RuntimeError(
                f"{self.name}: {shlex.join(cmd)} failed ({p.returncode}): "
                f"{p.stderr.decode(errors='replace').strip()[:400]}"
            )
        return p.stdout.decode(errors="replace")

    def popen(self, cmd: list[str], *, stdin: IO | int | None = None) -> subprocess.Popen:
        """A long-running ``cmd`` (a probe) whose stdout the runner reads."""
        return subprocess.Popen(
            self.argv(cmd),
            stdin=stdin if stdin is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def docker(self, *args: str) -> list[str]:
        return ["docker", *args]


def pids(target: Target, containers: list[str]) -> dict[str, int]:
    """Container id -> its main process's PID, in one ``docker inspect``."""
    if not containers:
        return {}
    text = target.out(
        target.docker("inspect", "-f", "{{.Id}} {{.State.Pid}}", *containers), timeout=300
    )
    out = {}
    for line in text.splitlines():
        cid, _, pid = line.partition(" ")
        if pid.strip().isdigit() and int(pid) > 0:
            out[cid] = int(pid)
    return out
