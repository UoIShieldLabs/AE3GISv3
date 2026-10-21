"""The benchmarked hosts: what each machine is, how it ran, and what to keep in
mind when reading its numbers (from each host's NOTES.md)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Host:
    key: str  # its folder under backend/benchmark-results/
    slug: str  # its notebook (and benchmarking/<slug> branch)
    name: str
    hardware: str
    os: str
    docker: str
    cpus: int  # Docker's CPUs
    mem_gb: float  # Docker's memory
    color: str
    cooling: str
    deviations: tuple[str, ...] = ()  # settings that differ from the shared suites
    issues: tuple[str, ...] = ()  # known problems in its data
    annotations: dict[str, str] = field(default_factory=dict)  # run key -> note

    @property
    def resources(self) -> str:
        return f"{self.cpus} CPUs / {self.mem_gb:.1f} GB"


HOSTS: dict[str, Host] = {
    h.key: h
    for h in (
        Host(
            key="m4-macbook-air",
            slug="m4-macbook-air",
            name="M4 MacBook Air",
            hardware='MacBook Air 15" (Mac16,13), Apple M4 (4P + 6E cores), 32 GB',
            os="macOS 26.7.1",
            docker="Docker Desktop 4.95.0 (Docker 29.8.2)",
            cpus=8,
            mem_gb=16.7,
            color="#1f77b4",
            cooling="fanless",
            issues=(
                "Traffic: measured with the old traffic driver until 2026-10-12, then the fixed "
                "one; 54 cells were searched again after the fix and 13 more after the "
                "memory-stall re-check (2026-10-19). 10 cells are still open (paused).",
                "Traffic cells rest before running (a quiet host, then an idle minute) because "
                "the fanless chip throttled under back-to-back heavy cells.",
            ),
        ),
        Host(
            key="m4max-studio-dd12-95g",
            slug="m4-max-mac-studio",
            name="M4 Max Mac Studio",
            hardware="Mac Studio, Apple M4 Max (12P + 4E cores), 128 GB",
            os="macOS (Darwin 24.6.0)",
            docker="Docker Desktop 4.47.0 (Docker 28.4.0, then 29.8.2 from climb 4)",
            cpus=12,
            mem_gb=101.9,
            color="#d62728",
            cooling="active",
            deviations=(
                "Random climbs: max_factor 1.25 instead of 2.0, to stay below Docker Desktop's "
                "deploy wall (~2400 hosts).",
            ),
            issues=(
                "Random climbs 1-3 ran on Docker 28.4 left broken by a wedged dockerd (thousands "
                "of leftover containers and networks): ~1160 hosts, not comparable with the clean "
                "climbs 4-10 (~2290). Climb 6's ceiling (1640) is a failed teardown at 2050, not "
                "capacity.",
                "Idle climbs stop at Docker Desktop's deploy wall (deploys time out), with memory "
                "at only ~75%: the hardware's memory is not what limits it.",
                "Traffic: measured with the old traffic driver (before 2026-10-12). Its fast cores "
                "and memory kept that driver mostly in step, but half the mesh runs at 850-1000 "
                "hosts had clients that sent nothing, so those limits may be understated.",
                "Traffic: 24 cells were searched again after a fix for false 'Not running' "
                "failures (manifest.before-repair.json keeps the earlier state). The search tops "
                "out at 1000 hosts.",
            ),
            annotations={
                "random-idle-run1": "broken Docker",
                "random-idle-run2": "broken Docker",
                "random-idle-run3": "broken Docker",
                "random-idle-run6": "teardown failed",
            },
        ),
        Host(
            key="microsoft-surface-7",
            slug="core-ultra-7-surface-laptop-7",
            name="Surface Laptop 7",
            hardware="Microsoft Surface Laptop 7, Intel Core Ultra 7 268V (8 cores), 32 GB",
            os="Windows 11 (Docker on WSL2)",
            docker="Docker Desktop 4.45.0 (Docker 28.3.3) on WSL2",
            cpus=8,
            mem_gb=16.6,
            color="#2ca02c",
            cooling="active",
            deviations=(
                "Traffic: quiet wait at most 180 s instead of 1200 s from round 4 (its idle CPU "
                "stays above the 10% threshold from ~260 hosts).",
            ),
            issues=(
                "Random climbs 1-2: timings skewed by Modern Standby (memory figures are fine); "
                "climb 1's ceiling comes from a slow deploy. Climb 10 took four attempts (the "
                "-invalid / -crashed / -cancelled folders); the fourth counts.",
                "Traffic: deploys of 450+ hosts take 30-60 min, so every cell stops at 400 "
                "(`deploy_slow`): '400 / 450' marks the most this host deploys in time, not a "
                "traffic limit.",
                "Traffic: measured with the old traffic driver (before 2026-10-12). Its labs stay "
                "at or under 400 hosts, where that driver kept up: no dead flows, no memory stalls.",
                "ae3gis.local/zeek doesn't build here; malicious-client runs (amd64).",
            ),
            annotations={
                "random-idle-run1": "sleep-skewed timings",
                "random-idle-run2": "sleep-skewed timings",
            },
        ),
    )
}

ORDER = ["m4-macbook-air", "m4max-studio-dd12-95g", "microsoft-surface-7"]
REFERENCE = "m4-macbook-air"  # ratios in the comparison are against this host


def by_slug(slug: str) -> Host:
    for h in HOSTS.values():
        if slug in (h.slug, h.key):
            return h
    raise KeyError(slug)
