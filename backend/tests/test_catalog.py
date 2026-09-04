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
