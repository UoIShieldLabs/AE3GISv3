// Which nodes a monitor records: the form's choice → the request's selector,
// and a preview of the nodes it matches (the backend resolves it again).
import type { NodeSelector } from '@/api/client';
import { roleFor } from '@/catalog/catalog';
import type { TopologyData } from '@/types/topology';

export type SelectionMode = 'all' | 'hosts' | 'subnets' | 'types' | 'nodes';

export interface Selection {
  mode: SelectionMode;
  /** Subnet ids, catalog types or node ids, depending on ``mode``. */
  picks: string[];
}

/** A node; a multi-homed one lists every subnet it is in. */
export interface NodeInfo { id: string; name: string; type: string; subnetIds: string[]; ip?: string }

export function nodesOf(topology: TopologyData): NodeInfo[] {
  const byId = new Map<string, NodeInfo>();
  for (const site of topology.sites) {
    for (const sub of site.subnets) {
      for (const c of sub.containers) {
        const known = byId.get(c.id);
        if (known) known.subnetIds.push(sub.id);
        else byId.set(c.id, { id: c.id, name: c.name, type: c.type, subnetIds: [sub.id], ip: c.ip });
      }
    }
  }
  return [...byId.values()];
}

export function toRequest(sel: Selection): 'all' | string[] | NodeSelector {
  switch (sel.mode) {
    case 'all':
      return 'all';
    case 'hosts':
      return { roles: ['host'] };
    case 'subnets':
      return { subnets: sel.picks };
    case 'types':
      return { types: sel.picks };
    case 'nodes':
      return sel.picks;
  }
}

/** The running nodes ``sel`` picks (the same rules as the backend's selectors). */
export function preview(nodes: readonly NodeInfo[], running: (id: string) => boolean, sel: Selection): NodeInfo[] {
  const picks = new Set(sel.picks);
  return nodes.filter((n) => {
    if (!running(n.id)) return false;
    switch (sel.mode) {
      case 'all':
        return true;
      case 'hosts':
        return roleFor(n.type) === 'host';
      case 'subnets':
        return n.subnetIds.some((s) => picks.has(s));
      case 'types':
        return picks.has(n.type);
      case 'nodes':
        return picks.has(n.id);
    }
  });
}
