import { useMemo, useState } from 'react';
import { ArrowRight, ChevronDown, ChevronRight, ChevronUp, Plus, Trash2 } from 'lucide-react';
import { useAppStore } from '@/store';
import type { Tutorial, TutorialSetup, TutorialTraffic } from '@/types/topology';
import { generateId } from '@/lib/ids';
import { cn } from '@/lib/cn';
import { CommitInput } from '@/shell/inspector/CommitInput';
import { Button, IconButton, MultiSelect, Select, type SelectOption } from '@/ui';
import { CommitTextarea } from '../CommitTextarea';
import { DEFAULT_BITRATE, rowProblem, TO, type SetupNode } from './model';

const KINDS: SelectOption<TutorialTraffic['kind']>[] = [
  { value: 'command', label: 'Custom command' },
  { value: 'iperf3', label: 'Throughput (iperf3)' },
];
const PROTOCOLS: SelectOption<'tcp' | 'udp'>[] = [{ value: 'tcp', label: 'TCP' }, { value: 'udp', label: 'UDP' }];

/** Edit a tutorial's lab setup: the commands "Configure lab" runs, and the
 *  background traffic (from these nodes, to those). Collapsed while empty. */
export function LabSetupEditor({ tutorial, nodes, nodeOptions }: {
  tutorial: Tutorial;
  nodes: ReadonlyMap<string, SetupNode>;
  nodeOptions: SelectOption[];
}) {
  const steps = tutorial.setup?.steps ?? [];
  const traffic = tutorial.setup?.traffic ?? [];
  const [open, setOpen] = useState(steps.length + traffic.length > 0);
  const pickOptions = useMemo(() => [...nodes.values()].map((n) => ({ value: n.id, label: n.ip ? `${n.name} · ${n.ip}` : n.name })), [nodes]);
  const edit = (recipe: (setup: TutorialSetup) => void) => useAppStore.getState().updateTutorialSetup(tutorial.id, recipe);
  const move = <T,>(list: T[], from: number, to: number) => { const [item] = list.splice(from, 1); list.splice(to, 0, item); };

  const addStep = () => {
    // Like a new command cell: start on the node of the step before it.
    const near = steps[steps.length - 1]?.containerId ?? '';
    edit((s) => { s.steps.push({ id: generateId('setup'), containerId: near, command: '' }); });
    setOpen(true);
  };
  const addTraffic = () => {
    edit((s) => { s.traffic.push({ id: generateId('traffic'), kind: 'command', from: [], to: [], command: '' }); });
    setOpen(true);
  };

  return (
    <section aria-label="Lab setup" className="mb-3 rounded-md border border-border bg-surface-2/40">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-1.5 px-2.5 py-2 text-left text-xs outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
      >
        <ChevronRight className={cn('size-3.5 shrink-0 text-fg-subtle transition-transform', open && 'rotate-90')} aria-hidden />
        <span className="font-medium text-fg">Lab setup</span>
        <span className="min-w-0 truncate text-2xs text-fg-muted">
          {steps.length + traffic.length === 0
            ? 'optional: what the lab needs before the first step'
            : [steps.length ? `${steps.length} step${steps.length === 1 ? '' : 's'}` : '', traffic.length ? `${traffic.length} traffic` : ''].filter(Boolean).join(' · ')}
        </span>
      </button>

      {open ? (
        <div className="space-y-3 border-t border-border/70 px-2.5 pb-2.5 pt-2">
          <div className="space-y-1.5">
            <p className="text-2xs text-fg-muted">Steps run in order, without a terminal, when the student clicks <span className="font-medium text-fg">Configure lab</span>.</p>
            {steps.map((step, i) => (
              <div key={step.id} className="group/row rounded-md border border-border bg-surface">
                <div className="flex items-center gap-1 border-b border-border/70 py-1 pl-1.5 pr-1">
                  <Select
                    size="sm"
                    className="h-6 w-auto min-w-28 max-w-[60%] text-xs"
                    value={nodes.has(step.containerId) ? step.containerId : undefined}
                    onValueChange={(containerId) => edit((s) => { s.steps[i].containerId = containerId; })}
                    options={nodeOptions}
                    placeholder={step.containerId ? 'Node removed' : 'Pick a node'}
                    aria-label="Setup step node"
                  />
                  <span className="ml-auto flex opacity-0 transition-opacity group-focus-within/row:opacity-100 group-hover/row:opacity-100">
                    <IconButton label="Move up" size="icon-xs" disabled={i === 0} onClick={() => edit((s) => move(s.steps, i, i - 1))}><ChevronUp /></IconButton>
                    <IconButton label="Move down" size="icon-xs" disabled={i === steps.length - 1} onClick={() => edit((s) => move(s.steps, i, i + 1))}><ChevronDown /></IconButton>
                    <IconButton label="Delete setup step" size="icon-xs" onClick={() => edit((s) => { s.steps.splice(i, 1); })}><Trash2 /></IconButton>
                  </span>
                </div>
                <div className="p-1">
                  <CommitTextarea
                    className="border-transparent bg-transparent px-1.5 py-1 font-mono text-xs hover:border-border focus:bg-surface"
                    value={step.command}
                    onCommit={(command) => edit((s) => { s.steps[i].command = command; })}
                    placeholder="command, e.g. nft insert rule inet filter forward …"
                    aria-label="Setup step command"
                    spellCheck={false}
                  />
                </div>
              </div>
            ))}
            <Button size="xs" variant="outline" onClick={addStep}><Plus /> Setup step</Button>
          </div>

          <div className="space-y-1.5">
            <p className="text-2xs text-fg-muted">Background traffic keeps running until it is switched off: every sender sends to every destination.</p>
            {traffic.map((row, i) => {
              const problem = rowProblem(row, nodes);
              const set = (patch: Partial<TutorialTraffic>) => edit((s) => { Object.assign(s.traffic[i], patch); });
              return (
                <div key={row.id} className="space-y-1.5 rounded-md border border-border bg-surface p-1.5">
                  <div className="flex items-center gap-1.5">
                    <div className="min-w-0 flex-1">
                      <CommitInput className="h-6 text-xs" value={row.label ?? ''} onCommit={(label) => set({ label })} placeholder="Name (optional)" aria-label="Traffic name" />
                    </div>
                    <Select size="sm" className="h-6 w-auto text-xs" value={row.kind} onValueChange={(kind) => set({ kind })} options={KINDS} aria-label="Traffic type" />
                    <IconButton label="Delete traffic" size="icon-xs" onClick={() => edit((s) => { s.traffic.splice(i, 1); })}><Trash2 /></IconButton>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <MultiSelect size="sm" className="min-w-0 flex-1" value={(row.from ?? []).filter((id) => nodes.has(id))} onValueChange={(from) => set({ from })} options={pickOptions} placeholder="From…" aria-label="Senders" />
                    <ArrowRight className="size-3.5 shrink-0 text-fg-subtle" aria-hidden />
                    <MultiSelect size="sm" className="min-w-0 flex-1" value={(row.to ?? []).filter((id) => nodes.has(id))} onValueChange={(to) => set({ to })} options={pickOptions} placeholder="To…" aria-label="Destinations" />
                  </div>
                  {row.kind === 'iperf3' ? (
                    <div className="flex items-center gap-1.5 text-2xs text-fg-muted">
                      <Select size="sm" className="h-6 w-20 text-xs" value={row.protocol ?? 'tcp'} onValueChange={(protocol) => set({ protocol })} options={PROTOCOLS} aria-label="Protocol" />
                      <span>at</span>
                      <div className="w-20">
                        <CommitInput className="h-6 font-mono text-xs" value={row.bitrate ?? DEFAULT_BITRATE} onCommit={(bitrate) => set({ bitrate: bitrate || DEFAULT_BITRATE })} aria-label="Rate" />
                      </div>
                      <span>per flow (e.g. 1M, 500K)</span>
                    </div>
                  ) : (
                    <>
                      <CommitTextarea
                        className="px-1.5 py-1 font-mono text-xs"
                        value={row.command ?? ''}
                        onCommit={(command) => set({ command })}
                        placeholder={`runs on every sender, e.g. while sleep 2; do nc -z ${TO} 2404; done`}
                        aria-label="Traffic command"
                        spellCheck={false}
                      />
                      <p className="text-2xs text-fg-subtle"><code className="font-mono">{TO}</code> becomes each destination's IP address (the command then runs once per destination).</p>
                    </>
                  )}
                  {problem ? <p className="text-2xs text-warning">{problem}</p> : null}
                </div>
              );
            })}
            <Button size="xs" variant="outline" onClick={addTraffic}><Plus /> Background traffic</Button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
