import { useMemo, useState } from 'react';
import { Play, Plus, Save, Trash2 } from 'lucide-react';
import { useAppStore } from '@/store';
import { useAppShallow } from '@/store/selectors';
import { Button, IconButton, Input, MultiSelect, Select, Switch } from '@/ui';
import type { ComboboxOption } from '@/ui';
import type { SavedFlow } from '@/types/topology';
import { nodesOf, preview } from '@/features/monitor/selection';
import { MAX_FLOWS, flowErrors, newFlow, toRequestFlow } from './flows';
import { flowCount, newPattern, patternError, toRequestPattern, type NodeSet, type PatternDraft } from './patterns';
import { startTrafficRun } from './actions';

type Mode = 'flows' | PatternDraft['kind'];

const MODES: { value: Mode; label: string }[] = [
  { value: 'flows', label: 'Flows (pick each pair)' },
  { value: 'clients_to_servers', label: 'Clients → servers' },
  { value: 'mesh', label: 'Mesh' },
];
const NODE_SETS: { value: NodeSet; label: string }[] = [
  { value: 'hosts', label: 'All hosts' },
  { value: 'all', label: 'All nodes' },
  { value: 'pick', label: 'Pick nodes' },
];
const PROTOCOLS: { value: PatternDraft['protocol']; label: string }[] = [{ value: 'tcp', label: 'TCP' }, { value: 'udp', label: 'UDP' }];
const DIRECTIONS: { value: PatternDraft['direction']; label: string }[] = [{ value: 'forward', label: 'Client → server' }, { value: 'reverse', label: 'Server → client' }, { value: 'bidir', label: 'Both ways' }];
/** The server's default flow limit (AE3GIS_TRAFFIC_MAX_FLOWS); it checks again. */
const SERVER_MAX_FLOWS = 2000;

/** The form behind a new traffic run: explicit flows (saved with the design)
 *  or a pattern (clients → servers, mesh), plus run settings. */
export function TrafficForm({ tabId, seed }: { tabId: string; seed?: { client?: string; nonce: number } }) {
  const { topology, containerStatus, deployStatus } = useAppShallow((s) => ({ topology: s.topology, containerStatus: s.containerStatus, deployStatus: s.deployStatus }));
  const nodes = useMemo(() => nodesOf(topology), [topology]);
  const options = useMemo(
    () => nodes.map((n) => ({ value: n.id, label: `${n.name}${n.ip ? ` · ${n.ip}` : ''}`, disabled: containerStatus[n.id] !== 'running' })),
    [nodes, containerStatus],
  );
  const firstTwo = options.filter((o) => !o.disabled).map((o) => o.value);
  const [mode, setMode] = useState<Mode>('flows');
  const [flows, setFlows] = useState<SavedFlow[]>(() => {
    const saved = topology.traffic?.flows;
    return saved?.length ? saved : [newFlow([], firstTwo[0] ?? '', firstTwo[1] ?? '')];
  });
  const [pattern, setPattern] = useState<PatternDraft>(() => newPattern('clients_to_servers'));
  const [untilStopped, setUntilStopped] = useState(false);
  const [duration, setDuration] = useState('30');
  const [interval, setIntervalS] = useState('1');
  const [ramp, setRamp] = useState('0');
  const [label, setLabel] = useState('');
  const [busy, setBusy] = useState(false);

  // "Generate traffic from here…": put the node in the first flow's client
  // slot, once per request (adjusting state while rendering, not in an effect).
  const [appliedSeed, setAppliedSeed] = useState<number | undefined>(undefined);
  if (seed?.client && seed.nonce !== appliedSeed) {
    const client = seed.client;
    setAppliedSeed(seed.nonce);
    setMode('flows');
    setFlows((fs) => (fs.length ? [{ ...fs[0], client, server: fs[0].server === client ? '' : fs[0].server }, ...fs.slice(1)] : [newFlow([], client)]));
  }

  const running = (id: string) => containerStatus[id] === 'running';
  const resolve = (set: NodeSet, picks: string[]) =>
    preview(nodes, running, set === 'hosts' ? { mode: 'hosts', picks: [] } : set === 'all' ? { mode: 'all', picks: [] } : { mode: 'nodes', picks }).map((n) => n.id);
  const patternFlows = mode === 'flows' ? 0 : flowCount(pattern, resolve);
  const errors = flowErrors(flows);
  const patternProblem = mode === 'flows' ? null : patternError(pattern, patternFlows, SERVER_MAX_FLOWS);
  const num = (v: string, lo: number, hi: number) => Number.isFinite(Number(v)) && Number(v) >= lo && Number(v) <= hi;
  const settingsOk = (untilStopped || num(duration, 1, 1e9)) && num(interval, 0.5, 60) && num(ramp, 0, 600);
  const flowsOk = mode === 'flows' ? flows.length > 0 && Object.keys(errors).length === 0 : patternProblem === null;
  const canRun = deployStatus === 'deployed' && flowsOk && settingsOk;
  const update = (id: string, patch: Partial<SavedFlow>) => setFlows((fs) => fs.map((f) => (f.id === id ? { ...f, ...patch } : f)));
  const setP = (patch: Partial<PatternDraft>) => setPattern((p) => ({ ...p, ...patch }));

  const run = async () => {
    setBusy(true);
    await startTrafficRun(tabId, {
      label: label.trim(),
      notes: '',
      flows: mode === 'flows' ? flows.map(toRequestFlow) : [],
      patterns: mode === 'flows' ? [] : [toRequestPattern(pattern)],
      duration_s: untilStopped ? null : Math.round(Number(duration)),
      interval_s: Number(interval),
      ramp_s: Number(ramp),
    });
    setBusy(false);
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-auto p-3 text-xs">
      <div className="mb-2 flex items-center gap-2">
        <Select size="sm" className="w-52" value={mode} onValueChange={(m) => { setMode(m); if (m !== 'flows') setP({ kind: m }); }} options={MODES} aria-label="How flows are chosen" />
        <span className="text-fg-subtle">
          {mode === 'flows'
            ? 'iperf3 from each client to its server; traffic follows the lab\'s routes.'
            : mode === 'mesh'
              ? 'Each node sends to the next nodes on a ring, so every node sends and receives the same number of flows.'
              : 'Each client sends to one server (round-robin) or to every server.'}
        </span>
      </div>

      {mode === 'flows' ? (
        <FlowsEditor flows={flows} errors={errors} options={options} update={update} setFlows={setFlows} firstTwo={firstTwo} />
      ) : (
        <PatternEditor pattern={pattern} setP={setP} options={options} flows={patternFlows} problem={patternProblem} />
      )}

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-border pt-3">
        <label className="flex items-center gap-2">
          <span className="text-fg-muted">Duration</span>
          <Input className="h-7 w-20 text-xs" type="number" min={1} value={duration} disabled={untilStopped} onChange={(e) => setDuration(e.target.value)} aria-label="Duration in seconds" />
          <span className="text-fg-subtle">s</span>
        </label>
        <label className="flex items-center gap-2 text-fg-muted">
          <Switch checked={untilStopped} onCheckedChange={setUntilStopped} aria-label="Run until stopped" /> Until stopped
        </label>
        <label className="flex items-center gap-2" title="iperf3 report interval: the samples' resolution">
          <span className="text-fg-muted">Every</span>
          <Input className="h-7 w-16 text-xs" type="number" min={0.5} max={60} step={0.5} value={interval} onChange={(e) => setIntervalS(e.target.value)} aria-label="Report interval in seconds" />
          <span className="text-fg-subtle">s</span>
        </label>
        <label className="flex items-center gap-2" title="Start the clients spread over this many seconds">
          <span className="text-fg-muted">Ramp</span>
          <Input className="h-7 w-16 text-xs" type="number" min={0} max={600} value={ramp} onChange={(e) => setRamp(e.target.value)} aria-label="Ramp-up in seconds" />
          <span className="text-fg-subtle">s</span>
        </label>
        <Input className="h-7 w-48 text-xs" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Label (e.g. baseline tcp)" aria-label="Run label" />
        <div className="ml-auto flex items-center gap-2">
          {mode === 'flows' ? <Button size="sm" variant="ghost" onClick={() => useAppStore.getState().setTrafficFlows(flows)} title="Keep these flows with the topology (save to persist)"><Save /> Save flows</Button> : null}
          <Button size="sm" variant="primary" loading={busy} disabled={!canRun} onClick={() => void run()} title={deployStatus !== 'deployed' ? 'Deploy the topology first' : undefined}><Play /> Start run</Button>
        </div>
      </div>
    </div>
  );
}

interface FlowsEditorProps {
  flows: SavedFlow[];
  errors: Record<string, string>;
  options: ComboboxOption[];
  update: (id: string, patch: Partial<SavedFlow>) => void;
  setFlows: React.Dispatch<React.SetStateAction<SavedFlow[]>>;
  firstTwo: string[];
}

function FlowsEditor({ flows, errors, options, update, setFlows, firstTwo }: FlowsEditorProps) {
  const grid = 'grid grid-cols-[2.5rem_minmax(9rem,1fr)_minmax(9rem,1fr)_5.5rem_9.5rem_6rem_4.5rem_2rem] items-center gap-2';
  return (
    <div className="flex flex-col gap-1.5">
      <div className={`${grid} text-2xs font-medium text-fg-muted`}>
        <span>ID</span><span>Client (sends)</span><span>Server</span><span>Protocol</span><span>Direction</span><span>Bitrate</span><span>Streams</span><span />
      </div>
      {flows.map((f) => (
        <div key={f.id} className="flex flex-col gap-0.5">
          <div className={grid}>
            <span className="font-mono text-fg-muted">{f.id}</span>
            <Select size="sm" value={f.client || undefined} onValueChange={(v) => update(f.id, { client: v })} options={options} placeholder="Client…" aria-label={`${f.id} client`} />
            <Select size="sm" value={f.server || undefined} onValueChange={(v) => update(f.id, { server: v })} options={options} placeholder="Server…" aria-label={`${f.id} server`} />
            <Select size="sm" value={f.protocol} onValueChange={(v) => update(f.id, { protocol: v })} options={PROTOCOLS} aria-label={`${f.id} protocol`} />
            <Select size="sm" value={f.direction} onValueChange={(v) => update(f.id, { direction: v })} options={DIRECTIONS} aria-label={`${f.id} direction`} />
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
  );
}

interface PatternEditorProps {
  pattern: PatternDraft;
  setP: (patch: Partial<PatternDraft>) => void;
  options: ComboboxOption[];
  flows: number;
  problem: string | null;
}

function PatternEditor({ pattern: p, setP, options, flows, problem }: PatternEditorProps) {
  return (
    <div className="grid max-w-4xl grid-cols-[9rem_1fr] items-center gap-x-3 gap-y-2.5">
      {p.kind === 'clients_to_servers' ? (
        <>
          <span className="text-fg-muted">Servers</span>
          <MultiSelect size="sm" className="w-72" value={p.servers} onValueChange={(servers) => setP({ servers })} options={options} placeholder="Pick servers…" aria-label="Servers" />
          <span className="text-fg-muted">Clients</span>
          <div className="flex items-center gap-2">
            <Select size="sm" className="w-36" value={p.clientSet} onValueChange={(clientSet) => setP({ clientSet })} options={NODE_SETS} aria-label="Which clients" />
            {p.clientSet === 'pick' ? <MultiSelect size="sm" className="w-72" value={p.clients} onValueChange={(clients) => setP({ clients })} options={options} placeholder="Pick clients…" aria-label="Clients" /> : <span className="text-fg-subtle">servers are left out</span>}
          </div>
          <span className="text-fg-muted">Each client sends to</span>
          <Select size="sm" className="w-56" value={p.each} onValueChange={(each) => setP({ each })} options={[{ value: 'one', label: 'One server (round-robin)' }, { value: 'all', label: 'Every server' }]} aria-label="Servers per client" />
        </>
      ) : (
        <>
          <span className="text-fg-muted">Nodes</span>
          <div className="flex items-center gap-2">
            <Select size="sm" className="w-36" value={p.nodeSet} onValueChange={(nodeSet) => setP({ nodeSet })} options={NODE_SETS} aria-label="Which nodes" />
            {p.nodeSet === 'pick' ? <MultiSelect size="sm" className="w-72" value={p.nodes} onValueChange={(nodes) => setP({ nodes })} options={options} placeholder="Pick nodes…" aria-label="Mesh nodes" /> : null}
          </div>
          <span className="text-fg-muted">Peers per node</span>
          <Input className="h-7 w-20 text-xs" type="number" min={1} value={p.fanout} onChange={(e) => setP({ fanout: Math.max(1, Math.floor(Number(e.target.value) || 1)) })} aria-label="Peers per node" />
        </>
      )}
      <span className="text-fg-muted">Each flow</span>
      <div className="flex flex-wrap items-center gap-2">
        <Select size="sm" className="w-20" value={p.protocol} onValueChange={(protocol) => setP({ protocol })} options={PROTOCOLS} aria-label="Protocol" />
        <Select size="sm" className="w-40" value={p.direction} onValueChange={(direction) => setP({ direction })} options={DIRECTIONS} aria-label="Direction" />
        <Input className="h-7 w-20 text-xs" mono value={p.bitrate} onChange={(e) => setP({ bitrate: e.target.value.trim() })} placeholder="10M" aria-label="Bitrate per flow" />
        <span className="text-fg-subtle">per stream ·</span>
        <Input className="h-7 w-16 text-xs" type="number" min={1} max={16} value={p.parallel} onChange={(e) => setP({ parallel: Number(e.target.value) || 1 })} aria-label="Parallel streams" />
        <span className="text-fg-subtle">stream(s)</span>
      </div>
      <span />
      <span className={problem ? 'text-danger' : 'text-fg-subtle'}>
        {problem ?? `${flows} flow${flows === 1 ? '' : 's'} · ${flows * 2} iperf3 processes in one driver container`}
      </span>
    </div>
  );
}
