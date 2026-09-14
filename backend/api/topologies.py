"""Topology CRUD, import, validation, plan, export, runtime, events, context."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Header, Query, Response, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.deps import get_db, get_engine
from api.errors import Invalid
from api.schemas import (
    ContextOut,
    Diagnostic,
    EventOut,
    PlanOut,
    RuntimeOut,
    TopologyCreate,
    TopologyRecord,
    TopologySummary,
    TopologyUpdate,
    ValidateBody,
    ValidationResult,
)
from auth import require_any_auth, require_instructor
from db.models import Topology
from domain import validation
from domain.export import containerlab, kathara, labspec
from engine.base import DeploymentEngine
from services import deployment, events, topologies

router = APIRouter(prefix="/api/v1/topologies", tags=["topologies"])


def _record(topo: Topology, diags: list[validation.Diagnostic]) -> TopologyRecord:
    rec = TopologyRecord.model_validate(topo)
    rec.diagnostics = [Diagnostic(**d.to_dict()) for d in diags]
    return rec


def _validation_result(diags: list[validation.Diagnostic]) -> ValidationResult:
    return ValidationResult(
        diagnostics=[Diagnostic(**d.to_dict()) for d in diags], summary=validation.summarize(diags)
    )


@router.get("", response_model=list[TopologySummary])
def list_topologies(db: Session = Depends(get_db), _=Depends(require_any_auth)):
    return topologies.list_all(db)


@router.post("", response_model=TopologyRecord, status_code=201)
def create_topology(
    body: TopologyCreate, db: Session = Depends(get_db), _=Depends(require_instructor)
):
    topo, diags = topologies.create(db, name=body.name, data=body.data)
    return _record(topo, diags)


@router.post("/import-json", response_model=TopologyRecord, status_code=201)
async def import_json(
    file: UploadFile = File(...), db: Session = Depends(get_db), _=Depends(require_instructor)
):
    topo, diags = topologies.import_json(db, await file.read(), file.filename)
    return _record(topo, diags)


@router.post("/validate", response_model=ValidationResult)
def validate_data(body: ValidateBody, _=Depends(require_any_auth)):
    """Validate a topology document without saving it."""
    return _validation_result(validation.validate(body.data))


@router.get("/{topology_id}", response_model=TopologyRecord)
def get_topology(topology_id: str, db: Session = Depends(get_db), _=Depends(require_any_auth)):
    topo = topologies.get_or_404(db, topology_id)
    return _record(topo, topologies.diagnostics_for(topo.data))


@router.put("/{topology_id}", response_model=TopologyRecord)
def update_topology(
    topology_id: str,
    body: TopologyUpdate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    _=Depends(require_instructor),
):
    topo = topologies.get_or_404(db, topology_id)
    expected = body.version
    if expected is None and if_match:
        try:
            expected = int(if_match.strip().strip('"'))
        except ValueError as exc:
            raise Invalid(
                "If-Match must be the topology version number", code="bad_if_match"
            ) from exc
    topo, diags = topologies.update(
        db, topo, name=body.name, data=body.data, expected_version=expected
    )
    return _record(topo, diags)


@router.delete("/{topology_id}", status_code=204)
def delete_topology(topology_id: str, db: Session = Depends(get_db), _=Depends(require_instructor)):
    topologies.delete(db, topologies.get_or_404(db, topology_id))
    return Response(status_code=204)


@router.post("/{topology_id}/validate", response_model=ValidationResult)
def validate_topology(topology_id: str, db: Session = Depends(get_db), _=Depends(require_any_auth)):
    topo = topologies.get_or_404(db, topology_id)
    return _validation_result(topologies.diagnostics_for(topo.data))


@router.get("/{topology_id}/plan", response_model=PlanOut)
def get_plan(topology_id: str, db: Session = Depends(get_db), _=Depends(require_any_auth)):
    """The engine-agnostic lab plan: what deploy would instantiate."""
    topo = topologies.get_or_404(db, topology_id)
    diags = topologies.diagnostics_for(topo.data)
    return PlanOut(
        plan=topologies.plan_for(topo).to_dict(),
        diagnostics=[Diagnostic(**d.to_dict()) for d in diags],
    )


@router.get("/{topology_id}/export")
def export_topology(
    topology_id: str,
    format: str = Query("labspec", pattern="^(labspec|kathara|containerlab)$"),
    db: Session = Depends(get_db),
    _=Depends(require_any_auth),
):
    """Portable representations of the lab: JSON spec, Kathara folder, or ContainerLab topology (zips)."""
    topo = topologies.get_or_404(db, topology_id)
    slug = "".join(ch if ch.isalnum() else "_" for ch in topo.name).strip("_").lower() or "topology"
    if format == "labspec":
        plan = topologies.plan_for(topo)
        spec = labspec.to_labspec(
            plan, topology_id=topo.id, topology_name=topo.name, generated_at=datetime.now(UTC)
        )
        return JSONResponse(
            spec, headers={"Content-Disposition": f'attachment; filename="{slug}.labspec.json"'}
        )
    if format == "kathara":
        payload = kathara.build_zip(topologies.plan_for(topo), description=topo.name)
        filename = f"{slug}-kathara.zip"
    else:
        payload = containerlab.build_zip(topologies.plan_for(topo, iface_base=1), name=slug)
        filename = f"{slug}-containerlab.zip"
    return Response(
        payload,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{topology_id}/runtime", response_model=RuntimeOut)
async def get_runtime(
    topology_id: str,
    db: Session = Depends(get_db),
    engine: DeploymentEngine = Depends(get_engine),
    _=Depends(require_any_auth),
):
    """Deployment status, the active job (with steps), and per-node state in one call."""
    topo = topologies.get_or_404(db, topology_id)
    return await deployment.runtime_view(db, engine, topo)


@router.get("/{topology_id}/events", response_model=list[EventOut])
def get_events(
    topology_id: str,
    after: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _=Depends(require_any_auth),
):
    topologies.get_or_404(db, topology_id)
    return events.list_events(db, topology_id, after_id=after, limit=limit)


@router.get("/{topology_id}/context", response_model=ContextOut)
async def get_context(
    topology_id: str,
    db: Session = Depends(get_db),
    engine: DeploymentEngine = Depends(get_engine),
    _=Depends(require_any_auth),
):
    """Everything about a topology in one response: record + diagnostics, plan, runtime, recent events."""
    topo = topologies.get_or_404(db, topology_id)
    diags = topologies.diagnostics_for(topo.data)
    return ContextOut(
        topology=_record(topo, diags),
        plan=topologies.plan_for(topo).to_dict(),
        runtime=RuntimeOut(**await deployment.runtime_view(db, engine, topo)),
        events=[EventOut.model_validate(e) for e in events.list_events(db, topology_id, limit=50)],
    )
