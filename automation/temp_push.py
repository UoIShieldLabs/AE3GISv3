import sys
from pathlib import Path

repo_root = Path(__file__).parent.parent
sys.path.append(str(repo_root))

from automation.builder import TopologyBuilder

builder = TopologyBuilder(name="Integration Test Push")
site = builder.add_site(name="Push Site", location="Server")
subnet = site.add_subnet(name="Push Subnet", cidr="10.0.0.0/24")
subnet = subnet.add_container(name="Route Dawg", ip="10.0.0.1", type="workstation")
print("Pushing to backend...")
response = builder.push_to_backend(url="http://localhost:8000", token="test")
print(f"Success! ID: {response['id']}")
