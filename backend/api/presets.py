"""Preset topology templates shipped in backend/presets."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_db
from api.errors import NotFound
from api.schemas import PresetList, PresetSummary, TopologyRecord
from auth import require_instructor
from config import BASE_DIR
from services import topologies

log = logging.getLogger(__name__)

PRESETS_DIR = BASE_DIR / "presets"

router = APIRouter(prefix="/api/v1/presets", tags=["presets"])


def _load_preset(preset_id: str) -> dict:
    path = (PRESETS_DIR / f"{preset_id}.json").resolve()
    if path.parent != PRESETS_DIR.resolve() or not path.is_file():
        raise NotFound("Preset")
    return json.loads(path.read_text())


@router.get("", response_model=PresetList)
def list_presets():
    presets: list[PresetSummary] = []
    for f in sorted(PRESETS_DIR.glob("*.json")) if PRESETS_DIR.exists() else []:
        try:
            data = json.loads(Path(f).read_text())
        except (json.JSONDecodeError, OSError):
            log.warning("Skipping invalid preset file: %s", f.name)
            continue
        topo = data.get("topology", {}) if isinstance(data.get("topology"), dict) else {}
        presets.append(
            PresetSummary(
                id=f.stem,
                name=data.get("name") or f.stem,
                description=data.get("description", ""),
                scenario_count=len(topo.get("scenarios", []) or []),
                site_count=len(topo.get("sites", []) or []),
            )
        )
    return PresetList(presets=presets)


@router.get("/{preset_id}")
def get_preset(preset_id: str) -> dict:
    return _load_preset(preset_id)


@router.post("/{preset_id}/load", response_model=TopologyRecord, status_code=201)
def load_preset(preset_id: str, db: Session = Depends(get_db), _=Depends(require_instructor)):
    """Create a new topology from a preset template."""
    preset = _load_preset(preset_id)
    data = preset.get("topology") if isinstance(preset.get("topology"), dict) else {}
    topo, diags = topologies.create(db, name=preset.get("name") or preset_id, data=data)
    rec = TopologyRecord.model_validate(topo)
    rec.diagnostics = [d.to_dict() for d in diags]  # type: ignore[assignment]
    return rec
