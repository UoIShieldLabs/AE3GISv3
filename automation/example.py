#!/usr/bin/env python3
"""
Example script demonstrating how to use the AE3GISv2 TopologyBuilder.
This builds a multi-site network and exports it to enterprise_topology.json
"""

import sys
from pathlib import Path

# Provide a convenience to run this from the repo root
sys.path.append(str(Path(__file__).parent.parent))

from automation.builder import TopologyBuilder


def main():
    print("Building Enterprise Topology...")
    
    # 1. Initialize the builder
    builder = TopologyBuilder(name="Automated Enterprise")

    # 2. Add Sites
    site_hq = builder.add_site(name="Headquarters", location="New York", x=100, y=100)
    site_branch = builder.add_site(name="Branch Office", location="London", x=800, y=100)

    # 3. Add Subnets to Sites
    # The HQ site has a main LAN and a DMZ
    subnet_hq_lan = site_hq.add_subnet(name="HQ-LAN", cidr="10.0.0.0/24")
    subnet_hq_dmz = site_hq.add_subnet(name="HQ-DMZ", cidr="10.0.1.0/24")
    
    # The Branch site just has a single LAN
    subnet_branch_lan = site_branch.add_subnet(name="Branch-LAN", cidr="10.1.0.0/24")

    # 4. Add Containers to Subnets
    # Populate HQ LAN
    hq_router = subnet_hq_lan.add_container(name="hq-core-router", type="router", ip="10.0.0.1")
    hq_switch = subnet_hq_lan.add_container(name="hq-core-switch", type="switch", ip="10.0.0.2")
    hq_ws1 = subnet_hq_lan.add_container(name="hq-workstation-1", type="workstation", ip="10.0.0.10")
    hq_ws2 = subnet_hq_lan.add_container(name="hq-workstation-2", type="workstation", ip="10.0.0.11")

    # Wire up HQ LAN (Workstations -> Switch -> Router)
    subnet_hq_lan.connect(from_container=hq_ws1, to_container=hq_switch)
    subnet_hq_lan.connect(from_container=hq_ws2, to_container=hq_switch)
    subnet_hq_lan.connect(from_container=hq_switch, to_container=hq_router)

    # Populate HQ DMZ
    # We add a firewall, and two servers
    hq_fw = subnet_hq_dmz.add_container(name="hq-firewall", type="firewall", ip="10.0.1.1")
    hq_web = subnet_hq_dmz.add_container(name="hq-web-server", type="web-server", ip="10.0.1.80")
    hq_file = subnet_hq_dmz.add_container(name="hq-file-server", type="file-server", ip="10.0.1.250")

    # Wire up HQ DMZ
    subnet_hq_dmz.connect(from_container=hq_web, to_container=hq_fw)
    subnet_hq_dmz.connect(from_container=hq_file, to_container=hq_fw)

    # Connect the HQ LAN to the HQ DMZ so they can route to each other
    # Because we connect subnets, the clab generator will automatically link the gateway
    # routers (hq-core-router <-> hq-firewall)
    site_hq.connect_subnets(from_subnet=subnet_hq_lan, to_subnet=subnet_hq_dmz, label="Internal Link")

    # Populate Branch LAN
    br_router = subnet_branch_lan.add_container(name="br-router", type="router", ip="10.1.0.1")
    br_plc = subnet_branch_lan.add_container(name="br-plc-controller", type="plc", ip="10.1.0.50")

    # Wire up Branch LAN
    subnet_branch_lan.connect(from_container=br_plc, to_container=br_router)

    # 5. Connect Sites (WAN Link)
    # The clab generator auto-detects that hq-core-router (the first router in HQ)
    # and br-router (first router in Branch) should be connected and handles auto-IP assignment.
    builder.connect_sites(from_site=site_hq, to_site=site_branch, label="WAN IPSEC")

    # 6. Save to JSON
    output_path = Path(__file__).parent / "enterprise_topology.json"
    builder.save(str(output_path))
    print(f"✅ Successfully wrote topology to {output_path}")


if __name__ == "__main__":
    main()
