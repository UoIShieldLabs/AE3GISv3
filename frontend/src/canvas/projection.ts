// Pure projection of the hierarchical topology into React Flow nodes/edges for
// a given scope + expansion state. No React, no store: unit-testable.
import type { Edge, Node } from '@xyflow/react';
import type { Connection, Container, Position, Site, Subnet, TopologyData } from '@/types/topology';
import { roleFor, type NodeRole } from '@/catalog/catalog';
import { countContainers, gatewayOf, subnetGateway, type ConnectionKind, type Scope } from '@/lib/topology';
import type { NodeProcess, RuntimeStatus, Selection, TrafficDir } from '@/store/types';
import type { Activity } from '@/api/client';
import { GROUP_HEADER, GROUP_PADDING, LAYOUT_SPACING, NODE_SIZE } from './constants';
import { boundsOf, groupSize, relativeSide, subnetRect, type Rect, type Side } from './layout/placement';

// ── Node / edge data ──────────────────────────────────────────────────

export interface SiteNodeData extends Record<string, unknown> {
  kind: 'site';
  site: Site;
  subnetCount: number;
  containerCount: number;
  /** Devices inside with something running: one colour each (see `NodeBusy`). */
  busy?: string[];
}

/** Something runs in a device right now (the live lab view). */
export interface NodeBusy {
  /** The node's colour in the open tutorial; the theme accent outside it. */
  color: string;
  /** Short text for the card: the first process and how many more. */
  label: string;
  /** One line per thing running, for the tooltip. */
  detail: string[];
}

export interface SubnetNodeData extends Record<string, unknown> {
  kind: 'subnet';
  subnet: Subnet;
  siteId: string;
  containerCount: number;
  /** The router the subnet routes through (a member, or one reaching it through a leg). */
  gateway?: { id: string; name: string; ip: string };
  /** Runtime state summary for the badge: running / total. */
  running?: number;
  /** Devices inside with something running: one colour each. */
  busy?: string[];
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
  /** Something runs in it right now (the live lab view). */
  busy?: NodeBusy;
  /** Its extra interface legs, by subnet name (multi-homing). */
  legs?: { subnet: string; ip: string }[];
  /** Drawn in another subnet's view because it joins that subnet through a leg:
   *  the address it holds there and the subnet it lives in. Not draggable. */
  guest?: { ip: string; homeSubnet: string };
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

export type EdgeVariant = 'link' | 'uplink' | 'wan' | 'site' | 'attachment';

export interface CanvasEdgeData extends Record<string, unknown> {
  variant: EdgeVariant;
  kind: ConnectionKind;
  connectionId: string;
  label?: string;
  /** Both endpoint containers are running. */
  active: boolean;
  /** It carries traffic right now, and which way along the drawn edge
   *  (source → target is `fwd`). Drives the moving dashes. */
  traffic?: TrafficDir;
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
  /** The live lab view (see `liveIndex`). */
  live?: CanvasLive;
}

/** The live lab view indexed for the canvas. */
export interface CanvasLive {
  /** Connection id (or `leg:<device>:<subnet>`) → which way its traffic flows. */
  linkTraffic: ReadonlyMap<string, TrafficDir>;
  /** Device id → what runs there. */
  busyNodes: ReadonlyMap<string, NodeBusy>;
}

/** The colour of a busy node no tutorial names. */
export const BUSY_FALLBACK_COLOR = 'var(--accent)';

/** Index the live view: a node is busy when the collector lists processes for
 *  it or its terminal is running a command; it wears its tutorial colour. */
export function liveIndex(input: {
  linkTraffic: Readonly<Record<string, TrafficDir>>;
  nodeProcesses: Readonly<Record<string, readonly NodeProcess[]>>;
  busyTerminals: Readonly<Record<string, true>>;
  colors?: ReadonlyMap<string, string>;
}): CanvasLive {
  const busyNodes = new Map<string, NodeBusy>();
  for (const id of new Set([...Object.keys(input.nodeProcesses), ...Object.keys(input.busyTerminals)])) {
    const procs = input.nodeProcesses[id] ?? [];
    const names = [...new Set(procs.map((p) => p.name))];
    if (!names.length && !input.busyTerminals[id]) continue;
    busyNodes.set(id, {
      color: input.colors?.get(id) ?? BUSY_FALLBACK_COLOR,
      label: names.length ? (names.length > 1 ? `${names[0]} +${names.length - 1}` : names[0]) : 'running',
      detail: procs.length ? procs.map((p) => p.args || p.name) : ['A command is running in its terminal'],
    });
  }
  return { linkTraffic: new Map(Object.entries(input.linkTraffic)), busyNodes };
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
    } else if (a.kind === 'background') {
      // A tutorial's background traffic: the same icon as a traffic run.
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
/** Guest cards (leg-attached devices in a LAN view): column gap and row gap. */
const GUEST_GAP = 96;
const GUEST_ROW_GAP = 24;
const pos = (p?: Position): Position => (p ? { x: p.x, y: p.y } : ZERO);

/** The `i`th of `n` guest cards beside device bounds `b`, on `side`. */
function guestPosition(side: Side, i: number, n: number, b: Rect): Position {
  const { width: w, height: h } = NODE_SIZE.device;
  if (side === 'left' || side === 'right') {
    return { x: side === 'right' ? b.x + b.width + GUEST_GAP : b.x - GUEST_GAP - w, y: b.y + i * (h + GUEST_ROW_GAP) };
  }
  const gap = LAYOUT_SPACING.subnet.nodeSpacing;
  const rowWidth = n * w + (n - 1) * gap;
  return { x: b.x + b.width / 2 - rowWidth / 2 + i * (w + gap), y: side === 'up' ? b.y - GUEST_GAP - h : b.y + b.height + GUEST_GAP };
}

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
        traffic: this.input.live?.linkTraffic.get(conn.id),
        captureJobId: this.input.activity?.captureConnections.get(conn.id),
      },
    });
  }

  /** Colours of the busy devices among `containers`, for a collapsed card. */
  private busyIn(containers: Container[]): string[] | undefined {
    const busy = this.input.live?.busyNodes;
    if (!busy?.size) return undefined;
    const colors = containers.flatMap((c) => { const b = busy.get(c.id); return b ? [b.color] : []; });
    return colors.length ? colors : undefined;
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
        busy: this.input.live?.busyNodes.get(c.id),
        legs: c.interfaces?.length
          ? c.interfaces.map((l) => ({ subnet: this.subnetsById.get(l.subnetId)?.name ?? l.subnetId, ip: l.ip }))
          : undefined,
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

  /** LAN scope: devices at their stored positions, then the guests. */
  private emitLan(subnet: Subnet, siteId: string) {
    for (const c of subnet.containers) this.push(this.deviceNode(c, subnet, siteId));
    this.deviceEdges(subnet);
    this.emitGuests(subnet, siteId);
  }

  /** Devices from other subnets that join this one through a leg (a firewall
   *  gatewaying it, a dual-homed historian): drawn at their leg address beside
   *  the subnet's own devices, on the side their home subnet sits (a row above
   *  or below, else a column left or right), wired to the switch the leg
   *  attaches to. Their position is synthetic, so they can't be dragged. */
  private emitGuests(subnet: Subnet, siteId: string) {
    const t = this.input.topology;
    const guests = t.sites.flatMap((site) =>
      site.subnets.flatMap((home) =>
        home.containers.flatMap((c) => {
          const leg = c.interfaces?.find((l) => l.subnetId === subnet.id);
          return leg ? [{ c, leg, home, siteId: site.id }] : [];
        }),
      ),
    );
    if (!guests.length) return;
    guests.sort((a, b) => a.c.name.localeCompare(b.c.name));
    const b = boundsOf(subnet.containers.map((c) => ({ ...pos(c.position), ...NODE_SIZE.device }))) ?? { x: 0, y: 0, width: 0, height: 0 };
    const gateway = subnetGateway(t, subnet)?.id;
    const anchor = subnet.containers.find((c) => roleFor(c.type) === 'switch') ?? gatewayOf(subnet) ?? subnet.containers[0];
    const expanded = this.input.expanded;
    const here = subnetRect(subnet, !!expanded[subnet.id]);
    const bySide = new Map<Side, typeof guests>();
    for (const g of guests) {
      const side = g.siteId === siteId ? relativeSide(here, subnetRect(g.home, !!expanded[g.home.id])) : 'right';
      bySide.set(side, [...(bySide.get(side) ?? []), g]);
    }
    for (const [side, list] of bySide) {
      list.forEach(({ c, leg, home, siteId: homeSite }, i) => {
        const node = this.deviceNode(c, home, homeSite);
        node.position = guestPosition(side, i, list.length, b);
        node.draggable = false;
        node.data = { ...node.data, isGateway: gateway === c.id, guest: { ip: leg.ip, homeSubnet: home.name } };
        this.push(node);
        if (anchor) this.pushLeg(`leg:${c.id}:${subnet.id}`, c.id, anchor.id);
      });
    }
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
        gateway: subnetGateway(this.input.topology, subnet),
        running: known > 0 ? running : undefined,
        busy: this.busyIn(subnet.containers),
      },
    });
    return NODE_SIZE.subnet;
  }

  /** Expanded subnet: a group node with its devices inside. */
  private subnetGroup(subnet: Subnet, siteId: string, parentId?: string, offset: Position = ZERO): Emitted['size'] {
    const rects: Rect[] = subnet.containers.map((c) => ({ ...pos(c.position), ...NODE_SIZE.device }));
    const b = boundsOf(rects) ?? { x: 0, y: 0, width: NODE_SIZE.device.width, height: NODE_SIZE.device.height };
    const origin: Position = { x: b.x - GROUP_PADDING, y: b.y - GROUP_HEADER - GROUP_PADDING };
    const { width, height } = groupSize(b);
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
      data: {
        kind: 'site',
        site,
        subnetCount: site.subnets.length,
        containerCount: countContainers(site, { userOnly: true }),
        busy: this.busyIn(site.subnets.flatMap((s) => s.containers)),
      },
    });
    return NODE_SIZE.site;
  }

  /** Expanded site: group containing its subnets (which may themselves be expanded). */
  private siteGroup(site: Site): Emitted['size'] {
    // Child sizes depend on whether each subnet is expanded; measure with a dry run.
    const sizes = new Map<string, { width: number; height: number }>();
    for (const subnet of site.subnets) {
      const { width, height } = subnetRect(subnet, !!this.input.expanded[subnet.id]);
      sizes.set(subnet.id, { width, height });
    }
    const rects: Rect[] = site.subnets.map((s) => ({ ...pos(s.position), ...sizes.get(s.id)! }));
    const b = boundsOf(rects) ?? { x: 0, y: 0, ...NODE_SIZE.subnet };
    const origin: Position = { x: b.x - GROUP_PADDING, y: b.y - GROUP_HEADER - GROUP_PADDING };
    const { width, height } = groupSize(b);
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

  private pushLeg(id: string, source: string, target: string, label?: string, traffic?: TrafficDir) {
    if (!this.visible.has(source) || !this.visible.has(target) || source === target) return;
    this.edges.push({
      id,
      source,
      target,
      type: 'topology',
      selectable: false,
      // A device's own leg is keyed like the collector reports it; merged legs pass theirs.
      data: { variant: 'attachment', kind: 'container', connectionId: id, active: false, label, traffic: traffic ?? this.input.live?.linkTraffic.get(id) },
    });
  }

  /** Multi-homing: a dashed edge for every interface leg, from the device — or,
   *  when it isn't drawn, its subnet or site card — to the switch the leg
   *  attaches to, else the target subnet's or site's card. Legs that collapse
   *  onto the same two cards become one edge naming their devices. */
  private legEdges() {
    const t = this.input.topology;
    const siteOf = new Map(t.sites.flatMap((s) => s.subnets.map((n) => [n.id, s.id] as const)));
    const merged = new Map<string, { source: string; target: string; names: string[]; traffic?: TrafficDir }>();
    for (const site of t.sites) {
      for (const subnet of site.subnets) {
        for (const c of subnet.containers) {
          for (const leg of c.interfaces ?? []) {
            const into = this.subnetsById.get(leg.subnetId);
            if (!into) continue;
            const sw = this.input.expanded[into.id] ? into.containers.find((x) => roleFor(x.type) === 'switch')?.id : undefined;
            const target = [sw, into.id, siteOf.get(into.id)].find((id): id is string => !!id && this.visible.has(id));
            if (this.visible.has(c.id)) {
              if (target && !this.edges.some((e) => e.id === `leg:${c.id}:${into.id}`)) this.pushLeg(`leg:${c.id}:${into.id}`, c.id, target);
              continue;
            }
            const source = [subnet.id, site.id].find((id) => this.visible.has(id));
            if (!source || !target || source === target) continue;
            const key = `leg:${source}:${target}`;
            const m = merged.get(key) ?? { source, target, names: [] as string[], traffic: undefined as TrafficDir | undefined };
            m.names.push(c.name);
            // Moving when any leg it stands for carries traffic (they all run source → target).
            const dir = this.input.live?.linkTraffic.get(`leg:${c.id}:${into.id}`);
            if (dir) m.traffic = m.traffic && m.traffic !== dir ? 'both' : dir;
            merged.set(key, m);
          }
        }
      }
    }
    for (const [id, m] of merged) this.pushLeg(id, m.source, m.target, m.names.join(', '), m.traffic);
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
    this.legEdges();
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
