// Which auto-layout a scope is "in". Applying a layout records its mode and a
// fingerprint of the positions it produced on the scope's own entity
// (topology / site / subnet). The scope reads as that mode while the
// fingerprint still matches, and as Custom once anything there is moved,
// added or removed — no mutation has to remember to clear it, and undo just
// works because the record lives in the (tracked) topology. Pure.
import type { AppliedLayout, TopologyData } from '@/types/topology';
import { findSite, findSubnet, type Scope } from '@/lib/topology';
import { LAYOUT_MODES, type LayoutMode } from './algorithms';
import { scopeChildren } from './scope';

export type LayoutState = LayoutMode | 'custom';

export function isLayoutMode(v: unknown): v is LayoutMode {
  return LAYOUT_MODES.some((m) => m.value === v);
}

/** The entity that owns a scope's layout record. */
export function layoutOwner(topology: TopologyData, scope: Scope): { layout?: AppliedLayout } | undefined {
  if (scope.level === 'root') return topology;
  if (scope.level === 'site') return findSite(topology, scope.siteId);
  return findSubnet(topology, scope.siteId, scope.subnetId);
}

/** Fingerprint of the positions a layout of this scope sets. Purdue at site
 *  scope also places every subnet's devices, so those count too. */
export function layoutFootprint(topology: TopologyData, scope: Scope, mode: LayoutMode): string {
  const entries = scopeChildren(topology, scope).map((c) => `${c.id}@${c.position?.x},${c.position?.y}`);
  if (mode === 'purdue' && scope.level === 'site') {
    for (const subnet of findSite(topology, scope.siteId)?.subnets ?? []) {
      for (const c of subnet.containers) entries.push(`${c.id}@${c.position?.x},${c.position?.y}`);
    }
  }
  entries.sort();
  // FNV-1a, 32-bit: short enough to store, collisions only matter cosmetically.
  let h = 0x811c9dc5;
  for (const ch of entries.join('|')) {
    h ^= ch.charCodeAt(0);
    h = Math.imul(h, 0x01000193);
  }
  return `${entries.length}:${(h >>> 0).toString(36)}`;
}

/** The layout last applied to the scope, whether or not it still holds. */
export function lastLayout(topology: TopologyData, scope: Scope): LayoutMode | undefined {
  const mode = layoutOwner(topology, scope)?.layout?.mode;
  return isLayoutMode(mode) ? mode : undefined;
}

/** The layout the scope is in now: the applied mode while untouched, else Custom. */
export function currentLayout(topology: TopologyData, scope: Scope): LayoutState {
  const record = layoutOwner(topology, scope)?.layout;
  if (!record || !isLayoutMode(record.mode)) return 'custom';
  return record.footprint === layoutFootprint(topology, scope, record.mode) ? record.mode : 'custom';
}
