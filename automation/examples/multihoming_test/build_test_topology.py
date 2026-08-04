import sys, json
from pathlib import Path

# This file lives at automation/examples/multihoming_test/ — walk up to the
# repo root so `automation.builder` imports regardless of where it's run from.
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from automation.builder import TopologyBuilder

b = TopologyBuilder(name="ae3gis-multihoming-test")
site = b.add_site(name="Enterprise", location="Test")

# ── Transit links (Section 3.1) ─────────────────────────────
isp_transit   = site.add_subnet(name="ISP Transit", cidr="203.0.113.0/30")
edge_perim    = site.add_subnet(name="Edge-Perimeter Transit", cidr="10.255.255.0/30")
perim_int     = site.add_subnet(name="Perimeter-Internal Transit", cidr="10.255.255.4/30")

# ── VLANs (Section 3.2) ─────────────────────────────────────
dmz     = site.add_subnet(name="DMZ", cidr="172.16.10.0/24", gateway="172.16.10.1")
servers = site.add_subnet(name="Servers", cidr="10.1.20.0/24", gateway="10.1.20.1")
users   = site.add_subnet(name="Users", cidr="10.1.30.0/24", gateway="10.1.30.1")
mgmt    = site.add_subnet(name="MgmtSec", cidr="10.1.99.0/24", gateway="10.1.99.1")

# ── isp + edge-rtr (2 legs) ──────────────────────────────────
isp = isp_transit.add_container(name="isp", type="router", ip="203.0.113.1")
edge_rtr_wan = isp_transit.add_container(name="edge-rtr", type="router", ip="203.0.113.2")
isp_transit.connect(isp, edge_rtr_wan)

edge_rtr_lan = edge_perim.add_container(name="edge-rtr", type="router", ip="10.255.255.1")
# same logical box -> reuse edge_rtr_wan's id for the second leg
edge_rtr_lan.container.id = edge_rtr_wan.id

# ── perim-fw (3 legs): wan(edge_perim) / dmz / int(perim_int) ──
perim_fw_wan = edge_perim.add_container(name="perim-fw", type="firewall", ip="10.255.255.2")
edge_perim.connect(edge_rtr_lan, perim_fw_wan)

perim_fw_dmz = dmz.add_container(name="perim-fw", type="firewall", ip="172.16.10.1")
perim_fw_dmz.container.id = perim_fw_wan.id

perim_fw_int = perim_int.add_container(name="perim-fw", type="firewall", ip="10.255.255.5")
perim_fw_int.container.id = perim_fw_wan.id

# ── int-fw (4 legs): wan(perim_int) / servers / users / mgmt ───
int_fw_wan = perim_int.add_container(name="int-fw", type="firewall", ip="10.255.255.6")
perim_int.connect(perim_fw_int, int_fw_wan)

int_fw_servers = servers.add_container(name="int-fw", type="firewall", ip="10.1.20.1")
int_fw_servers.container.id = int_fw_wan.id
int_fw_users = users.add_container(name="int-fw", type="firewall", ip="10.1.30.1")
int_fw_users.container.id = int_fw_wan.id
int_fw_mgmt = mgmt.add_container(name="int-fw", type="firewall", ip="10.1.99.1")
int_fw_mgmt.container.id = int_fw_wan.id

# ── sample hosts to prove host-side routing works ───────────
dmz_web = dmz.add_container(name="dmz-web", type="web-server", ip="172.16.10.10")
dmz.connect(dmz_web, perim_fw_dmz)

srv_squid = servers.add_container(name="squid", type="workstation", ip="10.1.20.60")
servers.connect(srv_squid, int_fw_servers)

usr_ws01 = users.add_container(name="ws-01", type="workstation", ip="10.1.30.101")
users.connect(usr_ws01, int_fw_users)

mgmt_jump = mgmt.add_container(name="jump", type="workstation", ip="10.1.99.10")
mgmt.connect(mgmt_jump, int_fw_mgmt)

data = b.to_dict()
out_path = Path(__file__).resolve().parent / "test_topology.json"
json.dump(data, open(out_path, "w"), indent=2)
print("wrote test_topology.json")
