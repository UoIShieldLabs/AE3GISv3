"""Rebuild the benchmark notebooks from the committed results.

    uv run --no-project --with-requirements analysis/requirements.txt python analysis/build.py [host …]

Runs ``host_report.ipynb`` once per host (``hosts/<slug>.ipynb``) and then
``comparison.ipynb`` in place, with their outputs saved so GitHub shows them.
A failing cell fails the build. Run timestamps are stripped so a rebuild only
changes the notebooks when the results or the code changed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import nbformat
import papermill as pm

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from benchlib.hosts import HOSTS, ORDER  # noqa: E402
from benchlib.load import RESULTS  # noqa: E402


def tidy(path: Path) -> None:
    """Drop papermill's per-run metadata (timings, parameters echo) and give
    pandas' styled tables stable ids (it picks random ones)."""
    nb = nbformat.read(path, as_version=4)
    nb.metadata.pop("papermill", None)
    ids: dict[str, str] = {}

    def stable(m: re.Match) -> str:
        return ids.setdefault(m.group(0), f"T_t{len(ids):03d}")

    for cell in nb.cells:
        cell.metadata.pop("papermill", None)
        cell.metadata.pop("execution", None)
        for out in cell.get("outputs", []):
            html = out.get("data", {}).get("text/html")
            if html:
                text = html if isinstance(html, str) else "".join(html)
                out["data"]["text/html"] = re.sub(r"T_[0-9a-f]{5}(?![0-9a-f])", stable, text)
                plain = "".join(out["data"].get("text/plain", ""))
                if plain.startswith("<pandas.io.formats.style.Styler at"):
                    out["data"]["text/plain"] = "<table>"
        if cell.metadata.get("tags") == ["injected-parameters"]:
            cell.metadata["tags"] = ["parameters"]
            cell["id"] = "parameters"  # papermill draws a new one each run
    nb.cells = [
        c
        for i, c in enumerate(nb.cells)
        if not (
            c.metadata.get("tags") == ["parameters"]
            and i + 1 < len(nb.cells)
            and nb.cells[i + 1].metadata.get("tags") == ["parameters"]
        )
    ]
    nbformat.write(nb, path)


def run(src: Path, dst: Path, **params) -> None:
    print(f"→ {dst.relative_to(HERE)}", flush=True)
    pm.execute_notebook(
        str(src),
        str(dst),
        parameters=params,
        cwd=str(HERE),
        kernel_name="python3",
        progress_bar=False,
    )
    tidy(dst)


def main(argv: list[str]) -> int:
    hosts = [h for h in (argv or ORDER) if (RESULTS / h).is_dir()]
    (HERE / "hosts").mkdir(exist_ok=True)
    for key in hosts:
        run(HERE / "host_report.ipynb", HERE / "hosts" / f"{HOSTS[key].slug}.ipynb", HOST=key)
    if not argv:
        run(HERE / "comparison.ipynb", HERE / "comparison.ipynb")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
