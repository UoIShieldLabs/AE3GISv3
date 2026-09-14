"""Deterministic names for Kathara labs and machines.

The lab name depends only on the topology id (never its display name, which a
user may change after deploying). The lab hash is what Kathara stamps on every
container; it is derived from the lab name exactly the way Kathara does it, so
a stored state without a hash can still be located.
"""

from __future__ import annotations

import base64
import hashlib
import re

from domain.plan import safe_name


def lab_name(topology_id: str) -> str:
    return f"ae3gis_{re.sub(r'[^a-z0-9]', '', topology_id.lower())[:12] or 'lab'}"


def lab_hash(name: str) -> str:
    """Kathara's ``utils.generate_urlsafe_hash`` (md5, urlsafe b64, no padding/dashes)."""
    digest = hashlib.md5(name.encode("utf-8", errors="ignore")).digest()  # noqa: S324 - not security
    return base64.urlsafe_b64encode(digest)[:-2].decode("utf-8").replace("-", "").replace("_", "")


def machine_name(node_id: str) -> str:
    return safe_name(node_id)
