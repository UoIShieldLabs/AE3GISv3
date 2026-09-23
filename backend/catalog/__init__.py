"""Declarative node-type catalog — the single source of truth for node types.

Loaded once from ``node_types.json`` and validated against ``catalog.models``.
Both the deployment engine (to pick a container image and decide how to
configure a node) and the frontend (served via ``GET /api/v1/catalog``) consume
this. Images are data here, never hardcoded in Python, so a new image set ships
by editing the JSON only.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from catalog.models import Catalog, ImageSpec, SourceSpec

_CATALOG_PATH = Path(__file__).resolve().parent / "node_types.json"

VALID_ROLES = {"router", "switch", "host"}


class CatalogError(RuntimeError):
    """Raised when the catalog file is missing or malformed."""


def parse_catalog(raw: dict) -> Catalog:
    try:
        return Catalog.model_validate(raw)
    except ValidationError as exc:
        raise CatalogError(f"Invalid catalog: {exc}") from exc


@lru_cache(maxsize=1)
def load_model() -> Catalog:
    """Load, validate, and cache the catalog."""
    try:
        raw = json.loads(_CATALOG_PATH.read_text())
    except FileNotFoundError as exc:  # pragma: no cover - config error
        raise CatalogError(f"Catalog file not found: {_CATALOG_PATH}") from exc
    except json.JSONDecodeError as exc:  # pragma: no cover - config error
        raise CatalogError(f"Catalog file is not valid JSON: {exc}") from exc
    return parse_catalog(raw)


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    """The validated catalog as plain JSON (what the API serves)."""
    return load_model().model_dump(mode="json")


def node_types() -> dict:
    """Return the mapping of type name -> spec."""
    return load_catalog()["types"]


def get_type(type_name: str) -> dict | None:
    """Return the spec for a node type, or None if unknown."""
    return node_types().get((type_name or "").strip())


def role_for(type_name: str) -> str:
    """Return the deployment role (router|switch|host) for a type.

    Unknown types are treated as plain hosts so an LLM- or import-supplied type
    never blocks a deploy.
    """
    spec = get_type(type_name)
    return spec["role"] if spec else "host"


def default_image_for(type_name: str) -> str:
    """Return the catalog default image for a type, falling back by role."""
    spec = get_type(type_name)
    if spec:
        return spec["defaultImage"]
    defaults = load_catalog()["defaults"]
    return defaults.get("host_image")


def resolve_image(type_name: str, explicit_image: str | None = None) -> str:
    """Return the image to deploy for a container.

    An explicit per-container image always wins; otherwise the catalog default
    for the type is used. This is the ONLY place image resolution happens.
    """
    explicit = (explicit_image or "").strip()
    if explicit:
        return explicit
    return default_image_for(type_name)


def image_spec(ref: str) -> ImageSpec | None:
    """What the catalog says about an image ref (None: a plain registry image)."""
    return load_model().images.get((ref or "").strip())


def sources() -> dict[str, SourceSpec]:
    return load_model().sources
