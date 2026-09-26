import type { Connection, Container, Position, Site, Subnet, TopologyData, SavedFlow } from '@/types/topology';
import { createEmptyTopology } from '@/types/topology';
import { generateId } from '@/lib/ids';
import { getNextAvailableIp } from '@/utils/validation';
import { displayNameFor } from '@/catalog/catalog';
import {
  gatewayOf, hasConnection, isRouterType, locate, locateConnection, nextName, siteRouter,
} from '@/lib/topology';
import { layoutScope, nextFreePosition, type Rect } from '@/canvas/layout';
import { NODE_SIZE } from '@/canvas/constants';
import { cloneTopology, normalizeTopology, type NormalizeReport } from '../normalize';
import type { SliceCreator, TopologySlice } from '../types';

const rects = (items: { position?: Position }[], size: { width: number; height: number }): Rect[] =>
  items.filter((i) => i.position).map((i) => ({ ...i.position!, ...size }));

/** Find or create the gateway router of a subnet; wires the switch → router uplink when creating. */
function ensureRouter(subnet: Subnet): string {
  const existing = gatewayOf(subnet);
  if (existing) return existing.id;
  const taken = subnet.containers.map((c) => c.ip).filter(Boolean);
  const ip = getNextAvailableIp(subnet.cidr, taken) ?? '';
  const id = generateId('node');
  subnet.containers.push({
    id,
    name: `${subnet.name} Router`,
    type: 'router',
    ip,
    position: nextFreePosition(rects(subnet.containers, NODE_SIZE.device), NODE_SIZE.device),
  });
  subnet.gateway = ip;
  const sw = subnet.containers.find((c) => c.type === 'switch');
  if (sw && !hasConnection(subnet.connections, sw.id, id)) subnet.connections.push({ id: generateId('c'), from: sw.id, to: id });
  return id;
}

function remapIds<T extends { id?: string }>(items: T[], map: Map<string, string>): T[] {
  return items.map((item) => {
    const copy = { ...item } as T & { from?: string; to?: string; fromContainer?: string; toContainer?: string };
    if (copy.id) copy.id = generateId('c');
    if (copy.from) copy.from = map.get(copy.from) ?? copy.from;
    if (copy.to) copy.to = map.get(copy.to) ?? copy.to;
    if (copy.fromContainer) copy.fromContainer = map.get(copy.fromContainer) ?? copy.fromContainer;
    if (copy.toContainer) copy.toContainer = map.get(copy.toContainer) ?? copy.toContainer;
    return copy;
  });
}

const OFFSET = 32;

function dropConnections(top: TopologyData, ids: string[]) {
  const drop = new Set(ids);
  top.siteConnections = top.siteConnections.filter((c) => !drop.has(c.id!));
  for (const site of top.sites) {
    site.subnetConnections = site.subnetConnections.filter((c) => !drop.has(c.id!));
    for (const subnet of site.subnets) subnet.connections = subnet.connections.filter((c) => !drop.has(c.id!));
  }
}

function dropNodes(top: TopologyData, ids: string[]) {
  const drop = new Set(ids);
  const touches = (c: Connection) => drop.has(c.from) || drop.has(c.to);
  const scrubRefs = (c: Connection) => {
    if (c.fromContainer && drop.has(c.fromContainer)) delete c.fromContainer;
    if (c.toContainer && drop.has(c.toContainer)) delete c.toContainer;
  };
  top.sites = top.sites.filter((site) => !drop.has(site.id));
  top.siteConnections = top.siteConnections.filter((c) => !touches(c));
  for (const site of top.sites) {
    site.subnets = site.subnets.filter((sn) => !drop.has(sn.id));
    site.subnetConnections = site.subnetConnections.filter((c) => !touches(c));
    for (const subnet of site.subnets) {
      subnet.containers = subnet.containers.filter((c) => !drop.has(c.id));
      subnet.connections = subnet.connections.filter((c) => !touches(c));
      if (subnet.gateway && !subnet.containers.some((c) => c.ip === subnet.gateway)) {
        const gw = gatewayOf(subnet);
        if (gw) subnet.gateway = gw.ip;
        else delete subnet.gateway;
      }
    }
    site.subnetConnections.forEach(scrubRefs);
  }
  top.siteConnections.forEach(scrubRefs);
}

export const createTopologySlice: SliceCreator<TopologySlice> = (set, get) => ({
  topology: normalizeTopology(createEmptyTopology()),
  dirty: false,
  savedTopology: null,

  loadTopology: (data) =>
    set((s) => {
      const report: NormalizeReport = { filledConnectionIds: 0 };
      const t = normalizeTopology(cloneTopology(data as TopologyData), report);
      s.topology = t;
      // Connections are addressed by id once deployed (captures pick a link by
      // it), so ids invented here must be saved: start out dirty.
      const changed = report.filledConnectionIds > 0;
      s.savedTopology = changed ? null : t;
      s.dirty = changed;
    }, false, 'loadTopology'),

  newTopology: (name) =>
    set((s) => {
      const t = normalizeTopology(createEmptyTopology(name));
      s.topology = t;
      s.savedTopology = t;
      s.dirty = false;
    }, false, 'newTopology'),

  setTopologyMeta: (meta) =>
    set((s) => {
      if (meta.name !== undefined) s.topology.name = meta.name;
      if (meta.description !== undefined) s.topology.description = meta.description;
      s.dirty = true;
    }, false, 'setTopologyMeta'),

  markClean: () => set({ savedTopology: get().topology, dirty: false }, false, 'markClean'),

  // ── Sites ──
  addSite: (input) => {
    const id = generateId('site');
    set((s) => {
      const position = input.position ?? nextFreePosition(rects(s.topology.sites, NODE_SIZE.site), NODE_SIZE.site);
      s.topology.sites.push({ id, name: input.name, location: input.location ?? '', position, subnets: [], subnetConnections: [] });
      s.dirty = true;
    }, false, 'addSite');
    return id;
  },

  updateSite: (siteId, updates) =>
    set((s) => {
      const site = s.topology.sites.find((x) => x.id === siteId);
      if (!site) return;
      Object.assign(site, updates);
      s.dirty = true;
    }, false, 'updateSite'),

  // ── Subnets ──
  addSubnet: (input) => {
    const site = get().topology.sites.find((x) => x.id === input.siteId);
    if (!site) return null;
    const id = generateId('subnet');
    set((s) => {
      const st = s.topology.sites.find((x) => x.id === input.siteId)!;
      const position = input.position ?? nextFreePosition(rects(st.subnets, NODE_SIZE.subnet), NODE_SIZE.subnet);
      const subnet: Subnet = { id, name: input.name, cidr: input.cidr, containers: [], connections: [], position };
      if (input.autoInfra !== false) {
        const routerIp = getNextAvailableIp(input.cidr, []) ?? '';
        const switchIp = getNextAvailableIp(input.cidr, routerIp ? [routerIp] : []) ?? '';
        const routerId = generateId('node');
        const switchId = generateId('node');
        subnet.gateway = routerIp;
        subnet.containers.push(
          { id: routerId, name: `${input.name} Router`, type: 'router', ip: routerIp, position: { x: 0, y: 0 } },
          { id: switchId, name: `${input.name} Switch`, type: 'switch', ip: switchIp, position: { x: 0, y: NODE_SIZE.device.height + 72 } },
        );
        subnet.connections.push({ id: generateId('c'), from: switchId, to: routerId });
      }
      st.subnets.push(subnet);
      s.dirty = true;
    }, false, 'addSubnet');
    return id;
  },

  updateSubnet: (subnetId, updates) =>
    set((s) => {
      const hit = locate(s.topology as TopologyData, subnetId);
      if (hit?.kind !== 'subnet') return;
      Object.assign(hit.subnet, updates);
      s.dirty = true;
    }, false, 'updateSubnet'),

  // ── Containers ──
  addContainer: (input) => {
    const hit = locate(get().topology, input.subnetId);
    if (hit?.kind !== 'subnet') return null;
    const id = generateId('node');
    set((s) => {
      const h = locate(s.topology as TopologyData, input.subnetId);
      if (h?.kind !== 'subnet') return;
      const { subnet } = h;
      const taken = subnet.containers.map((c) => c.ip).filter(Boolean);
      const ip = input.ip ?? getNextAvailableIp(subnet.cidr, taken) ?? '';
      const name = input.name?.trim() || nextName(subnet.containers.map((c) => c.name), displayNameFor(input.type));
      const position = input.position ?? nextFreePosition(rects(subnet.containers, NODE_SIZE.device), NODE_SIZE.device);
      const container: Container = { id, name, type: input.type, ip, position };
      if (input.image) container.image = input.image;
      if (input.metadata && Object.keys(input.metadata).length) container.metadata = input.metadata;
      if (input.persistencePaths?.length) container.persistencePaths = input.persistencePaths;
      if (input.config && Object.keys(input.config).length) container.config = input.config;
      subnet.containers.push(container);
      if (isRouterType(input.type) && !subnet.gateway) subnet.gateway = ip;
      s.dirty = true;
    }, false, 'addContainer');
    return id;
  },

  updateContainer: (containerId, updates) =>
    set((s) => {
      const hit = locate(s.topology as TopologyData, containerId);
      if (hit?.kind !== 'container') return;
      Object.assign(hit.container, updates);
      // Drop keys explicitly set to undefined so they don't linger as nulls in JSON.
      for (const [k, v] of Object.entries(updates)) if (v === undefined) delete hit.container[k];
      if (hit.subnet.gateway === undefined && isRouterType(hit.container.type)) hit.subnet.gateway = hit.container.ip;
      s.dirty = true;
    }, false, 'updateContainer'),

  // ── Connections ──
  addConnection: ({ from, to, label }) => {
    if (from === to) return null;
    const t = get().topology;
    const a = locate(t, from);
    const b = locate(t, to);
    if (!a || !b) return null;
    const id = generateId('c');
    let added = false;
    const conn = (extra: Partial<Connection>): Connection => ({ id, ...extra, ...(label ? { label } : {}) } as Connection);

    set((s) => {
      const top = s.topology as TopologyData;
      const A = locate(top, from)!;
      const B = locate(top, to)!;

      // site ↔ site
      if (A.kind === 'site' && B.kind === 'site') {
        if (hasConnection(top.siteConnections, A.site.id, B.site.id)) return;
        top.siteConnections.push(conn({ from: A.site.id, to: B.site.id, fromContainer: siteRouter(A.site)?.id, toContainer: siteRouter(B.site)?.id }));
        added = true;
      }
      // subnet ↔ subnet
      else if (A.kind === 'subnet' && B.kind === 'subnet') {
        if (A.site.id === B.site.id) {
          if (hasConnection(A.site.subnetConnections, A.subnet.id, B.subnet.id)) return;
          const fc = ensureRouter(A.subnet);
          const tc = ensureRouter(B.subnet);
          A.site.subnetConnections.push(conn({ from: A.subnet.id, to: B.subnet.id, fromContainer: fc, toContainer: tc }));
        } else {
          if (hasConnection(top.siteConnections, A.site.id, B.site.id)) return;
          const fc = ensureRouter(A.subnet);
          const tc = ensureRouter(B.subnet);
          top.siteConnections.push(conn({ from: A.site.id, to: B.site.id, fromContainer: fc, toContainer: tc }));
        }
        added = true;
      }
      // container ↔ container
      else if (A.kind === 'container' && B.kind === 'container') {
        if (A.subnet.id === B.subnet.id) {
          if (hasConnection(A.subnet.connections, from, to)) return;
          A.subnet.connections.push(conn({ from, to }));
        } else if (!isRouterType(A.container.type) || !isRouterType(B.container.type)) {
          return; // only routers link across subnets/sites
        } else if (A.site.id === B.site.id) {
          if (hasConnection(A.site.subnetConnections, A.subnet.id, B.subnet.id)) return;
          A.site.subnetConnections.push(conn({ from: A.subnet.id, to: B.subnet.id, fromContainer: from, toContainer: to }));
        } else {
          if (hasConnection(top.siteConnections, A.site.id, B.site.id)) return;
          top.siteConnections.push(conn({ from: A.site.id, to: B.site.id, fromContainer: from, toContainer: to }));
        }
        added = true;
      }
      // subnet ↔ router container (same site)
      else if ((A.kind === 'subnet' && B.kind === 'container') || (A.kind === 'container' && B.kind === 'subnet')) {
        const sub = A.kind === 'subnet' ? A : (B as Extract<typeof B, { kind: 'subnet' }>);
        const con = A.kind === 'container' ? A : (B as Extract<typeof B, { kind: 'container' }>);
        if (sub.site.id !== con.site.id || sub.subnet.id === con.subnet.id) return;
        if (!isRouterType(con.container.type)) return;
        if (hasConnection(sub.site.subnetConnections, sub.subnet.id, con.subnet.id)) return;
        const subRouter = ensureRouter(sub.subnet);
        const fromIsSub = A.kind === 'subnet';
        sub.site.subnetConnections.push(
          conn({
            from: fromIsSub ? sub.subnet.id : con.subnet.id,
            to: fromIsSub ? con.subnet.id : sub.subnet.id,
            fromContainer: fromIsSub ? subRouter : con.container.id,
            toContainer: fromIsSub ? con.container.id : subRouter,
          }),
        );
        added = true;
      }
      if (added) s.dirty = true;
    }, false, 'addConnection');
    return added ? id : null;
  },

  updateConnection: (id, updates) =>
    set((s) => {
      const hit = locateConnection(s.topology as TopologyData, id);
      if (!hit) return;
      Object.assign(hit.connection, updates);
      for (const [k, v] of Object.entries(updates)) if (v === undefined) delete hit.connection[k];
      s.dirty = true;
    }, false, 'updateConnection'),

  deleteConnections: (ids) => set((s) => { dropConnections(s.topology as TopologyData, ids); s.dirty = true; }, false, 'deleteConnections'),

  setTrafficFlows: (flows) =>
    set((s) => {
      const t = s.topology as TopologyData;
      t.traffic = { ...(t.traffic ?? {}), flows: JSON.parse(JSON.stringify(flows)) as SavedFlow[] };
      s.dirty = true;
    }, false, 'setTrafficFlows'),

  deleteNodes: (ids) => set((s) => { dropNodes(s.topology as TopologyData, ids); s.dirty = true; }, false, 'deleteNodes'),

  deleteItems: (nodeIds, edgeIds) =>
    set((s) => {
      const top = s.topology as TopologyData;
      if (edgeIds.length) dropConnections(top, edgeIds);
      if (nodeIds.length) dropNodes(top, nodeIds);
      s.dirty = true;
    }, false, 'deleteItems'),

  duplicateNodes: (ids) => {
    const created: string[] = [];
    set((s) => {
      const top = s.topology as TopologyData;
      for (const id of ids) {
        const hit = locate(top, id);
        if (!hit) continue;
        if (hit.kind === 'container') {
          const { subnet, container } = hit;
          const taken = subnet.containers.map((c) => c.ip).filter(Boolean);
          const copy: Container = {
            ...JSON.parse(JSON.stringify(container)),
            id: generateId('node'),
            name: nextName(subnet.containers.map((c) => c.name), container.name.replace(/\s+\d+$/, '')),
            ip: getNextAvailableIp(subnet.cidr, taken) ?? '',
            position: { x: (container.position?.x ?? 0) + OFFSET, y: (container.position?.y ?? 0) + OFFSET },
          };
          subnet.containers.push(copy);
          created.push(copy.id);
        } else if (hit.kind === 'subnet') {
          const { site, subnet } = hit;
          const map = new Map<string, string>();
          const containers = subnet.containers.map((c) => {
            const nid = generateId('node');
            map.set(c.id, nid);
            return { ...JSON.parse(JSON.stringify(c)), id: nid } as Container;
          });
          const copy: Subnet = {
            ...JSON.parse(JSON.stringify(subnet)),
            id: generateId('subnet'),
            name: nextName(site.subnets.map((x) => x.name), subnet.name.replace(/\s+\d+$/, '')),
            containers,
            connections: remapIds(subnet.connections, map),
            position: { x: (subnet.position?.x ?? 0) + OFFSET, y: (subnet.position?.y ?? 0) + OFFSET },
          };
          site.subnets.push(copy);
          created.push(copy.id);
        } else {
          const { site } = hit;
          const map = new Map<string, string>();
          const subnets = site.subnets.map((sn) => {
            const nsid = generateId('subnet');
            map.set(sn.id, nsid);
            const containers = sn.containers.map((c) => {
              const nid = generateId('node');
              map.set(c.id, nid);
              return { ...JSON.parse(JSON.stringify(c)), id: nid } as Container;
            });
            return { ...JSON.parse(JSON.stringify(sn)), id: nsid, containers, connections: remapIds(sn.connections, map) } as Subnet;
          });
          const copy: Site = {
            ...JSON.parse(JSON.stringify(site)),
            id: generateId('site'),
            name: nextName(top.sites.map((x) => x.name), site.name.replace(/\s+\d+$/, '')),
            subnets,
            subnetConnections: remapIds(site.subnetConnections, map),
            position: { x: site.position.x + OFFSET, y: site.position.y + OFFSET },
          };
          top.sites.push(copy);
          created.push(copy.id);
        }
      }
      if (created.length) s.dirty = true;
    }, false, 'duplicateNodes');
    return created;
  },

  moveNodes: (moves) =>
    set((s) => {
      const top = s.topology as TopologyData;
      let changed = false;
      for (const { id, position } of moves) {
        const hit = locate(top, id);
        if (!hit) continue;
        const target = hit.kind === 'site' ? hit.site : hit.kind === 'subnet' ? hit.subnet : hit.container;
        if (target.position?.x === position.x && target.position?.y === position.y) continue;
        target.position = { x: Math.round(position.x), y: Math.round(position.y) };
        changed = true;
      }
      if (changed) s.dirty = true;
    }, false, 'moveNodes'),

  applyLayout: (scope, mode, sizes) => {
    const positions = layoutScope(get().topology, scope, mode, { sizes });
    get().moveNodes([...positions.entries()].map(([id, position]) => ({ id, position })));
  },
});
