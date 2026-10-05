"""Request/response envelopes for /api/v1.

Topology ``data`` stays an opaque dict: the backend persists what the frontend
sends and reports diagnostics about it, but does not model its shape.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class Diagnostic(BaseModel):
    code: str
    severity: Literal["error", "warning"]
    message: str
    path: str = ""
    node_id: str | None = None


class DiagnosticsSummary(BaseModel):
    errors: int
    warnings: int


class ValidationResult(BaseModel):
    diagnostics: list[Diagnostic]
    summary: DiagnosticsSummary


class TopologyCreate(BaseModel):
    name: str
    data: dict[str, Any]


class TopologyUpdate(BaseModel):
    name: str | None = None
    data: dict[str, Any] | None = None
    # Optimistic concurrency: the version the client last saw. 409 if it moved.
    version: int | None = None


class ValidateBody(BaseModel):
    data: dict[str, Any]


class TopologySummary(BaseModel):
    id: str
    name: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TopologyRecord(TopologySummary):
    data: dict[str, Any]
    engine_state: dict[str, Any] | None = None
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class JobStep(BaseModel):
    name: str
    status: str
    message: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    # Other jobs this step waits on (a deploy's images step lists its builds).
    jobs: list[str] = Field(default_factory=list)


class JobOut(BaseModel):
    id: str
    # Set for topology jobs (deploy/destroy); None for image builds and syncs.
    topology_id: str | None = None
    # What the job serialises on: topology:<id> | image:<ref> | source:<name> |
    # capture:<topology>:<node>:<interface> | traffic:<topology>.
    subject: str | None = None
    kind: str
    status: str
    steps: list[JobStep]
    error: str | None = None
    # The job's inputs (e.g. a capture's target and filter).
    params: dict[str, Any] | None = None
    # What it produced (e.g. a capture's packet counts, a traffic run's summary).
    result: dict[str, Any] | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobLogOut(BaseModel):
    """A line-aligned slice of a job's log. Poll again from ``next_offset``."""

    offset: int
    next_offset: int
    size: int
    text: str
    done: bool


ImageStatus = Literal["ready", "missing", "stale", "unmanaged", "unavailable", "building", "failed"]


class HostBuildOut(BaseModel):
    platform: str
    can_build: bool
    detail: str


class SourceOut(BaseModel):
    name: str
    kind: Literal["git", "path"]
    url: str | None = None
    ref: str | None = None
    path: str
    available: bool
    can_sync: bool
    revision: str | None = None
    detail: str
    active_job: JobOut | None = None
    last_job: JobOut | None = None


class ImageStatusOut(BaseModel):
    ref: str
    display_name: str
    description: str = ""
    stability: Literal["stable", "experimental", "hidden"]
    kind: Literal["build", "registry"]
    source: str | None = None
    status: ImageStatus
    reason: str
    expected_fingerprint: str | None = None
    built_fingerprint: str | None = None
    built_revision: str | None = None
    created: str | None = None
    size: int | None = None
    platforms: list[str] | None = None
    active_job: JobOut | None = None
    last_job: JobOut | None = None


class ImagesReport(BaseModel):
    host: HostBuildOut
    sources: list[SourceOut]
    images: list[ImageStatusOut]


class BuildRequest(BaseModel):
    refs: list[str] = Field(min_length=1)
    # Rebuild from scratch: refresh the base image and skip the build cache.
    fresh: bool = False


class NodeState(BaseModel):
    id: str
    name: str
    state: str


class ActivityOut(BaseModel):
    """A capture or traffic run in progress on the topology."""

    job_id: str
    kind: str  # capture | traffic
    status: str
    label: str = ""
    node_ids: list[str] = []
    connection_ids: list[str] = []
    started_at: datetime | None = None
    message: str | None = None


class RuntimeOut(BaseModel):
    topology_id: str
    status: str
    version: int
    # The deploy/destroy job, if one is running.
    active_job: JobOut | None = None
    # Captures and traffic runs (they never block deploy or destroy).
    activity: list[ActivityOut] = []
    nodes: list[NodeState]


class LinkEndpointOut(BaseModel):
    node: str
    machine_name: str
    interface: str
    ip: str | None = None
    prefix_len: str | None = None


class LinkOut(BaseModel):
    collision_domain: str
    # The topology connection it realises; None if the connection had no id.
    connection_id: str | None = None
    kind: str | None = None  # container | subnet | site
    # Resolved end nodes (a subnet/site end becomes its gateway router).
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    endpoints: list[LinkEndpointOut]

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class InterfaceOut(BaseModel):
    name: str
    collision_domain: str
    connection_id: str | None = None
    peer_node_id: str | None = None
    ip: str | None = None


class DeployedInterfacesOut(BaseModel):
    """The deployed lab's interfaces: what captures can target."""

    deployed: bool
    # deployed: saved at deploy time; recomputed: rebuilt from current data for
    # a lab deployed before links were saved; none: nothing is deployed.
    mapping: Literal["deployed", "recomputed", "none"]
    nodes: dict[str, list[InterfaceOut]]
    links: list[LinkOut]


class ArtifactOut(BaseModel):
    name: str
    size: int
    modified_at: datetime
    content_type: str


class EventOut(BaseModel):
    id: int
    topology_id: str | None
    job_id: str | None
    ts: datetime
    level: str
    type: str
    message: str
    data: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class PlanOut(BaseModel):
    plan: dict[str, Any]
    diagnostics: list[Diagnostic]


class LabOut(BaseModel):
    lab_hash: str
    user_prefix: str
    machines: list[str]
    running: int
    total: int
    classification: Literal["tracked", "orphan"]
    topology_id: str | None = None
    topology_name: str | None = None


class StaleOut(BaseModel):
    topology_id: str
    topology_name: str
    lab_hash: str


class LabsReport(BaseModel):
    labs: list[LabOut]
    stale: list[StaleOut]


class ReconcileResult(BaseModel):
    reset: int
    orphans: int


class PurgeResult(BaseModel):
    lab_hash: str
    topology_id: str | None = None


class HealthOut(BaseModel):
    status: str
    version: str
    engine: str
    engine_ok: bool
    engine_detail: str
    auth_required: bool
    topologies: int


class ContextOut(BaseModel):
    topology: TopologyRecord
    plan: dict[str, Any]
    runtime: RuntimeOut
    events: list[EventOut]


class PresetSummary(BaseModel):
    id: str
    name: str
    description: str = ""
    scenario_count: int = 0
    site_count: int = 0


class PresetList(BaseModel):
    presets: list[PresetSummary]


# ── packet capture ────────────────────────────────────────────────────


class LinkTarget(BaseModel):
    """Capture a whole link (a topology connection) from one of its ends."""

    kind: Literal["link"]
    connection_id: str = Field(min_length=1, max_length=128)
    # Either end sees everything on the link; defaults to the "from" end.
    endpoint: Literal["from", "to"] | None = None


class InterfaceTarget(BaseModel):
    """Capture one interface of a node."""

    kind: Literal["interface"]
    node_id: str = Field(min_length=1, max_length=128)
    interface: str = Field(pattern=r"^eth\d{1,3}$")


CaptureTarget = Annotated[LinkTarget | InterfaceTarget, Field(discriminator="kind")]


class CaptureRequest(BaseModel):
    target: CaptureTarget
    # A tcpdump/BPF filter, e.g. "icmp" or "tcp port 502". Passed as one
    # argument (never through a shell).
    filter: str = Field(default="", max_length=512)
    # Bytes kept per packet; 0 = whole packets. 96–128 keeps headers only.
    snaplen: int = Field(default=0, ge=0, le=262144)
    max_seconds: int | None = Field(default=None, ge=1)
    max_bytes: int | None = Field(default=None, ge=10_000)
    max_packets: int | None = Field(default=None, ge=1)
    label: str = Field(default="", max_length=80)

    @field_validator("filter")
    @classmethod
    def _printable(cls, v: str) -> str:
        if any(not ch.isprintable() for ch in v):
            raise ValueError("the filter must be a single line of printable text")
        return v.strip()

    @field_validator("snaplen")
    @classmethod
    def _snaplen(cls, v: int) -> int:
        if 0 < v < 64:
            raise ValueError("snaplen must be 0 (whole packets) or at least 64")
        return v


class CaptureEndpointOut(BaseModel):
    node_id: str
    machine: str
    interface: str
    collision_domain: str
    connection_id: str | None = None
    peer_node_id: str | None = None
    ip: str | None = None


class CaptureStatsOut(BaseModel):
    packets: int = 0
    # Bytes on the wire (original packet lengths).
    bytes: int = 0
    # Size of the pcap file so far.
    file_bytes: int = 0
    # Packets not shown in the live view (rate limit); the pcap has them all.
    undecoded: int = 0
    dropped_by_kernel: int | None = None
    duration_s: float | None = None
    # user | destroy | shutdown | limit:size | limit:packets | limit:time | sidecar_exit
    stopped_by: str | None = None


class CaptureOut(BaseModel):
    id: str  # the capture's job id
    topology_id: str
    label: str
    status: str
    live: bool  # still capturing
    target: dict[str, Any]
    endpoint: CaptureEndpointOut
    filter: str
    snaplen: int
    limits: dict[str, Any]
    stats: CaptureStatsOut
    job: JobOut
    # GET: the pcap so far (add ?follow=true to stream it live).
    pcap_url: str
    # WebSocket for live packet summaries (append ?token= when auth is on).
    ws_path: str


class PacketSummaryOut(BaseModel):
    n: int
    ts: float
    len: int
    caplen: int
    src: str = ""
    dst: str = ""
    proto: str = ""
    sport: int | None = None
    dport: int | None = None
    info: str = ""


class PacketPageOut(BaseModel):
    items: list[PacketSummaryOut]
    # Pass as ``after`` to get the next page.
    next_after: int
    # Packets in the file (so far).
    total: int


class NodeSelector(BaseModel):
    """Nodes by id and/or by type, subnet or role; ``exclude`` applies last."""

    ids: list[str] | None = None
    types: list[str] | None = None
    subnets: list[str] | None = None
    roles: list[Literal["router", "switch", "host"]] | None = None
    exclude: list[str] | None = None


# ── traffic ───────────────────────────────────────────────────────────


class Iperf3Flow(BaseModel):
    """One iperf3 flow: ``client`` sends to ``server`` (reverse: the other way)."""

    generator: Literal["iperf3"] = "iperf3"
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,32}$")
    client: str = Field(min_length=1, max_length=128)  # node id
    server: str = Field(min_length=1, max_length=128)  # node id
    # Where the client connects; defaults to the server node's IP.
    server_address: str | None = Field(default=None, max_length=64)
    protocol: Literal["tcp", "udp"] = "tcp"
    # Target rate, e.g. "50M" (UDP defaults to 1M; TCP to unlimited).
    bitrate: str | None = Field(default=None, pattern=r"^\d+(\.\d+)?[KMGkmg]?$")
    parallel: int = Field(default=1, ge=1, le=16)
    # Bytes per write (TCP) / datagram (UDP).
    length: int | None = Field(default=None, ge=16, le=65507)
    direction: Literal["forward", "reverse", "bidir"] = "forward"
    # Seconds of warm-up left out of the results.
    omit_s: int = Field(default=0, ge=0, le=60)
    # Paced bursts: send bitrate × interval at once, every this many ms.
    burst_interval_ms: int | None = Field(default=None, ge=10, le=60000)

    @model_validator(mode="after")
    def _burst_needs_a_rate(self):
        if self.burst_interval_ms and self.protocol == "tcp" and _unlimited(self.bitrate):
            raise ValueError("burst_interval_ms needs a bitrate")
        return self


def _unlimited(bitrate: str | None) -> bool:
    return not bitrate or float(bitrate.rstrip("KMGkmg") or 0) == 0


class TrafficPattern(BaseModel):
    """Many flows from one line (see domain/traffic/patterns): each client
    sends to a server (``clients_to_servers``), or each node to the next
    ``fanout`` nodes on a ring (``mesh``). Node sets are selectors like a
    monitor's: ``"all"``, a list of ids, or ``{types, subnets, roles…}``;
    clients and mesh nodes default to every host."""

    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,16}$")
    kind: Literal["clients_to_servers", "mesh"]
    clients: Literal["all"] | list[str] | NodeSelector | None = None
    servers: Literal["all"] | list[str] | NodeSelector | None = None
    # clients_to_servers: to one server each (round-robin) or to every server.
    each: Literal["one", "all"] = "one"
    nodes: Literal["all"] | list[str] | NodeSelector | None = None
    fanout: int = Field(default=1, ge=1, le=1000)
    protocol: Literal["tcp", "udp"] = "tcp"
    # Target rate per flow and stream, e.g. "10M"; "0" = as fast as the path allows.
    bitrate: str = Field(pattern=r"^\d+(\.\d+)?[KMGkmg]?$")
    parallel: int = Field(default=1, ge=1, le=16)
    length: int | None = Field(default=None, ge=16, le=65507)
    direction: Literal["forward", "reverse", "bidir"] = "forward"
    omit_s: int = Field(default=0, ge=0, le=60)
    # Paced bursts: each flow sends bitrate × interval at once, every this many ms.
    burst_interval_ms: int | None = Field(default=None, ge=10, le=60000)

    @model_validator(mode="after")
    def _burst_needs_a_rate(self):
        if self.burst_interval_ms and _unlimited(self.bitrate):
            raise ValueError("burst_interval_ms needs a bitrate")
        return self


class TrafficRunRequest(BaseModel):
    label: str = Field(default="", max_length=80)
    notes: str = Field(default="", max_length=2000)
    flows: list[Iperf3Flow] = Field(default_factory=list, max_length=64)
    patterns: list[TrafficPattern] = Field(default_factory=list, max_length=16)
    # Seconds; null runs until stopped (capped by the server's limit).
    duration_s: int | None = Field(default=30, ge=1)
    # iperf3 report interval (the samples' resolution).
    interval_s: float = Field(default=1.0, ge=0.5, le=60)
    # Clients start spread over this many seconds (servers first, all at once).
    ramp_s: float = Field(default=0.0, ge=0, le=600)

    @field_validator("patterns")
    @classmethod
    def _unique_patterns(cls, v: list[TrafficPattern]) -> list[TrafficPattern]:
        ids = [p.id for p in v]
        if len(ids) != len(set(ids)):
            raise ValueError("pattern ids must be unique")
        return v


class FlowSampleOut(BaseModel):
    t: float
    flow_id: str
    direction: Literal["fwd", "rev"]
    side: Literal["sender", "receiver"]
    bps: float
    bytes: int
    seconds: float
    omitted: bool = False
    retransmits: int | None = None
    rtt_ms: float | None = None
    packets: int | None = None
    jitter_ms: float | None = None
    lost_packets: int | None = None
    lost_percent: float | None = None


class TrafficTotalsOut(BaseModel):
    """All flows at one moment: what arrived (receiver-measured) vs. what was asked."""

    t: float
    delivered_bps: float
    # Null when a running flow has no target rate (TCP as fast as it goes).
    offered_bps: float | None = None
    active: int  # clients running


class TrafficSamplesOut(BaseModel):
    flows: list[FlowSampleOut]
    totals: list[TrafficTotalsOut]


class TrafficRunOut(BaseModel):
    id: str  # the run's job id
    topology_id: str
    label: str
    status: str
    live: bool
    # Every flow (explicit and expanded from patterns); empty in listings.
    flows: list[dict[str, Any]]
    flow_count: int
    patterns: list[dict[str, Any]] = []
    duration_s: int | None
    interval_s: float
    ramp_s: float = 0.0
    # The run's outcome (totals, per-flow summaries, stopped_by, environment fingerprint).
    result: dict[str, Any] | None = None
    job: JobOut
    ws_path: str


# ── monitors ──────────────────────────────────────────────────────────


class MonitorRequest(BaseModel):
    label: str = Field(default="", max_length=80)
    notes: str = Field(default="", max_length=2000)
    # Which nodes are recorded one by one: all, a list of ids, or a selector.
    # The host and group totals are always recorded.
    nodes: Literal["all"] | list[str] | NodeSelector = "all"
    interval_s: float = Field(default=1.0, ge=0.5, le=60)
    # Seconds; null runs until stopped (capped by the server's limit).
    duration_s: int | None = Field(default=None, ge=1)


class MonitorOut(BaseModel):
    id: str  # the monitor's job id
    topology_id: str
    label: str
    status: str
    live: bool
    interval_s: float
    duration_s: int | None
    selector: Any
    monitored: list[str]
    # The monitor's outcome (host summary, notable nodes, stopped_by…).
    result: dict[str, Any] | None = None
    job: JobOut
    ws_path: str


class MonitorSamplesOut(BaseModel):
    """Recorded rows (see the monitor's CSV files); numbers are per sweep."""

    host: list[dict[str, Any]]
    nodes: list[dict[str, Any]]
    ifaces: list[dict[str, Any]]
    markers: list[dict[str, Any]]


# ── generated topologies and benchmarks ──────────────────────────────


class MixEntry(BaseModel):
    """A share of the hosts (or switches): ``weight`` relative to the others."""

    type: str = Field(min_length=1)
    image: str | None = None  # None: the type's default image
    weight: float = Field(gt=0)


class ServerMixEntry(BaseModel):
    """Servers of one kind: a fixed ``count``, or one per ``per_hosts`` hosts."""

    type: str = Field(min_length=1)
    image: str | None = None
    count: int | None = Field(default=None, ge=0, le=230)
    per_hosts: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _one(self) -> ServerMixEntry:
        if (self.count is None) == (self.per_hosts is None):
            raise ValueError("give either count or per_hosts")
        return self


class GeneratorSpec(BaseModel):
    """The shape of a generated topology (see domain/generator)."""

    servers: int = Field(default=1, ge=0, le=230)
    # Clients per subnet (a /24 each, at most 64 of them) and per access switch.
    hosts_per_subnet: int = Field(default=200, ge=1, le=230)
    hosts_per_switch: int = Field(default=48, ge=1, le=230)
    host_type: str = "workstation"
    server_type: str = "workstation"
    router_type: str = "router"
    switch_type: str = "switch"
    # A mixed topology: hosts and switches split by weight, servers by count or
    # per hosts (replacing ``servers``), the core router's type and image, and
    # the seed that places them.
    host_mix: list[MixEntry] | None = Field(default=None, min_length=1)
    server_mix: list[ServerMixEntry] | None = Field(default=None, min_length=1)
    switch_mix: list[MixEntry] | None = Field(default=None, min_length=1)
    core_type: str | None = None
    core_image: str | None = None
    seed: int = 0


class GenerateRequest(GeneratorSpec):
    name: str = Field(default="", max_length=200)
    hosts: int = Field(ge=1, le=14720)


class BenchmarkTopology(BaseModel):
    """What each step deploys: a generated topology of ``scale`` hosts, or an
    existing (idle) topology repeated."""

    generate: GeneratorSpec | None = None
    topology_id: str | None = None

    @model_validator(mode="after")
    def _one(self) -> BenchmarkTopology:
        if (self.generate is None) == (self.topology_id is None):
            raise ValueError("give either generate or topology_id")
        return self


class BenchmarkMonitor(BaseModel):
    interval_s: float = Field(default=5.0, ge=1, le=60)


class BenchmarkTraffic(BaseModel):
    """Each step's load during its hold window (see TrafficPattern)."""

    patterns: list[TrafficPattern] = Field(min_length=1, max_length=16)
    interval_s: float = Field(default=5.0, ge=0.5, le=60)
    ramp_s: float = Field(default=10.0, ge=0, le=600)


class BenchmarkStop(BaseModel):
    """When a step fails and the sweep ends (see domain/benchmark)."""

    deploy_timeout_s: float = Field(default=1800, ge=10)
    ready_timeout_s: float = Field(default=300, ge=5)
    max_mem_pct: float | None = Field(default=90, gt=0, le=100)
    # Share of time every task stalled on memory (PSI "full"), per sweep.
    max_psi_mem_full: float | None = Field(default=10, ge=0, le=100)
    min_delivered_ratio: float | None = Field(default=0.8, ge=0, le=1)
    max_loss_pct: float | None = Field(default=5, ge=0, le=100)
    # A step whose traffic falls short ends the sweep (else it is noted and the sweep goes on).
    stop_on_degraded: bool = True
    # Skip a step whose deploy would, by the last step's memory per node, cross
    # max_mem_pct (deploys cannot be interrupted once they start).
    project_memory: bool = True


class BenchmarkAdaptive(BaseModel):
    """Scales chosen step by step until the host's memory is nearly full
    (generated topologies; replaces ``scale``). Start at ``start`` hosts; after
    each step, project from its marginal memory per node the hosts at which
    memory would reach ``target_mem_pct`` and close ``approach`` of the gap (at
    least ``min_step`` hosts, but never past ×``max_factor``). The climb is
    over once a step's memory peaks at ``reach_mem_pct`` (or a step fails); the
    highest passing scale is then run ``confirm`` more times."""

    start: int = Field(ge=1)
    target_mem_pct: float = Field(default=93, gt=0, le=100)
    reach_mem_pct: float = Field(default=90, gt=0, le=100)
    approach: float = Field(default=0.6, gt=0, le=1)
    max_factor: float = Field(default=2.0, gt=1, le=10)
    min_step: int = Field(default=25, ge=1)
    max_steps: int = Field(default=20, ge=1, le=100)
    confirm: int = Field(default=2, ge=0, le=10)

    @model_validator(mode="after")
    def _reach_below_target(self) -> BenchmarkAdaptive:
        if self.reach_mem_pct > self.target_mem_pct:
            raise ValueError("reach_mem_pct cannot be above target_mem_pct")
        return self


class BenchmarkRequest(BaseModel):
    label: str = Field(default="", max_length=80)
    notes: str = Field(default="", max_length=2000)
    # What the benchmark does; inferred from the spec when omitted.
    kind: Literal["sweep", "adaptive"] | None = None
    topology: BenchmarkTopology = Field(
        default_factory=lambda: BenchmarkTopology(generate=GeneratorSpec())
    )
    # Hosts per step, increasing (generated topologies only).
    scale: list[int] = Field(default_factory=list, max_length=100)
    # Or let the sweep pick each step's scale until memory is nearly full.
    adaptive: BenchmarkAdaptive | None = None
    repetitions: int = Field(default=1, ge=1, le=20)
    cooldown_s: float = Field(default=20, ge=0, le=3600)
    # Before each step's reference window, wait (up to quiet_timeout_s) until
    # host CPU stays under quiet_cpu_pct: Docker keeps tearing the previous
    # step down after its destroy job ends.
    quiet_cpu_pct: float = Field(default=10, gt=0, le=100)
    quiet_timeout_s: float = Field(default=300, ge=0, le=3600)
    settle_s: float = Field(default=20, ge=0, le=3600)
    hold_s: float = Field(default=60, ge=0, le=86400)
    # Seconds the host is measured at rest before the first step (0 = not).
    rest_s: float = Field(default=0, ge=0, le=600)
    monitor: BenchmarkMonitor = Field(default_factory=BenchmarkMonitor)
    traffic: BenchmarkTraffic | None = None
    stop: BenchmarkStop = Field(default_factory=BenchmarkStop)
    # Run although other labs or jobs load the host (recorded with the results).
    allow_busy_host: bool = False
    # Leave the last step's lab deployed for inspection.
    keep_last: bool = False
    # Also copy each traffic run's per-interval samples into the export (big).
    keep_samples: bool = False

    @field_validator("scale")
    @classmethod
    def _increasing(cls, v: list[int]) -> list[int]:
        if any(x < 1 for x in v) or any(b <= a for a, b in zip(v, v[1:], strict=False)):
            raise ValueError("scale must be positive and strictly increasing")
        return v

    @model_validator(mode="after")
    def _adaptive_generates(self) -> BenchmarkRequest:
        if self.adaptive is not None and (self.scale or self.topology.generate is None):
            raise ValueError("adaptive replaces scale and needs a generated topology")
        return self

    @model_validator(mode="after")
    def _kind(self) -> BenchmarkRequest:
        inferred = "adaptive" if self.adaptive is not None else "sweep"
        if self.kind is not None and self.kind != inferred:
            raise ValueError(f"kind {self.kind!r} does not match the spec (a {inferred})")
        self.kind = inferred
        return self


class BenchmarkOut(BaseModel):
    id: str  # the benchmark's job id
    label: str
    kind: str  # sweep | adaptive | census | matrix
    status: str
    live: bool
    topology_id: str | None
    spec: dict[str, Any]
    # rows (one per step), by_scale, ceiling, reason, stopped_by… (updated after each step)
    result: dict[str, Any] | None = None
    # The running step and what it is doing.
    current: str | None = None
    job: JobOut
