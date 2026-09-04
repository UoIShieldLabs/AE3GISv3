"""Serve the node-type catalog to the frontend (single source of truth)."""

from fastapi import APIRouter

import catalog

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("")
def get_catalog() -> dict:
    """Return the full node-type catalog (types, defaults, metadata)."""
    return catalog.load_catalog()
