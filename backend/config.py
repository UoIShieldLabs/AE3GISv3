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

# Auth is OPT-IN. Set AE3GIS_INSTRUCTOR_TOKEN to require a bearer token on every
# API call and WebSocket upgrade. Unset or empty (the default) leaves the API
# open, which suits a local single-user lab but NOT a shared host or anything
# reachable from a network: the API can create and destroy containers.
INSTRUCTOR_TOKEN = os.getenv("AE3GIS_INSTRUCTOR_TOKEN", "").strip()


def auth_required() -> bool:
    """True when a token is configured. Read at call time so tests can patch."""
    return bool(INSTRUCTOR_TOKEN)


# CORS. Comma-separated origins, or "*" for any (dev default).
_cors = os.getenv("AE3GIS_CORS_ORIGINS", "*").strip()
CORS_ORIGINS = ["*"] if _cors == "*" else [o.strip() for o in _cors.split(",") if o.strip()]
