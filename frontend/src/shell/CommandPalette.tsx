import { Dialog as RDialog } from 'radix-ui';
import { useNavigate } from 'react-router';
import { Boxes, Building2, Download, Layers3, Library, Monitor, Moon, Network, PanelLeft, PanelRight, Play, Plus, Save, Sparkles, Square, Sun } from 'lucide-react';
import { useAppStore } from '@/store';
import { useAppShallow } from '@/store/selectors';
import { colorFor } from '@/catalog/catalog';
import { NodeGlyph } from '@/catalog/icons';
import { MOD } from '@/lib/keyboard';
import type { Scope } from '@/lib/topology';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator } from '@/ui';
import { createNewTopology, deployTopology, destroyTopology, exportLab, exportTopologyJson } from '@/features/deployment/actions';
import { useAddEntity } from '@/features/topology/AddEntityContext';
import { targetSiteFor, targetSubnetFor } from '@/features/topology/addTargets';

export interface CommandPaletteProps {
  scope: Scope;
  onNavigate: (scope: Scope) => void;
  onSave: () => void;
}

/** ⌘K: jump to any entity or run an editor action. */
export function CommandPalette({ scope, onNavigate, onSave }: CommandPaletteProps) {
  const { open, topology, deployStatus, backendId, sidebarOpen, inspectorOpen, layoutMode, selection } = useAppShallow((s) => ({
    open: s.commandPaletteOpen, topology: s.topology, deployStatus: s.deployStatus, backendId: s.backendId,
    sidebarOpen: s.sidebarOpen, inspectorOpen: s.inspectorOpen, layoutMode: s.layoutMode, selection: s.selection,
  }));
  const navigate = useNavigate();
  const { requestAdd } = useAddEntity();
  const st = useAppStore.getState;

  const close = () => st().setCommandPaletteOpen(false);
  const run = (fn: () => void) => () => { close(); fn(); };
  const goTo = (target: Scope, selectId?: string) => run(() => { if (selectId) st().selectNodes([selectId]); onNavigate(target); });

  return (
    <RDialog.Root open={open} onOpenChange={(o) => st().setCommandPaletteOpen(o)}>
      <RDialog.Portal>
        <RDialog.Overlay className="fixed inset-0 z-[85] bg-black/40 animate-fade" />
        <RDialog.Content className="fixed left-1/2 top-[12vh] z-[86] w-[calc(100vw-32px)] max-w-xl -translate-x-1/2 overflow-hidden rounded-xl border border-border bg-elevated shadow-lg outline-none animate-pop">
          <RDialog.Title className="sr-only">Command palette</RDialog.Title>
          <RDialog.Description className="sr-only">Search entities and actions</RDialog.Description>
          <Command loop>
            <CommandInput placeholder="Jump to a site, subnet, device… or run an action" />
            <CommandList className="max-h-[50vh]">
              <CommandEmpty>Nothing matches.</CommandEmpty>

              <CommandGroup heading="Actions">
                <CommandItem onSelect={run(onSave)} shortcut={`${MOD}S`}><Save /> Save topology</CommandItem>
                {deployStatus === 'deployed' ? (
                  <CommandItem onSelect={run(() => void destroyTopology())}><Square /> Destroy deployment</CommandItem>
                ) : (
                  <CommandItem onSelect={run(() => void deployTopology())} disabled={!backendId || deployStatus === 'deploying'}><Play /> Deploy topology</CommandItem>
                )}
                <CommandItem onSelect={run(() => st().applyLayout(scope, layoutMode))} shortcut="L"><Sparkles /> Apply {layoutMode} layout</CommandItem>
                {scope.level === 'root' ? <CommandItem onSelect={run(() => requestAdd({ kind: 'site' }, {}))}><Plus /> Add site…</CommandItem> : null}
                {scope.level !== 'subnet' ? <CommandItem onSelect={run(() => requestAdd({ kind: 'subnet' }, { siteId: targetSiteFor(scope, selection.nodeIds) }))}><Plus /> Add subnet…</CommandItem> : null}
                {scope.level !== 'root' ? <CommandItem onSelect={run(() => requestAdd({ kind: 'device', type: 'workstation' }, { subnetId: targetSubnetFor(scope, selection.nodeIds) }))}><Plus /> Add device…</CommandItem> : null}
                <CommandItem onSelect={run(exportTopologyJson)}><Download /> Export design (JSON)</CommandItem>
                <CommandItem onSelect={run(() => void exportLab('kathara'))} disabled={!backendId}><Download /> Export Kathara lab (zip)</CommandItem>
                <CommandItem onSelect={run(() => void exportLab('containerlab'))} disabled={!backendId}><Download /> Export ContainerLab topology (zip)</CommandItem>
                <CommandItem onSelect={run(() => st().setPurdueOpen(true))}><Layers3 /> Purdue model view</CommandItem>
                <CommandItem onSelect={run(() => st().openImages())} keywords={['images', 'build', 'dockerfile', 'containers']}><Boxes /> Images</CommandItem>
              </CommandGroup>

              <CommandSeparator />
              <CommandGroup heading="Go to">
                <CommandItem onSelect={goTo({ level: 'root' })} keywords={['network', 'overview', 'root']}><Network /> Network overview</CommandItem>
                {topology.sites.map((site) => (
                  <CommandItem key={site.id} value={`site ${site.name} ${site.location}`} onSelect={goTo({ level: 'site', siteId: site.id })}>
                    <Building2 className="!text-accent" /> {site.name} <span className="text-2xs text-fg-subtle">site</span>
                  </CommandItem>
                ))}
                {topology.sites.flatMap((site) => site.subnets.map((sn) => (
                  <CommandItem key={sn.id} value={`subnet ${sn.name} ${sn.cidr} ${site.name}`} onSelect={goTo({ level: 'subnet', siteId: site.id, subnetId: sn.id })}>
                    <Network className="!text-info" /> {sn.name} <span className="font-mono text-2xs text-fg-subtle">{sn.cidr}</span>
                  </CommandItem>
                )))}
                {topology.sites.flatMap((site) => site.subnets.flatMap((sn) => sn.containers.map((c) => (
                  <CommandItem key={c.id} value={`device ${c.name} ${c.ip} ${c.type} ${sn.name}`} onSelect={goTo({ level: 'subnet', siteId: site.id, subnetId: sn.id }, c.id)}>
                    <NodeGlyph type={c.type} size={14} color={colorFor(c.type)} /> {c.name} <span className="font-mono text-2xs text-fg-subtle">{c.ip}</span>
                  </CommandItem>
                ))))}
              </CommandGroup>

              <CommandSeparator />
              <CommandGroup heading="View">
                <CommandItem onSelect={run(() => st().setSidebarOpen(!sidebarOpen))} shortcut={`${MOD}B`}><PanelLeft /> {sidebarOpen ? 'Hide' : 'Show'} sidebar</CommandItem>
                <CommandItem onSelect={run(() => st().setInspectorOpen(!inspectorOpen))} shortcut={`${MOD}I`}><PanelRight /> {inspectorOpen ? 'Hide' : 'Show'} inspector</CommandItem>
                <CommandItem onSelect={run(() => st().setTheme('light'))}><Sun /> Light theme</CommandItem>
                <CommandItem onSelect={run(() => st().setTheme('dark'))}><Moon /> Dark theme</CommandItem>
                <CommandItem onSelect={run(() => st().setTheme('system'))}><Monitor /> System theme</CommandItem>
              </CommandGroup>

              <CommandSeparator />
              <CommandGroup heading="Topologies">
                <CommandItem onSelect={run(() => void navigate('/'))}><Library /> Open library</CommandItem>
                <CommandItem onSelect={run(() => { createNewTopology(); void navigate('/t/draft'); })}><Plus /> New topology</CommandItem>
              </CommandGroup>
            </CommandList>
          </Command>
        </RDialog.Content>
      </RDialog.Portal>
    </RDialog.Root>
  );
}
