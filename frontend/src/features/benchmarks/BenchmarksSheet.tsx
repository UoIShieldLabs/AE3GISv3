import { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Download, FileText, Gauge, RefreshCw, Square, X } from 'lucide-react';
import * as api from '@/api/client';
import { Badge, Button, EmptyState, IconButton, Sheet, toast } from '@/ui';
import { TimeSeriesChart } from '@/ui/charts/TimeSeriesChart';
import { benchKind, memoryChart, outcomeTone, stepsLine, summaryLine, timingChart, type BenchResult, type BenchRow, type BenchSpec } from './model';

const POLL_MS = 3000;
const CLI = './bench.sh baseline --host my-machine';

const when = (iso?: string | null) => (iso ? new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }) : '–');
const mb = (x?: number | null) => (x === null || x === undefined ? '–' : (x / 1e6).toFixed(1));
const num = (x?: number | null, d = 1) => (x === null || x === undefined ? '–' : x.toFixed(d));

function StatusBadge({ b }: { b: api.Benchmark }) {
  if (b.live) return <Badge tone="success" dot="pulse">Running</Badge>;
  if (b.status === 'failed') return <Badge tone="danger">Failed</Badge>;
  if (b.status === 'cancelled') return <Badge tone="warning">Cancelled</Badge>;
  return <Badge>Done</Badge>;
}

function download(url: string, name: string) {
  api.downloadUrl(url, name).catch((err: unknown) => toast.error('Download failed', { description: api.errorMessage(err) }));
}

async function act(fn: () => Promise<unknown>, what: string) {
  try {
    await fn();
  } catch (err) {
    toast.error(`Could not ${what}`, { description: api.errorMessage(err) });
  }
}

/** Benchmarks on this host (sweeps, climbs, image censuses, traffic
 *  matrices): started from the CLI (a suite per host) or the API, followed
 *  and read here. */
export function BenchmarksSheet({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const [items, setItems] = useState<api.Benchmark[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    api.listBenchmarks()
      .then((b) => { setItems(b); setError(null); })
      .catch((err: unknown) => setError(api.errorMessage(err)));
  }, []);

  const anyLive = !!items?.some((b) => b.live);
  useEffect(() => {
    if (!open) return;
    refresh();
    if (!anyLive && !selected) return;
    const t = setInterval(refresh, POLL_MS);
    return () => clearInterval(t);
  }, [open, refresh, anyLive, selected]);

  const current = items?.find((b) => b.id === selected) ?? null;

  return (
    <Sheet
      open={open}
      onOpenChange={onOpenChange}
      side="right"
      size="min(1040px, 100vw)"
      title="Benchmarks"
      description="Deploy, measure and load generated topologies until the host stops coping: sweeps, climbs, image censuses and traffic matrices."
      headerAction={<IconButton label="Refresh" size="icon-sm" onClick={refresh}><RefreshCw /></IconButton>}
    >
      {error ? <div className="mb-3 rounded-md bg-danger-soft px-3 py-2 text-xs text-danger">{error}</div> : null}
      {current ? (
        <BenchmarkDetail b={current} onBack={() => setSelected(null)} />
      ) : items?.length ? (
        <ul className="divide-y divide-border rounded-md border border-border text-xs">
          {items.map((b) => {
            const result = b.result as BenchResult | null;
            return (
              <li key={b.id} className="flex items-center gap-3 px-3 py-2">
                <Gauge className="size-3.5 shrink-0 text-fg-muted" aria-hidden />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate font-medium text-fg">{b.label || 'Benchmark'}</span>
                    <StatusBadge b={b} />
                  </div>
                  <div className="truncate text-2xs text-fg-muted">
                    {when(b.job.started_at ?? b.job.created_at)} · {summaryLine(result, { ...(b.spec as BenchSpec), kind: b.kind as BenchSpec['kind'] })}
                    {b.live && b.current ? ` · ${b.current}` : ''}
                    {b.status === 'failed' && b.job.error ? ` · ${b.job.error}` : ''}
                  </div>
                </div>
                <Button size="xs" variant="secondary" onClick={() => setSelected(b.id)}>Open</Button>
              </li>
            );
          })}
        </ul>
      ) : (
        <EmptyState
          title={items ? 'No benchmarks yet' : 'Loading…'}
          description={items ? <>Start one headless from the backend folder: <code className="font-mono">{CLI}</code> from the repository root (see docs/benchmarks).</> : undefined}
        />
      )}
    </Sheet>
  );
}

function BenchmarkDetail({ b, onBack }: { b: api.Benchmark; onBack: () => void }) {
  const result = (b.result ?? {}) as BenchResult;
  const rows: BenchRow[] = result.rows ?? [];
  const entries = useMemo(() => result.by_scale ?? [], [result.by_scale]);
  const timing = useMemo(() => timingChart(entries), [entries]);
  const memory = useMemo(() => memoryChart(entries), [entries]);
  const spec = b.spec as BenchSpec & { hold_s?: number; settle_s?: number; cooldown_s?: number };
  const kind = benchKind(spec);
  const traffic = !!spec.traffic || kind === 'matrix';
  const cases = rows.some((r) => r.case);

  return (
    <div className="flex flex-col gap-4 text-xs">
      <div className="flex items-center gap-2">
        <IconButton label="Back" size="icon-sm" onClick={onBack}><ArrowLeft /></IconButton>
        <span className="font-medium text-fg">{b.label || 'Benchmark'}</span>
        <StatusBadge b={b} />
        <div className="ml-auto flex items-center gap-1.5">
          <Button size="sm" variant="ghost" onClick={() => download(api.benchmarkReportUrl(b.id), `benchmark-${b.id.slice(0, 8)}.md`)}><FileText /> Report</Button>
          <Button size="sm" variant="ghost" onClick={() => download(api.benchmarkExportUrl(b.id), `benchmark-${b.id.slice(0, 8)}.zip`)}><Download /> Export</Button>
          {b.live ? <Button size="sm" variant="ghost" onClick={() => void act(() => api.stopJob(b.id), 'stop the benchmark')} title="Finish the current step, then stop"><Square /> Stop</Button> : null}
          {b.live ? <Button size="sm" variant="danger-soft" onClick={() => void act(() => api.cancelJob(b.id), 'cancel the benchmark')} title="Stop now (what it deployed is removed)"><X /> Cancel</Button> : null}
        </div>
      </div>
      <p className="text-2xs text-fg-muted">
        {stepsLine(spec)} · reference {spec.cooldown_s}s, settle {spec.settle_s}s, hold {spec.hold_s}s {traffic ? 'under traffic' : 'idle'}
        {b.live && b.current ? <> · <span className="text-fg">{b.current}</span></> : null}
        {result.ceiling ? <> · ceiling <span className="text-fg">{result.ceiling} hosts</span></> : null}
        {result.limit ? <> · climb: {result.limit}</> : null}
        {result.census ? <> · <span className="text-fg">{result.census.filter((c) => c.usable).length} of {result.census.length} cases usable</span></> : null}
        {result.reason ? <> · stopped: {result.detail ?? result.reason}</> : null}
      </p>
      {b.status === 'failed' && b.job.error ? <div className="rounded-md bg-danger-soft px-3 py-2 text-danger">{b.job.error}</div> : null}

      {entries.length && (kind === 'sweep' || kind === 'adaptive') ? (
        <div className="grid grid-cols-[repeat(auto-fit,minmax(22rem,1fr))] gap-x-5 gap-y-4">
          <TimeSeriesChart title="Deploy, ready and destroy time" unit="s" data={timing} xUnit=" hosts" />
          <TimeSeriesChart title="Memory per node" unit="MB" data={memory} xUnit=" hosts" note="host lost vs. Docker vs. the container itself" />
        </div>
      ) : null}

      {rows.length ? (
        <table className="w-full text-left text-2xs tabular-nums">
          <thead className="text-fg-muted">
            <tr className="border-b border-border">
              {cases ? <th className="py-1 font-medium">{kind === 'matrix' ? 'Cell' : 'Case'}</th> : null}
              <th className="py-1 font-medium">Hosts</th><th className="text-right font-medium">Nodes</th><th className="text-right font-medium">Links</th>
              <th className="text-right font-medium">Deploy s</th><th className="text-right font-medium">Ready s</th><th className="text-right font-medium">Destroy s</th>
              <th className="text-right font-medium">MB/node</th><th className="text-right font-medium">Docker MB/node</th><th className="text-right font-medium">Cgroup MB</th>
              <th className="text-right font-medium">Host CPU %</th><th className="text-right font-medium" title="dockerd, containerd, shims and VDE switches">Docker cores</th><th className="text-right font-medium">Mem % max</th>
              {traffic ? <th className="text-right font-medium">Delivered</th> : null}
              <th className="pl-3 font-medium">Outcome</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.step} className="border-b border-border/60 text-fg">
                {cases ? <td className="py-1 font-mono">{r.case ?? r.step}</td> : null}
                <td className="py-1">{r.scale}{r.rep > 1 || (spec.repetitions ?? 1) > 1 ? <span className="text-fg-subtle"> #{r.rep}</span> : null}</td>
                <td className="text-right">{r.nodes ?? '–'}</td><td className="text-right">{r.links ?? '–'}</td>
                <td className="text-right">{num(r.deploy_s)}</td><td className="text-right">{num(r.ready_s, 2)}</td><td className="text-right">{num(r.destroy_s)}</td>
                <td className="text-right">{mb(r.marginal_mem_per_node)}</td><td className="text-right">{mb(r.docker_mem_per_node)}</td><td className="text-right">{mb(r.node_mem_mean)}</td>
                <td className="text-right">{num(r.hold_cpu_mean)}</td>
                <td className="text-right">{r.hold_docker_cpu_mean === null || r.hold_docker_cpu_mean === undefined ? '–' : (r.hold_docker_cpu_mean / 100).toFixed(2)}</td>
                <td className="text-right">{num(r.hold_mem_pct_max)}</td>
                {traffic ? <td className="text-right">{r.delivered_ratio === null || r.delivered_ratio === undefined ? '–' : `${(r.delivered_ratio * 100).toFixed(1)}%`}</td> : null}
                <td className="pl-3"><Badge tone={outcomeTone(r.outcome)}>{r.outcome}</Badge>{r.detail ? <span className="ml-1.5 text-fg-muted">{r.detail}</span> : null}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="text-fg-subtle">{b.live ? 'The first step is running…' : 'No steps recorded.'}</p>
      )}
      <p className="text-2xs text-fg-subtle">
        MB/node: host memory used after deploy minus before, per node (everything a node costs). Docker: the daemons, a shim per container and a VDE switch per link. Cgroup: the container's own figure, what <code className="font-mono">docker stats</code> shows.
      </p>
    </div>
  );
}
