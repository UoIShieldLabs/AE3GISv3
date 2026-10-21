# Benchmark reports

Notebooks that turn the committed benchmark results into reports. They live on
the `benchmarking/results` branch, which merges every host's
`benchmarking/<host>` branch and is never merged to main.

| Notebook | What it shows |
|---|---|
| [`comparison.ipynb`](comparison.ipynb) | The hosts side by side: idle capacity, how alike they measure images, traffic at high and low rates, CPU per Mb/s, data quality, key takeaways |
| [`hosts/m4-macbook-air.ipynb`](hosts/m4-macbook-air.ipynb) | One host's full report (from `host_report.ipynb`) |
| [`hosts/m4-max-mac-studio.ipynb`](hosts/m4-max-mac-studio.ipynb) | 〃 |
| [`hosts/core-ultra-7-surface-laptop-7.ipynb`](hosts/core-ultra-7-surface-laptop-7.ipynb) | 〃 |

Each host report has three parts:
1. **Idle capacity** (`random` suite): census per image, every climb's ceiling and trajectory, and what drives the spread.
2. **Traffic limits** (`traffic` suite):
   - limit grids and the traffic carried;
   - CPU per 100 Mb/s by lab size;
   - what set each limit;
   - latency and loss, the burst interval's effect, lab cost by size;
   - search history.
3. **Data quality:** which traffic driver measured each run, and that driver's symptoms.

## Data

Only what is committed under `backend/benchmark-results/<host>/`:
- each suite folder's `manifest.json`;
- every benchmark's `benchmark.json`, its per-step rows;
- `limits-*.json` and `random-*.json`.

The raw `export.zip` files (time series) stay on each machine, so the reports work from per-step metrics, not samples over time.

Traffic limits are worked out with the runner's own `limit_result` (`backend/scripts/bench_suite.py`), so the grids match each `summary.md`.

Every run counts in the statistics. Known problems from each host's `NOTES.md` are annotated rather than left out; they're listed in `benchlib/hosts.py`. Examples: the Studio's first three climbs ran on a broken Docker, and the Surface's first two climbs have sleep-skewed timings.

**Comparability:** the Studio's and Surface's traffic runs used the traffic driver from before 2026-10-12. Its symptoms are checked in each report and in §6 of the comparison.

## Layout

```
benchlib/hosts.py          host metadata, settings that differ from the shared suites, known issues
benchlib/load.py           results → tidy DataFrames (climbs, steps, census, traffic cells / rows / deploys)
benchlib/random_suite.py   idle summaries
benchlib/traffic_suite.py  traffic summaries, data-quality checks
benchlib/plots.py          shared figures (static matplotlib, so GitHub renders them)
host_report.ipynb          the per-host template (parameter: HOST)
build.py                   runs the template per host and the comparison, outputs saved
```

## Rebuild

```bash
uv run --no-project --with-requirements analysis/requirements.txt python analysis/build.py
```

Run it from the repo root; a plain venv with `pip install -r analysis/requirements.txt` works too. It takes about 20 s.
- **Single host:** add the host's results folder name, e.g. `build.py m4-macbook-air`, to rebuild just that report.
- **Failures:** a cell that fails fails the build, and each notebook starts with sanity checks: complete data, grids that match the runner's.

**When a host has new results** (e.g. the M4 MacBook Air's last traffic cells, or a re-check on another host):
1. Commit them on its `benchmarking/<host>` branch, as `docs/benchmarks/RUNNING.md` describes.
2. Merge that branch into `benchmarking/results`.
3. Rebuild, then commit the notebooks.

**Adding a host:** add it to `benchlib/hosts.py` (`HOSTS` and `ORDER`), then rebuild.
