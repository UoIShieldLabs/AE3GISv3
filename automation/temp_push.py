import sys
from pathlib import Path
# Add the parent folder (AE3GISv2) to your Python path
sys.path.append(str(Path(__file__).parent.parent))

from  automation.builder import TopologyBuilder

# Initialize a new topology
builder = TopologyBuilder(name="Automated Enterprise")

# 1. Create a Site
site_hq = builder.add_site(name="Headquarters", location="New York", x=100, y=100)

# 2. Add a Subnet
subnet_dmz = site_hq.add_subnet(name="HQ-DMZ", cidr="10.0.1.0/24")

# 3. Add Containers to the Subnet
router = subnet_dmz.add_container(name="dmz-router", type="router", ip="10.0.1.1")
web1 = subnet_dmz.add_container(name="web-01", type="web-server", ip="10.0.1.10")

# 4. Connect the Containers
subnet_dmz.connect(from_container=web1, to_container=router)

# 5. Export or Push
builder.save("my_topology.json")

# Or Push Directly to backend:
response = builder.push_to_backend(url="http://localhost:8000", token="test")
