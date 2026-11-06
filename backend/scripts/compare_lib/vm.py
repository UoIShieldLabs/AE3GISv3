"""Each platform's VM, controlled from the host: running?, start, stop, and
which host processes and disk files belong to it, on macOS and Windows.

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

- **Docker Desktop on Windows** (WSL 2): the same CLI; its VM is WSL's
  utility VM (``vmmem`` / ``vmmemWSL``), shared by every running WSL distro,
  so a stop also runs ``wsl --shutdown`` (WSL would otherwise keep the VM for
  its idle timeout) and other distros must not be running. Its CPUs and memory
  are ``.wslconfig``'s ``processors`` and ``memory``.
- **VirtualBox** (GNS3 on Windows): ``VBoxManage startvm --type headless``,
  ``controlvm acpipowerbutton`` (then ``poweroff``). Its address comes from
  the Guest Additions' property, or a fixed ``address`` in the config. The VM
  is ``VBoxHeadless`` / ``VirtualBoxVM``; ``VBoxSVC`` and the rest are its
  helpers.

Both report time to stop and to start, so restarts are part of the record.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from .target import Target

WINDOWS = sys.platform == "win32"
VMRUN = "/Applications/VMware Fusion.app/Contents/Library/vmrun"
DOCKER_RAW = "~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw"
DOCKER_SETTINGS = "~/Library/Group Containers/group.com.docker/settings-store.json"
# Windows: newer Docker Desktops first.
WIN_DOCKER_DISKS = (
    r"%LOCALAPPDATA%\Docker\wsl\disk\docker_data.vhdx",
    r"%LOCALAPPDATA%\Docker\wsl\data\ext4.vhdx",
)
WIN_DOCKER_SETTINGS = (r"%APPDATA%\Docker\settings-store.json", r"%APPDATA%\Docker\settings.json")
WIN_VM = ("vmmem", "vmmemwsl", "vmmem.exe", "vmmemwsl.exe")
VBOXMANAGE = shutil.which("VBoxManage") or r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"


def _pgrep(*args: str) -> list[int]:
    out = subprocess.run(["pgrep", *args], capture_output=True, text=True).stdout
    return [int(x) for x in out.split()]


def _named(match) -> list[int]:
    """PIDs whose process (name, command line) ``match`` accepts (psutil)."""
    import psutil

    out = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = (proc.info["name"] or "").lower()
            if match(name, " ".join(proc.info["cmdline"] or [])):
                out.append(proc.info["pid"])
        except (psutil.Error, OSError):
            continue
    return out


def _first(paths) -> Path | None:
    for raw in paths:
        p = Path(os.path.expandvars(raw)).expanduser()
        if p.exists():
            return p
    return None


def memory_mib(text: str) -> int | None:
    """``16GB`` / ``16384MB`` / ``16G`` (``.wslconfig``) in MiB."""
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([KMGT]?)B?\s*", text, re.I)
    if not m:
        return None
    mult = {"": 1 / 2**20, "K": 1 / 1024, "M": 1, "G": 1024, "T": 1024**2}[m.group(2).upper()]
    return int(float(m.group(1)) * mult)


def wslconfig(path: Path | None = None) -> dict[str, str]:
    """The ``[wsl2]`` section of ``%USERPROFILE%\\.wslconfig``."""
    path = path or Path.home() / ".wslconfig"
    out, section = {}, ""
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if line.startswith("["):
            section = line.strip("[]").strip().lower()
        elif "=" in line and section == "wsl2":
            k, _, v = line.partition("=")
            out[k.strip().lower()] = v.strip()
    return out


def _get(url: str, timeout: float = 5) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read() or b"null")
    except (OSError, ValueError):
        return None


def _docker_answers(target: Target) -> bool:
    """The VM's Docker answers over SSH; a hang while the VM boots is a no."""
    try:
        return target.run(target.docker("info", "-f", "{{.ID}}"), timeout=20).returncode == 0
    except subprocess.TimeoutExpired:
        return False


def _wait(ok, timeout: float, what: str, every: float = 2.0) -> float:
    t0 = time.monotonic()
    while not ok():
        if time.monotonic() - t0 > timeout:
            raise RuntimeError(f"{what} not up after {timeout:.0f}s")
        time.sleep(every)
    return round(time.monotonic() - t0, 2)


def allocated(path: Path) -> int:
    """Bytes a (sparse) file really takes on disk (its size on Windows, where
    a dynamic VHDX or VMDK grows as it fills)."""
    try:
        st = path.stat()
    except OSError:
        return 0
    blocks = getattr(st, "st_blocks", None)
    return blocks * 512 if blocks is not None else st.st_size


class DockerDesktopVm:
    name = "ae3gis"

    def __init__(self, root: Path, project: str, backend_url: str) -> None:
        self.root, self.project, self.backend_url = root, project, backend_url
        self.target = Target("docker-desktop")

    def _vm_pids(self) -> list[int]:
        if WINDOWS:
            return _named(lambda n, _c: n in WIN_VM)
        return _pgrep("-f", "com.apple.Virtualization.VirtualMachine")

    def running(self) -> bool:
        return bool(self._vm_pids()) and (
            subprocess.run(["docker", "info"], capture_output=True).returncode == 0
        )

    def root_netns_sh(self, script: str) -> list[str] | None:
        """argv running ``script`` in the VM's initial network namespace, when
        ``docker run --network host`` doesn't reach it: on WSL 2, Docker's host
        network is a namespace of its own, and the neighbour table's global
        ``gc_thresh*`` sysctls exist only in the initial one."""
        if WINDOWS:
            return ["wsl", "-d", "docker-desktop", "-u", "root", "-e", "sh", "-c", script]
        return None

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
        if WINDOWS:  # WSL keeps its VM up for a while after the last distro stops
            subprocess.run(["wsl", "--shutdown"], capture_output=True, timeout=timeout)
        _wait(lambda: not self._vm_pids(), timeout, "Docker Desktop's VM to stop")
        return round(time.monotonic() - t0, 2)

    def processes(self) -> dict[str, list[int]]:
        vm = self._vm_pids()
        if WINDOWS:
            helpers = _named(
                lambda n, _c: (
                    n.startswith("com.docker.")
                    or n.startswith("docker desktop")
                    or n in ("wslservice.exe", "wslhost.exe", "wslrelay.exe")
                )
            )
        else:
            helpers = _pgrep("-f", "/Applications/Docker.app/")
        return {"vm": vm, "helpers": [p for p in helpers if p not in vm]}

    def disk_bytes(self) -> int:
        path = _first(WIN_DOCKER_DISKS) if WINDOWS else Path(DOCKER_RAW).expanduser()
        return allocated(path) if path else 0

    def settings(self) -> dict:
        path = _first(WIN_DOCKER_SETTINGS) if WINDOWS else Path(DOCKER_SETTINGS).expanduser()
        try:
            return json.loads(path.read_text()) if path else {}
        except (OSError, ValueError):
            return {}

    def resources(self) -> dict[str, int | None]:
        """The CPUs and memory (MiB) its VM is given: Docker Desktop's settings
        on macOS, ``.wslconfig`` with WSL 2 (unset: WSL's defaults, which the
        comparison does not accept)."""
        if WINDOWS:
            w = wslconfig()
            cpus = w.get("processors")
            return {
                "cpus": int(cpus) if cpus and cpus.isdigit() else None,
                "memory_mib": memory_mib(w["memory"]) if "memory" in w else None,
            }
        st = self.settings()
        return {"cpus": st.get("Cpus"), "memory_mib": st.get("MemoryMiB")}

    def other_distros(self) -> list[str]:
        """Running WSL distros besides Docker Desktop's (Windows)."""
        if not WINDOWS:
            return []
        raw = subprocess.run(["wsl", "-l", "--running", "-q"], capture_output=True).stdout
        text = raw.decode("utf-16-le", errors="replace") if b"\x00" in raw else raw.decode()
        names = [x.strip().strip("\x00") for x in text.splitlines() if x.strip().strip("\x00")]
        return [n for n in names if not n.startswith("docker-desktop")]


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
        return _docker_answers(self.target)

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

    def resources(self) -> dict[str, int | None]:
        c = self.config()
        num = lambda k: int(c[k]) if c.get(k, "").isdigit() else None  # noqa: E731
        return {"cpus": num("numvcpus"), "memory_mib": num("memsize")}


class VirtualBoxVm:
    """The GNS3 VM in VirtualBox (Windows), by its VirtualBox name."""

    name = "gns3"
    HELPERS = ("vboxsvc.exe", "vboxsds.exe", "vboxnetdhcp.exe", "vboxnetnat.exe", "virtualbox.exe")

    def __init__(
        self,
        vm: str,
        target: Target,
        user: str = "gns3",
        adapter=None,
        address: str | None = None,
        nic: int = 0,
        api_port: int = 80,
    ) -> None:
        self.vm, self.target, self.user, self.adapter = vm, target, user, adapter
        self.address, self.nic, self.api_port = address, nic, api_port
        self.ip: str | None = None
        self.api_url = ""

    def _vbox(self, *args: str, timeout: float = 300) -> subprocess.CompletedProcess:
        return subprocess.run([VBOXMANAGE, *args], capture_output=True, text=True, timeout=timeout)

    def info(self) -> dict[str, str]:
        out = {}
        for line in self._vbox("showvminfo", self.vm, "--machinereadable").stdout.splitlines():
            k, sep, v = line.partition("=")
            if sep:
                out[k.strip().strip('"')] = v.strip().strip('"')
        return out

    def running(self) -> bool:
        return self.info().get("VMState") == "running"

    def _guest_ip(self) -> str | None:
        prop = f"/VirtualBox/GuestInfo/Net/{self.nic}/V4/IP"
        out = self._vbox("guestproperty", "get", self.vm, prop).stdout.strip()
        return out.split(":", 1)[1].strip() if out.startswith("Value:") else None

    def resolve(self, timeout: float = 300) -> str:
        """The VM's address (fixed, or from the Guest Additions); the API URL,
        the SSH target and the GNS3 adapter follow it."""
        ip = self.address
        t0 = time.monotonic()
        while not ip:
            ip = self._guest_ip()
            if not ip:
                if time.monotonic() - t0 > timeout:
                    raise RuntimeError(
                        f"no address for {self.vm}: set gns3.address in compare.local.json"
                    )
                time.sleep(2)
        port = "" if self.api_port == 80 else f":{self.api_port}"
        self.ip, self.api_url = ip, f"http://{ip}{port}"
        self.target.ssh = f"{self.user}@{ip}"
        if self.adapter is not None:
            self.adapter.url = self.api_url
        return ip

    def up(self) -> bool:
        if not self.api_url or not _get(self.api_url + "/v2/version"):
            return False
        return _docker_answers(self.target)

    def start(self, timeout: float = 600) -> float:
        t0 = time.monotonic()
        p = self._vbox("startvm", self.vm, "--type", "headless", timeout=timeout)
        if p.returncode != 0:
            raise RuntimeError(f"VBoxManage startvm: {p.stdout.strip()} {p.stderr.strip()}")
        self.resolve(timeout)
        _wait(self.up, timeout, "the GNS3 VM (API and Docker)")
        return round(time.monotonic() - t0, 2)

    def stop(self, timeout: float = 300) -> float:
        t0 = time.monotonic()
        if self.running():
            self._vbox("controlvm", self.vm, "acpipowerbutton", timeout=60)
            try:
                _wait(lambda: not self.running(), timeout / 2, "the GNS3 VM to power off")
            except RuntimeError:
                self._vbox("controlvm", self.vm, "poweroff", timeout=60)
        _wait(lambda: not self._vm_pids(), timeout, "the GNS3 VM's process to exit")
        return round(time.monotonic() - t0, 2)

    def _vm_pids(self) -> list[int]:
        uuid = self.info().get("UUID", "")
        return _named(
            lambda n, c: (
                n in ("vboxheadless.exe", "virtualboxvm.exe", "vboxheadless", "virtualboxvm")
                and (self.vm in c or (uuid and uuid in c))
            )
        )

    def processes(self) -> dict[str, list[int]]:
        vm = self._vm_pids()
        helpers = _named(lambda n, _c: n in self.HELPERS)
        return {"vm": vm, "helpers": [p for p in helpers if p not in vm]}

    def disk_bytes(self) -> int:
        disks = {v for v in self.info().values() if v.lower().endswith((".vmdk", ".vdi", ".vhd"))}
        return sum(allocated(Path(d)) for d in disks)

    def resources(self) -> dict[str, int | None]:
        i = self.info()
        num = lambda k: int(i[k]) if i.get(k, "").isdigit() else None  # noqa: E731
        return {"cpus": num("cpus"), "memory_mib": num("memory")}


def restart(vm, timeout: float = 600) -> dict[str, float]:
    return {"stop_s": vm.stop(timeout), "start_s": vm.start(timeout)}
