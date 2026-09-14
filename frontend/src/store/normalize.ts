// Bring any topology JSON (old saves, presets, hand-written imports) up to the
// shape the editor relies on: arrays present, every connection has an id,
// every node has a position. Unknown fields are preserved.
import type { Connection, Position, Site, Subnet, TopologyData } from '@/types/topology';
import { generateId } from '@/lib/ids';
import { layoutScope, nextFreePosition, type Rect } from '@/canvas/layout';
import { NODE_SIZE } from '@/canvas/constants';
import type { Scope } from '@/lib/topology';

export const POSITION_FORMAT_VERSION = 2;

/** v1 stored site positions in a compressed space that the old view scaled ×3/×2.5. */
const V1_SITE_SCALE = { x: 3, y: 2.5 };

function isObj(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

function ensureConnections(list: unknown): Connection[] {
  if (!Array.isArray(list)) return [];
  const out: Connection[] = [];
  for (const raw of list) {
    if (!isObj(raw) || typeof raw.from !== 'string' || typeof raw.to !== 'string') continue;
    const c = raw as Connection;
    if (typeof c.id !== 'string' || !c.id) c.id = generateId('c');
    out.push(c);
  }
  return out;
}

function fillPositions(topology: TopologyData, scope: Scope, items: { position?: Position }[], kind: keyof typeof NODE_SIZE) {
  const missing = items.filter((i) => !i.position || typeof i.position.x !== 'number' || typeof i.position.y !== 'number');
  if (missing.length === 0) return;
  if (missing.length === items.length) {
    const layout = layoutScope(topology, scope, 'tree');
    const ids = scopeIds(topology, scope);
    items.forEach((item, i) => {
      item.position = layout.get(ids[i]) ?? { x: 0, y: 0 };
    });
    return;
  }
  const size = NODE_SIZE[kind];
  const occupied: Rect[] = items.filter((i) => i.position).map((i) => ({ ...i.position!, ...size }));
  for (const item of missing) {
    item.position = nextFreePosition(occupied, size);
    occupied.push({ ...item.position, ...size });
  }
}

function scopeIds(topology: TopologyData, scope: Scope): string[] {
  if (scope.level === 'root') return topology.sites.map((s) => s.id);
  const site = topology.sites.find((s) => s.id === scope.siteId);
  if (!site) return [];
  if (scope.level === 'site') return site.subnets.map((s) => s.id);
  return site.subnets.find((s) => s.id === scope.subnetId)?.containers.map((c) => c.id) ?? [];
}

/** Normalise in place and return the same object (typed). Safe to call repeatedly. */
export function normalizeTopology(input: unknown): TopologyData {
  const t = (isObj(input) ? input : {}) as TopologyData;
  if (!Array.isArray(t.sites)) t.sites = [];
  t.siteConnections = ensureConnections(t.siteConnections);
  const version = typeof t.view?.version === 'number' ? t.view.version : 1;

  for (const site of t.sites as Site[]) {
    if (typeof site.id !== 'string') site.id = generateId('site');
    if (typeof site.name !== 'string') site.name = 'Site';
    if (typeof site.location !== 'string') site.location = '';
    if (!Array.isArray(site.subnets)) site.subnets = [];
    site.subnetConnections = ensureConnections(site.subnetConnections);
    if (version < 2 && site.position && typeof site.position.x === 'number') {
      site.position = { x: site.position.x * V1_SITE_SCALE.x, y: site.position.y * V1_SITE_SCALE.y };
    }
    for (const subnet of site.subnets as Subnet[]) {
      if (typeof subnet.id !== 'string') subnet.id = generateId('subnet');
      if (typeof subnet.name !== 'string') subnet.name = 'Subnet';
      if (typeof subnet.cidr !== 'string') subnet.cidr = '';
      if (!Array.isArray(subnet.containers)) subnet.containers = [];
      subnet.connections = ensureConnections(subnet.connections);
      for (const c of subnet.containers) {
        if (typeof c.id !== 'string') c.id = generateId('node');
        if (typeof c.name !== 'string') c.name = c.id;
        if (typeof c.type !== 'string') c.type = 'workstation';
        if (typeof c.ip !== 'string') c.ip = '';
      }
    }
  }

  // Positions: whole-scope layout when nothing is positioned, otherwise slot the stragglers in.
  fillPositions(t, { level: 'root' }, t.sites, 'site');
  for (const site of t.sites) {
    fillPositions(t, { level: 'site', siteId: site.id }, site.subnets, 'subnet');
    for (const subnet of site.subnets) {
      fillPositions(t, { level: 'subnet', siteId: site.id, subnetId: subnet.id }, subnet.containers, 'device');
    }
  }

  t.view = { ...(t.view ?? {}), version: POSITION_FORMAT_VERSION };
  return t;
}

/** Deep clone via JSON (topologies are plain data). */
export function cloneTopology(t: TopologyData): TopologyData {
  return JSON.parse(JSON.stringify(t)) as TopologyData;
}
