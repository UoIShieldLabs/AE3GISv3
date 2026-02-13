from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Topology data types (mirrors frontend TypeScript) ──────────────


ContainerType = Literal[
    "web-server",
    "file-server",
    "plc",
    "firewall",
    "switch",
    "router",
    "workstation",
]


class Container(BaseModel):
    id: str
    name: str
    type: ContainerType
    ip: str
    kind: str | None = None
    image: str | None = None
    status: Literal["running", "stopped", "paused"] | None = None
    metadata: dict[str, str] | None = None


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
    containers: list[Container]
    connections: list[Connection]


class Position(BaseModel):
    x: float
    y: float


class Site(BaseModel):
    id: str
    name: str
    location: str
    position: Position
    subnets: list[Subnet]
    subnetConnections: list[Connection]


class TopologyData(BaseModel):
    name: str | None = None
    sites: list[Site]
    siteConnections: list[Connection]


# ── API request/response models ────────────────────────────────────


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
    clab_yaml: str | None = None
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
