"""Environment-driven configuration.

No engine-specific paths any more (ContainerLab needed a shared host workdir;
Kathara does not). The SQLite DB and any runtime data live under DATA_DIR.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = Path(os.getenv("AE3GIS_DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{os.getenv('AE3GIS_DB_PATH', str(DATA_DIR / 'ae3gis.db'))}"

# Auth. Keep a dev-friendly default but make it overridable; production must set
# AE3GIS_INSTRUCTOR_TOKEN explicitly.
INSTRUCTOR_TOKEN = os.getenv("AE3GIS_INSTRUCTOR_TOKEN", "test")

# CORS. Comma-separated origins, or "*" for any (dev default).
_cors = os.getenv("AE3GIS_CORS_ORIGINS", "*").strip()
CORS_ORIGINS = ["*"] if _cors == "*" else [o.strip() for o in _cors.split(",") if o.strip()]
