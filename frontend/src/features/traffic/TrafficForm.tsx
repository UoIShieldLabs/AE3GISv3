import { useMemo, useState } from 'react';
import { Play, Plus, Save, Trash2 } from 'lucide-react';
import { useAppStore } from '@/store';
import { useAppShallow } from '@/store/selectors';
import { Button, IconButton, Input, Select, Switch } from '@/ui';
import type { SavedFlow } from '@/types/topology';
import { MAX_FLOWS, flowErrors, newFlow, toRequestFlow } from './flows';
import { startTrafficRun } from './actions';

/** The form behind a new traffic run: flows (saved with the design) plus run settings. */
export function TrafficForm({ tabId, seed }: { tabId: string; seed?: { client?: string; nonce: number } }) {
  const { topology, containerStatus, deployStatus } = useAppShallow((s) => ({ topology: s.topology, containerStatus: s.containerStatus, deployStatus: s.deployStatus }));
  const nodes = useMemo(
    () => topology.sites.flatMap((site) => site.subnets.flatMap((sub) => sub.containers.map((c) => ({ id: c.id, name: c.name, ip: c.ip })))),
    [topology],
  );
  const options = useMemo(
    () => nodes.map((n) => ({ value: n.id, label: `${n.name}${n.ip ? ` · ${n.ip}` : ''}`, disabled: containerStatus[n.id] !== 'running' })),
    [nodes, containerStatus],
  );
  const firstTwo = options.filter((o) => !o.disabled).map((o) => o.value);
  const [flows, setFlows] = useState<SavedFlow[]>(() => {
    const saved = topology.traffic?.flows;
    return saved?.length ? saved : [newFlow([], firstTwo[0] ?? '', firstTwo[1] ?? '')];
  });
  const [untilStopped, setUntilStopped] = useState(false);
  const [duration, setDuration] = useState('30');
  const [label, setLabel] = useState('');
  const [monitor, setMonitor] = useState<'all' | 'flows'>('all');
  const [busy, setBusy] = useState(false);

  // "Generate traffic from here…": put the node in the first flow's client
  // slot, once per request (adjusting state while rendering, not in an effect).
  const [appliedSeed, setAppliedSeed] = useState<number | undefined>(undefined);
  if (seed?.client && seed.nonce !== appliedSeed) {
    const client = seed.client;
    setAppliedSeed(seed.nonce);
    setFlows((fs) => (fs.length ? [{ ...fs[0], client, server: fs[0].server === client ? '' : fs[0].server }, ...fs.slice(1)] : [newFlow([], client)]));
  }

  const errors = flowErrors(flows);
  const durationOk = untilStopped || (Number(duration) >= 1 && Number.isFinite(Number(duration)));
  const canRun = deployStatus === 'deployed' && flows.length > 0 && Object.keys(errors).length === 0 && durationOk;
  const update = (id: string, patch: Partial<SavedFlow>) => setFlows((fs) => fs.map((f) => (f.id === id ? { ...f, ...patch } : f)));

  const run = async () => {
    setBusy(true);
    await startTrafficRun(tabId, {
      label: label.trim(),
      notes: '',
      flows: flows.map(toRequestFlow),
      duration_s: untilStopped ? null : Math.round(Number(duration)),
      interval_s: 1,
      monitor_nodes: monitor,
    });
    setBusy(false);
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-auto p-3 text-xs">
      <div className="mb-2 flex items-center gap-2">
        <span className="font-medium text-fg">Flows</span>
        <span className="text-fg-subtle">iperf3 from each client to its server; traffic follows the lab's routes.</span>
      </div>
      <div className="flex flex-col gap-1.5">
        <div className="grid grid-cols-[2.5rem_minmax(9rem,1fr)_minmax(9rem,1fr)_5.5rem_9.5rem_6rem_4.5rem_2rem] items-center gap-2 text-2xs font-medium text-fg-muted">
          <span>ID</span><span>Client (sends)</span><span>Server</span><span>Protocol</span><span>Direction</span><span>Bitrate</span><span>Streams</span><span />
        </div>
        {flows.map((f) => (
          <div key={f.id} className="flex flex-col gap-0.5">
            <div className="grid grid-cols-[2.5rem_minmax(9rem,1fr)_minmax(9rem,1fr)_5.5rem_9.5rem_6rem_4.5rem_2rem] items-center gap-2">
              <span className="font-mono text-fg-muted">{f.id}</span>
              <Select size="sm" value={f.client || undefined} onValueChange={(v) => update(f.id, { client: v })} options={options} placeholder="Client…" aria-label={`${f.id} client`} />
              <Select size="sm" value={f.server || undefined} onValueChange={(v) => update(f.id, { server: v })} options={options} placeholder="Server…" aria-label={`${f.id} server`} />
              <Select size="sm" value={f.protocol} onValueChange={(v) => update(f.id, { protocol: v })} options={[{ value: 'tcp', label: 'TCP' }, { value: 'udp', label: 'UDP' }]} aria-label={`${f.id} protocol`} />
              <Select
                size="sm"
                value={f.direction}
                onValueChange={(v) => update(f.id, { direction: v })}
                options={[{ value: 'forward', label: 'Client → server' }, { value: 'reverse', label: 'Server → client' }, { value: 'bidir', label: 'Both ways' }]}
                aria-label={`${f.id} direction`}
              />
              <Input className="h-7 text-xs" mono value={f.bitrate ?? ''} onChange={(e) => update(f.id, { bitrate: e.target.value.trim() })} placeholder={f.protocol === 'udp' ? '1M' : 'max'} aria-label={`${f.id} bitrate`} />
              <Input className="h-7 text-xs" type="number" min={1} max={16} value={f.parallel ?? 1} onChange={(e) => update(f.id, { parallel: Number(e.target.value) || 1 })} aria-label={`${f.id} parallel streams`} />
              <IconButton label="Remove flow" size="icon-sm" disabled={flows.length === 1} onClick={() => setFlows((fs) => fs.filter((x) => x.id !== f.id))}><Trash2 /></IconButton>
            </div>
            {errors[f.id] ? <span className="pl-12 text-2xs text-danger">{errors[f.id]}</span> : null}
          </div>
        ))}
        <div>
          <Button size="xs" variant="ghost" disabled={flows.length >= MAX_FLOWS} onClick={() => setFlows((fs) => [...fs, newFlow(fs, firstTwo[0] ?? '', firstTwo[1] ?? '')])}><Plus /> Add flow</Button>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-border pt-3">
        <label className="flex items-center gap-2">
          <span className="text-fg-muted">Duration</span>
          <Input className="h-7 w-20 text-xs" type="number" min={1} value={duration} disabled={untilStopped} onChange={(e) => setDuration(e.target.value)} aria-label="Duration in seconds" />
          <span className="text-fg-subtle">s</span>
        </label>
        <label className="flex items-center gap-2 text-fg-muted">
          <Switch checked={untilStopped} onCheckedChange={setUntilStopped} aria-label="Run until stopped" /> Until stopped
        </label>
        <label className="flex items-center gap-2">
          <span className="text-fg-muted">Monitor</span>
          <Select size="sm" className="w-40" value={monitor} onValueChange={setMonitor} options={[{ value: 'all', label: 'All nodes' }, { value: 'flows', label: 'Flow endpoints' }]} aria-label="Nodes to monitor" />
        </label>
        <Input className="h-7 w-48 text-xs" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Label (e.g. baseline tcp)" aria-label="Run label" />
        <div className="ml-auto flex items-center gap-2">
          <Button size="sm" variant="ghost" onClick={() => useAppStore.getState().setTrafficFlows(flows)} title="Keep these flows with the topology (save to persist)"><Save /> Save flows</Button>
          <Button size="sm" variant="primary" loading={busy} disabled={!canRun} onClick={() => void run()} title={deployStatus !== 'deployed' ? 'Deploy the topology first' : undefined}><Play /> Start run</Button>
        </div>
      </div>
    </div>
  );
}
