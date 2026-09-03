import sys
from pathlib import Path

# Make the backend package root importable (catalog, engine, ...).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
