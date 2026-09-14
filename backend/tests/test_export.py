import io
import zipfile

import yaml

from domain.export import containerlab, kathara, labspec
from domain.plan import build_lab_plan
from tests.conftest import TWO_SUBNETS


def _plan(iface_base=0):
    return build_lab_plan(TWO_SUBNETS, "ae3gis_demo", iface_base=iface_base)


def test_lab_conf_lists_every_machine_interface_and_image():
    conf = kathara.render_lab_conf(_plan(), description="Demo")
    assert conf.startswith('LAB_DESCRIPTION="Demo"')
    assert 'ra[image]="kathara/frr"' in conf
    assert 'ha[0]="cd' in conf
    # the WAN link between routers shares one collision domain
    ra_cds = {
        line.split('"')[1]
        for line in conf.splitlines()
        if line.startswith("ra[") and "image" not in line
    }
    rb_cds = {
        line.split('"')[1]
        for line in conf.splitlines()
        if line.startswith("rb[") and "image" not in line
    }
    assert ra_cds & rb_cds


def test_kathara_zip_has_startup_files():
    z = zipfile.ZipFile(io.BytesIO(kathara.build_zip(_plan())))
    names = set(z.namelist())
    assert {"lab.conf", "README.txt", "ra.startup", "ha.startup"} <= names
    assert "sysctl -w net.ipv4.ip_forward=1" in z.read("ra.startup").decode()


def test_containerlab_yaml_uses_eth1_and_pairs_links():
    text = containerlab.render_clab_yaml(_plan(iface_base=1), name="demo")
    doc = yaml.safe_load(text)
    assert doc["name"] == "demo"
    nodes = doc["topology"]["nodes"]
    assert nodes["ra"]["kind"] == "linux" and nodes["ra"]["image"] == "kathara/frr"
    assert any("dev eth1" in cmd for cmd in nodes["ha"]["exec"])
    for link in doc["topology"]["links"]:
        assert len(link["endpoints"]) == 2
        assert all(":eth" in e and ":eth0" not in e for e in link["endpoints"])


def test_labspec_shape():
    spec = labspec.to_labspec(_plan(), topology_id="t1", topology_name="Demo")
    assert spec["labspec_version"] == 1 and spec["lab"] == "ae3gis_demo"
    assert {n["machine_name"] for n in spec["nodes"]} == {"ra", "swa", "ha", "rb", "swb", "hb"}
    assert all(len(link["endpoints"]) == 2 for link in spec["links"])
