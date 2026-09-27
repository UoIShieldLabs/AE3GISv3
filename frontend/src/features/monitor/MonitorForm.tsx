import { useMemo, useState } from 'react';
import { Gauge, Play } from 'lucide-react';
import { labelFor } from '@/catalog/catalog';
import { useAppShallow } from '@/store/selectors';
import { Button, Input, MultiSelect, Select, Switch } from '@/ui';
import { NODE_ROWS_LIMIT } from './useMonitorStream';
import { nodesOf, preview, toRequest, type Selection, type SelectionMode } from './selection';
import { startMonitor } from './actions';

const MODES: { value: SelectionMode; label: string }[] = [
  { value: 'all', label: 'All nodes' },
  { value: 'hosts', label: 'Hosts only' },
  { value: 'subnets', label: 'By subnet' },
  { value: 'types', label: 'By device type' },
  { value: 'nodes', label: 'Pick nodes' },
];

/** The form behind a new monitor: which nodes to record one by one, and how often. */
export function MonitorForm({ tabId, seed }: { tabId: string; seed?: { nodes?: string[]; nonce: number } }) {
  const { topology, containerStatus, deployStatus } = useAppShallow((s) => ({ topology: s.topology, containerStatus: s.containerStatus, deployStatus: s.deployStatus }));
  const nodes = useMemo(() => nodesOf(topology), [topology]);
  const [sel, setSel] = useState<Selection>(() => (seed?.nodes?.length ? { mode: 'nodes', picks: seed.nodes } : { mode: 'all', picks: [] }));
  const [everyText, setEveryText] = useState('1');
  const [untilStopped, setUntilStopped] = useState(true);
  const [duration, setDuration] = useState('300');
  const [label, setLabel] = useState('');
  const [busy, setBusy] = useState(false);

  // "Monitor this node…": pick the node, once per request (adjusting state while rendering).
  const [appliedSeed, setAppliedSeed] = useState<number | undefined>(seed?.nonce);
  if (seed?.nodes?.length && seed.nonce !== appliedSeed) {
    setAppliedSeed(seed.nonce);
    setSel({ mode: 'nodes', picks: seed.nodes });
  }

  const running = (id: string) => containerStatus[id] === 'running';
  const matched = preview(nodes, running, sel);
  const subnetOptions = topology.sites.flatMap((site) => site.subnets.map((sn) => ({ value: sn.id, label: sn.name, description: sn.cidr, group: site.name })));
  const typeOptions = [...new Set(nodes.map((n) => n.type))].sort().map((t) => ({ value: t, label: labelFor(t) }));
  const nodeOptions = nodes.map((n) => ({ value: n.id, label: n.name, description: n.ip, keywords: [n.type], disabled: !running(n.id) }));
  const everyS = Number(everyText);
  const intervalOk = Number.isFinite(everyS) && everyS >= 0.5 && everyS <= 60;
  const durationOk = untilStopped || Number(duration) >= 1;
  const canStart = deployStatus === 'deployed' && matched.length > 0 && intervalOk && durationOk;

  const start = async () => {
    setBusy(true);
    await startMonitor(tabId, {
      label: label.trim(),
      notes: '',
      nodes: toRequest(sel),
      interval_s: everyS,
      duration_s: untilStopped ? null : Math.round(Number(duration)),
    });
    setBusy(false);
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-auto p-3 text-xs">
      <div className="mb-3 flex items-center gap-2">
        <Gauge className="size-3.5 text-fg-muted" aria-hidden />
        <span className="font-medium text-fg">New monitor</span>
        <span className="text-fg-subtle">CPU, memory and network of each chosen node, plus the host and Docker itself, every interval.</span>
      </div>

      <div className="grid max-w-3xl grid-cols-[8rem_1fr] items-center gap-x-3 gap-y-2.5">
        <span className="text-fg-muted">Nodes</span>
        <div className="flex flex-wrap items-center gap-2">
          <Select size="sm" className="w-40" value={sel.mode} onValueChange={(mode) => setSel({ mode, picks: [] })} options={MODES} aria-label="Which nodes" />
          {sel.mode === 'subnets' ? <MultiSelect size="sm" className="w-64" value={sel.picks} onValueChange={(picks) => setSel({ ...sel, picks })} options={subnetOptions} placeholder="Subnets…" aria-label="Subnets" /> : null}
          {sel.mode === 'types' ? <MultiSelect size="sm" className="w-64" value={sel.picks} onValueChange={(picks) => setSel({ ...sel, picks })} options={typeOptions} placeholder="Device types…" aria-label="Device types" /> : null}
          {sel.mode === 'nodes' ? <MultiSelect size="sm" className="w-64" value={sel.picks} onValueChange={(picks) => setSel({ ...sel, picks })} options={nodeOptions} placeholder="Nodes…" aria-label="Nodes" /> : null}
          <span className="text-fg-subtle">
            {matched.length} running node{matched.length === 1 ? '' : 's'}
            {matched.length > NODE_ROWS_LIMIT ? ' · shown as totals and top nodes; every node is still recorded' : ''}
          </span>
        </div>

        <span className="text-fg-muted">Every</span>
        <div className="flex items-center gap-2">
          <Input className="h-7 w-20 text-xs" type="number" min={0.5} max={60} step={0.5} value={everyText} onChange={(e) => setEveryText(e.target.value)} aria-label="Interval in seconds" aria-invalid={!intervalOk} />
          <span className="text-fg-subtle">s · 2–5 s keeps the collector light at a few hundred nodes</span>
        </div>

        <span className="text-fg-muted">Duration</span>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-fg-muted">
            <Switch checked={untilStopped} onCheckedChange={setUntilStopped} aria-label="Run until stopped" /> Until stopped
          </label>
          <Input className="h-7 w-20 text-xs" type="number" min={1} value={duration} disabled={untilStopped} onChange={(e) => setDuration(e.target.value)} aria-label="Duration in seconds" />
          <span className="text-fg-subtle">s</span>
        </div>

        <span className="text-fg-muted">Label</span>
        <Input className="h-7 w-64 text-xs" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="e.g. idle baseline" aria-label="Monitor label" />
      </div>

      <div className="mt-4 flex max-w-3xl items-center border-t border-border pt-3">
        <span className="text-2xs text-fg-subtle">Runs alongside captures and traffic; data is kept on the server (CSV) and can be exported.</span>
        <Button className="ml-auto" size="sm" variant="primary" loading={busy} disabled={!canStart} onClick={() => void start()} title={deployStatus !== 'deployed' ? 'Deploy the topology first' : undefined}>
          <Play /> Start monitor
        </Button>
      </div>
    </div>
  );
}
