import type { TopologyData, Site, Subnet, Container, Connection } from '../data/sampleTopology';
import { generateId } from '../utils/idGenerator';
import { getNextAvailableIp } from '../utils/validation';

export type DeployStatus = 'idle' | 'deployed' | 'error' | 'deploying' | 'destroying';

export interface TopologyState {
  topology: TopologyData;
  backendId: string | null;
  backendName: string | null;
  deployStatus: DeployStatus;
  dirty: boolean;
}

export type TopologyAction =
  // Sites
  | { type: 'ADD_SITE'; payload: Site }
  | { type: 'UPDATE_SITE'; payload: { siteId: string; updates: Partial<Omit<Site, 'id' | 'subnets' | 'subnetConnections'>> } }
  | { type: 'DELETE_SITE'; payload: { siteId: string } }
  // Subnets
  | { type: 'ADD_SUBNET'; payload: { siteId: string; subnet: Subnet } }
  | { type: 'UPDATE_SUBNET'; payload: { siteId: string; subnetId: string; updates: Partial<Omit<Subnet, 'id' | 'containers' | 'connections'>> } }
  | { type: 'DELETE_SUBNET'; payload: { siteId: string; subnetId: string } }
  // Containers
  | { type: 'ADD_CONTAINER'; payload: { siteId: string; subnetId: string; container: Container } }
  | { type: 'UPDATE_CONTAINER'; payload: { siteId: string; subnetId: string; containerId: string; updates: Partial<Omit<Container, 'id'>> } }
  | { type: 'DELETE_CONTAINER'; payload: { siteId: string; subnetId: string; containerId: string } }
  // Site connections
  | { type: 'ADD_SITE_CONNECTION'; payload: Connection }
  | { type: 'DELETE_SITE_CONNECTION'; payload: { from: string; to: string } }
  // Inter-subnet connections (subnet-to-subnet within a site)
  | { type: 'ADD_INTER_SUBNET_CONNECTION'; payload: { siteId: string; connection: Connection } }
  | { type: 'DELETE_INTER_SUBNET_CONNECTION'; payload: { siteId: string; from: string; to: string } }
  // Subnet connections (container-to-container within a subnet)
  | { type: 'ADD_SUBNET_CONNECTION'; payload: { siteId: string; subnetId: string; connection: Connection } }
  | { type: 'DELETE_SUBNET_CONNECTION'; payload: { siteId: string; subnetId: string; from: string; to: string } }
  // Bulk
  | { type: 'LOAD_TOPOLOGY'; payload: TopologyData }
  // Backend integration
  | { type: 'SET_BACKEND_INFO'; payload: { id: string; name: string; status: string } }
  | { type: 'SET_DEPLOY_STATUS'; payload: DeployStatus }
  | { type: 'MARK_CLEAN' }
  | { type: 'CLEAR_BACKEND' }
  | { type: 'UPDATE_CONTAINER_STATUSES'; payload: { statuses: Record<string, 'running' | 'stopped' | 'paused'> } };

export function topologyReducer(draft: TopologyState, action: TopologyAction) {
  switch (action.type) {
    // ── Sites ──
    case 'ADD_SITE':
      draft.topology.sites.push(action.payload);
      draft.dirty = true;
      break;

    case 'UPDATE_SITE': {
      const site = draft.topology.sites.find(s => s.id === action.payload.siteId);
      if (site) Object.assign(site, action.payload.updates);
      draft.dirty = true;
      break;
    }

    case 'DELETE_SITE': {
      const { siteId } = action.payload;
      draft.topology.sites = draft.topology.sites.filter(s => s.id !== siteId);
      draft.topology.siteConnections = draft.topology.siteConnections.filter(
        c => c.from !== siteId && c.to !== siteId
      );
      draft.dirty = true;
      break;
    }

    // ── Subnets ──
    case 'ADD_SUBNET': {
      const site = draft.topology.sites.find(s => s.id === action.payload.siteId);
      if (!site) break;

      const { id, name, cidr } = action.payload.subnet;

      // Auto-populate every new subnet with a gateway router (first IP)
      // and a switch (second IP), wired together.
      const routerIp = getNextAvailableIp(cidr, []) ?? '';
      const switchIp = getNextAvailableIp(cidr, routerIp ? [routerIp] : []) ?? '';
      const routerId = generateId();
      const switchId = generateId();

      site.subnets.push({
        id,
        name,
        cidr,
        gateway: routerIp,
        containers: [
          { id: routerId, name: `${name} Router`, type: 'router', ip: routerIp },
          { id: switchId, name: `${name} Switch`, type: 'switch', ip: switchIp },
        ],
        connections: [{ from: switchId, to: routerId }],
      });
      draft.dirty = true;
      break;
    }

    case 'UPDATE_SUBNET': {
      const site = draft.topology.sites.find(s => s.id === action.payload.siteId);
      const subnet = site?.subnets.find(s => s.id === action.payload.subnetId);
      if (subnet) Object.assign(subnet, action.payload.updates);
      draft.dirty = true;
      break;
    }

    case 'DELETE_SUBNET': {
      const site = draft.topology.sites.find(s => s.id === action.payload.siteId);
      if (site) {
        const subnetId = action.payload.subnetId;
        site.subnets = site.subnets.filter(s => s.id !== subnetId);
        site.subnetConnections = site.subnetConnections.filter(
          c => c.from !== subnetId && c.to !== subnetId
        );
      }
      draft.dirty = true;
      break;
    }

    // ── Containers ──
    case 'ADD_CONTAINER': {
      const site = draft.topology.sites.find(s => s.id === action.payload.siteId);
      const subnet = site?.subnets.find(s => s.id === action.payload.subnetId);
      if (subnet) subnet.containers.push(action.payload.container);
      draft.dirty = true;
      break;
    }

    case 'UPDATE_CONTAINER': {
      const site = draft.topology.sites.find(s => s.id === action.payload.siteId);
      const subnet = site?.subnets.find(s => s.id === action.payload.subnetId);
      const container = subnet?.containers.find(c => c.id === action.payload.containerId);
      if (container) Object.assign(container, action.payload.updates);
      draft.dirty = true;
      break;
    }

    case 'DELETE_CONTAINER': {
      const { siteId, subnetId, containerId } = action.payload;
      const site = draft.topology.sites.find(s => s.id === siteId);
      const subnet = site?.subnets.find(s => s.id === subnetId);
      if (subnet) {
        subnet.containers = subnet.containers.filter(c => c.id !== containerId);
        subnet.connections = subnet.connections.filter(
          c => c.from !== containerId && c.to !== containerId
        );
      }
      draft.dirty = true;
      break;
    }

    // ── Site Connections ──
    case 'ADD_SITE_CONNECTION': {
      const conn = action.payload;
      // Resolve fromContainer/toContainer to the gateway router of each site
      const findSiteRouter = (siteId: string): string | undefined => {
        const site = draft.topology.sites.find(s => s.id === siteId);
        if (!site) return undefined;
        for (const subnet of site.subnets) {
          const r = subnet.containers.find(c => c.type === 'router' || c.type === 'firewall');
          if (r) return r.id;
        }
        return undefined;
      };
      draft.topology.siteConnections.push({
        ...conn,
        fromContainer: conn.fromContainer ?? findSiteRouter(conn.from),
        toContainer:   conn.toContainer   ?? findSiteRouter(conn.to),
      });
      draft.dirty = true;
      break;
    }

    case 'DELETE_SITE_CONNECTION':
      draft.topology.siteConnections = draft.topology.siteConnections.filter(
        c => !(c.from === action.payload.from && c.to === action.payload.to) &&
             !(c.from === action.payload.to && c.to === action.payload.from)
      );
      draft.dirty = true;
      break;

    // ── Inter-Subnet Connections ──
    case 'ADD_INTER_SUBNET_CONNECTION': {
      const site = draft.topology.sites.find(s => s.id === action.payload.siteId);
      if (!site) break;

      const conn = action.payload.connection;
      const fromSubnet = site.subnets.find(s => s.id === conn.from);
      const toSubnet   = site.subnets.find(s => s.id === conn.to);
      if (!fromSubnet || !toSubnet) break;

      // Skip if this subnet pair already has a connection (either direction)
      const alreadyConnected = site.subnetConnections.some(
        c => (c.from === conn.from && c.to === conn.to) ||
             (c.from === conn.to   && c.to === conn.from)
      );
      if (alreadyConnected) break;

      // Find or auto-create a gateway router in a subnet. If created, also
      // wires the first switch → router connection and sets subnet.gateway.
      const ensureRouter = (subnet: typeof fromSubnet): string => {
        const existing = subnet.containers.find(
          c => c.type === 'router' || c.type === 'firewall'
        );
        if (existing) return existing.id;

        const takenIps = subnet.containers.map(c => c.ip).filter(Boolean);
        const routerIp = getNextAvailableIp(subnet.cidr, takenIps) ?? '';
        const routerId = generateId();
        subnet.containers.push({
          id: routerId,
          name: `${subnet.name} Router`,
          type: 'router',
          ip: routerIp,
        } as Container);
        subnet.gateway = routerIp;

        // Auto-uplink the subnet's switch to the new router
        const sw = subnet.containers.find(c => c.type === 'switch');
        if (sw) subnet.connections.push({ from: sw.id, to: routerId });

        return routerId;
      };

      const fromRouterId = ensureRouter(fromSubnet);
      const toRouterId   = ensureRouter(toSubnet);

      site.subnetConnections.push({
        from: conn.from,
        to:   conn.to,
        fromContainer: fromRouterId,
        toContainer:   toRouterId,
      });
      draft.dirty = true;
      break;
    }

    case 'DELETE_INTER_SUBNET_CONNECTION': {
      const site = draft.topology.sites.find(s => s.id === action.payload.siteId);
      if (site) {
        site.subnetConnections = site.subnetConnections.filter(
          c => !(c.from === action.payload.from && c.to === action.payload.to) &&
               !(c.from === action.payload.to && c.to === action.payload.from)
        );
      }
      draft.dirty = true;
      break;
    }

    // ── Subnet Connections ──
    case 'ADD_SUBNET_CONNECTION': {
      const site = draft.topology.sites.find(s => s.id === action.payload.siteId);
      const subnet = site?.subnets.find(s => s.id === action.payload.subnetId);
      if (subnet) subnet.connections.push(action.payload.connection);
      draft.dirty = true;
      break;
    }

    case 'DELETE_SUBNET_CONNECTION': {
      const site = draft.topology.sites.find(s => s.id === action.payload.siteId);
      const subnet = site?.subnets.find(s => s.id === action.payload.subnetId);
      if (subnet) {
        subnet.connections = subnet.connections.filter(
          c => !(c.from === action.payload.from && c.to === action.payload.to) &&
               !(c.from === action.payload.to && c.to === action.payload.from)
        );
      }
      draft.dirty = true;
      break;
    }

    // ── Bulk ──
    case 'LOAD_TOPOLOGY':
      draft.topology = action.payload;
      draft.dirty = false;
      break;

    // ── Backend Integration ──
    case 'SET_BACKEND_INFO':
      draft.backendId = action.payload.id;
      draft.backendName = action.payload.name;
      draft.deployStatus = action.payload.status as DeployStatus;
      break;

    case 'SET_DEPLOY_STATUS':
      draft.deployStatus = action.payload;
      break;

    case 'MARK_CLEAN':
      draft.dirty = false;
      break;

    case 'CLEAR_BACKEND':
      draft.backendId = null;
      draft.backendName = null;
      draft.deployStatus = 'idle';
      draft.dirty = false;
      break;

    case 'UPDATE_CONTAINER_STATUSES': {
      const { statuses } = action.payload;
      for (const site of draft.topology.sites) {
        for (const subnet of site.subnets) {
          for (const container of subnet.containers) {
            if (container.id in statuses) {
              container.status = statuses[container.id];
            }
          }
        }
      }
      // NOTE: does NOT set dirty — status updates are transient
      break;
    }
  }
}
