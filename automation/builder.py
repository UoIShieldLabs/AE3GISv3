import json
from typing import Optional, Union, Dict, Any

from automation.models import (
    TopologyData,
    Site,
    Subnet,
    Container,
    Connection,
    Position,
    ContainerType,
)

class ContainerBuilder:
    def __init__(self, subnet_builder: "SubnetBuilder", container: Container):
        self.subnet = subnet_builder
        self.container = container

    @property
    def id(self) -> str:
        return self.container.id


class SubnetBuilder:
    def __init__(self, site_builder: "SiteBuilder", subnet: Subnet):
        self.site = site_builder
        self.subnet = subnet
        self.containers: Dict[str, ContainerBuilder] = {}

    @property
    def id(self) -> str:
        return self.subnet.id

    def add_container(
        self,
        name: str,
        type: ContainerType,
        ip: str,
        kind: Optional[str] = None,
        image: Optional[str] = None,
        **kwargs
    ) -> ContainerBuilder:
        container = Container(
            name=name, type=type, ip=ip, kind=kind, image=image, **kwargs
        )
        self.subnet.containers.append(container)
        builder = ContainerBuilder(self, container)
        self.containers[container.id] = builder
        return builder

    def connect(
        self,
        from_container: Union[ContainerBuilder, str],
        to_container: Union[ContainerBuilder, str],
        label: Optional[str] = None,
        from_interface: Optional[str] = None,
        to_interface: Optional[str] = None,
    ) -> Connection:
        """Connect two containers within this subnet."""
        from_id = from_container.id if isinstance(from_container, ContainerBuilder) else from_container
        to_id = to_container.id if isinstance(to_container, ContainerBuilder) else to_container

        connection = Connection(
            from_=from_id,
            to=to_id,
            label=label,
            fromInterface=from_interface,
            toInterface=to_interface,
            fromContainer=from_id,
            toContainer=to_id,
        )
        self.subnet.connections.append(connection)
        return connection


class SiteBuilder:
    def __init__(self, topology_builder: "TopologyBuilder", site: Site):
        self.topology = topology_builder
        self.site = site
        self.subnets: Dict[str, SubnetBuilder] = {}

    @property
    def id(self) -> str:
        return self.site.id

    def add_subnet(
        self, name: str, cidr: str, gateway: Optional[str] = None
    ) -> SubnetBuilder:
        subnet = Subnet(name=name, cidr=cidr, gateway=gateway)
        self.site.subnets.append(subnet)
        builder = SubnetBuilder(self, subnet)
        self.subnets[subnet.id] = builder
        return builder

    def connect_subnets(
        self,
        from_subnet: Union[SubnetBuilder, str],
        to_subnet: Union[SubnetBuilder, str],
        label: Optional[str] = None,
    ) -> Connection:
        """Connect two subnets within this site (typically relies on auto-gateway routing)."""
        from_id = from_subnet.id if isinstance(from_subnet, SubnetBuilder) else from_subnet
        to_id = to_subnet.id if isinstance(to_subnet, SubnetBuilder) else to_subnet

        connection = Connection(
            from_=from_id,
            to=to_id,
            label=label,
        )
        self.site.subnetConnections.append(connection)
        return connection


class TopologyBuilder:
    def __init__(self, name: Optional[str] = None):
        self.topology = TopologyData(name=name)
        self.sites: Dict[str, SiteBuilder] = {}

    def add_site(
        self, name: str, location: str, x: float = 0, y: float = 0
    ) -> SiteBuilder:
        site = Site(name=name, location=location, position=Position(x=x, y=y))
        self.topology.sites.append(site)
        builder = SiteBuilder(self, site)
        self.sites[site.id] = builder
        return builder

    def connect_sites(
        self,
        from_site: Union[SiteBuilder, str],
        to_site: Union[SiteBuilder, str],
        label: Optional[str] = None,
    ) -> Connection:
        """Connect two sites directly (relies on auto-discovery of best gateway router)."""
        from_id = from_site.id if isinstance(from_site, SiteBuilder) else from_site
        to_id = to_site.id if isinstance(to_site, SiteBuilder) else to_site

        connection = Connection(
            from_=from_id,
            to=to_id,
            label=label,
        )
        self.topology.siteConnections.append(connection)
        return connection

    def connect(
        self,
        from_node: Union[ContainerBuilder, SubnetBuilder, SiteBuilder, str],
        to_node: Union[ContainerBuilder, SubnetBuilder, SiteBuilder, str],
        label: Optional[str] = None,
        from_interface: Optional[str] = None,
        to_interface: Optional[str] = None,
    ) -> Connection:
        """
        Generic top-level connection method for making topology-level siteConnections.
        Mainly useful for site-to-site WAN links or connecting extremely remote containers.
        """
        from_id = from_node.id if hasattr(from_node, "id") else str(from_node)
        to_id = to_node.id if hasattr(to_node, "id") else str(to_node)

        connection_kwargs = {
            "from_": from_id,
            "to": to_id,
            "label": label,
        }
        
        # If the user explicitly provided interfaces, pass them
        if from_interface:
            connection_kwargs["fromInterface"] = from_interface
        if to_interface:
            connection_kwargs["toInterface"] = to_interface
            
        # If the user is definitely connecting containers, helpfully set these fields too
        # so frontend rendering is complete.
        if isinstance(from_node, ContainerBuilder):
            connection_kwargs["fromContainer"] = from_id
        if isinstance(to_node, ContainerBuilder):
            connection_kwargs["toContainer"] = to_id

        connection = Connection(**connection_kwargs)
        self.topology.siteConnections.append(connection)
        return connection

    def to_dict(self) -> dict:
        """Convert the built topology to a dict suitable for JSON serialization."""
        return self.topology.model_dump(by_alias=True)

    def to_json(self, indent: int = 2) -> str:
        """Convert the built topology to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, filepath: str, indent: int = 2) -> None:
        """Save the built topology JSON to a file."""
        with open(filepath, "w") as f:
            f.write(self.to_json(indent=indent))
