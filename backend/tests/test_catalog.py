import catalog


def test_catalog_loads_and_validates():
    data = catalog.load_catalog()
    assert data["types"], "catalog must define node types"
    assert data["defaults"]["host_image"]


def test_roles_are_valid():
    for name in catalog.node_types():
        assert catalog.role_for(name) in catalog.VALID_ROLES


def test_router_and_switch_roles():
    assert catalog.role_for("router") == "router"
    assert catalog.role_for("firewall") == "router"  # firewall behaves as a router in the core
    assert catalog.role_for("switch") == "switch"
    assert catalog.role_for("workstation") == "host"


def test_unknown_type_defaults_to_host():
    assert catalog.role_for("totally-made-up") == "host"


def test_image_resolution_prefers_explicit():
    assert catalog.resolve_image("router") == catalog.default_image_for("router")
    assert catalog.resolve_image("router", "my/router:2.0") == "my/router:2.0"
    # unknown type still resolves to a sane fallback image
    assert catalog.resolve_image("mystery")


def _minimal(**over):
    raw = {
        "version": 2,
        "defaults": {"host_image": "kathara/base"},
        "categories": [{"id": "net", "label": "Network"}],
        "sources": {"repo": {"kind": "git", "url": "https://example.com/r.git"}},
        "images": {
            "ae3gis.local/x": {
                "displayName": "X",
                "source": {"kind": "build", "repo": "repo", "context": "x"},
            }
        },
        "types": {
            "box": {
                "displayName": "Box",
                "role": "host",
                "category": "net",
                "defaultImage": "kathara/base",
                "images": ["kathara/base", "ae3gis.local/x"],
                "color": "#fff",
                "label": "BOX",
                "icon": "default",
            }
        },
    }
    raw.update(over)
    return raw


def test_catalog_v2_describes_images_and_variants():
    model = catalog.load_model()
    assert [c.id for c in model.categories][0] == "network"
    firewall = catalog.get_type("firewall")
    assert firewall["defaultImage"] == "kathara/frr"
    assert "ae3gis.local/nftables" in firewall["images"]
    spec = catalog.image_spec("ae3gis.local/nftables")
    assert spec.source.kind == "build" and spec.source.repo in catalog.sources()
    assert catalog.image_spec("kathara/frr").source.kind == "registry"
    assert catalog.image_spec("some/random:tag") is None
    # every type's images are declared, and every build source exists
    for name, t in catalog.node_types().items():
        assert t["defaultImage"] in t["images"], name


def test_catalog_validation_rejects_inconsistencies():
    import pytest

    catalog.parse_catalog(_minimal())  # the baseline is valid
    bad_default = _minimal()
    bad_default["types"]["box"]["defaultImage"] = "nope"
    bad_repo = _minimal()
    bad_repo["images"]["ae3gis.local/x"]["source"]["repo"] = "missing"
    escape = _minimal()
    escape["images"]["ae3gis.local/x"]["source"]["context"] = "../etc"
    bad_category = _minimal()
    bad_category["types"]["box"]["category"] = "other"
    hidden_default = _minimal()
    hidden_default["images"]["ae3gis.local/x"]["stability"] = "hidden"
    hidden_default["types"]["box"]["defaultImage"] = "ae3gis.local/x"
    for raw in (bad_default, bad_repo, escape, bad_category, hidden_default):
        with pytest.raises(catalog.CatalogError):
            catalog.parse_catalog(raw)


def test_type_without_images_lists_its_default():
    raw = _minimal()
    del raw["types"]["box"]["images"]
    assert catalog.parse_catalog(raw).types["box"].images == ["kathara/base"]
