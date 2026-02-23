import dagre from '@dagrejs/dagre';

export type LayoutMode = 'dagre' | 'circle' | 'grid';

interface LayoutNode {
  id: string;
  width: number;
  height: number;
}

interface LayoutEdge {
  source: string;
  target: string;
}

interface LayoutOptions {
  direction?: 'TB' | 'LR';
  nodeSpacing?: number;
  rankSpacing?: number;
}

export function computeLayout(
  nodes: LayoutNode[],
  edges: LayoutEdge[],
  options: LayoutOptions = {}
): Map<string, { x: number; y: number }> {
  const { direction = 'TB', nodeSpacing = 80, rankSpacing = 100 } = options;

  const g = new dagre.graphlib.Graph();
  g.setGraph({
    rankdir: direction,
    nodesep: nodeSpacing,
    ranksep: rankSpacing,
    marginx: 50,
    marginy: 50,
  });
  g.setDefaultEdgeLabel(() => ({}));

  for (const node of nodes) {
    g.setNode(node.id, { width: node.width, height: node.height });
  }
  for (const edge of edges) {
    g.setEdge(edge.source, edge.target);
  }

  dagre.layout(g);

  // Use dagre for y-positions (rank/layer assignment) only.
  // Compute x-positions with a subtree-width algorithm so children are always
  // placed in input-array order (first-added = leftmost) and each parent is
  // perfectly centered over its children.
  const yMap = new Map<string, { y: number; height: number }>();
  for (const nodeId of g.nodes()) {
    const n = g.node(nodeId);
    if (n) yMap.set(nodeId, { y: n.y, height: n.height });
  }

  const inputOrder = new Map(nodes.map((n, i) => [n.id, i]));
  const nodeMap = new Map(nodes.map(n => [n.id, n]));

  // Build parent→children adjacency, children sorted by input order
  const childrenOf = new Map<string, string[]>(nodes.map(n => [n.id, []]));
  const hasParent = new Set<string>();
  for (const edge of edges) {
    childrenOf.get(edge.source)?.push(edge.target);
    hasParent.add(edge.target);
  }
  for (const list of childrenOf.values()) {
    list.sort((a, b) => (inputOrder.get(a) ?? 0) - (inputOrder.get(b) ?? 0));
  }

  // Roots: nodes with no incoming edge in the layout graph
  const roots = nodes
    .filter(n => !hasParent.has(n.id))
    .sort((a, b) => (inputOrder.get(a.id) ?? 0) - (inputOrder.get(b.id) ?? 0));

  // Compute subtree widths bottom-up.
  // A node's subtree width = max(its own slot, sum of children subtree widths).
  const subtreeWidths = new Map<string, number>();
  function getSubtreeWidth(id: string): number {
    if (subtreeWidths.has(id)) return subtreeWidths.get(id)!;
    const nw = (nodeMap.get(id)?.width ?? 110) + nodeSpacing;
    const kids = childrenOf.get(id) ?? [];
    const w = kids.length === 0 ? nw : Math.max(nw, kids.reduce((s, c) => s + getSubtreeWidth(c), 0));
    subtreeWidths.set(id, w);
    return w;
  }
  for (const node of nodes) getSubtreeWidth(node.id);

  // Assign x-positions top-down.
  // Each node is placed at the center of its subtree slot.
  // Its children are packed side-by-side and centered under it.
  const xCenter = new Map<string, number>();
  function assignX(id: string, leftBound: number): void {
    if (xCenter.has(id)) return;
    const sw = subtreeWidths.get(id) ?? 0;
    xCenter.set(id, leftBound + sw / 2);

    const kids = childrenOf.get(id) ?? [];
    if (kids.length === 0) return;

    const totalKidWidth = kids.reduce((s, c) => s + (subtreeWidths.get(c) ?? 0), 0);
    let kidLeft = leftBound + sw / 2 - totalKidWidth / 2;
    for (const kid of kids) {
      assignX(kid, kidLeft);
      kidLeft += subtreeWidths.get(kid) ?? 0;
    }
  }

  const margin = 50;
  let cursor = margin;
  for (const root of roots) {
    assignX(root.id, cursor);
    cursor += subtreeWidths.get(root.id) ?? 0;
  }
  // Handle any nodes not reachable from roots (e.g. isolated nodes)
  for (const node of nodes) {
    if (!xCenter.has(node.id)) {
      xCenter.set(node.id, cursor + (node.width + nodeSpacing) / 2);
      cursor += node.width + nodeSpacing;
    }
  }

  const positions = new Map<string, { x: number; y: number }>();
  for (const node of nodes) {
    const cx = xCenter.get(node.id) ?? 0;
    const yd = yMap.get(node.id);
    positions.set(node.id, {
      x: cx - node.width / 2,
      y: yd ? yd.y - yd.height / 2 : 0,
    });
  }

  return positions;
}

export function computeCircleLayout(
  nodes: LayoutNode[],
  edges: LayoutEdge[] = [],
  options: { radius?: number; nodePriority?: Map<string, number> } = {}
): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();
  const n = nodes.length;
  if (n === 0) return positions;
  if (n === 1) {
    positions.set(nodes[0].id, { x: 400, y: 300 });
    return positions;
  }

  let ring: LayoutNode[];
  let center: LayoutNode[];

  if (options.nodePriority) {
    // Priority-based: sort ascending (lower number = first = top of ring), all on ring
    ring = [...nodes].sort(
      (a, b) => (options.nodePriority!.get(a.id) ?? 99) - (options.nodePriority!.get(b.id) ?? 99)
    );
    center = [];
  } else {
    // Count connections per node
    const degree = new Map<string, number>();
    for (const nd of nodes) degree.set(nd.id, 0);
    for (const e of edges) {
      degree.set(e.source, (degree.get(e.source) ?? 0) + 1);
      degree.set(e.target, (degree.get(e.target) ?? 0) + 1);
    }

    // Sort: most connected first
    const sorted = [...nodes].sort((a, b) => (degree.get(b.id) ?? 0) - (degree.get(a.id) ?? 0));

    // Place top hub nodes at center, rest on the ring
    const avgDegree = edges.length > 0
      ? [...degree.values()].reduce((s, d) => s + d, 0) / n
      : 0;
    const centerNodes = sorted.filter(nd => (degree.get(nd.id) ?? 0) > avgDegree);
    const ringNodes = sorted.filter(nd => (degree.get(nd.id) ?? 0) <= avgDegree);

    // If all nodes have equal degree (or no edges), put them all on the ring
    const hasCenter = centerNodes.length > 0 && ringNodes.length > 0;
    ring = hasCenter ? ringNodes : sorted;
    center = hasCenter ? centerNodes : [];
  }

  const ringCount = ring.length;
  const avgSize = nodes.reduce((s, nd) => s + Math.max(nd.width, nd.height), 0) / n;
  const minRadius = (ringCount * avgSize) / (2 * Math.PI) + avgSize;
  const radius = options.radius ?? Math.max(minRadius, 200);

  const cx = radius + 50;
  const cy = radius + 50;

  // Place ring nodes around the circle
  for (let i = 0; i < ringCount; i++) {
    const angle = (2 * Math.PI * i) / ringCount - Math.PI / 2;
    positions.set(ring[i].id, {
      x: cx + radius * Math.cos(angle) - ring[i].width / 2,
      y: cy + radius * Math.sin(angle) - ring[i].height / 2,
    });
  }

  // Place center nodes in a tight cluster at the middle
  if (center.length === 1) {
    positions.set(center[0].id, {
      x: cx - center[0].width / 2,
      y: cy - center[0].height / 2,
    });
  } else if (center.length > 1) {
    const innerRadius = Math.min(radius * 0.3, center.length * avgSize / (2 * Math.PI) + avgSize / 2);
    for (let i = 0; i < center.length; i++) {
      const angle = (2 * Math.PI * i) / center.length - Math.PI / 2;
      positions.set(center[i].id, {
        x: cx + innerRadius * Math.cos(angle) - center[i].width / 2,
        y: cy + innerRadius * Math.sin(angle) - center[i].height / 2,
      });
    }
  }

  return positions;
}

export function computeGridLayout(
  nodes: LayoutNode[],
  options: { spacing?: number } = {}
): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();
  const n = nodes.length;
  if (n === 0) return positions;

  const spacing = options.spacing ?? 60;
  const cols = Math.ceil(Math.sqrt(n));
  const maxW = Math.max(...nodes.map(nd => nd.width));
  const maxH = Math.max(...nodes.map(nd => nd.height));

  for (let i = 0; i < n; i++) {
    const col = i % cols;
    const row = Math.floor(i / cols);
    positions.set(nodes[i].id, {
      x: col * (maxW + spacing) + 50,
      y: row * (maxH + spacing) + 50,
    });
  }
  return positions;
}
