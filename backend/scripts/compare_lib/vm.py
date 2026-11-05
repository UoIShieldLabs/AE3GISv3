"""Each platform's VM, controlled from the host: running?, start, stop, and
which host processes and disk files belong to it (macOS for now).

- **Docker Desktop** (AE3GIS): ``docker desktop start|stop``; after a start the
  comparison backend (compose project ``ae3gis-compare``, bench mode) is
  brought up and must answer before the platform counts as up. Its VM runs in
  Apple's Virtualization framework (``com.apple.Virtualization.VirtualMachine``);
  its other processes are Docker Desktop's own.
- **VMware Fusion** (GNS3): ``vmrun -T fusion start <vmx> nogui | stop <vmx>
  soft``; up once the GNS3 API and the VM's Docker answer. Its NAT DHCP may
  hand the VM a new address after a start, so the address comes from VMware
  Tools (``getGuestIPAddress``) every time, and the API URL and SSH target
  follow it. The VM is
  ``vmware-vmx``; the rest of Fusion (its app, services, ``vmnet-*``) are its
  helpers.

Both report time to stop and to start, so restarts are part of the record.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

from .target import Target

VMRUN = "/Applications/VMware Fusion.app/Contents/Library/vmrun"
DOCKER_RAW = "~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw"
DOCKER_SETTINGS = "~/Library/Group Containers/group.com.docker/settings-store.json"


def _pgrep(*args: str) -> list[int]:
    out = subprocess.run(["pgrep", *args], capture_output=True, text=True).stdout
    return [int(x) for x in out.split()]


def _get(url: str, timeout: float = 5) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read() or b"null")
    except (OSError, ValueError):
        return None


def _wait(ok, timeout: float, what: str, every: float = 2.0) -> float:
    t0 = time.monotonic()
    while not ok():
        if time.monotonic() - t0 > timeout:
            raise RuntimeError(f"{what} not up after {timeout:.0f}s")
        time.sleep(every)
    return round(time.monotonic() - t0, 2)


def allocated(path: Path) -> int:
    """Bytes a (sparse) file really takes on disk."""
    try:
        return path.stat().st_blocks * 512
    except OSError:
        return 0


class DockerDesktopVm:
    name = "ae3gis"

    def __init__(self, root: Path, project: str, backend_url: str) -> None:
        self.root, self.project, self.backend_url = root, project, backend_url
        self.target = Target("docker-desktop")

    def running(self) -> bool:
        return bool(_pgrep("-f", "com.apple.Virtualization.VirtualMachine")) and (
            subprocess.run(["docker", "info"], capture_output=True).returncode == 0
        )

    def compose(self, *args: str) -> None:
        env = {**os.environ, "COMPOSE_PROJECT_NAME": self.project}
        files = ["-f", "docker-compose.yml", "-f", "docker-compose.bench.yml"]
        subprocess.run(
            ["docker", "compose", *files, *args],
            cwd=self.root,
            env=env,
            check=True,
            capture_output=True,
        )

    def healthy(self) -> bool:
        h = _get(self.backend_url.rstrip("/") + "/api/v1/system/health")
        return bool(h and h.get("status") == "ok" and h.get("engine_ok"))

    def start(self, timeout: float = 600) -> float:
        t0 = time.monotonic()
        subprocess.run(
            ["docker", "desktop", "start", "--timeout", str(int(timeout))],
            check=True,
            capture_output=True,
        )
        _wait(
            lambda: subprocess.run(["docker", "info"], capture_output=True).returncode == 0,
            timeout,
            "Docker",
        )
        self.compose("up", "-d", "backend")
        _wait(self.healthy, timeout, "the AE3GIS backend")
        return round(time.monotonic() - t0, 2)

    def stop(self, timeout: float = 300) -> float:
        t0 = time.monotonic()
        subprocess.run(
            ["docker", "desktop", "stop", "--timeout", str(int(timeout))], capture_output=True
        )
        _wait(
            lambda: not _pgrep("-f", "com.apple.Virtualization.VirtualMachine"),
            timeout,
            "Docker Desktop's VM to stop",
        )
        return round(time.monotonic() - t0, 2)

    def processes(self) -> dict[str, list[int]]:
        vm = _pgrep("-f", "com.apple.Virtualization.VirtualMachine")
        helpers = [p for p in _pgrep("-f", "/Applications/Docker.app/") if p not in vm]
        return {"vm": vm, "helpers": helpers}

    def disk_bytes(self) -> int:
        return allocated(Path(DOCKER_RAW).expanduser())

    def settings(self) -> dict:
        try:
            return json.loads(Path(DOCKER_SETTINGS).expanduser().read_text())
        except (OSError, ValueError):
            return {}


class FusionVm:
    name = "gns3"

    def __init__(self, vmx: str, target: Target, user: str = "gns3", adapter=None) -> None:
        self.vmx = str(Path(vmx).expanduser())
        self.target, self.user, self.adapter = target, user, adapter
        self.ip: str | None = None
        self.api_url = ""

    def resolve(self, timeout: float = 300) -> str:
        """The VM's address now, from VMware Tools; the API URL, the SSH target
        and the GNS3 adapter follow it."""
        p = self._vmrun("getGuestIPAddress", self.vmx, "-wait", timeout=timeout)
        ip = p.stdout.strip()
        if p.returncode != 0 or not ip or " " in ip:
            raise RuntimeError(f"no address for the GNS3 VM: {p.stdout.strip()} {p.stderr.strip()}")
        self.ip, self.api_url = ip, f"http://{ip}"
        self.target.ssh = f"{self.user}@{ip}"
        if self.adapter is not None:
            self.adapter.url = self.api_url
        return ip

    def _vmrun(self, *args: str, timeout: float = 300) -> subprocess.CompletedProcess:
        return subprocess.run(
            [VMRUN, "-T", "fusion", *args], capture_output=True, text=True, timeout=timeout
        )

    def running(self) -> bool:
        return self.vmx in self._vmrun("list").stdout

    def up(self) -> bool:
        if not self.api_url or not _get(self.api_url + "/v2/version"):
            return False
        return (
            self.target.run(self.target.docker("info", "-f", "{{.ID}}"), timeout=20).returncode == 0
        )

    def start(self, timeout: float = 600) -> float:
        t0 = time.monotonic()
        p = self._vmrun("start", self.vmx, "nogui", timeout=timeout)
        if p.returncode != 0:
            raise RuntimeError(f"vmrun start: {p.stdout.strip()} {p.stderr.strip()}")
        self.resolve(timeout)
        _wait(self.up, timeout, "the GNS3 VM (API and Docker)")
        return round(time.monotonic() - t0, 2)

    def stop(self, timeout: float = 300) -> float:
        t0 = time.monotonic()
        if self.running():
            p = self._vmrun("stop", self.vmx, "soft", timeout=timeout)
            if p.returncode != 0 or self.running():
                self._vmrun("stop", self.vmx, "hard", timeout=60)
        _wait(lambda: not _pgrep("-x", "vmware-vmx"), timeout, "the GNS3 VM to stop")
        return round(time.monotonic() - t0, 2)

    def quit_app(self) -> None:
        """Fusion's app stays open after its VM stops; close it when the other
        platform is measured."""
        subprocess.run(["osascript", "-e", 'quit app "VMware Fusion"'], capture_output=True)

    def processes(self) -> dict[str, list[int]]:
        vm = _pgrep("-x", "vmware-vmx")
        helpers = _pgrep("-f", "VMware Fusion.app/|Application Support/VMware|vmnet-")
        return {"vm": vm, "helpers": [p for p in helpers if p not in vm]}

    def disk_bytes(self) -> int:
        return sum(allocated(p) for p in Path(self.vmx).parent.glob("*.vmdk"))

    def config(self) -> dict[str, str]:
        out = {}
        for line in Path(self.vmx).read_text(errors="replace").splitlines():
            k, _, v = line.partition("=")
            if k.strip() in ("numvcpus", "memsize", "guestOS"):
                out[k.strip()] = v.strip().strip('"')
        return out


def restart(vm, timeout: float = 600) -> dict[str, float]:
    return {"stop_s": vm.stop(timeout), "start_s": vm.start(timeout)}
