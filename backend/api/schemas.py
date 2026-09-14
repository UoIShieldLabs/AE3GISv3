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


class JobOut(BaseModel):
    id: str
    topology_id: str
    kind: str
    status: str
    steps: list[JobStep]
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


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
