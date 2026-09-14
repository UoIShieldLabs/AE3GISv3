import dagre from '@dagrejs/dagre';
import type { Position } from '@/types/topology';

export type LayoutMode = 'tree' | 'circle' | 'grid';

export const LAYOUT_MODES: { value: LayoutMode; label: string }[] = [
  { value: 'tree', label: 'Tree' },
  { value: 'circle', label: 'Circle' },
  { value: 'grid', label: 'Grid' },
];

export interface LayoutNode {
  id: string;
  width: number;
  height: number;
}

export interface LayoutEdge {
  source: string;
  target: string;
}

export interface TreeLayoutOptions {
  direction?: 'TB' | 'LR';
  nodeSpacing?: number;
  rankSpacing?: number;
}

/**
 * Layered ("tree") layout. Dagre assigns ranks (y for TB); x-positions are then
 * recomputed with a subtree-width pass so children keep input order and each
 * parent is centred over its children. Positions are top-left corners.
 */
export function computeTreeLayout(nodes: LayoutNode[], edges: LayoutEdge[], options: TreeLayoutOptions = {}): Map<string, Position> {
  const { direction = 'TB', nodeSpacing = 48, rankSpacing = 72 } = options;
  const positions = new Map<string, Position>();
  if (nodes.length === 0) return positions;

  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: direction, nodesep: nodeSpacing, ranksep: rankSpacing, marginx: 0, marginy: 0 });
  g.setDefaultEdgeLabel(() => ({}));
  for (const n of nodes) g.setNode(n.id, { width: n.width, height: n.height });
  for (const e of edges) if (e.source !== e.target) g.setEdge(e.source, e.target);
  dagre.layout(g);

  if (direction === 'LR') {
    for (const n of nodes) {
      const d = g.node(n.id);
      positions.set(n.id, { x: (d?.x ?? 0) - n.width / 2, y: (d?.y ?? 0) - n.height / 2 });
    }
    return positions;
  }

  const yMap = new Map<string, { y: number; height: number }>();
  for (const id of g.nodes()) {
    const d = g.node(id);
    if (d) yMap.set(id, { y: d.y, height: d.height });
  }

  const inputOrder = new Map(nodes.map((n, i) => [n.id, i]));
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const childrenOf = new Map<string, string[]>(nodes.map((n) => [n.id, []]));
  const hasParent = new Set<string>();
  for (const e of edges) {
    if (e.source === e.target) continue;
    if (hasParent.has(e.target)) continue; // keep a tree: first parent wins
    childrenOf.get(e.source)?.push(e.target);
    hasParent.add(e.target);
  }
  for (const list of childrenOf.values()) list.sort((a, b) => (inputOrder.get(a) ?? 0) - (inputOrder.get(b) ?? 0));

  const roots = nodes.filter((n) => !hasParent.has(n.id)).sort((a, b) => (inputOrder.get(a.id) ?? 0) - (inputOrder.get(b.id) ?? 0));

  const subtreeWidths = new Map<string, number>();
  const visiting = new Set<string>();
  const subtreeWidth = (id: string): number => {
    const cached = subtreeWidths.get(id);
    if (cached !== undefined) return cached;
    if (visiting.has(id)) return 0;
    visiting.add(id);
    const own = (nodeMap.get(id)?.width ?? 0) + nodeSpacing;
    const kids = childrenOf.get(id) ?? [];
    const w = kids.length === 0 ? own : Math.max(own, kids.reduce((s, c) => s + subtreeWidth(c), 0));
    visiting.delete(id);
    subtreeWidths.set(id, w);
    return w;
  };
  for (const n of nodes) subtreeWidth(n.id);

  const xCenter = new Map<string, number>();
  const assignX = (id: string, left: number) => {
    if (xCenter.has(id)) return;
    const sw = subtreeWidths.get(id) ?? 0;
    xCenter.set(id, left + sw / 2);
    const kids = childrenOf.get(id) ?? [];
    if (kids.length === 0) return;
    const total = kids.reduce((s, c) => s + (subtreeWidths.get(c) ?? 0), 0);
    let cursor = left + sw / 2 - total / 2;
    for (const kid of kids) {
      assignX(kid, cursor);
      cursor += subtreeWidths.get(kid) ?? 0;
    }
  };

  let cursor = 0;
  for (const root of roots) {
    assignX(root.id, cursor);
    cursor += subtreeWidths.get(root.id) ?? 0;
  }
  for (const n of nodes) {
    if (!xCenter.has(n.id)) {
      xCenter.set(n.id, cursor + (n.width + nodeSpacing) / 2);
      cursor += n.width + nodeSpacing;
    }
  }

  for (const n of nodes) {
    const cx = xCenter.get(n.id) ?? 0;
    const yd = yMap.get(n.id);
    positions.set(n.id, { x: cx - n.width / 2, y: yd ? yd.y - yd.height / 2 : 0 });
  }
  return positions;
}

export interface CircleLayoutOptions {
  radius?: number;
  /** Lower value = earlier on the ring (used to keep routers/switches first). */
  priority?: Map<string, number>;
}

/** Ring layout; hub nodes (above-average degree) go to the centre unless a priority map is given. */
export function computeCircleLayout(nodes: LayoutNode[], edges: LayoutEdge[] = [], options: CircleLayoutOptions = {}): Map<string, Position> {
  const positions = new Map<string, Position>();
  const n = nodes.length;
  if (n === 0) return positions;
  if (n === 1) {
    positions.set(nodes[0].id, { x: 0, y: 0 });
    return positions;
  }

  let ring: LayoutNode[];
  let center: LayoutNode[] = [];
  if (options.priority) {
    const p = options.priority;
    ring = [...nodes].sort((a, b) => (p.get(a.id) ?? 99) - (p.get(b.id) ?? 99));
  } else {
    const degree = new Map<string, number>(nodes.map((nd) => [nd.id, 0]));
    for (const e of edges) {
      degree.set(e.source, (degree.get(e.source) ?? 0) + 1);
      degree.set(e.target, (degree.get(e.target) ?? 0) + 1);
    }
    const sorted = [...nodes].sort((a, b) => (degree.get(b.id) ?? 0) - (degree.get(a.id) ?? 0));
    const avg = edges.length > 0 ? [...degree.values()].reduce((s, d) => s + d, 0) / n : 0;
    const hubs = sorted.filter((nd) => (degree.get(nd.id) ?? 0) > avg);
    const rest = sorted.filter((nd) => (degree.get(nd.id) ?? 0) <= avg);
    const useCenter = hubs.length > 0 && rest.length > 0 && hubs.length <= 3;
    ring = useCenter ? rest : sorted;
    center = useCenter ? hubs : [];
  }

  const avgSize = nodes.reduce((s, nd) => s + Math.max(nd.width, nd.height), 0) / n;
  const minRadius = (ring.length * avgSize) / (2 * Math.PI) + avgSize;
  const radius = options.radius ?? Math.max(minRadius, 180);
  const cx = radius;
  const cy = radius;

  ring.forEach((nd, i) => {
    const angle = (2 * Math.PI * i) / ring.length - Math.PI / 2;
    positions.set(nd.id, { x: cx + radius * Math.cos(angle) - nd.width / 2, y: cy + radius * Math.sin(angle) - nd.height / 2 });
  });

  if (center.length === 1) {
    positions.set(center[0].id, { x: cx - center[0].width / 2, y: cy - center[0].height / 2 });
  } else if (center.length > 1) {
    const inner = Math.min(radius * 0.35, (center.length * avgSize) / (2 * Math.PI) + avgSize / 2);
    center.forEach((nd, i) => {
      const angle = (2 * Math.PI * i) / center.length - Math.PI / 2;
      positions.set(nd.id, { x: cx + inner * Math.cos(angle) - nd.width / 2, y: cy + inner * Math.sin(angle) - nd.height / 2 });
    });
  }
  return positions;
}

/** Simple row-major grid, roughly square. */
export function computeGridLayout(nodes: LayoutNode[], options: { spacing?: number; columns?: number } = {}): Map<string, Position> {
  const positions = new Map<string, Position>();
  const n = nodes.length;
  if (n === 0) return positions;
  const spacing = options.spacing ?? 40;
  const cols = options.columns ?? Math.max(1, Math.ceil(Math.sqrt(n)));
  const maxW = Math.max(...nodes.map((nd) => nd.width));
  const maxH = Math.max(...nodes.map((nd) => nd.height));
  nodes.forEach((nd, i) => {
    positions.set(nd.id, { x: (i % cols) * (maxW + spacing), y: Math.floor(i / cols) * (maxH + spacing) });
  });
  return positions;
}

export function computeLayout(mode: LayoutMode, nodes: LayoutNode[], edges: LayoutEdge[], options: TreeLayoutOptions & CircleLayoutOptions = {}): Map<string, Position> {
  switch (mode) {
    case 'circle':
      return computeCircleLayout(nodes, edges, options);
    case 'grid':
      return computeGridLayout(nodes);
    default:
      return computeTreeLayout(nodes, edges, options);
  }
}
