// Layout of the direct children of a scope, using the topology's own
// connections as edges. Pure: returns positions, never mutates.
import type { Connection, Position, TopologyData } from '@/types/topology';
import { rankFor } from '@/catalog/catalog';
import { findSite, findSubnet, gatewayOf, type Scope } from '@/lib/topology';
import { NODE_SIZE, type NodeKind } from '../constants';
import { computeLayout, type LayoutEdge, type LayoutMode, type LayoutNode } from './algorithms';

export interface ScopeChild {
  id: string;
  kind: NodeKind;
  position?: Position;
}

/** Direct children of a scope with their node kind. */
export function scopeChildren(topology: TopologyData, scope: Scope): ScopeChild[] {
  if (scope.level === 'root') return topology.sites.map((s) => ({ id: s.id, kind: 'site', position: s.position }));
  if (scope.level === 'site') {
    return findSite(topology, scope.siteId)?.subnets.map((s) => ({ id: s.id, kind: 'subnet', position: s.position })) ?? [];
  }
  return findSubnet(topology, scope.siteId, scope.subnetId)?.containers.map((c) => ({ id: c.id, kind: 'device', position: c.position })) ?? [];
}

/** Connections whose endpoints are children of the scope. */
export function scopeConnections(topology: TopologyData, scope: Scope): Connection[] {
  if (scope.level === 'root') return topology.siteConnections;
  if (scope.level === 'site') return findSite(topology, scope.siteId)?.subnetConnections ?? [];
  return findSubnet(topology, scope.siteId, scope.subnetId)?.connections ?? [];
}

/** Edges oriented for a layered layout (router → switch → hosts in a LAN). */
export function scopeLayoutEdges(topology: TopologyData, scope: Scope): LayoutEdge[] {
  const conns = scopeConnections(topology, scope);
  if (scope.level !== 'subnet') return conns.map((c) => ({ source: c.from, target: c.to }));
  const subnet = findSubnet(topology, scope.siteId, scope.subnetId);
  const rank = new Map(subnet?.containers.map((c) => [c.id, rankFor(c.type)]) ?? []);
  return conns.map((c) => {
    const fr = rank.get(c.from) ?? 2;
    const tr = rank.get(c.to) ?? 2;
    return fr <= tr ? { source: c.from, target: c.to } : { source: c.to, target: c.from };
  });
}

export interface LayoutScopeOptions {
  /** Rendered sizes to use instead of the default per-kind size (e.g. expanded groups). */
  sizes?: ReadonlyMap<string, { width: number; height: number }>;
}

/** Compute positions for every child of a scope with the given algorithm. */
export function layoutScope(topology: TopologyData, scope: Scope, mode: LayoutMode, options: LayoutScopeOptions = {}): Map<string, Position> {
  const children = scopeChildren(topology, scope);
  const nodes: LayoutNode[] = children.map((c) => ({ id: c.id, ...(options.sizes?.get(c.id) ?? NODE_SIZE[c.kind]) }));
  const edges = scopeLayoutEdges(topology, scope);

  let priority: Map<string, number> | undefined;
  if (scope.level === 'subnet') {
    const subnet = findSubnet(topology, scope.siteId, scope.subnetId);
    priority = new Map(subnet?.containers.map((c) => [c.id, rankFor(c.type)]) ?? []);
  }

  const spacing =
    scope.level === 'subnet'
      ? { nodeSpacing: 40, rankSpacing: 72 }
      : scope.level === 'site'
        ? { nodeSpacing: 72, rankSpacing: 110 }
        : { nodeSpacing: 96, rankSpacing: 140, direction: 'LR' as const };

  // In a LAN the gateway router is the natural root; make sure it is first so
  // the tree pass places it top-centre.
  if (scope.level === 'subnet') {
    const subnet = findSubnet(topology, scope.siteId, scope.subnetId);
    const gw = subnet ? gatewayOf(subnet) : undefined;
    if (gw) {
      const i = nodes.findIndex((n) => n.id === gw.id);
      if (i > 0) nodes.unshift(...nodes.splice(i, 1));
    }
  }

  return computeLayout(mode, nodes, edges, { ...spacing, priority });
}
