import uuid
from typing import Literal, Optional, List, Dict
from pydantic import BaseModel, Field

def generate_id() -> str:
    """Generate a random UUID string."""
    return str(uuid.uuid4())

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
    id: str = Field(default_factory=generate_id)
    name: str
    type: ContainerType
    ip: str
    kind: Optional[str] = None
    image: Optional[str] = None
    status: Optional[Literal["running", "stopped", "paused"]] = None
    metadata: Optional[Dict[str, str]] = None

class Connection(BaseModel):
    from_: str = Field(alias="from")
    to: str
    label: Optional[str] = None
    fromInterface: Optional[str] = None
    toInterface: Optional[str] = None
    fromContainer: Optional[str] = None
    toContainer: Optional[str] = None

    model_config = {"populate_by_name": True}

class Subnet(BaseModel):
    id: str = Field(default_factory=generate_id)
    name: str
    cidr: str
    gateway: Optional[str] = None
    containers: List[Container] = Field(default_factory=list)
    connections: List[Connection] = Field(default_factory=list)

class Position(BaseModel):
    x: float = 0.0
    y: float = 0.0

class Site(BaseModel):
    id: str = Field(default_factory=generate_id)
    name: str
    location: str
    position: Position = Field(default_factory=Position)
    subnets: List[Subnet] = Field(default_factory=list)
    subnetConnections: List[Connection] = Field(default_factory=list)

class TopologyData(BaseModel):
    name: Optional[str] = None
    sites: List[Site] = Field(default_factory=list)
    siteConnections: List[Connection] = Field(default_factory=list)
