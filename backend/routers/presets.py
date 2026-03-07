"""Preset topology+scenario templates shipped with AE3GIS."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import require_instructor
from database import get_db
from models import Topology

log = logging.getLogger(__name__)

PRESETS_DIR = Path(__file__).resolve().parent.parent / "presets"

router = APIRouter(prefix="/api/presets", tags=["presets"])


def _load_preset(preset_id: str) -> dict:
    """Load and return a preset JSON file by id (filename without extension)."""
    path = PRESETS_DIR / f"{preset_id}.json"
    if not path.exists() or not path.is_file():
        raise HTTPException(404, f"Preset '{preset_id}' not found")
    # Prevent path traversal
    if not path.resolve().parent == PRESETS_DIR.resolve():
        raise HTTPException(404, f"Preset '{preset_id}' not found")
    return json.loads(path.read_text())


@router.get("")
def list_presets():
    """List all available preset templates."""
    presets = []
    if not PRESETS_DIR.exists():
        return {"presets": []}
    for f in sorted(PRESETS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            presets.append({
                "id": f.stem,
                "name": data.get("name") or f.stem,
                "description": data.get("description", ""),
                "scenario_count": len(data.get("topology", {}).get("scenarios", [])),
                "site_count": len(data.get("topology", {}).get("sites", [])),
            })
        except (json.JSONDecodeError, KeyError):
            log.warning("Skipping invalid preset file: %s", f.name)
    return {"presets": presets}


@router.get("/{preset_id}")
def get_preset(preset_id: str):
    """Get full preset data (topology + metadata)."""
    return _load_preset(preset_id)


@router.post("/{preset_id}/load", status_code=201)
def load_preset(
    preset_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_instructor),
):
    """Create a new topology from a preset template."""
    preset = _load_preset(preset_id)
    topology_data = preset.get("topology", {})
    name = preset.get("name") or preset_id

    topo = Topology(
        name=name,
        data=topology_data,
    )
    db.add(topo)
    db.commit()
    db.refresh(topo)

    return {
        "id": topo.id,
        "name": topo.name,
        "status": topo.status,
        "created_at": str(topo.created_at),
    }
