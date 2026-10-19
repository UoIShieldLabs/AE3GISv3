"""Merging registry snapshots over the built-in catalog (catalog/registry.py)."""

import catalog
from catalog.registry import Candidate, Snapshot, hub_category, merge
from tests.hubfake import standard_labels

BASE = catalog.builtin_model()


def cand(repo: str, labels: dict | None = None, **kw) -> Candidate:
    return Candidate(repo=repo, tag=kw.pop("tag", "latest"), labels=labels, **kw)


def test_an_image_of_a_built_in_type_joins_it_as_a_variant():
    labels = standard_labels("plc", type_name="Ignored", type_role="router")
    labels["org.opencontainers.image.title"] = "OpenPLC (Hub)"
    snap = Snapshot("lab", [cand("openplc", labels, platforms=["linux/amd64"])])
    merged, reports = merge(BASE, [snap])

    plc = merged.types["plc"]
    assert plc.images[-1] == "lab/openplc:latest"
    # the built-in type's fields and default win
    assert plc.role == "host" and plc.defaultImage == BASE.types["plc"].defaultImage
    assert plc.origin is None
    spec = merged.images["lab/openplc:latest"]
    assert spec.displayName == "OpenPLC (Hub)" and spec.platforms == ["linux/amd64"]
    assert spec.source.kind == "registry" and spec.source.registry == "lab"
    assert reports["lab"].loaded == [
        {
            "ref": "lab/openplc:latest",
            "repo": "openplc",
            "tag": "latest",
            "type": "plc",
            "name": "OpenPLC (Hub)",
            "platforms": ["linux/amd64"],
            "new_type": False,
        }
    ]
    # the built-in catalog is untouched
    assert "lab/openplc:latest" not in BASE.types["plc"].images


def test_a_new_type_comes_from_its_default_image():
    a = standard_labels("bastion", type_name="Bastion A", type_role="host")
    b = standard_labels(
        "bastion",
        default="true",
        type_name="Bastion Host",
        type_role="host",
        type_label="BS",
        type_color="#240177",
        type_icon="server",
        type_category="security",
        shell="/bin/sh",
    )
    merged, reports = merge(BASE, [Snapshot("lab", [cand("a-bastion", a), cand("b-bastion", b)])])

    t = merged.types["bastion"]
    assert (t.displayName, t.role, t.label, t.color, t.icon, t.category, t.origin) == (
        "Bastion Host",
        "host",
        "BS",
        "#240177",
        "server",
        "security",
        "lab",
    )
    assert t.defaultImage == "lab/b-bastion:latest"
    assert t.images == ["lab/b-bastion:latest", "lab/a-bastion:latest"]
    assert merged.images["lab/b-bastion:latest"].shell == "/bin/sh"
    assert [c.id for c in merged.categories] == [c.id for c in BASE.categories]
    # a-bastion's differing type name is reported, not fatal
    assert any("a-bastion" in w and "name" in w for w in reports["lab"].warnings)
    assert {i["new_type"] for i in reports["lab"].loaded} == {True}


def test_new_type_defaults_and_its_registry_category():
    labels = standard_labels("honey-pot", type_name="Honeypot", type_role="host")
    merged, _ = merge(BASE, [Snapshot("lab", [cand("canary", labels)])])
    t = merged.types["honey-pot"]
    assert (t.label, t.color, t.icon, t.category) == ("HONE", "#9ca3af", "default", "hub:lab")
    assert merged.categories[-1].model_dump() == {"id": hub_category("lab"), "label": "lab"}


def test_a_new_category_id_gets_a_title():
    labels = standard_labels(
        "dc", type_name="DC", type_role="host", type_category="active-directory"
    )
    merged, _ = merge(BASE, [Snapshot("lab", [cand("dc", labels)])])
    assert merged.categories[-1].model_dump() == {
        "id": "active-directory",
        "label": "Active Directory",
    }


def test_a_new_type_without_name_or_role_is_rejected_whole():
    a = standard_labels("proxy", default="true", type_name="Proxy")  # no role
    b = standard_labels("proxy", type_name="Proxy", type_role="host")
    merged, reports = merge(BASE, [Snapshot("lab", [cand("squid", a), cand("tinyproxy", b)])])
    assert "proxy" not in merged.types
    assert {r["repo"] for r in reports["lab"].rejected} == {"squid", "tinyproxy"}
    assert "io.ae3gis.type.role" in reports["lab"].rejected[0]["reasons"][0]


def test_two_defaults_warn_and_the_first_wins():
    a = standard_labels("ldap", default="true", type_name="LDAP A", type_role="host")
    b = standard_labels("ldap", default="true", type_name="LDAP B", type_role="host")
    merged, reports = merge(BASE, [Snapshot("lab", [cand("b", b), cand("a", a)])])
    assert merged.types["ldap"].displayName == "LDAP A"
    assert any("2 images say io.ae3gis.default" in w for w in reports["lab"].warnings)


def test_bad_labels_errors_and_pending_candidates():
    snap = Snapshot(
        "lab",
        [
            cand("good", standard_labels("plc")),
            cand("nolabels", {}),
            cand("badcolor", standard_labels("x", type_color="red")),
            cand("unreadable", error="could not read its labels: boom"),
            cand("later", pending=True),
        ],
    )
    merged, reports = merge(BASE, [snap])
    r = reports["lab"]
    assert [i["repo"] for i in r.loaded] == ["good"]
    assert {x["repo"] for x in r.rejected} == {"nolabels", "badcolor", "unreadable"}
    assert r.pending == ["later"]
    assert "x" not in merged.types


def test_an_earlier_registry_defines_a_shared_type():
    first = standard_labels("bastion", type_name="First", type_role="host")
    second = standard_labels("bastion", type_name="Second", type_role="router")
    merged, reports = merge(
        BASE,
        [Snapshot("one", [cand("b", first)]), Snapshot("two", [cand("b", second)])],
    )
    t = merged.types["bastion"]
    assert (t.displayName, t.role, t.origin) == ("First", "host", "one")
    assert t.images == ["one/b:latest", "two/b:latest"]
    assert any("comes from registry one" in w for w in reports["two"].warnings)
    assert reports["two"].loaded[0]["new_type"] is False


def test_a_ref_the_built_in_catalog_describes_keeps_its_spec():
    snap = Snapshot("kathara", [cand("frr", standard_labels("router"), tag="latest")])
    builtin = BASE.model_copy(deep=True)
    builtin.images["kathara/frr:latest"] = builtin.images["kathara/frr"]
    merged, reports = merge(builtin, [snap])
    assert merged.images["kathara/frr:latest"] is builtin.images["kathara/frr:latest"]
    assert any("built-in catalog" in w for w in reports["kathara"].warnings)


def test_no_snapshots_is_the_built_in_catalog():
    merged, reports = merge(BASE, [])
    assert merged.types.keys() == BASE.types.keys() and reports == {}
