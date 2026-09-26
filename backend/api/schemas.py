"""Request/response envelopes for /api/v1.

Topology ``data`` stays an opaque dict: the backend persists what the frontend
sends and reports diagnostics about it, but does not model its shape.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator


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


class TrafficRunRequest(BaseModel):
    label: str = Field(default="", max_length=80)
    notes: str = Field(default="", max_length=2000)
    flows: list[Iperf3Flow] = Field(min_length=1, max_length=8)
    # Seconds; null runs until stopped (capped by the server's limit).
    duration_s: int | None = Field(default=30, ge=1)
    # Sampling interval for iperf3 reports and node telemetry.
    interval_s: float = Field(default=1.0, ge=0.5, le=10)
    # Nodes whose CPU/memory/interfaces are sampled: all, the flows' ends, or a list.
    monitor_nodes: Literal["all", "flows"] | list[str] = "all"


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


class IfaceRatesOut(BaseModel):
    rx_bps: float
    tx_bps: float
    rx_pps: float
    tx_pps: float
    rx_dropped: int = 0
    tx_dropped: int = 0
    errors: int = 0


class NodeSampleOut(BaseModel):
    t: float
    target: str  # node id, or sidecar name (see the run's ``sidecars``)
    kind: Literal["node", "sidecar"]
    cpu_percent: float | None = None  # 100 = one core
    mem_used: int
    mem_limit: int | None = None
    pids: int | None = None
    ifaces: dict[str, IfaceRatesOut] = {}


class TrafficSamplesOut(BaseModel):
    flows: list[FlowSampleOut]
    nodes: list[NodeSampleOut]


class SidecarRoleOut(BaseModel):
    flow_id: str
    role: Literal["client", "server"]
    node_id: str


class TrafficRunOut(BaseModel):
    id: str  # the run's job id
    topology_id: str
    label: str
    status: str
    live: bool
    flows: list[dict[str, Any]]
    duration_s: int | None
    interval_s: float
    monitored: list[str]
    sidecars: dict[str, SidecarRoleOut] = {}
    # The run's outcome (summary per flow, stopped_by, environment fingerprint).
    result: dict[str, Any] | None = None
    job: JobOut
    ws_path: str
