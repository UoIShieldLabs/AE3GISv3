"""Topology CRUD, import, validation, plan, export, runtime, events, context;
copies, reset and publishing (classroom mode, see ``api.access``)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Header, Query, Response, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import catalog
from api.access import can_view, owned_topology, visible_topology
from api.deps import get_db, get_engine, get_runner
from api.errors import Conflict, Invalid
from api.schemas import (
    ContextOut,
    Diagnostic,
    EventOut,
    GenerateRequest,
    PlanOut,
    PublishIn,
    RuntimeOut,
    SavedStateOut,
    TopologyCreate,
    TopologyRecord,
    TopologySummary,
    TopologyUpdate,
    ValidateBody,
    ValidationResult,
)
from auth import current_identity, require_instructor
from db.models import Topology
from domain import saved_state, validation
from domain.export import containerlab, kathara, labspec
from domain.generator import GeneratorError, GeneratorParams, check_catalog, generate
from engine.base import DeploymentEngine
from services import deployment, events, lessons, topologies
from services.accounts import Identity
from services.jobs import JobRunner

router = APIRouter(prefix="/api/v1/topologies", tags=["topologies"])


def record_out(db: Session, topo: Topology, diags: list[validation.Diagnostic]) -> TopologyRecord:
    rec = TopologyRecord.model_validate(
        {**_columns(topo), **topologies.summary_meta(db, [topo])[topo.id]}
    )
    rec.diagnostics = [Diagnostic(**d.to_dict()) for d in diags]
    saved = saved_state.summary(topo.saved_state)
    rec.saved = SavedStateOut(**saved) if saved else None
    return rec


def _columns(topo: Topology) -> dict:
    return {
        "id": topo.id,
        "name": topo.name,
        "status": topo.status,
        "version": topo.version,
        "created_at": topo.created_at,
        "updated_at": topo.updated_at,
        "data": topo.data or {},
        "engine_state": topo.engine_state,
    }


def _validation_result(diags: list[validation.Diagnostic]) -> ValidationResult:
    return ValidationResult(
        diagnostics=[Diagnostic(**d.to_dict()) for d in diags], summary=validation.summarize(diags)
    )


@router.get("", response_model=list[TopologySummary])
def list_topologies(db: Session = Depends(get_db), identity: Identity = Depends(current_identity)):
    """The instructor sees every topology; a student their own and the published."""
    topos = topologies.list_visible(db, identity)
    meta = topologies.summary_meta(db, topos)
    return [TopologySummary.model_validate({**_columns(t), **meta[t.id]}) for t in topos]


@router.post("", response_model=TopologyRecord, status_code=201)
def create_topology(
    body: TopologyCreate,
    db: Session = Depends(get_db),
    identity: Identity = Depends(current_identity),
):
    topo, diags = topologies.create(db, name=body.name, data=body.data, owner_id=identity.owner_id)
    return record_out(db, topo, diags)


@router.post("/generate", response_model=TopologyRecord, status_code=201)
def generate_topology(
    body: GenerateRequest, db: Session = Depends(get_db), _=Depends(require_instructor)
):
    """Create a topology from a few numbers (the benchmarks' generator): a
    servers subnet behind a core router, client subnets behind their own
    routers, access switches under a distribution switch per subnet."""
    try:
        params = GeneratorParams(**body.model_dump())
        check_catalog(params, catalog.node_types())
        data = generate(params)
    except GeneratorError as exc:
        raise Invalid(str(exc), code="bad_generator") from exc
    topo, diags = topologies.create(db, name=data["name"], data=data)
    return record_out(db, topo, diags)


@router.post("/import-json", response_model=TopologyRecord, status_code=201)
async def import_json(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    identity: Identity = Depends(current_identity),
):
    topo, diags = topologies.import_json(
        db, await file.read(), file.filename, owner_id=identity.owner_id
    )
    return record_out(db, topo, diags)


@router.post("/validate", response_model=ValidationResult)
def validate_data(body: ValidateBody, _: Identity = Depends(current_identity)):
    """Validate a topology document without saving it."""
    return _validation_result(validation.validate(body.data))


@router.get("/{topology_id}", response_model=TopologyRecord)
def get_topology(db: Session = Depends(get_db), topo: Topology = Depends(visible_topology)):
    return record_out(db, topo, topologies.diagnostics_for(topo.data))


@router.put("/{topology_id}", response_model=TopologyRecord)
def update_topology(
    body: TopologyUpdate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    topo: Topology = Depends(owned_topology),
):
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
    return record_out(db, topo, diags)


@router.delete("/{topology_id}", status_code=204)
async def delete_topology(
    db: Session = Depends(get_db),
    engine: DeploymentEngine = Depends(get_engine),
    runner: JobRunner = Depends(get_runner),
    topo: Topology = Depends(owned_topology),
):
    """Delete a topology. Deleting a lesson removes the students' copies of it
    (their labs are destroyed in the background); their duplicates stay."""
    refs = saved_state.refs(topo.saved_state)
    retired = topologies.delete(db, topo)
    lessons.schedule(runner, engine, retired)
    await engine.remove_images(refs)
    return Response(status_code=204)


@router.delete("/{topology_id}/saved-state", status_code=204)
async def discard_saved_state(
    db: Session = Depends(get_db),
    engine: DeploymentEngine = Depends(get_engine),
    topo: Topology = Depends(owned_topology),
):
    """Forget the saved lab state (and remove its images): the next deploy starts fresh."""
    await engine.remove_images(deployment.discard_saved_state_refs(db, topo))
    return Response(status_code=204)


@router.post("/{topology_id}/validate", response_model=ValidationResult)
def validate_topology(topo: Topology = Depends(visible_topology)):
    return _validation_result(topologies.diagnostics_for(topo.data))


@router.get("/{topology_id}/plan", response_model=PlanOut)
def get_plan(topo: Topology = Depends(visible_topology)):
    """The engine-agnostic lab plan: what deploy would instantiate."""
    diags = topologies.diagnostics_for(topo.data)
    return PlanOut(
        plan=topologies.plan_for(topo).to_dict(),
        diagnostics=[Diagnostic(**d.to_dict()) for d in diags],
    )


@router.get("/{topology_id}/export")
def export_topology(
    format: str = Query("labspec", pattern="^(labspec|kathara|containerlab)$"),
    topo: Topology = Depends(visible_topology),
):
    """Portable representations of the lab: JSON spec, Kathara folder, or ContainerLab topology (zips)."""
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
    db: Session = Depends(get_db),
    engine: DeploymentEngine = Depends(get_engine),
    topo: Topology = Depends(owned_topology),
):
    """Deployment status, the active job (with steps), and per-node state in one call."""
    return await deployment.runtime_view(db, engine, topo)


@router.get("/{topology_id}/events", response_model=list[EventOut])
def get_events(
    topology_id: str,
    after: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: Topology = Depends(owned_topology),
):
    return events.list_events(db, topology_id, after_id=after, limit=limit)


@router.get("/{topology_id}/context", response_model=ContextOut)
async def get_context(
    db: Session = Depends(get_db),
    engine: DeploymentEngine = Depends(get_engine),
    topo: Topology = Depends(owned_topology),
):
    """Everything about a topology in one response: record + diagnostics, plan, runtime, recent events."""
    diags = topologies.diagnostics_for(topo.data)
    return ContextOut(
        topology=record_out(db, topo, diags),
        plan=topologies.plan_for(topo).to_dict(),
        runtime=RuntimeOut(**await deployment.runtime_view(db, engine, topo)),
        events=[EventOut.model_validate(e) for e in events.list_events(db, topo.id, limit=50)],
    )


@router.post("/{topology_id}/copy", response_model=TopologyRecord)
def copy_topology(
    response: Response,
    duplicate: bool = Query(
        False, description="A plain duplicate the caller owns, never a lesson copy."
    ),
    db: Session = Depends(get_db),
    identity: Identity = Depends(current_identity),
    source: Topology = Depends(visible_topology),
):
    """A copy for the caller. A student opening a published topology (a
    lesson) gets their lesson copy (200 with the one they started, 201 when
    new), which goes when the lesson is unpublished. ``duplicate``, or copying
    your own topology (the instructor: any), makes an unlinked duplicate (201)."""
    topo, created = topologies.copy_for(db, identity, source, duplicate=duplicate)
    response.status_code = 201 if created else 200
    return record_out(db, topo, topologies.diagnostics_for(topo.data))


@router.post("/{topology_id}/reset", response_model=TopologyRecord)
async def reset_topology(
    db: Session = Depends(get_db),
    engine: DeploymentEngine = Depends(get_engine),
    identity: Identity = Depends(current_identity),
    topo: Topology = Depends(owned_topology),
):
    """Replace a copy's design with its source's latest (your edits to it are
    lost). The lab must be destroyed first (409 ``bad_state``); its saved
    state is discarded. 409 ``no_source`` when it is not a copy or its source
    is gone or no longer published."""
    source = db.get(Topology, topo.source_id) if topo.source_id else None
    if source is None or not can_view(identity, source):
        raise Conflict(
            "This topology is not a copy of a topology published to you", code="no_source"
        )
    refs = topologies.reset_from_source(db, topo, source)
    await engine.remove_images(refs)
    return record_out(db, topo, topologies.diagnostics_for(topo.data))


@router.put("/{topology_id}/published", response_model=TopologyRecord)
async def publish_topology(
    body: PublishIn,
    db: Session = Depends(get_db),
    engine: DeploymentEngine = Depends(get_engine),
    runner: JobRunner = Depends(get_runner),
    _: Identity = Depends(require_instructor),
    topo: Topology = Depends(owned_topology),
):
    """Publish a topology to students as a lesson (or stop): they see it in
    their library and open it as their own copy. Unpublishing removes those
    copies (their labs are destroyed in the background); a republished lesson
    starts students afresh, and what they duplicated stays. Does not change the
    topology's version."""
    retired = topologies.set_published(db, topo, body.published)
    lessons.schedule(runner, engine, retired)
    return record_out(db, topo, topologies.diagnostics_for(topo.data))
