// Purdue layout: subnets stacked by Purdue level at site scope (IT on top,
// the DMZ in the middle, OT at the bottom), devices in rows by level inside
// each subnet, the switch on the edge bordering the next zone. Devices that
// bridge to another subnet sit on the edge facing it. Pure: returns
// positions, never mutates.
import type { Container, Position, Site, Subnet, TopologyData } from '@/types/topology';
import { roleFor } from '@/catalog/catalog';
import { deviceLevel, subnetLevel, zoneOf } from '@/lib/purdue';
import { findSite, gatewayOf, type Scope } from '@/lib/topology';
import { LAYOUT_SPACING, NODE_SIZE } from '../constants';
import type { LayoutEdge } from './algorithms';
import { boundsOf, groupSize, relativeSide, subnetRect, type Side } from './placement';

export interface PurdueLayoutOptions {
  /** Ids drawn expanded: their size comes from their (re-laid-out) devices. */
  expanded?: Readonly<Record<string, true>>;
  /** Subnet ↔ subnet edges of the site (`scopeLayoutEdges`). */
  edges?: LayoutEdge[];
}

/** Which side of a subnet faces another subnet of the same site (undefined: not placed). */
type SideOf = (otherSubnetId: string) => Side | undefined;

/** Positions for a site scope (subnets + every subnet's devices) or a subnet
 *  scope (its devices). Root scope has no Purdue meaning: empty map. */
export function layoutPurdue(topology: TopologyData, scope: Scope, options: PurdueLayoutOptions = {}): Map<string, Position> {
  if (scope.level === 'root') return new Map();
  const site = findSite(topology, scope.siteId);
  if (!site) return new Map();
  if (scope.level === 'site') return layoutSite(site, options);
  const subnet = site.subnets.find((s) => s.id === scope.subnetId);
  if (!subnet) return new Map();
  const expanded = options.expanded ?? {};
  const rects = new Map(site.subnets.map((s) => [s.id, subnetRect(s, !!expanded[s.id])]));
  const here = rects.get(subnet.id)!;
  return layoutSubnetDevices(site, subnet, (id) => {
    const other = rects.get(id);
    return other ? relativeSide(here, other) : undefined;
  });
}

// ── Site scope ────────────────────────────────────────────────────────

function layoutSite(site: Site, options: PurdueLayoutOptions): Map<string, Position> {
  const out = new Map<string, Position>();
  if (site.subnets.length === 0) return out;
  const { nodeSpacing, rankSpacing } = LAYOUT_SPACING.site;
  const expanded = options.expanded ?? {};

  const neighbours = new Map<string, string[]>(site.subnets.map((s) => [s.id, []]));
  for (const e of options.edges ?? []) {
    if (e.source === e.target) continue;
    neighbours.get(e.source)?.push(e.target);
    neighbours.get(e.target)?.push(e.source);
  }

  // Rows: one per Purdue level, highest first. Each row after the first is
  // ordered by where its neighbours sit in the rows above (fewer crossings).
  const levelOf = new Map(site.subnets.map((s) => [s.id, subnetLevel(s)]));
  const levels = [...new Set(levelOf.values())].sort((a, b) => b - a);
  const inputOrder = new Map(site.subnets.map((s, i) => [s.id, i]));
  const centreX = new Map<string, number>();
  const rows: string[][] = [];
  for (const level of levels) {
    let row = site.subnets.filter((s) => levelOf.get(s.id) === level).map((s) => s.id);
    if (rows.length > 0) {
      const provisional = centredSlots(row.length, NODE_SIZE.subnet.width, nodeSpacing);
      const key = new Map(row.map((id, i) => {
        const above = (neighbours.get(id) ?? []).filter((n) => centreX.has(n)).map((n) => centreX.get(n)!);
        return [id, above.length ? above.reduce((s, x) => s + x, 0) / above.length : provisional[i]];
      }));
      row = [...row].sort((a, b) => key.get(a)! - key.get(b)! || inputOrder.get(a)! - inputOrder.get(b)!);
    }
    centredSlots(row.length, NODE_SIZE.subnet.width, nodeSpacing).forEach((x, i) => centreX.set(row[i], x));
    rows.push(row);
  }

  const rowOf = new Map<string, number>();
  const slotOf = new Map<string, number>();
  rows.forEach((row, r) => row.forEach((id, i) => { rowOf.set(id, r); slotOf.set(id, i); }));

  // Devices first: an expanded subnet's size depends on them.
  const sizes = new Map<string, { width: number; height: number }>();
  for (const subnet of site.subnets) {
    const devices = layoutSubnetDevices(site, subnet, (other) => {
      if (!rowOf.has(other)) return undefined;
      const dr = rowOf.get(other)! - rowOf.get(subnet.id)!;
      if (dr !== 0) return dr < 0 ? 'up' : 'down';
      return slotOf.get(other)! < slotOf.get(subnet.id)! ? 'left' : 'right';
    });
    for (const [id, p] of devices) out.set(id, p);
    if (expanded[subnet.id]) {
      const rects = subnet.containers.map((c) => ({ ...(devices.get(c.id) ?? { x: 0, y: 0 }), ...NODE_SIZE.device }));
      sizes.set(subnet.id, groupSize(boundsOf(rects) ?? { x: 0, y: 0, ...NODE_SIZE.device }));
    } else {
      sizes.set(subnet.id, NODE_SIZE.subnet);
    }
  }

  let y = 0;
  for (const row of rows) {
    const widths = row.map((id) => sizes.get(id)!.width);
    const total = widths.reduce((s, w) => s + w, 0) + nodeSpacing * (row.length - 1);
    let x = -total / 2;
    row.forEach((id, i) => {
      out.set(id, { x, y });
      x += widths[i] + nodeSpacing;
    });
    y += Math.max(...row.map((id) => sizes.get(id)!.height)) + rankSpacing;
  }
  return out;
}

// ── Devices inside one subnet ─────────────────────────────────────────

/** Rows of a subnet, top to bottom by a sort value: a device's Purdue level;
 *  devices bridging to a subnet above / below on the top / bottom edge; the
 *  switch just past the subnet's own level toward the next zone (below it in
 *  IT, above it in OT; a DMZ's first switch above, the others below). So in an
 *  IT LAN a DMZ-level firewall sits under the switch, and in an OT LAN a
 *  higher-level device sits over it. Every row is centred. */
function layoutSubnetDevices(site: Site, subnet: Subnet, sideOf: SideOf): Map<string, Position> {
  const { nodeSpacing, rankSpacing } = LAYOUT_SPACING.subnet;
  const { width, height } = NODE_SIZE.device;
  const hubs = subnet.containers.filter((c) => roleFor(c.type) === 'switch');
  const others = subnet.containers.filter((c) => roleFor(c.type) !== 'switch');
  const isOther = new Set(others.map((c) => c.id));

  // Sides each device bridges to: its interface legs and the subnet links it ends.
  const bridged = new Map<string, Side[]>();
  const bridge = (deviceId: string | undefined, otherSubnet: string) => {
    if (!deviceId || !isOther.has(deviceId) || otherSubnet === subnet.id) return;
    const side = sideOf(otherSubnet);
    if (side) bridged.set(deviceId, [...(bridged.get(deviceId) ?? []), side]);
  };
  for (const c of others) for (const leg of c.interfaces ?? []) bridge(c.id, leg.subnetId);
  for (const conn of site.subnetConnections) {
    if (conn.from === subnet.id) bridge(conn.fromContainer ?? gatewayOf(subnet)?.id, conn.to);
    if (conn.to === subnet.id) bridge(conn.toContainer ?? gatewayOf(subnet)?.id, conn.from);
  }
  const edgeSide = new Map<string, Side>();
  for (const [id, sides] of bridged) {
    const side = majority(sides);
    if (side) edgeSide.set(id, side);
  }

  const level = subnetLevel(subnet);
  const zone = zoneOf(level);
  const rows = new Map<number, Container[]>();
  const add = (value: number, c: Container) => rows.set(value, [...(rows.get(value) ?? []), c]);
  for (const c of others) {
    const side = edgeSide.get(c.id);
    add(side === 'up' ? TOP_EDGE : side === 'down' ? BOTTOM_EDGE : deviceLevel(c, subnet), c);
  }
  hubs.forEach((c, i) => add(zone === 'IT' || (zone === 'DMZ' && i > 0) ? level - PAST : level + PAST, c));

  // Devices bridging sideways go to that end of their row.
  const end = (c: Container) => (edgeSide.get(c.id) === 'left' ? -1 : edgeSide.get(c.id) === 'right' ? 1 : 0);
  const ordered = [...rows.entries()]
    .sort((a, b) => b[0] - a[0])
    .map(([, row]) => row.map((c, i) => ({ c, i })).sort((a, b) => end(a.c) - end(b.c) || a.i - b.i).map(({ c }) => c));

  const out = new Map<string, Position>();
  ordered.forEach((row, r) => {
    centredSlots(row.length, width, nodeSpacing).forEach((cx, i) => out.set(row[i].id, { x: cx - width / 2, y: r * (height + rankSpacing) }));
  });
  return out;
}

/** Row sort values: the edges, and how far past its subnet's level a switch
 *  sits (Purdue levels are at least 0.5 apart). */
const TOP_EDGE = 100;
const BOTTOM_EDGE = -100;
const PAST = 0.25;

// ── Helpers ───────────────────────────────────────────────────────────

/** Centre x of `n` boxes of `width` in a row centred on 0. */
function centredSlots(n: number, width: number, gap: number): number[] {
  const total = n * width + Math.max(0, n - 1) * gap;
  return Array.from({ length: n }, (_, i) => -total / 2 + width / 2 + i * (width + gap));
}

/** The most frequent side, or undefined on a tie. */
function majority(sides: Side[]): Side | undefined {
  const count = new Map<Side, number>();
  for (const s of sides) count.set(s, (count.get(s) ?? 0) + 1);
  const ranked = [...count.entries()].sort((a, b) => b[1] - a[1]);
  if (ranked.length === 0 || (ranked.length > 1 && ranked[0][1] === ranked[1][1])) return undefined;
  return ranked[0][0];
}
