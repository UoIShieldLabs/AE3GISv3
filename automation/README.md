# AE3GISv2 Python Automation Toolkit

This directory contains a complete Python API to programmatically generate and interact with AE3GISv2 Topologies. With this Toolkit, you can leverage standard Python syntax to build extensive, complex Multi-Site and Multi-Subnet environments without needing to use the React Flow UI.

## Features

- **Object-Oriented API**: Simple `TopologyBuilder`, `SiteBuilder`, `SubnetBuilder`, and `ContainerBuilder` methods to progressively assemble your network.
- **Auto-Routing Magic**: The generators intuitively handle bridging gateways. For example, connecting two `Subnets` together will automatically configure `frr` routing paths between their respective routers in the ContainerLab YAML.
- **Strict Pydantic Validation**: Uses exact schema parity with the FastAPI backend to guarantee that generated Topologies will successfully deploy.
- **Direct Backend Push**: You can save generated Topologies as JSON files, or transmit them directly into an active AE3GISv2 node via the API.

## Installation

The generator relies on the `pydantic` package for strict typing. 
If you wish to use the `.push_to_backend` functionality, you must also have `requests` installed.

```bash
pip install pydantic requests
```

## Basic Usage

Detailed documentation and examples can be found in `example.py`.
Here is a crash course on how to generate a basic network:

```python
from automation.builder import TopologyBuilder

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
response = builder.push_to_backend(url="http://localhost:8000", token="your-secret-token")
```

### Connection Rules

- To connect two containers within the same subnet, call `subnet.connect(web, router)`.
- To allow traffic to route between two subnets, call `site.connect_subnets(subnet1, subnet2)`.
- To create a cross-site WAN link, call `builder.connect_sites(site1, site2)`.

*(The backend ContainerLab generators are smart enough to locate the best router in each site/subnet and automatically assign PtP connection interfaces for WAN links).*
