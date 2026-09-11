"""API request/response envelope models.

The topology `data` payload is intentionally opaque JSON: the backend persists
and serves whatever the frontend sends and does NOT model its internal shape.
This keeps the frontend fully decoupled — it owns its own view of topology data
(frontend/src/types/topology.ts) and can add, rename, or drop fields with no
backend change. The deployment engine reads the fields it needs defensively.

The only cross-tier contracts are these envelope models and the node catalog
served at GET /api/catalog.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class TopologyCreate(BaseModel):
    name: str
    data: dict[str, Any]


class TopologyUpdate(BaseModel):
    name: str | None = None
    data: dict[str, Any] | None = None


class TopologyRecord(BaseModel):
    id: str
    name: str
    data: dict[str, Any]
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
