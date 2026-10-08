"""The image standard's label parser (domain/image_labels.py)."""

import pytest

from domain.image_labels import is_candidate, parse_image_labels, relevant


def test_the_marker_opts_a_repo_in():
    assert is_candidate("[ae3gis] OpenSSH bastion")
    assert is_candidate("  [AE3GIS] anything")
    assert not is_candidate("OpenSSH bastion [ae3gis]")
    assert not is_candidate("server database postgres #240177 DB 1.0 latest #")
    assert not is_candidate(None) and not is_candidate("")


def test_only_the_standard_keys_are_kept():
    labels = {
        "io.ae3gis.type": "plc",
        "org.opencontainers.image.title": "PLC",
        "maintainer": "someone",
        "com.example.x": "y",
    }
    assert relevant(labels) == {
        "io.ae3gis.type": "plc",
        "org.opencontainers.image.title": "PLC",
    }


def test_minimal_image():
    p = parse_image_labels({"io.ae3gis.schema": "1", "io.ae3gis.type": "plc"})
    assert p.errors == [] and p.warnings == []
    assert p.image.type == "plc" and p.image.stability == "stable" and not p.image.default
    assert p.image.type_meta.given() == {}


def test_every_label():
    p = parse_image_labels(
        {
            "io.ae3gis.schema": "1",
            "io.ae3gis.type": "bastion",
            "org.opencontainers.image.title": "OpenSSH bastion",
            "org.opencontainers.image.description": "Jump host",
            "io.ae3gis.default": "TRUE",
            "io.ae3gis.stability": "experimental",
            "io.ae3gis.shell": "/bin/sh",
            "io.ae3gis.own-bridge": "br0",
            "io.ae3gis.type.name": "Bastion Host",
            "io.ae3gis.type.role": "host",
            "io.ae3gis.type.label": "BS",
            "io.ae3gis.type.color": "#24AB77",
            "io.ae3gis.type.icon": "server",
            "io.ae3gis.type.category": "security",
            "io.ae3gis.type.description": "A jump host",
            "io.ae3gis.type.purdue-level": "3.5",
            "io.ae3gis.type.web-ui-port": "8080",
        }
    )
    assert p.errors == []
    img = p.image
    assert (img.title, img.description, img.default, img.stability) == (
        "OpenSSH bastion",
        "Jump host",
        True,
        "experimental",
    )
    assert (img.shell, img.own_bridge) == ("/bin/sh", "br0")
    assert img.type_meta.given() == {
        "name": "Bastion Host",
        "role": "host",
        "label": "BS",
        "color": "#24ab77",
        "icon": "server",
        "category": "security",
        "description": "A jump host",
        "purdue_level": 3.5,
        "web_ui_port": 8080,
    }


def test_images_without_the_schema_label_are_rejected():
    p = parse_image_labels({"io.ae3gis.type": "plc"})
    assert p.image is None and "io.ae3gis.schema" in p.errors[0]
    assert parse_image_labels(None).image is None


def test_an_unknown_schema_version_is_rejected():
    p = parse_image_labels({"io.ae3gis.schema": "2", "io.ae3gis.type": "plc"})
    assert p.image is None and "not supported" in p.errors[0]


def test_the_type_is_required():
    p = parse_image_labels({"io.ae3gis.schema": "1"})
    assert p.image is None and p.errors == [
        "io.ae3gis.type is required: the node type this image is a variant of"
    ]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("io.ae3gis.type", "Bad Type"),
        ("io.ae3gis.default", "yes"),
        ("io.ae3gis.stability", "hidden"),
        ("io.ae3gis.shell", "sh"),
        ("io.ae3gis.own-bridge", "a bridge name too long"),
        ("io.ae3gis.type.role", "firewall"),
        ("io.ae3gis.type.label", "TOOLONG"),
        ("io.ae3gis.type.color", "red"),
        ("io.ae3gis.type.icon", "rocket"),
        ("io.ae3gis.type.category", "Security"),
        ("io.ae3gis.type.purdue-level", "7"),
        ("io.ae3gis.type.web-ui-port", "http"),
        ("org.opencontainers.image.title", "  "),
    ],
)
def test_each_bad_value_is_named(key, value):
    labels = {"io.ae3gis.schema": "1", "io.ae3gis.type": "plc", key: value}
    p = parse_image_labels(labels)
    assert p.image is None
    assert any(e.startswith(f"{key}=") for e in p.errors), p.errors


def test_unknown_keys_warn_and_build_labels_are_ignored():
    p = parse_image_labels(
        {
            "io.ae3gis.schema": "1",
            "io.ae3gis.type": "plc",
            "io.ae3gis.type.colour": "#000000",
            "io.ae3gis.fingerprint": "abc",
        }
    )
    assert p.image is not None and p.errors == []
    assert p.warnings == ["unknown label io.ae3gis.type.colour (ignored)"]
