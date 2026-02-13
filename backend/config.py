from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'ae3gis.db'}"
CLAB_WORKDIR = BASE_DIR / "clab-workdir"

# Ensure workdir exists
CLAB_WORKDIR.mkdir(exist_ok=True)
