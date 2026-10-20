// Pure helpers over the frontend topology model. No store, no React.
import type { Connection, Container, Site, Subnet, TopologyData } from '@/types/topology';
import { roleFor } from '@/catalog/catalog';

// ── Scope (drill-down focus) ──────────────────────────────────────────

export type Scope =
  | { level: 'root' }
  | { level: 'site'; siteId: string }
  | { level: 'subnet'; siteId: string; subnetId: string };

export const ROOT_SCOPE: Scope = { level: 'root' };

export function scopeEquals(a: Scope, b: Scope): boolean {
  if (a.level !== b.level) return false;
  if (a.level === 'site' && b.level === 'site') return a.siteId === b.siteId;
  if (a.level === 'subnet' && b.level === 'subnet') return a.siteId === b.siteId && a.subnetId === b.subnetId;
  return true;
}

export function scopePath(topologyId: string, scope: Scope): string {
  const base = `/t/${encodeURIComponent(topologyId)}`;
  if (scope.level === 'root') return base;
  if (scope.level === 'site') return `${base}/site/${encodeURIComponent(scope.siteId)}`;
  return `${base}/site/${encodeURIComponent(scope.siteId)}/subnet/${encodeURIComponent(scope.subnetId)}`;
}

/** Parent scope (root has none). */
export function parentScope(scope: Scope): Scope | null {
  if (scope.level === 'root') return null;
  if (scope.level === 'site') return ROOT_SCOPE;
  return { level: 'site', siteId: scope.siteId };
}

/** Deepest scope reachable through single-child chains (1 site → open site; 1 subnet → open LAN). */
export function defaultScopeFor(topology: TopologyData): Scope {
  if (topology.sites.length !== 1) return ROOT_SCOPE;
  const site = topology.sites[0];
  if (site.subnets.length !== 1) return { level: 'site', siteId: site.id };
  return { level: 'subnet', siteId: site.id, subnetId: site.subnets[0].id };
}

/** Coerce a scope to one that exists in the topology (falls back up the chain). */
export function resolveScope(topology: TopologyData, scope: Scope): Scope {
  if (scope.level === 'root') return scope;
  const site = findSite(topology, scope.siteId);
  if (!site) return ROOT_SCOPE;
  if (scope.level === 'site') return scope;
  return site.subnets.some((s) => s.id === scope.subnetId) ? scope : { level: 'site', siteId: site.id };
}

// ── Lookup ────────────────────────────────────────────────────────────

export function findSite(t: TopologyData, siteId: string): Site | undefined {
  return t.sites.find((s) => s.id === siteId);
}

export function findSubnet(t: TopologyData, siteId: string, subnetId: string): Subnet | undefined {
  return findSite(t, siteId)?.subnets.find((s) => s.id === subnetId);
}

export type Located =
  | { kind: 'site'; site: Site }
  | { kind: 'subnet'; site: Site; subnet: Subnet }
  | { kind: 'container'; site: Site; subnet: Subnet; container: Container };

/** Find any entity by id, wherever it lives. Linear; topologies are small. */
export function locate(t: TopologyData, id: string): Located | null {
  for (const site of t.sites) {
    if (site.id === id) return { kind: 'site', site };
    for (const subnet of site.subnets) {
      if (subnet.id === id) return { kind: 'subnet', site, subnet };
      for (const container of subnet.containers) {
        if (container.id === id) return { kind: 'container', site, subnet, container };
      }
    }
  }
  return null;
}

export type ConnectionKind = 'site' | 'subnet' | 'container';

export interface LocatedConnection {
  kind: ConnectionKind;
  connection: Connection;
  list: Connection[];
  index: number;
  site?: Site;
  subnet?: Subnet;
}

export function locateConnection(t: TopologyData, id: string): LocatedConnection | null {
  const i0 = t.siteConnections.findIndex((c) => c.id === id);
  if (i0 >= 0) return { kind: 'site', connection: t.siteConnections[i0], list: t.siteConnections, index: i0 };
  for (const site of t.sites) {
    const i1 = site.subnetConnections.findIndex((c) => c.id === id);
    if (i1 >= 0) return { kind: 'subnet', connection: site.subnetConnections[i1], list: site.subnetConnections, index: i1, site };
    for (const subnet of site.subnets) {
      const i2 = subnet.connections.findIndex((c) => c.id === id);
      if (i2 >= 0) return { kind: 'container', connection: subnet.connections[i2], list: subnet.connections, index: i2, site, subnet };
    }
  }
  return null;
}

// ── Roles ─────────────────────────────────────────────────────────────

export function isRouterType(type: string): boolean {
  return roleFor(type) === 'router';
}

export function isInfrastructureType(type: string): boolean {
  return roleFor(type) !== 'host';
}

/** Switches only bridge their own subnet's segment: they never take an interface
 *  leg (a leg port would be enslaved into the bridge and merge two subnets). */
export function canTakeInterfaceLegs(type: string): boolean {
  return roleFor(type) !== 'switch';
}

/** The subnet's gateway: the first router-role container. */
export function gatewayOf(subnet: Subnet): Container | undefined {
  return subnet.containers.find((c) => isRouterType(c.type));
}

/** First router in any of a site's subnets (used to anchor site-to-site links). */
export function siteRouter(site: Site): Container | undefined {
  for (const subnet of site.subnets) {
    const r = gatewayOf(subnet);
    if (r) return r;
  }
  return undefined;
}

/** IPs already used in a subnet: home container IPs plus any interface legs
 *  (multi-homing) attached to it from elsewhere in the topology. Every IP
 *  allocation and "already used" check must go through this, or a new device
 *  can be handed an address a leg already holds (e.g. a firewall's gateway leg).
 *  `except` leaves out one device's own addresses (when checking its own edit). */
export function usedIpsInSubnet(t: TopologyData, subnetId: string, except?: string): string[] {
  const ips: string[] = [];
  for (const site of t.sites) {
    for (const subnet of site.subnets) {
      const isTarget = subnet.id === subnetId;
      for (const c of subnet.containers) {
        if (c.id === except) continue;
        if (isTarget && c.ip) ips.push(c.ip);
        for (const leg of c.interfaces ?? []) {
          if (leg.subnetId === subnetId && leg.ip) ips.push(leg.ip);
        }
      }
    }
  }
  return ips;
}

/** Routers attached to a subnet — in-subnet members and routers reaching it via
 *  an interface leg — each with the IP it holds on that subnet. Drives the
 *  gateway picker so a multi-homed firewall can be a subnet's gateway. */
export function routersForSubnet(t: TopologyData, subnetId: string): { id: string; name: string; ip: string }[] {
  const out: { id: string; name: string; ip: string }[] = [];
  for (const site of t.sites) {
    for (const subnet of site.subnets) {
      for (const c of subnet.containers) {
        if (!isRouterType(c.type)) continue;
        if (subnet.id === subnetId && c.ip) out.push({ id: c.id, name: c.name, ip: c.ip });
        for (const leg of c.interfaces ?? []) {
          if (leg.subnetId === subnetId && leg.ip) out.push({ id: c.id, name: c.name, ip: leg.ip });
        }
      }
    }
  }
  return out;
}

/** The router a subnet routes through: the one holding the subnet's `gateway`
 *  address — in the subnet or reaching it through a leg — else its first router. */
export function subnetGateway(t: TopologyData, subnet: Subnet): { id: string; name: string; ip: string } | undefined {
  const routers = routersForSubnet(t, subnet.id);
  return routers.find((r) => r.ip === subnet.gateway) ?? routers[0];
}

/** Devices on a subnet's segment: its own members plus devices attached to it
 *  through an interface leg (with the address they hold there). */
export function membersOfSubnet(t: TopologyData, subnetId: string): { id: string; name: string; ip: string }[] {
  const out: { id: string; name: string; ip: string }[] = [];
  for (const site of t.sites) {
    for (const subnet of site.subnets) {
      for (const c of subnet.containers) {
        if (subnet.id === subnetId) out.push({ id: c.id, name: c.name, ip: c.ip });
        const leg = (c.interfaces ?? []).find((l) => l.subnetId === subnetId);
        if (leg) out.push({ id: c.id, name: c.name, ip: leg.ip });
      }
    }
  }
  return out;
}

// ── Counts ────────────────────────────────────────────────────────────

function isSubnet(x: TopologyData | Site | Subnet): x is Subnet {
  return Array.isArray((x as Subnet).containers);
}
function isSite(x: TopologyData | Site | Subnet): x is Site {
  return Array.isArray((x as Site).subnets) && !Array.isArray((x as TopologyData).sites);
}

export function countContainers(scope: TopologyData | Site | Subnet, opts: { userOnly?: boolean } = {}): number {
  const count = (cs: Container[]) => (opts.userOnly ? cs.filter((c) => !isInfrastructureType(c.type)).length : cs.length);
  if (isSubnet(scope)) return count(scope.containers);
  if (isSite(scope)) return scope.subnets.reduce((n, s) => n + count(s.containers), 0);
  return (scope as TopologyData).sites.reduce((n, site) => n + site.subnets.reduce((m, s) => m + count(s.containers), 0), 0);
}

export function countSubnets(t: TopologyData): number {
  return t.sites.reduce((n, s) => n + s.subnets.length, 0);
}

// ── Connections ───────────────────────────────────────────────────────

/** True if `list` already links a↔b in either direction. */
export function hasConnection(list: Connection[], a: string, b: string): boolean {
  return list.some((c) => (c.from === a && c.to === b) || (c.from === b && c.to === a));
}

/** All connections whose endpoints are both in `ids`. */
export function connectionsAmong(list: Connection[], ids: ReadonlySet<string>): Connection[] {
  return list.filter((c) => ids.has(c.from) && ids.has(c.to));
}

/** Every entity id in the topology (sites, subnets, containers). */
export function allEntityIds(t: TopologyData): Set<string> {
  const ids = new Set<string>();
  for (const site of t.sites) {
    ids.add(site.id);
    for (const subnet of site.subnets) {
      ids.add(subnet.id);
      for (const c of subnet.containers) ids.add(c.id);
    }
  }
  return ids;
}

/** Next unused name of the form `${base} N`. */
export function nextName(existing: Iterable<string>, base: string): string {
  const b = (base || 'Node').trim();
  const escaped = b.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const pattern = new RegExp(`^${escaped}\\s*(\\d+)$`, 'i');
  let max = 0;
  let bareTaken = false;
  for (const n of existing) {
    const t = n.trim();
    if (t.toLowerCase() === b.toLowerCase()) bareTaken = true;
    const m = t.match(pattern);
    if (m) max = Math.max(max, parseInt(m[1], 10));
  }
  if (max === 0 && !bareTaken) return `${b} 1`;
  return `${b} ${max + 1}`;
}

/** First unused 10.0.N.0/24 (N from 1) across the whole topology. */
export function suggestCidr(t: TopologyData): string {
  const used = new Set<string>();
  for (const site of t.sites) for (const subnet of site.subnets) used.add(subnet.cidr.trim());
  for (let n = 1; n < 255; n++) {
    const c = `10.0.${n}.0/24`;
    if (!used.has(c)) return c;
  }
  return '';
}
