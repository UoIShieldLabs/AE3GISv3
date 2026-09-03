"""Declarative node-type catalog — the single source of truth for node types.

Loaded once from ``node_types.json``. Both the deployment engine (to pick a
container image and decide how to configure a node) and the frontend (served via
``GET /api/catalog``) consume this. Images are data here, never hardcoded in
Python, so a new image set ships by editing the JSON only.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_CATALOG_PATH = Path(__file__).resolve().parent / "node_types.json"

VALID_ROLES = {"router", "switch", "host"}


class CatalogError(RuntimeError):
    """Raised when the catalog file is missing or malformed."""


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    """Load, validate, and cache the node-type catalog."""
    try:
        raw = json.loads(_CATALOG_PATH.read_text())
    except FileNotFoundError as exc:  # pragma: no cover - config error
        raise CatalogError(f"Catalog file not found: {_CATALOG_PATH}") from exc
    except json.JSONDecodeError as exc:  # pragma: no cover - config error
        raise CatalogError(f"Catalog file is not valid JSON: {exc}") from exc

    types = raw.get("types")
    if not isinstance(types, dict) or not types:
        raise CatalogError("Catalog must contain a non-empty 'types' object")

    for name, spec in types.items():
        role = spec.get("role")
        if role not in VALID_ROLES:
            raise CatalogError(
                f"Node type '{name}' has invalid role {role!r} (expected one of {sorted(VALID_ROLES)})"
            )
        if not spec.get("defaultImage"):
            raise CatalogError(f"Node type '{name}' is missing 'defaultImage'")

    defaults = raw.get("defaults", {})
    if not defaults.get("host_image"):
        raise CatalogError("Catalog 'defaults.host_image' is required as a fallback")

    return raw


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
