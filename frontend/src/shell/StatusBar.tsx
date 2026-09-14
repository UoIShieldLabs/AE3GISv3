import { useAppShallow } from '@/store/selectors';
import { countContainers, countSubnets, type Scope } from '@/lib/topology';
import { cn } from '@/lib/cn';

export function StatusBar({ scope }: { scope: Scope }) {
  const { topology, selection, zoom, snap, deployStatus, dirty } = useAppShallow((s) => ({
    topology: s.topology, selection: s.selection, zoom: s.zoom, snap: s.snapToGrid, deployStatus: s.deployStatus, dirty: s.dirty,
  }));
  const selected = selection.nodeIds.length + selection.edgeIds.length;
  const level = scope.level === 'root' ? 'Network' : scope.level === 'site' ? 'Site' : 'Subnet';
  return (
    <div className="flex w-full items-center gap-4 tabular">
      <span className="font-medium text-fg-muted">{level}</span>
      <span>{topology.sites.length} sites · {countSubnets(topology)} subnets · {countContainers(topology)} devices</span>
      {selected ? <span className="text-accent">{selected} selected</span> : null}
      <span className="ml-auto" />
      <span className={cn(dirty ? 'text-warning' : 'text-fg-subtle')}>{dirty ? 'Unsaved changes' : 'Saved'}</span>
      <span className={cn(deployStatus === 'deployed' && 'text-success', deployStatus === 'error' && 'text-danger')}>{deployStatus}</span>
      <span>Snap {snap ? 'on' : 'off'}</span>
      <span>{Math.round(zoom * 100)}%</span>
    </div>
  );
}
