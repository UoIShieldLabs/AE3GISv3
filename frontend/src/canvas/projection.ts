// Pure projection of the hierarchical topology into React Flow nodes/edges for
// a given scope + expansion state. No React, no store: unit-testable.
import type { Edge, Node } from '@xyflow/react';
import type { Connection, Container, Position, Site, Subnet, TopologyData } from '@/types/topology';
import { roleFor, type NodeRole } from '@/catalog/catalog';
import { countContainers, gatewayOf, type ConnectionKind, type Scope } from '@/lib/topology';
import type { RuntimeStatus, Selection } from '@/store/types';
import type { Activity } from '@/api/client';
import { GROUP_HEADER, GROUP_PADDING, NODE_SIZE } from './constants';
import { boundsOf, type Rect } from './layout/placement';

// ── Node / edge data ──────────────────────────────────────────────────

export interface SiteNodeData extends Record<string, unknown> {
  kind: 'site';
  site: Site;
  subnetCount: number;
  containerCount: number;
}

export interface SubnetNodeData extends Record<string, unknown> {
  kind: 'subnet';
  subnet: Subnet;
  siteId: string;
  containerCount: number;
  gateway?: Container;
  /** Runtime state summary for the badge: running / total. */
  running?: number;
}

export interface DeviceNodeData extends Record<string, unknown> {
  kind: 'device';
  container: Container;
  subnetId: string;
  siteId: string;
  role: NodeRole;
  isGateway: boolean;
  status?: RuntimeStatus;
  /** The capture running on one of its interfaces (its job id). */
  captureJobId?: string;
  /** It sends or receives generated traffic right now. */
  traffic?: boolean;
}

export interface GroupNodeData extends Record<string, unknown> {
  kind: 'group';
  entity: 'site' | 'subnet';
  title: string;
  subtitle?: string;
  siteId: string;
  width: number;
  height: number;
  /** Add this to a child's rendered (relative) position to get its stored position. */
  origin: Position;
  childCount: number;
}

export type SiteNode = Node<SiteNodeData, 'site'>;
export type SubnetNode = Node<SubnetNodeData, 'subnet'>;
export type DeviceNode = Node<DeviceNodeData, 'device'>;
export type GroupNode = Node<GroupNodeData, 'group'>;
export type CanvasNode = SiteNode | SubnetNode | DeviceNode | GroupNode;

export type EdgeVariant = 'link' | 'uplink' | 'wan' | 'site';

export interface CanvasEdgeData extends Record<string, unknown> {
  variant: EdgeVariant;
  kind: ConnectionKind;
  connectionId: string;
  label?: string;
  /** Both endpoint containers are running (drives the animated style). */
  active: boolean;
  /** The capture watching this link (its job id). */
  captureJobId?: string;
}

export type CanvasEdge = Edge<CanvasEdgeData, 'topology'>;

export interface ProjectionInput {
  topology: TopologyData;
  scope: Scope;
  expanded: Record<string, true>;
  containerStatus?: Record<string, RuntimeStatus>;
  selection?: Selection;
  /** Captures and traffic runs in progress (see `activityIndex`). */
  activity?: CanvasActivity;
}

/** Runtime activity indexed for the canvas. */
export interface CanvasActivity {
  /** Connection id → the capture (job id) watching it. */
  captureConnections: ReadonlyMap<string, string>;
  /** Node id → a capture (job id) running on it (its sidecar shares the node's network). */
  captureNodes: ReadonlyMap<string, string>;
  /** Nodes that send or receive generated traffic. */
  trafficNodes: ReadonlySet<string>;
}

export function activityIndex(activity: readonly Activity[]): CanvasActivity {
  const captureConnections = new Map<string, string>();
  const captureNodes = new Map<string, string>();
  const trafficNodes = new Set<string>();
  for (const a of activity) {
    if (a.kind === 'capture') {
      for (const id of a.connection_ids ?? []) captureConnections.set(id, a.job_id);
      // node_ids = [the capturing node, its peer on the link]
      if (a.node_ids?.[0]) captureNodes.set(a.node_ids[0], a.job_id);
    } else if (a.kind === 'traffic') {
      for (const id of a.node_ids ?? []) trafficNodes.add(id);
    }
  }
  return { captureConnections, captureNodes, trafficNodes };
}

export interface Projection {
  nodes: CanvasNode[];
  edges: CanvasEdge[];
}

// ── Helpers ───────────────────────────────────────────────────────────

const ZERO: Position = { x: 0, y: 0 };
/** Groups never get narrower than this so the header stays readable. */
const MIN_GROUP_WIDTH = 300;
const pos = (p?: Position): Position => (p ? { x: p.x, y: p.y } : ZERO);

interface Emitted {
  nodes: CanvasNode[];
  edges: CanvasEdge[];
  /** Rendered size of the emitted top-level element (node or group). */
  size: { width: number; height: number };
}

function edgeVariantForContainers(a?: Container, b?: Container): EdgeVariant {
  if (!a || !b) return 'link';
  const ra = roleFor(a.type);
  const rb = roleFor(b.type);
  const set = new Set([ra, rb]);
  if (set.has('switch') && set.has('router')) return 'uplink';
  return 'link';
}

class Projector {
  private nodes: CanvasNode[] = [];
  private edges: CanvasEdge[] = [];
  private visible = new Set<string>();
  private selectedNodes: Set<string>;
  private selectedEdges: Set<string>;

  private input: ProjectionInput;
  private subnetsById: Map<string, Subnet>;

  constructor(input: ProjectionInput) {
    this.input = input;
    this.subnetsById = new Map(input.topology.sites.flatMap((s) => s.subnets.map((n) => [n.id, n] as const)));
    this.selectedNodes = new Set(input.selection?.nodeIds ?? []);
    this.selectedEdges = new Set(input.selection?.edgeIds ?? []);
  }

  private status(id: string): RuntimeStatus | undefined {
    return this.input.containerStatus?.[id];
  }

  private push(node: CanvasNode) {
    node.selected = this.selectedNodes.has(node.id);
    this.nodes.push(node);
    this.visible.add(node.id);
  }

  private pushEdge(conn: Connection, source: string, target: string, variant: EdgeVariant, kind: ConnectionKind, active: boolean) {
    if (!conn.id || !this.visible.has(source) || !this.visible.has(target) || source === target) return;
    this.edges.push({
      id: conn.id,
      source,
      target,
      type: 'topology',
      selected: this.selectedEdges.has(conn.id),
      data: {
        variant,
        kind,
        connectionId: conn.id,
        label: conn.label,
        active,
        captureJobId: this.input.activity?.captureConnections.get(conn.id),
      },
    });
  }

  // ── Devices ──

  private deviceNode(c: Container, subnet: Subnet, siteId: string, parentId?: string, offset: Position = ZERO): DeviceNode {
    const p = pos(c.position);
    return {
      id: c.id,
      type: 'device',
      position: { x: p.x - offset.x, y: p.y - offset.y },
      parentId,
      width: NODE_SIZE.device.width,
      height: NODE_SIZE.device.height,
      data: {
        kind: 'device',
        container: c,
        subnetId: subnet.id,
        siteId,
        role: roleFor(c.type),
        isGateway: gatewayOf(subnet)?.id === c.id,
        status: this.status(c.id),
        captureJobId: this.input.activity?.captureNodes.get(c.id),
        traffic: this.input.activity?.trafficNodes.has(c.id) || undefined,
      },
    };
  }

  private deviceEdges(subnet: Subnet) {
    const byId = new Map(subnet.containers.map((c) => [c.id, c]));
    for (const conn of subnet.connections) {
      const a = byId.get(conn.from);
      const b = byId.get(conn.to);
      const active = this.status(conn.from) === 'running' && this.status(conn.to) === 'running';
      this.pushEdge(conn, conn.from, conn.to, edgeVariantForContainers(a, b), 'container', active);
    }
  }

  /** LAN scope: devices at their stored positions. */
  private emitLan(subnet: Subnet, siteId: string) {
    for (const c of subnet.containers) this.push(this.deviceNode(c, subnet, siteId));
    this.deviceEdges(subnet);
  }

  // ── Subnets ──

  private subnetCollapsed(subnet: Subnet, siteId: string, parentId?: string, offset: Position = ZERO): Emitted['size'] {
    const p = pos(subnet.position);
    const statuses = subnet.containers.map((c) => this.status(c.id));
    const known = statuses.filter(Boolean).length;
    const running = statuses.filter((s) => s === 'running').length;
    this.push({
      id: subnet.id,
      type: 'subnet',
      position: { x: p.x - offset.x, y: p.y - offset.y },
      parentId,
      width: NODE_SIZE.subnet.width,
      height: NODE_SIZE.subnet.height,
      data: {
        kind: 'subnet',
        subnet,
        siteId,
        containerCount: countContainers(subnet, { userOnly: true }),
        gateway: gatewayOf(subnet),
        running: known > 0 ? running : undefined,
      },
    });
    return NODE_SIZE.subnet;
  }

  /** Expanded subnet: a group node with its devices inside. */
  private subnetGroup(subnet: Subnet, siteId: string, parentId?: string, offset: Position = ZERO): Emitted['size'] {
    const rects: Rect[] = subnet.containers.map((c) => ({ ...pos(c.position), ...NODE_SIZE.device }));
    const b = boundsOf(rects) ?? { x: 0, y: 0, width: NODE_SIZE.device.width, height: NODE_SIZE.device.height };
    const origin: Position = { x: b.x - GROUP_PADDING, y: b.y - GROUP_HEADER - GROUP_PADDING };
    const width = Math.max(b.width + GROUP_PADDING * 2, MIN_GROUP_WIDTH);
    const height = b.height + GROUP_PADDING * 2 + GROUP_HEADER;
    const p = pos(subnet.position);
    this.push({
      id: subnet.id,
      type: 'group',
      position: { x: p.x - offset.x, y: p.y - offset.y },
      parentId,
      width,
      height,
      style: { width, height },
      data: {
        kind: 'group',
        entity: 'subnet',
        title: subnet.name,
        subtitle: subnet.cidr,
        siteId,
        width,
        height,
        origin,
        childCount: subnet.containers.length,
      },
    });
    for (const c of subnet.containers) this.push(this.deviceNode(c, subnet, siteId, subnet.id, origin));
    this.deviceEdges(subnet);
    return { width, height };
  }

  private emitSubnet(subnet: Subnet, siteId: string, parentId?: string, offset: Position = ZERO): Emitted['size'] {
    return this.input.expanded[subnet.id] ? this.subnetGroup(subnet, siteId, parentId, offset) : this.subnetCollapsed(subnet, siteId, parentId, offset);
  }

  /** Visible node for a subnet-level endpoint: the named container when the subnet is expanded
   *  (falling back to its gateway router), otherwise the subnet node itself. */
  private subnetEndpoint(subnetId: string, containerId?: string): string {
    if (!this.input.expanded[subnetId]) return subnetId;
    if (containerId && this.visible.has(containerId)) return containerId;
    const subnet = this.subnetsById.get(subnetId);
    const gw = subnet ? gatewayOf(subnet) : undefined;
    if (gw && this.visible.has(gw.id)) return gw.id;
    return subnetId;
  }

  private interSubnetEdges(site: Site) {
    for (const conn of site.subnetConnections) {
      const source = this.subnetEndpoint(conn.from, conn.fromContainer);
      const target = this.subnetEndpoint(conn.to, conn.toContainer);
      const active = !!conn.fromContainer && !!conn.toContainer && this.status(conn.fromContainer) === 'running' && this.status(conn.toContainer) === 'running';
      this.pushEdge(conn, source, target, 'wan', 'subnet', active);
    }
  }

  /** Site scope: subnets (collapsed or expanded) at their stored positions. */
  private emitSiteContents(site: Site, parentId?: string, offset: Position = ZERO) {
    for (const subnet of site.subnets) this.emitSubnet(subnet, site.id, parentId, offset);
    this.interSubnetEdges(site);
  }

  // ── Sites ──

  private siteCollapsed(site: Site): Emitted['size'] {
    this.push({
      id: site.id,
      type: 'site',
      position: pos(site.position),
      width: NODE_SIZE.site.width,
      height: NODE_SIZE.site.height,
      data: { kind: 'site', site, subnetCount: site.subnets.length, containerCount: countContainers(site, { userOnly: true }) },
    });
    return NODE_SIZE.site;
  }

  /** Expanded site: group containing its subnets (which may themselves be expanded). */
  private siteGroup(site: Site): Emitted['size'] {
    // Child sizes depend on whether each subnet is expanded; measure with a dry run.
    const sizes = new Map<string, { width: number; height: number }>();
    for (const subnet of site.subnets) {
      if (this.input.expanded[subnet.id]) {
        const rects: Rect[] = subnet.containers.map((c) => ({ ...pos(c.position), ...NODE_SIZE.device }));
        const b = boundsOf(rects) ?? { x: 0, y: 0, ...NODE_SIZE.device };
        sizes.set(subnet.id, { width: Math.max(b.width + GROUP_PADDING * 2, MIN_GROUP_WIDTH), height: b.height + GROUP_PADDING * 2 + GROUP_HEADER });
      } else {
        sizes.set(subnet.id, NODE_SIZE.subnet);
      }
    }
    const rects: Rect[] = site.subnets.map((s) => ({ ...pos(s.position), ...sizes.get(s.id)! }));
    const b = boundsOf(rects) ?? { x: 0, y: 0, ...NODE_SIZE.subnet };
    const origin: Position = { x: b.x - GROUP_PADDING, y: b.y - GROUP_HEADER - GROUP_PADDING };
    const width = Math.max(b.width + GROUP_PADDING * 2, MIN_GROUP_WIDTH);
    const height = b.height + GROUP_PADDING * 2 + GROUP_HEADER;
    this.push({
      id: site.id,
      type: 'group',
      position: pos(site.position),
      width,
      height,
      style: { width, height },
      data: {
        kind: 'group',
        entity: 'site',
        title: site.name,
        subtitle: site.location || undefined,
        siteId: site.id,
        width,
        height,
        origin,
        childCount: site.subnets.length,
      },
    });
    this.emitSiteContents(site, site.id, origin);
    return { width, height };
  }

  /** Visible node representing a site-level endpoint. */
  private siteEndpoint(site: Site | undefined, siteId: string, containerId?: string): string {
    if (!site || !this.input.expanded[siteId]) return siteId;
    const subnet = containerId ? site.subnets.find((s) => s.containers.some((c) => c.id === containerId)) : undefined;
    const sub = subnet ?? site.subnets.find((s) => gatewayOf(s)) ?? site.subnets[0];
    if (!sub) return siteId;
    return this.subnetEndpoint(sub.id, containerId ?? gatewayOf(sub)?.id);
  }

  private siteEdges() {
    const t = this.input.topology;
    for (const conn of t.siteConnections) {
      const source = this.siteEndpoint(t.sites.find((s) => s.id === conn.from), conn.from, conn.fromContainer);
      const target = this.siteEndpoint(t.sites.find((s) => s.id === conn.to), conn.to, conn.toContainer);
      const active = !!conn.fromContainer && !!conn.toContainer && this.status(conn.fromContainer) === 'running' && this.status(conn.toContainer) === 'running';
      this.pushEdge(conn, source, target, 'site', 'site', active);
    }
  }

  // ── Entry ──

  run(): Projection {
    const { topology, scope } = this.input;
    if (scope.level === 'root') {
      for (const site of topology.sites) {
        if (this.input.expanded[site.id]) this.siteGroup(site);
        else this.siteCollapsed(site);
      }
      this.siteEdges();
    } else if (scope.level === 'site') {
      const site = topology.sites.find((s) => s.id === scope.siteId);
      if (site) this.emitSiteContents(site);
    } else {
      const site = topology.sites.find((s) => s.id === scope.siteId);
      const subnet = site?.subnets.find((s) => s.id === scope.subnetId);
      if (site && subnet) this.emitLan(subnet, site.id);
    }
    return { nodes: this.nodes, edges: this.edges };
  }
}

export function project(input: ProjectionInput): Projection {
  return new Projector(input).run();
}

/** Ids that can be expanded in place within a scope (sites at root, subnets at root/site). */
export function expandableIds(topology: TopologyData, scope: Scope): string[] {
  if (scope.level === 'root') return topology.sites.flatMap((s) => [s.id, ...s.subnets.map((x) => x.id)]);
  if (scope.level === 'site') return topology.sites.find((s) => s.id === scope.siteId)?.subnets.map((x) => x.id) ?? [];
  return [];
}

/** Convert a rendered (possibly parent-relative) position back to the stored coordinate space. */
export function toStoredPosition(node: Pick<CanvasNode, 'position' | 'parentId'>, nodes: CanvasNode[]): Position {
  if (!node.parentId) return node.position;
  const parent = nodes.find((n) => n.id === node.parentId);
  if (!parent || parent.type !== 'group') return node.position;
  const origin = (parent.data as GroupNodeData).origin;
  return { x: node.position.x + origin.x, y: node.position.y + origin.y };
}
