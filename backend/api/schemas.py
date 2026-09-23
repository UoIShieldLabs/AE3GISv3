"""Request/response envelopes for /api/v1.

Topology ``data`` stays an opaque dict: the backend persists what the frontend
sends and reports diagnostics about it, but does not model its shape.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


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
    # What the job serialises on: topology:<id> | image:<ref> | source:<name>.
    subject: str | None = None
    kind: str
    status: str
    steps: list[JobStep]
    error: str | None = None
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


class RuntimeOut(BaseModel):
    topology_id: str
    status: str
    version: int
    active_job: JobOut | None = None
    nodes: list[NodeState]


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
