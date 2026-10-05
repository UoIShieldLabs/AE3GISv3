"""The checked-in benchmark specs and suites stay runnable: every spec passes
the API's checks, the generator's and the catalog's (as a start would)."""

import json
from pathlib import Path

import pytest

import catalog
from api.schemas import BenchmarkRequest
from domain import benchmark as bm
from domain.generator import GeneratorParams, check, check_catalog
from services.benchmark import _census_params, _check_matrix, _hidden_images

ROOT = Path(__file__).resolve().parent.parent / "benchmarks"
SPECS = sorted((ROOT / "specs").rglob("*.json"))
SUITES = sorted((ROOT / "suites").glob("*.json"))


@pytest.mark.parametrize("path", SPECS, ids=lambda p: str(p.relative_to(ROOT / "specs")))
def test_specs_validate(path):
    spec = BenchmarkRequest.model_validate(json.loads(path.read_text())).model_dump()
    g = dict(spec["topology"]["generate"])
    if spec["census"]:
        cases = bm.census_cases(catalog.node_types(), _hidden_images(), spec["census"]["cases"])
        for case in cases:
            check_catalog(_census_params(spec, case), catalog.node_types())
        return
    scales = [spec["adaptive"]["start"]] if spec["adaptive"] else spec["scale"]
    for hosts in (min(scales), max(scales)):
        p = GeneratorParams(hosts=hosts, **g)
        check(p)
        check_catalog(p, catalog.node_types())
    if spec["matrix"]:
        _check_matrix(spec["matrix"], None, spec, spec["scale"])


@pytest.mark.parametrize("path", SUITES, ids=lambda p: p.name)
def test_suites_name_existing_specs(path):
    suite = json.loads(path.read_text())
    assert suite["name"] == path.stem
    ids = [item["id"] for item in suite["items"]]
    assert len(ids) == len(set(ids))
    for item in suite["items"]:
        assert (ROOT / "specs" / item["spec"]).is_file(), item["spec"]
