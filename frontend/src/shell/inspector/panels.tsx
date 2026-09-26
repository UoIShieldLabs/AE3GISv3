import { Activity, ArrowDownRight, Copy, Maximize2, Minimize2, Radio, Terminal, Trash2 } from 'lucide-react';
import type { Container, Site, Subnet } from '@/types/topology';
import { useAppStore, undo } from '@/store';
import { useAppShallow } from '@/store/selectors';
import { colorFor, displayNameFor, labelFor, variantsFor } from '@/catalog/catalog';
import { NodeGlyph } from '@/catalog/icons';
import { countContainers, countSubnets, gatewayOf, isRouterType, locate, locateConnection, type Scope } from '@/lib/topology';
import { isIpInCidr, isValidCidr, isValidIp } from '@/utils/validation';
import { Badge, Button, Select, Textarea, toast } from '@/ui';
import { DeviceTypePicker } from '@/features/topology/DeviceTypePicker';
import { ImagePicker } from '@/features/images/ImagePicker';
import { ImageStatusLine } from '@/features/images/ImageStatusLine';
import { CommitInput } from './CommitInput';
import { KeyValueEditor } from './KeyValueEditor';
import { Row, Section, Stat } from './Section';
import { IssuesSection } from './IssuesSection';
import { DeploymentSection } from './DeploymentSection';
import { openCaptureTab, stopCapture } from '@/features/capture/actions';
import { openTrafficPanel } from '@/features/traffic/actions';

export interface PanelContext {
  scope: Scope;
  onNavigate: (scope: Scope) => void;
}

function useRemove() {
  return (nodeIds: string[], edgeIds: string[] = []) => {
    const st = useAppStore.getState();
    st.deleteItems(nodeIds, edgeIds);
    st.clearSelection();
    const n = nodeIds.length + edgeIds.length;
    toast(`Deleted ${n} item${n === 1 ? '' : 's'}`, { action: { label: 'Undo', onClick: () => undo() } });
  };
}

function Actions({ children }: { children: React.ReactNode }) {
  return <div className="flex flex-wrap gap-1.5 px-3 py-3">{children}</div>;
}

// ── Topology ──────────────────────────────────────────────────────────

export function TopologyPanel() {
  const { topology, backendId, deployStatus, lastError } = useAppShallow((s) => ({ topology: s.topology, backendId: s.backendId, deployStatus: s.deployStatus, lastError: s.lastError }));
  const setMeta = useAppStore((s) => s.setTopologyMeta);
  return (
    <>
      <Section title="Topology">
        <Row label="Name">
          <CommitInput value={topology.name ?? ''} onCommit={(v) => setMeta({ name: v })} placeholder="Untitled topology" validate={(v) => (v ? null : 'Name is required')} />
        </Row>
        <Row label="Description">
          <Textarea key={topology.description ?? ''} defaultValue={topology.description ?? ''} placeholder="What this network models…" onBlur={(e) => { const v = e.target.value.trim(); if (v !== (topology.description ?? '')) setMeta({ description: v }); }} />
        </Row>
      </Section>
      <Section title="Summary">
        <Stat label="Sites" value={topology.sites.length} />
        <Stat label="Subnets" value={countSubnets(topology)} />
        <Stat label="Devices" value={countContainers(topology)} />
        <Stat label="Deployment" value={<Badge tone={deployStatus === 'deployed' ? 'success' : deployStatus === 'error' ? 'danger' : 'neutral'}>{deployStatus}</Badge>} />
        {backendId ? <Stat label="Id" value={<span className="font-mono text-2xs text-fg-muted">{backendId.slice(0, 12)}…</span>} /> : <Stat label="Saved" value={<span className="text-warning">not yet</span>} />}
        {lastError ? <p className="rounded-md bg-danger-soft p-2 text-2xs text-danger">{lastError}</p> : null}
      </Section>
      <IssuesSection />
      <Section title="Tips" defaultOpen={false}>
        <ul className="list-disc space-y-1 pl-4 text-2xs text-fg-muted">
          <li>Drag device types from the palette onto a subnet.</li>
          <li>Drag from a node's edge to link it; hosts link within a subnet, routers link subnets and sites.</li>
          <li>Press <kbd className="font-mono">E</kbd> on a subnet to expand it in place.</li>
        </ul>
      </Section>
    </>
  );
}

// ── Site ──────────────────────────────────────────────────────────────

export function SitePanel({ site, ctx }: { site: Site; ctx: PanelContext }) {
  const { updateSite, duplicateNodes, selectNodes, toggleExpanded } = useAppStore.getState();
  const expanded = useAppStore((s) => !!s.expanded[site.id]);
  const remove = useRemove();
  return (
    <>
      <Section title="Site">
        <Row label="Name"><CommitInput value={site.name} onCommit={(v) => updateSite(site.id, { name: v })} validate={(v) => (v ? null : 'Name is required')} /></Row>
        <Row label="Location"><CommitInput value={site.location} onCommit={(v) => updateSite(site.id, { location: v })} placeholder="e.g. Rotterdam" /></Row>
      </Section>
      <Section title="Summary">
        <Stat label="Subnets" value={site.subnets.length} />
        <Stat label="Devices" value={countContainers(site)} />
        <Stat label="Links to other sites" value={useAppStore.getState().topology.siteConnections.filter((c) => c.from === site.id || c.to === site.id).length} />
      </Section>
      <Actions>
        <Button size="sm" onClick={() => ctx.onNavigate({ level: 'site', siteId: site.id })}><ArrowDownRight /> Open</Button>
        {ctx.scope.level === 'root' ? (
          <Button size="sm" variant="ghost" onClick={() => toggleExpanded(site.id)}>{expanded ? <Minimize2 /> : <Maximize2 />} {expanded ? 'Collapse' : 'Expand'}</Button>
        ) : null}
        <Button size="sm" variant="ghost" onClick={() => { const ids = duplicateNodes([site.id]); if (ids.length) selectNodes(ids); }}><Copy /> Duplicate</Button>
        <Button size="sm" variant="danger-soft" className="ml-auto" onClick={() => remove([site.id])}><Trash2 /> Delete</Button>
      </Actions>
    </>
  );
}

// ── Subnet ────────────────────────────────────────────────────────────

export function SubnetPanel({ site, subnet, ctx }: { site: Site; subnet: Subnet; ctx: PanelContext }) {
  const { updateSubnet, duplicateNodes, selectNodes, toggleExpanded } = useAppStore.getState();
  const expanded = useAppStore((s) => !!s.expanded[subnet.id]);
  const remove = useRemove();
  const routers = subnet.containers.filter((c) => isRouterType(c.type));
  const outside = subnet.containers.filter((c) => c.ip && isValidCidr(subnet.cidr) && !isIpInCidr(c.ip, subnet.cidr));
  return (
    <>
      <Section title="Subnet">
        <Row label="Name"><CommitInput value={subnet.name} onCommit={(v) => updateSubnet(subnet.id, { name: v })} validate={(v) => (v ? null : 'Name is required')} /></Row>
        <Row label="CIDR" hint={outside.length ? <span className="text-warning">{outside.length} device{outside.length === 1 ? ' is' : 's are'} outside this range</span> : undefined}>
          <CommitInput value={subnet.cidr} mono onCommit={(v) => updateSubnet(subnet.id, { cidr: v })} validate={(v) => (isValidCidr(v) ? null : 'Enter a CIDR such as 10.0.1.0/24')} />
        </Row>
        <Row label="Gateway" hint={routers.length === 0 ? 'Add a router to route traffic out of this subnet.' : undefined}>
          <Select
            value={subnet.gateway ?? undefined}
            onValueChange={(ip) => updateSubnet(subnet.id, { gateway: ip })}
            options={routers.map((r) => ({ value: r.ip, label: `${r.name} · ${r.ip}` }))}
            placeholder={routers.length ? 'Choose a router' : 'No routers'}
            disabled={routers.length === 0}
            mono
          />
        </Row>
      </Section>
      <Section title="Summary">
        <Stat label="Devices" value={subnet.containers.length} />
        <Stat label="Links" value={subnet.connections.length} />
        <Stat label="Site" value={site.name} />
      </Section>
      <Actions>
        <Button size="sm" onClick={() => ctx.onNavigate({ level: 'subnet', siteId: site.id, subnetId: subnet.id })}><ArrowDownRight /> Open</Button>
        {ctx.scope.level !== 'subnet' ? (
          <Button size="sm" variant="ghost" onClick={() => toggleExpanded(subnet.id)}>{expanded ? <Minimize2 /> : <Maximize2 />} {expanded ? 'Collapse' : 'Expand'}</Button>
        ) : null}
        <Button size="sm" variant="ghost" onClick={() => { const ids = duplicateNodes([subnet.id]); if (ids.length) selectNodes(ids); }}><Copy /> Duplicate</Button>
        <Button size="sm" variant="danger-soft" className="ml-auto" onClick={() => remove([subnet.id])}><Trash2 /> Delete</Button>
      </Actions>
    </>
  );
}

// ── Device ────────────────────────────────────────────────────────────

export function DevicePanel({ subnet, container, ctx }: { site: Site; subnet: Subnet; container: Container; ctx: PanelContext }) {
  const { updateContainer, updateSubnet, duplicateNodes, selectNodes, openTerminal } = useAppStore.getState();
  const { status, deployStatus } = useAppShallow((s) => ({ status: s.containerStatus[container.id], deployStatus: s.deployStatus }));
  const remove = useRemove();
  const color = colorFor(container.type);
  const isGateway = gatewayOf(subnet)?.id === container.id;
  const takenByOthers = subnet.containers.filter((c) => c.id !== container.id).map((c) => c.ip);
  void ctx;

  const commitIp = (ip: string) => {
    const wasGateway = subnet.gateway === container.ip;
    updateContainer(container.id, { ip });
    if (wasGateway) updateSubnet(subnet.id, { gateway: ip });
  };

  return (
    <>
      <div className="flex items-center gap-2.5 border-b border-border px-3 py-3">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-md" style={{ background: `color-mix(in srgb, ${color} 14%, transparent)` }}>
          <NodeGlyph type={container.type} size={22} color={color} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold">{container.name}</div>
          <div className="flex items-center gap-1.5 text-2xs">
            <span className="font-semibold tracking-wide" style={{ color }}>{labelFor(container.type)}</span>
            <span className="text-fg-muted">{displayNameFor(container.type)}</span>
            {isGateway ? <Badge tone="neutral">gateway</Badge> : null}
          </div>
        </div>
        {status ? <Badge tone={status === 'running' ? 'success' : status === 'paused' ? 'warning' : 'danger'} dot={status === 'running' ? 'pulse' : true}>{status}</Badge> : null}
      </div>

      <Section title="Identity">
        <Row label="Name"><CommitInput value={container.name} onCommit={(v) => updateContainer(container.id, { name: v })} validate={(v) => (v ? null : 'Name is required')} /></Row>
        <Row label="Type">
          <DeviceTypePicker
            value={container.type}
            onValueChange={(type) => {
              // Variants belong to a type: keep a custom image, or a variant the new type shares.
              const img = container.image;
              const keep = img && (!variantsFor(container.type).includes(img) || variantsFor(type).includes(img)) ? img : undefined;
              updateContainer(container.id, { type, image: keep });
            }}
          />
        </Row>
        <Row label="Variant">
          <ImagePicker type={container.type} value={container.image} onChange={(image) => updateContainer(container.id, { image })} />
          <ImageStatusLine container={container} />
        </Row>
      </Section>

      <Section title="Network">
        <Row label="IP address" hint={`in ${subnet.cidr}`}>
          <CommitInput
            value={container.ip}
            mono
            onCommit={commitIp}
            validate={(v) => (!isValidIp(v) ? 'Enter a valid IPv4 address' : !isIpInCidr(v, subnet.cidr) ? `Must be inside ${subnet.cidr}` : takenByOthers.includes(v) ? 'Already used in this subnet' : null)}
          />
        </Row>
      </Section>

      <Section title="Metadata" defaultOpen={!!container.metadata && Object.keys(container.metadata).length > 0}>
        <KeyValueEditor value={container.metadata ?? {}} onChange={(next) => updateContainer(container.id, { metadata: Object.keys(next).length ? next : undefined })} addLabel="Add metadata" />
      </Section>

      <Section title="Configuration" defaultOpen={!!container.config && Object.keys(container.config).length > 0}>
        <p className="text-2xs text-fg-subtle">Free-form settings passed to the node at deploy time.</p>
        <KeyValueEditor
          mono
          value={Object.fromEntries(Object.entries(container.config ?? {}).map(([k, v]) => [k, typeof v === 'string' ? v : JSON.stringify(v)]))}
          onChange={(next) => updateContainer(container.id, { config: Object.keys(next).length ? next : undefined })}
          addLabel="Add setting"
        />
      </Section>

      <DeploymentSection nodeId={container.id} />

      <Actions>
        <Button size="sm" onClick={() => openTerminal(container)} disabled={deployStatus !== 'deployed'} title={deployStatus !== 'deployed' ? 'Deploy to open a terminal' : undefined}><Terminal /> Terminal</Button>
        <Button size="sm" variant="ghost" onClick={() => { const ids = duplicateNodes([container.id]); if (ids.length) selectNodes(ids); }}><Copy /> Duplicate</Button>
        <Button size="sm" variant="danger-soft" className="ml-auto" onClick={() => remove([container.id])}><Trash2 /> Delete</Button>
      </Actions>
      {deployStatus === 'deployed' ? (
        <Actions>
          <Button size="sm" variant="ghost" onClick={() => useAppStore.getState().openCaptureDialog({ kind: 'interface', nodeId: container.id })}><Radio /> Capture…</Button>
          <Button size="sm" variant="ghost" onClick={() => openTrafficPanel({ client: container.id })}><Activity /> Traffic…</Button>
        </Actions>
      ) : null}
    </>
  );
}

// ── Connection ────────────────────────────────────────────────────────

export function ConnectionPanel({ id }: { id: string }) {
  const topology = useAppStore((s) => s.topology);
  const deployStatus = useAppStore((s) => s.deployStatus);
  const capture = useAppStore((s) => s.activity.find((a) => a.kind === 'capture' && a.connection_ids?.includes(id)));
  const { updateConnection } = useAppStore.getState();
  const remove = useRemove();
  const hit = locateConnection(topology, id);
  if (!hit) return <p className="p-3 text-xs text-fg-muted">Connection no longer exists.</p>;
  const { connection, kind } = hit;
  const nameOf = (nid?: string) => { if (!nid) return '—'; const h = locate(topology, nid); return h ? (h.kind === 'site' ? h.site.name : h.kind === 'subnet' ? h.subnet.name : h.container.name) : nid; };
  const KIND = { site: 'Site link', subnet: 'Subnet link', container: 'Device link' } as const;
  return (
    <>
      <Section title={KIND[kind]}>
        <Stat label="From" value={nameOf(connection.from)} />
        <Stat label="To" value={nameOf(connection.to)} />
        {kind !== 'container' ? (
          <>
            <Stat label="Via" value={<span className="font-mono text-2xs">{nameOf(connection.fromContainer)} ↔ {nameOf(connection.toContainer)}</span>} />
          </>
        ) : null}
        <Row label="Label"><CommitInput value={connection.label ?? ''} placeholder="Optional label" onCommit={(v) => updateConnection(id, { label: v || undefined })} /></Row>
      </Section>
      <Actions>
        {capture ? (
          <>
            <Button size="sm" onClick={() => openCaptureTab(capture.job_id, capture.label || 'Capture')}><Radio /> View capture</Button>
            <Button size="sm" variant="ghost" onClick={() => void stopCapture(capture.job_id)}>Stop</Button>
          </>
        ) : (
          <Button
            size="sm"
            onClick={() => useAppStore.getState().openCaptureDialog({ kind: 'link', connectionId: id })}
            disabled={deployStatus !== 'deployed'}
            title={deployStatus !== 'deployed' ? 'Deploy to capture packets' : undefined}
          >
            <Radio /> Capture packets
          </Button>
        )}
        <Button size="sm" variant="danger-soft" className="ml-auto" onClick={() => remove([], [id])}><Trash2 /> Delete connection</Button>
      </Actions>
    </>
  );
}

// ── Multi-select ──────────────────────────────────────────────────────

export function MultiPanel({ nodeIds, edgeIds }: { nodeIds: string[]; edgeIds: string[] }) {
  const topology = useAppStore((s) => s.topology);
  const { duplicateNodes, selectNodes } = useAppStore.getState();
  const remove = useRemove();
  const kinds = { site: 0, subnet: 0, container: 0 };
  for (const id of nodeIds) { const h = locate(topology, id); if (h) kinds[h.kind]++; }
  return (
    <>
      <Section title="Selection">
        {kinds.site ? <Stat label="Sites" value={kinds.site} /> : null}
        {kinds.subnet ? <Stat label="Subnets" value={kinds.subnet} /> : null}
        {kinds.container ? <Stat label="Devices" value={kinds.container} /> : null}
        {edgeIds.length ? <Stat label="Connections" value={edgeIds.length} /> : null}
      </Section>
      <Actions>
        {nodeIds.length ? <Button size="sm" variant="ghost" onClick={() => { const ids = duplicateNodes(nodeIds); if (ids.length) selectNodes(ids); }}><Copy /> Duplicate</Button> : null}
        <Button size="sm" variant="danger-soft" className="ml-auto" onClick={() => remove(nodeIds, edgeIds)}><Trash2 /> Delete all</Button>
      </Actions>
    </>
  );
}
