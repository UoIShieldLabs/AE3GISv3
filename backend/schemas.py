"""Pydantic request/response models mirroring the frontend topology types.

`Container.type` is kept as a loose string (validated against the catalog on the
frontend and by the engine's role lookup) so imported/AI-authored types never
block a save.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Container(BaseModel):
    id: str
    name: str
    type: str
    ip: str = ""
    kind: str | None = None
    image: str | None = None
    status: str | None = None
    metadata: dict | None = None
    config: dict | None = None
    persistencePaths: list[str] | None = None


class Connection(BaseModel):
    from_: str = Field(alias="from")
    to: str
    label: str | None = None
    fromInterface: str | None = None
    toInterface: str | None = None
    fromContainer: str | None = None
    toContainer: str | None = None

    model_config = {"populate_by_name": True}


class Subnet(BaseModel):
    id: str
    name: str
    cidr: str
    gateway: str | None = None
    containers: list[Container] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)


class Position(BaseModel):
    x: float
    y: float


class Site(BaseModel):
    id: str
    name: str
    location: str = ""
    position: Position = Field(default_factory=lambda: Position(x=100, y=100))
    subnets: list[Subnet] = Field(default_factory=list)
    subnetConnections: list[Connection] = Field(default_factory=list)


class ScriptExecution(BaseModel):
    containerId: str
    script: str
    args: list[str] | None = None


class AttackPhase(BaseModel):
    id: str
    name: str
    description: str | None = None
    executions: list[ScriptExecution] = Field(default_factory=list)


class Scenario(BaseModel):
    id: str
    name: str
    description: str | None = None
    phases: list[AttackPhase] = Field(default_factory=list)


class TopologyData(BaseModel):
    name: str | None = None
    sites: list[Site] = Field(default_factory=list)
    siteConnections: list[Connection] = Field(default_factory=list)
    scenarios: list[Scenario] | None = None


class TopologyCreate(BaseModel):
    name: str
    data: TopologyData


class TopologyUpdate(BaseModel):
    name: str | None = None
    data: TopologyData | None = None


class TopologyRecord(BaseModel):
    id: str
    name: str
    data: TopologyData
    engine_state: dict | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TopologySummary(BaseModel):
    id: str
    name: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
