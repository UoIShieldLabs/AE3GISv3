import { useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, Gauge, Play } from 'lucide-react';
import { useAppShallow } from '@/store/selectors';
import { Button, Input, Switch } from '@/ui';
import { nodesOf } from './selection';
import { startMonitor } from './actions';

/** A new monitor: it records every device of the lab, so there is nothing to
 *  choose up front; which devices to look at is picked in the view (pins).
 *  ``seed`` devices start pinned. Interval, duration and label are folded away. */
export function MonitorForm({ tabId, seed }: { tabId: string; seed?: { nodes?: string[]; nonce: number } }) {
  const { topology, containerStatus, deployStatus } = useAppShallow((s) => ({ topology: s.topology, containerStatus: s.containerStatus, deployStatus: s.deployStatus }));
  const devices = useMemo(() => nodesOf(topology), [topology]);
  const [optionsOpen, setOptionsOpen] = useState(false);
  const [everyText, setEveryText] = useState('1');
  const [untilStopped, setUntilStopped] = useState(true);
  const [duration, setDuration] = useState('300');
  const [label, setLabel] = useState('');
  const [busy, setBusy] = useState(false);

  const running = devices.filter((d) => containerStatus[d.id] === 'running').length;
  const pins = (seed?.nodes ?? []).filter((id) => devices.some((d) => d.id === id));
  const nameOf = (id: string) => devices.find((d) => d.id === id)?.name ?? id;
  const everyS = Number(everyText);
  const intervalOk = Number.isFinite(everyS) && everyS >= 0.5 && everyS <= 60;
  const durationOk = untilStopped || Number(duration) >= 1;
  const canStart = deployStatus === 'deployed' && running > 0 && intervalOk && durationOk;

  const start = async () => {
    setBusy(true);
    await startMonitor(
      tabId,
      {
        label: label.trim(),
        notes: '',
        nodes: 'all',
        interval_s: everyS,
        duration_s: untilStopped ? null : Math.round(Number(duration)),
      },
      pins,
    );
    setBusy(false);
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-auto p-3 text-xs">
      <div className="flex max-w-3xl flex-col gap-3">
        <div className="flex items-center gap-2">
          <Gauge className="size-3.5 text-fg-muted" aria-hidden />
          <span className="font-medium text-fg">New monitor</span>
        </div>
        <p className="text-fg-muted">
          Records the CPU, memory and network of every device in the lab ({running} running), and of the machine running it.
          Pin devices or group them by subnet once it runs.
          {pins.length ? <span className="text-fg"> Starts with {pins.map(nameOf).join(', ')} pinned.</span> : null}
        </p>

        <div className="flex items-center gap-3">
          <Button size="sm" variant="primary" loading={busy} disabled={!canStart} onClick={() => void start()} title={deployStatus !== 'deployed' ? 'Deploy the topology first' : undefined}>
            <Play /> Start monitoring
          </Button>
          <button type="button" className="flex items-center gap-1 text-fg-muted hover:text-fg" aria-expanded={optionsOpen} onClick={() => setOptionsOpen((o) => !o)}>
            {optionsOpen ? <ChevronDown className="size-3.5" aria-hidden /> : <ChevronRight className="size-3.5" aria-hidden />}
            Options
            {!optionsOpen ? <span className="text-fg-subtle">· every {intervalOk ? everyS : '?'}s, {untilStopped ? 'until stopped' : `${duration}s`}</span> : null}
          </button>
        </div>

        {optionsOpen ? (
          <div className="grid grid-cols-[8rem_1fr] items-center gap-x-3 gap-y-2.5 border-t border-border pt-3">
            <span className="text-fg-muted">Every</span>
            <div className="flex items-center gap-2">
              <Input className="h-7 w-20 text-xs" type="number" min={0.5} max={60} step={0.5} value={everyText} onChange={(e) => setEveryText(e.target.value)} aria-label="Interval in seconds" aria-invalid={!intervalOk} />
              <span className="text-fg-subtle">s · 2–5 s keeps the collector light at a few hundred devices</span>
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
        ) : null}

        <p className="text-2xs text-fg-subtle">Runs alongside captures and traffic; the data stays on the server (CSV) and can be exported.</p>
      </div>
    </div>
  );
}
