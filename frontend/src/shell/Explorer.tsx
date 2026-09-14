import { useMemo, useState } from 'react';
import { Building2, ChevronDown, ChevronRight, Network, Search } from 'lucide-react';
import { useAppStore } from '@/store';
import { useAppShallow } from '@/store/selectors';
import { colorFor } from '@/catalog/catalog';
import { NodeGlyph } from '@/catalog/icons';
import { cn } from '@/lib/cn';
import { scopeEquals, type Scope } from '@/lib/topology';
import { Input } from '@/ui';

export interface ExplorerProps {
  scope: Scope;
  onNavigate: (scope: Scope) => void;
}

const STATUS_DOT = { running: 'bg-success', stopped: 'bg-danger', paused: 'bg-warning' } as const;

/** Tree of sites → subnets → devices; click selects (navigating to the right scope), double-click drills in. */
export function Explorer({ scope, onNavigate }: ExplorerProps) {
  const topology = useAppStore((s) => s.topology);
  const { selection, expanded, containerStatus } = useAppShallow((s) => ({ selection: s.selection, expanded: s.expanded, containerStatus: s.containerStatus }));
  const [query, setQuery] = useState('');
  const [collapsed, setCollapsed] = useState<Record<string, true>>({});
  const q = query.trim().toLowerCase();
  const selected = new Set(selection.nodeIds);

  const matches = (text: string) => !q || text.toLowerCase().includes(q);

  const tree = useMemo(() => topology.sites.map((site) => ({
    site,
    subnets: site.subnets.map((subnet) => ({
      subnet,
      devices: subnet.containers.filter((c) => matches(`${c.name} ${c.ip} ${c.type}`)),
    })).filter((s) => !q || matches(`${s.subnet.name} ${s.subnet.cidr}`) || s.devices.length > 0),
  })).filter((s) => !q || matches(s.site.name) || s.subnets.length > 0), [topology, q]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggle = (id: string) => setCollapsed((c) => { const n = { ...c }; if (n[id]) delete n[id]; else n[id] = true; return n; });

  const select = (id: string, needed: Scope) => {
    const st = useAppStore.getState();
    st.selectNodes([id]);
    st.setInspectorOpen(true);
    // Reveal: navigate unless the node is already drawn in this scope (directly or inside an expanded group).
    const visibleHere =
      scopeEquals(scope, needed) ||
      (needed.level === 'site' && scope.level === 'root' && expanded[needed.siteId]) ||
      (needed.level === 'subnet' && ((scope.level === 'site' && scope.siteId === needed.siteId && expanded[needed.subnetId]) || (scope.level === 'root' && expanded[needed.siteId] && expanded[needed.subnetId])));
    if (!visibleHere) onNavigate(needed);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="p-2">
        <Input leading={<Search />} placeholder="Find sites, subnets, devices…" value={query} onChange={(e) => setQuery(e.target.value)} className="h-7 text-xs" />
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-1 pb-3 text-xs">
        {tree.length === 0 ? <p className="px-3 py-6 text-center text-fg-muted">{q ? 'No matches.' : 'No sites yet.'}</p> : null}
        {tree.map(({ site, subnets }) => {
          const open = !collapsed[site.id] || !!q;
          return (
            <div key={site.id}>
              <Row
                depth={0}
                selected={selected.has(site.id)}
                current={scope.level !== 'root' && scope.siteId === site.id}
                icon={<Building2 className="size-3.5 text-accent" />}
                label={site.name}
                meta={`${site.subnets.length}`}
                caret={open ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
                onCaret={() => toggle(site.id)}
                onClick={() => select(site.id, { level: 'root' })}
                onDoubleClick={() => onNavigate({ level: 'site', siteId: site.id })}
              />
              {open ? subnets.map(({ subnet, devices }) => {
                const sopen = !collapsed[subnet.id] || !!q;
                return (
                  <div key={subnet.id}>
                    <Row
                      depth={1}
                      selected={selected.has(subnet.id)}
                      current={scope.level === 'subnet' && scope.subnetId === subnet.id}
                      icon={<Network className="size-3.5 text-info" />}
                      label={subnet.name}
                      meta={subnet.cidr}
                      caret={sopen ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
                      onCaret={() => toggle(subnet.id)}
                      onClick={() => select(subnet.id, { level: 'site', siteId: site.id })}
                      onDoubleClick={() => onNavigate({ level: 'subnet', siteId: site.id, subnetId: subnet.id })}
                    />
                    {sopen ? devices.map((c) => (
                      <Row
                        key={c.id}
                        depth={2}
                        selected={selected.has(c.id)}
                        icon={<NodeGlyph type={c.type} size={14} color={colorFor(c.type)} />}
                        label={c.name}
                        meta={c.ip}
                        status={containerStatus[c.id]}
                        onClick={() => select(c.id, { level: 'subnet', siteId: site.id, subnetId: subnet.id })}
                      />
                    )) : null}
                  </div>
                );
              }) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Row({ depth, selected, current, icon, label, meta, status, caret, onCaret, onClick, onDoubleClick }: {
  depth: number; selected: boolean; current?: boolean; icon: React.ReactNode; label: string; meta?: string;
  status?: 'running' | 'stopped' | 'paused'; caret?: React.ReactNode; onCaret?: () => void; onClick: () => void; onDoubleClick?: () => void;
}) {
  return (
    <div
      role="treeitem"
      aria-selected={selected}
      tabIndex={0}
      onClick={onClick}
      onDoubleClick={onDoubleClick}
      onKeyDown={(e) => { if (e.key === 'Enter') (onDoubleClick ?? onClick)(); }}
      className={cn(
        'flex h-7 cursor-default select-none items-center gap-1 rounded-md pr-2 transition-colors',
        selected ? 'bg-accent-soft text-fg' : 'hover:bg-hover',
        'focus-visible:outline-2 focus-visible:outline-ring',
      )}
      style={{ paddingLeft: 6 + depth * 14 }}
    >
      <span className="flex size-4 shrink-0 items-center justify-center text-fg-subtle" onClick={(e) => { if (onCaret) { e.stopPropagation(); onCaret(); } }}>
        {caret}
      </span>
      <span className="flex size-4 shrink-0 items-center justify-center">{icon}</span>
      <span className={cn('min-w-0 flex-1 truncate', current && 'font-semibold')}>{label}</span>
      {status ? <span className={cn('size-1.5 shrink-0 rounded-full', STATUS_DOT[status])} /> : null}
      {meta ? <span className="shrink-0 font-mono text-2xs text-fg-subtle">{meta}</span> : null}
    </div>
  );
}
