"""Images AE3GIS builds from Dockerfiles, and the sources they come from."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_db, get_images
from api.schemas import BuildRequest, ImagesReport, JobOut
from auth import require_any_auth, require_instructor
from domain.topology import images_in
from services import jobs, topologies
from services.images import ImageManager

router = APIRouter(prefix="/api/v1", tags=["images"])


@router.get("/images", response_model=ImagesReport)
async def list_images(
    topology_id: str | None = Query(
        default=None, description="Only the images this topology's nodes use"
    ),
    db: Session = Depends(get_db),
    images: ImageManager = Depends(get_images),
    _=Depends(require_any_auth),
):
    """Host build support, image sources, and the status of each image.

    Without ``topology_id``: every image the catalog describes.
    """
    if topology_id:
        refs = images_in(topologies.get_or_404(db, topology_id).data or {})
    else:
        refs = images.catalog_refs()
    return await images.report(refs)


@router.post("/images/builds", response_model=list[JobOut], status_code=202)
def build_images(
    body: BuildRequest,
    db: Session = Depends(get_db),
    images: ImageManager = Depends(get_images),
    _=Depends(require_instructor),
):
    """Start a build job per image (an image already building returns its job)."""
    return [jobs.job_to_dict(j) for j in images.start_builds(db, body.refs, fresh=body.fresh)]


@router.post("/sources/{name}/sync", response_model=JobOut, status_code=202)
def sync_source(
    name: str,
    db: Session = Depends(get_db),
    images: ImageManager = Depends(get_images),
    _=Depends(require_instructor),
):
    """Fetch a git source's configured ref; the job reports which images changed."""
    return jobs.job_to_dict(images.start_sync(db, name))
