"""Docker Hub registries: namespaces whose standard images join the catalog."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from api.deps import get_db, get_registries
from api.schemas import JobOut, RegistryCreate, RegistryOut
from auth import require_any_auth, require_instructor
from services import jobs
from services.registries import RegistryManager

router = APIRouter(prefix="/api/v1/registries", tags=["registries"])


@router.get("", response_model=list[RegistryOut])
def list_registries(
    registries: RegistryManager = Depends(get_registries),
    _=Depends(require_any_auth),
):
    """Every registry, with what its last sync loaded, rejected and skipped."""
    return registries.rows()


@router.post("", response_model=RegistryOut, status_code=201)
def add_registry(
    body: RegistryCreate,
    db: Session = Depends(get_db),
    registries: RegistryManager = Depends(get_registries),
    _=Depends(require_instructor),
):
    """Add a Docker Hub namespace (by URL or name) and start its first sync."""
    reg = registries.add(db, body.url)
    return registries.row(db, reg.id)


@router.post("/{registry_id}/sync", response_model=JobOut, status_code=202)
def sync_registry(
    registry_id: str,
    db: Session = Depends(get_db),
    registries: RegistryManager = Depends(get_registries),
    _=Depends(require_instructor),
):
    """Re-read the namespace (a sync already running returns its job)."""
    return jobs.job_to_dict(registries.start_sync(db, registry_id))


@router.delete("/{registry_id}", status_code=204)
def remove_registry(
    registry_id: str,
    db: Session = Depends(get_db),
    registries: RegistryManager = Depends(get_registries),
    _=Depends(require_instructor),
):
    """Remove a registry: its images and types leave the catalog."""
    registries.remove(db, registry_id)
    return Response(status_code=204)
