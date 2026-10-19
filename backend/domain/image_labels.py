"""The AE3GIS image standard, v1: node metadata carried by an image's labels.

An image published for AE3GIS says, in OCI labels, which node type it is a
variant of and how to run it; ``docs/image-standard.md`` is the reference for
image authors. A Docker Hub repo opts in with a short description starting
with ``[ae3gis]`` (so other repos in a namespace are never inspected) and its
image with ``io.ae3gis.schema``.

Pure: parses a label dict into what the catalog needs, with one readable error
per bad label (a rejected image shows them to its author).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from catalog.models import check_bridge, check_shell

MARKER = "[ae3gis]"
SCHEMA_VERSIONS = ("1",)

AE3GIS = "io.ae3gis."
OCI = "org.opencontainers.image."

SCHEMA = AE3GIS + "schema"
TYPE = AE3GIS + "type"
DEFAULT = AE3GIS + "default"
STABILITY = AE3GIS + "stability"
SHELL = AE3GIS + "shell"
OWN_BRIDGE = AE3GIS + "own-bridge"
TITLE = OCI + "title"
DESCRIPTION = OCI + "description"

TYPE_NAME = AE3GIS + "type.name"
TYPE_ROLE = AE3GIS + "type.role"
TYPE_LABEL = AE3GIS + "type.label"
TYPE_COLOR = AE3GIS + "type.color"
TYPE_ICON = AE3GIS + "type.icon"
TYPE_CATEGORY = AE3GIS + "type.category"
TYPE_DESCRIPTION = AE3GIS + "type.description"
TYPE_PURDUE = AE3GIS + "type.purdue-level"
TYPE_WEB_UI_PORT = AE3GIS + "type.web-ui-port"

# Labels AE3GIS stamps on images it builds itself (domain/images.py): not part
# of the standard, but not typos either.
_BUILD_LABELS = {AE3GIS + "fingerprint", AE3GIS + "source", AE3GIS + "ref"}

ROLES = ("router", "switch", "host")
ICONS = (
    "router",
    "switch",
    "firewall",
    "server",
    "workstation",
    "plc",
    "hmi",
    "ids",
    "siem",
    "attacker",
)
_ID = re.compile(r"[a-z][a-z0-9-]{0,39}")
_COLOR = re.compile(r"#[0-9a-fA-F]{6}")


def is_candidate(description: str | None) -> bool:
    """Whether a Docker Hub repo opts in (its short description starts with the marker)."""
    return (description or "").strip().lower().startswith(MARKER)


def relevant(labels: dict[str, str] | None) -> dict[str, str]:
    """The labels the standard reads (an image's others are never stored)."""
    return {k: v for k, v in (labels or {}).items() if k.startswith((AE3GIS, OCI))}


@dataclass
class TypeMeta:
    """``io.ae3gis.type.*``: used only when the type is not a built-in one."""

    name: str | None = None
    role: str | None = None
    label: str | None = None
    color: str | None = None
    icon: str | None = None
    category: str | None = None
    description: str | None = None
    purdue_level: float | None = None
    web_ui_port: int | None = None

    def given(self) -> dict[str, object]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class ImageLabels:
    type: str
    title: str | None = None
    description: str | None = None
    default: bool = False
    stability: str = "stable"
    shell: str | None = None
    own_bridge: str | None = None
    type_meta: TypeMeta = field(default_factory=TypeMeta)


@dataclass
class Parsed:
    image: ImageLabels | None
    errors: list[str]
    warnings: list[str]


def _text(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("must not be empty")
    return v


def _id(v: str) -> str:
    if not _ID.fullmatch(v):
        raise ValueError("must be a lowercase id: a letter, then letters, digits or '-' (≤40)")
    return v


def _bool(v: str) -> bool:
    if v.strip().lower() not in ("true", "false"):
        raise ValueError("must be true or false")
    return v.strip().lower() == "true"


def _one_of(*choices: str):
    def parse(v: str) -> str:
        if v not in choices:
            raise ValueError(f"must be one of {', '.join(choices)}")
        return v

    return parse


def _label(v: str) -> str:
    v = v.strip()
    if not 1 <= len(v) <= 5:
        raise ValueError("must be 1 to 5 characters")
    return v


def _color(v: str) -> str:
    if not _COLOR.fullmatch(v):
        raise ValueError("must be a #rrggbb color")
    return v.lower()


def _purdue(v: str) -> float:
    try:
        n = float(v)
    except ValueError:
        raise ValueError("must be a number from 0 to 5") from None
    if not 0 <= n <= 5:
        raise ValueError("must be a number from 0 to 5")
    return n


def _port(v: str) -> int:
    if not v.isdigit() or not 1 <= int(v) <= 65535:
        raise ValueError("must be a port number (1-65535)")
    return int(v)


# label → (where it goes, parser). "image.x" sets ImageLabels.x, "type.x" TypeMeta.x.
_FIELDS = {
    TYPE: ("image.type", _id),
    TITLE: ("image.title", _text),
    DESCRIPTION: ("image.description", _text),
    DEFAULT: ("image.default", _bool),
    STABILITY: ("image.stability", _one_of("stable", "experimental")),
    SHELL: ("image.shell", check_shell),
    OWN_BRIDGE: ("image.own_bridge", check_bridge),
    TYPE_NAME: ("type.name", _text),
    TYPE_ROLE: ("type.role", _one_of(*ROLES)),
    TYPE_LABEL: ("type.label", _label),
    TYPE_COLOR: ("type.color", _color),
    TYPE_ICON: ("type.icon", _one_of(*ICONS)),
    TYPE_CATEGORY: ("type.category", _id),
    TYPE_DESCRIPTION: ("type.description", _text),
    TYPE_PURDUE: ("type.purdue_level", _purdue),
    TYPE_WEB_UI_PORT: ("type.web_ui_port", _port),
}


def parse_image_labels(labels: dict[str, str] | None) -> Parsed:
    """Read an image's labels against the standard.

    No ``io.ae3gis.schema``, an unknown schema version, a missing type or any
    bad value make ``errors`` (the image is rejected); unknown ``io.ae3gis.*``
    keys only warn (likely typos).
    """
    labels = labels or {}
    if SCHEMA not in labels:
        return Parsed(None, [f"no {SCHEMA} label: the image does not follow the standard"], [])
    version = labels[SCHEMA].strip()
    if version not in SCHEMA_VERSIONS:
        return Parsed(
            None,
            [
                f"{SCHEMA}={version!r} is not supported "
                f"(this AE3GIS reads {', '.join(SCHEMA_VERSIONS)})"
            ],
            [],
        )

    errors: list[str] = []
    warnings: list[str] = []
    image: dict[str, object] = {}
    meta: dict[str, object] = {}
    for key, value in sorted(labels.items()):
        if key == SCHEMA or key in _BUILD_LABELS:
            continue
        if key not in _FIELDS:
            if key.startswith(AE3GIS):
                warnings.append(f"unknown label {key} (ignored)")
            continue
        target, parse = _FIELDS[key]
        try:
            parsed = parse(value)
        except ValueError as exc:
            errors.append(f"{key}={value!r}: {exc}")
            continue
        scope, name = target.split(".", 1)
        (image if scope == "image" else meta)[name] = parsed

    if "type" not in image and not any(e.startswith(TYPE + "=") for e in errors):
        errors.append(f"{TYPE} is required: the node type this image is a variant of")
    if errors:
        return Parsed(None, errors, warnings)
    return Parsed(ImageLabels(**image, type_meta=TypeMeta(**meta)), [], warnings)  # type: ignore[arg-type]
