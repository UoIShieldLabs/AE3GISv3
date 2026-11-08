"""Images AE3GIS builds from Dockerfiles, and the sources they come from."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.access import check_view
from api.deps import get_db, get_images, get_registries
from api.schemas import BuildRequest, ImagesReport, JobOut
from auth import current_identity, require_instructor
from db.models import Topology
from domain.topology import images_in
from services import jobs
from services.accounts import Identity
from services.images import ImageManager
from services.registries import RegistryManager

router = APIRouter(prefix="/api/v1", tags=["images"])


@router.get("/images", response_model=ImagesReport)
async def list_images(
    topology_id: str | None = Query(
        default=None, description="Only the images this topology's nodes use"
    ),
    db: Session = Depends(get_db),
    images: ImageManager = Depends(get_images),
    registries: RegistryManager = Depends(get_registries),
    identity: Identity = Depends(current_identity),
):
    """Host build support, image sources and registries, and the status of each image.

    Without ``topology_id``: every image the catalog describes.
    """
    if topology_id:
        topo = check_view(identity, db.get(Topology, topology_id))
        refs = images_in(topo.data or {})
    else:
        refs = images.catalog_refs()
    report = await images.report(refs)
    report["registries"] = registries.rows()
    return report


@router.post("/images/builds", response_model=list[JobOut], status_code=202)
def build_images(
    body: BuildRequest,
    db: Session = Depends(get_db),
    images: ImageManager = Depends(get_images),
    _: Identity = Depends(require_instructor),
):
    """Start a build job per image (an image already building returns its job)."""
    return [jobs.job_to_dict(j) for j in images.start_builds(db, body.refs, fresh=body.fresh)]


@router.post("/sources/{name}/sync", response_model=JobOut, status_code=202)
def sync_source(
    name: str,
    db: Session = Depends(get_db),
    images: ImageManager = Depends(get_images),
    _: Identity = Depends(require_instructor),
):
    """Fetch a git source's configured ref; the job reports which images changed."""
    return jobs.job_to_dict(images.start_sync(db, name))
