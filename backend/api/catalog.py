"""Serve the node-type catalog to the frontend (single source of truth)."""

from fastapi import APIRouter

import catalog
from catalog.models import Catalog

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


@router.get("", response_model=Catalog)
def get_catalog() -> dict:
    """Return the full node-type catalog (categories, types, images, sources)."""
    return catalog.load_catalog()
