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

  const positions = new Map<string, { x: number; y: number }>();
  for (const nodeId of g.nodes()) {
    const n = g.node(nodeId);
    if (n) {
      positions.set(nodeId, {
        x: n.x - n.width / 2,
        y: n.y - n.height / 2,
      });
    }
  }
  return positions;
}

export function computeCircleLayout(
  nodes: LayoutNode[],
  edges: LayoutEdge[] = [],
  options: { radius?: number } = {}
): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();
  const n = nodes.length;
  if (n === 0) return positions;
  if (n === 1) {
    positions.set(nodes[0].id, { x: 400, y: 300 });
    return positions;
  }

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
  const ring = hasCenter ? ringNodes : sorted;
  const center = hasCenter ? centerNodes : [];

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
