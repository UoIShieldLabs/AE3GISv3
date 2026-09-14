import { X } from 'lucide-react';
import { useAppStore } from '@/store';
import { useAppShallow } from '@/store/selectors';
import { locate, type Scope } from '@/lib/topology';
import { IconButton } from '@/ui';
import { ConnectionPanel, DevicePanel, MultiPanel, SitePanel, SubnetPanel, TopologyPanel } from './inspector/panels';

export interface InspectorProps {
  scope: Scope;
  onNavigate: (scope: Scope) => void;
}

/** Context-sensitive properties for the current selection (or the topology when nothing is selected). */
export function Inspector({ scope, onNavigate }: InspectorProps) {
  const { selection, topology } = useAppShallow((s) => ({ selection: s.selection, topology: s.topology }));
  const setOpen = useAppStore((s) => s.setInspectorOpen);
  const ctx = { scope, onNavigate };

  let title = 'Topology';
  let body: React.ReactNode = <TopologyPanel />;
  const total = selection.nodeIds.length + selection.edgeIds.length;
  if (total > 1) {
    title = `${total} selected`;
    body = <MultiPanel nodeIds={selection.nodeIds} edgeIds={selection.edgeIds} />;
  } else if (selection.edgeIds.length === 1) {
    title = 'Connection';
    body = <ConnectionPanel id={selection.edgeIds[0]} />;
  } else if (selection.nodeIds.length === 1) {
    const hit = locate(topology, selection.nodeIds[0]);
    if (hit?.kind === 'site') { title = 'Site'; body = <SitePanel site={hit.site} ctx={ctx} />; }
    else if (hit?.kind === 'subnet') { title = 'Subnet'; body = <SubnetPanel site={hit.site} subnet={hit.subnet} ctx={ctx} />; }
    else if (hit?.kind === 'container') { title = 'Device'; body = <DevicePanel site={hit.site} subnet={hit.subnet} container={hit.container} ctx={ctx} />; }
  }

  return (
    <aside className="flex h-full min-w-0 flex-col border-l border-border bg-surface">
      <div className="flex h-9 shrink-0 items-center justify-between border-b border-border pl-3 pr-1.5">
        <span className="text-xs font-semibold">{title}</span>
        <IconButton label="Hide inspector" shortcut="⌘I" size="icon-xs" onClick={() => setOpen(false)}><X /></IconButton>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">{body}</div>
    </aside>
  );
}
