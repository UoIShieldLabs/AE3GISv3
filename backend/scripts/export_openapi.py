"""Write (or check) backend/openapi.json from the live app definition.

    python scripts/export_openapi.py          # regenerate
    python scripts/export_openapi.py --check  # fail if the file is out of date (CI)

The frontend generates its TypeScript API types from this file.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import Settings  # noqa: E402
from engine.fake import FakeEngine  # noqa: E402
from main import create_app  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "openapi.json"


def build() -> str:
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(data_dir=Path(tmp), db_path=Path(tmp) / "openapi.db", engine="fake")
        spec = create_app(settings, FakeEngine()).openapi()
    return json.dumps(spec, indent=2, sort_keys=True) + "\n"


def main() -> int:
    content = build()
    if "--check" in sys.argv:
        if OUT.exists() and OUT.read_text() == content:
            return 0
        print(f"{OUT} is out of date; run: python scripts/export_openapi.py", file=sys.stderr)
        return 1
    OUT.write_text(content)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
