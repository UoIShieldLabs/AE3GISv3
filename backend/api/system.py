"""Health and engine-level administration (labs on the host, reconcile, purge)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.deps import get_db, get_engine, get_settings
from api.schemas import HealthOut, LabsReport, PurgeResult, ReconcileResult
from auth import require_any_auth, require_instructor
from config import Settings
from db.models import Topology
from engine.base import DeploymentEngine
from services import environment, reconcile

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/health", response_model=HealthOut)
async def health(
    request: Request,
    db: Session = Depends(get_db),
    engine: DeploymentEngine = Depends(get_engine),
    settings: Settings = Depends(get_settings),
):
    ok, detail = await engine.is_available()
    return HealthOut(
        status="ok",
        version=request.app.version,
        engine=engine.name,
        engine_ok=ok,
        engine_detail=detail,
        auth_required=settings.auth_required,
        topologies=db.scalar(select(func.count(Topology.id))) or 0,
    )


@router.get("/environment")
async def get_environment(
    engine: DeploymentEngine = Depends(get_engine),
    settings: Settings = Depends(get_settings),
    _=Depends(require_any_auth),
) -> dict[str, Any]:
    """The host, Docker, Kathara and AE3GIS versions every run records."""
    return await environment.system_environment(engine, settings)


@router.get("/labs", response_model=LabsReport)
async def labs(
    db: Session = Depends(get_db),
    engine: DeploymentEngine = Depends(get_engine),
    _=Depends(require_any_auth),
):
    """Every lab the engine is running, matched against saved topologies."""
    return await reconcile.report(db, engine)


@router.post("/reconcile", response_model=ReconcileResult)
async def run_reconcile(
    db: Session = Depends(get_db),
    engine: DeploymentEngine = Depends(get_engine),
    _=Depends(require_instructor),
):
    """Reset topologies whose lab is gone; report orphans (purge is explicit)."""
    return await reconcile.apply(db, engine)


@router.post("/labs/{lab_hash}/purge", response_model=PurgeResult)
async def purge_lab(
    lab_hash: str,
    db: Session = Depends(get_db),
    engine: DeploymentEngine = Depends(get_engine),
    _=Depends(require_instructor),
):
    """Remove a lab's containers and networks whatever user prefix they carry."""
    return await reconcile.purge(db, engine, lab_hash)
