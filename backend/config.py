import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = f"sqlite:///{os.getenv('AE3GIS_DB_PATH', str(BASE_DIR / 'ae3gis.db'))}"
CLAB_WORKDIR = Path(os.getenv("AE3GIS_CLAB_WORKDIR", str(BASE_DIR / "clab-workdir")))

# Ensure workdir exists
CLAB_WORKDIR.mkdir(exist_ok=True)

# Auth
INSTRUCTOR_TOKEN = os.getenv("AE3GIS_INSTRUCTOR_TOKEN", "test")

# LLM
LLM_BASE_URL = os.getenv("AE3GIS_LLM_BASE_URL", "http://localhost:11434/v1")
LLM_API_KEY = os.getenv("AE3GIS_LLM_API_KEY", "ollama")  # Ollama doesn't need a real key
LLM_MODEL = os.getenv("AE3GIS_LLM_MODEL", "openai/gpt-oss-120b")
