import pytest

from engine.kathara.naming import lab_hash, lab_name, machine_name


def test_lab_name_depends_only_on_topology_id():
    assert lab_name("702f4e4c7e2e4b4f81eabf7155b2e545") == "ae3gis_702f4e4c7e2e"
    assert lab_name("ABC-123") == "ae3gis_abc123"


def test_lab_hash_matches_kathara():
    # Observed on a real Kathara 3.8 deployment of this lab name.
    assert lab_hash("two_subnet_demo_702f4e4c") == "E5jINFmCmfIehpVUVhCsiw"
    kathara_utils = pytest.importorskip("Kathara.utils")
    assert lab_hash("ae3gis_abc") == kathara_utils.generate_urlsafe_hash("ae3gis_abc")


def test_machine_names_are_safe():
    assert machine_name("Router-A") == "router_a"
    assert machine_name("") == "node"
