"""Image fingerprints and statuses (pure).

An image AE3GIS builds is stamped with a *fingerprint* of its build inputs: the
Dockerfile path, every file in the build context (path, executable bit,
contents), and the build args. Recomputing the fingerprint from the current
source and comparing it with the image's label says whether the image is out of
date. It cannot see upstream drift (new apt packages, a moved base image); a
fresh rebuild (``--pull --no-cache``) covers that.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

# Bump when the fingerprint recipe changes, so every image reads as stale once.
BUILD_SCHEMA = "1"

LABEL_FINGERPRINT = "io.ae3gis.fingerprint"
LABEL_SOURCE = "io.ae3gis.source"
LABEL_REF = "io.ae3gis.ref"
LABEL_REVISION = "org.opencontainers.image.revision"
LABEL_CREATED = "org.opencontainers.image.created"

# Entries never part of a build context's identity.
SKIPPED_NAMES = frozenset({".git", ".DS_Store"})

Status = Literal["ready", "missing", "stale", "unmanaged", "unavailable", "building", "failed"]


@dataclass(frozen=True)
class ContextFile:
    path: str  # relative, "/"-separated
    executable: bool
    data: bytes


def fingerprint(files: Iterable[ContextFile], dockerfile: str, args: dict[str, str]) -> str:
    h = hashlib.sha256()
    h.update(f"schema={BUILD_SCHEMA}\0dockerfile={dockerfile}\0".encode())
    for key in sorted(args):
        h.update(f"arg:{key}={args[key]}\0".encode())
    for f in sorted(files, key=lambda f: f.path):
        h.update(f"file:{f.path}\0{int(f.executable)}\0{len(f.data)}\0".encode())
        h.update(f.data)
    return h.hexdigest()


@dataclass(frozen=True)
class StatusInput:
    buildable: bool  # the catalog says AE3GIS builds this image
    present: bool
    built_fingerprint: str | None  # the image's label, if present
    expected_fingerprint: str | None  # from the current source, if readable
    unavailable_reason: str | None = None  # why it cannot be built here, if so
    building: bool = False
    last_build_error: str | None = None  # the most recent build failed with this


def image_status(i: StatusInput) -> tuple[Status, str]:
    """(status, human reason) for one image."""
    if i.building:
        return "building", "Building now"
    if not i.buildable:
        if i.present:
            return "ready", "Present locally"
        return "missing", "Pulled from its registry on first deploy"
    if not i.present:
        if i.unavailable_reason:
            return "unavailable", i.unavailable_reason
        if i.last_build_error:
            return "failed", i.last_build_error
        return "missing", "Built on first deploy"
    if not i.built_fingerprint:
        return "unmanaged", "Built outside AE3GIS; rebuild to track changes"
    if i.expected_fingerprint is None:
        return "ready", "Built; its source is not available to check for changes"
    if i.built_fingerprint != i.expected_fingerprint:
        return "stale", "Its Dockerfile or build files changed since it was built"
    return "ready", "Up to date with its source"
