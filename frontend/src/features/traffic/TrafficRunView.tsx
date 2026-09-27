import { useMemo } from 'react';
import { Activity, Download, Gauge, Plus, Square } from 'lucide-react';
import { useAppStore } from '@/store';
import { locate } from '@/lib/topology';
import { Badge, Button } from '@/ui';
import { TimeSeriesChart } from '@/ui/charts/TimeSeriesChart';
import { formatBps, formatBytes } from '@/features/capture/packetBuffer';
import { openMonitorPanel } from '@/features/monitor/actions';
import { useTrafficStream } from './useTrafficStream';
import { latestRates, throughputSeries, totalsSeries } from './series';
import { exportTrafficRun, openTrafficPanel, stopTrafficRun } from './actions';
import { EnvironmentDetails } from './EnvironmentDetails';

const STOPPED_BY: Record<string, string> = {
  completed: 'Completed',
  user: 'Stopped',
  destroy: 'Stopped: the topology was destroyed',
  shutdown: 'Stopped: the server shut down',
  'limit:time': 'Stopped at the time limit',
};

/** Per-flow charts and the header's per-flow rates up to this many flows. */
const FEW_FLOWS = 16;

interface DirectionSummary {
  intervals: number;
  bps?: { mean: number; p50: number; min: number; max: number } | null;
  bytes: number;
  retransmits?: number;
  rtt_ms?: { mean: number } | null;
  jitter_ms?: { mean: number } | null;
  lost_percent?: number;
}
interface FlowResult {
  id: string;
  client: string;
  server: string;
  protocol: string;
  direction: string;
  summary: Record<string, DirectionSummary>;
  errors: string[];
}
interface RunTotals {
  flows: number;
  processes: number;
  delivered_bps: number;
  offered_bps: number | null;
  delivered_ratio: number | null;
  retransmits: number;
  lost_percent: number | null;
  flows_with_errors: number;
  flows_without_data: number;
}
interface RunResult {
  flows?: FlowResult[];
  flows_truncated?: boolean;
  totals?: RunTotals;
  stopped_by?: string;
  environment_fingerprint?: string;
  duration_s?: number;
}

const mbps = (bps?: number) => (bps === undefined ? '–' : (bps / 1e6).toFixed(1));

/** A traffic run in the dock: live throughput, then its summary. Node load is
 *  the Monitor's job (open one for the run's nodes from here). */
export function TrafficRunView({ jobId }: { jobId: string }) {
  const backendId = useAppStore((s) => s.backendId);
  const topology = useAppStore((s) => s.topology);
  const { run, flows, totals, rates, elapsed, ended } = useTrafficStream(backendId, jobId);
  const live = !!run?.live && !ended;
  const failed = run?.status === 'failed';
  const count = run?.flow_count ?? 0;
  const few = count <= FEW_FLOWS;
  const flowIds = useMemo(() => (run?.flows ?? []).map((f) => String(f.id)), [run]);
  const endpoints = useMemo(() => [...new Set((run?.flows ?? []).flatMap((f) => [String(f.client), String(f.server)]))], [run]);

  const nameOf = (id: string) => {
    const hit = locate(topology, id);
    return hit?.kind === 'container' ? hit.container.name : id;
  };

  const total = useMemo(() => totalsSeries(totals), [totals]);
  const throughput = useMemo(() => (few ? throughputSeries(flows, flowIds) : null), [few, flows, flowIds]);
  const perFlow = few ? latestRates(flows) : rates;
  const busiest = useMemo(
    () => Object.entries(rates).map(([id, r]) => [id, (r.fwd ?? 0) + (r.rev ?? 0)] as const).sort((a, b) => b[1] - a[1]).slice(0, 10),
    [rates],
  );
  const latest = totals[totals.length - 1];

  const result = run?.result as RunResult | null | undefined;
  const t = result?.totals;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex h-9 shrink-0 items-center gap-3 border-b border-border bg-surface px-3 text-xs">
        <Activity className="size-3.5 text-fg-muted" aria-hidden />
        <span className="font-medium text-fg">{run?.label || 'Traffic run'}</span>
        {live ? <Badge tone="success" dot="pulse">Running</Badge> : failed ? <Badge tone="danger">Failed</Badge> : run ? <Badge>{STOPPED_BY[result?.stopped_by ?? ''] ?? 'Done'}</Badge> : null}
        {live && elapsed !== null ? <span className="tabular-nums text-fg-muted">{elapsed.toFixed(0)}s{run?.duration_s ? ` / ${run.duration_s}s` : ''}</span> : null}
        {run ? <span className="text-fg-muted tabular-nums">{count} flow{count === 1 ? '' : 's'}</span> : null}
        {live && latest ? (
          <span className="tabular-nums text-fg-muted">
            {formatBps(latest.delivered_bps)}{latest.offered_bps ? ` of ${formatBps(latest.offered_bps)}` : ''} · {latest.active} running
          </span>
        ) : null}
        {few ? (
          <div className="flex min-w-0 items-center gap-2 overflow-hidden">
            {flowIds.map((id) => (
              <span key={id} className="shrink-0 tabular-nums text-fg-muted">
                <span className="font-mono text-fg-subtle">{id}</span> {formatBps(perFlow[id]?.fwd ?? perFlow[id]?.rev)}
              </span>
            ))}
          </div>
        ) : null}
        <div className="ml-auto flex items-center gap-1.5">
          {run && endpoints.length ? <Button size="sm" variant="ghost" onClick={() => openMonitorPanel({ nodes: endpoints })} title="Record CPU, memory and network of the run's nodes"><Gauge /> Monitor…</Button> : null}
          {!live && run ? <Button size="sm" variant="ghost" onClick={() => exportTrafficRun(jobId)}><Download /> Export</Button> : null}
          {!live && run ? <Button size="sm" variant="ghost" onClick={() => openTrafficPanel()}><Plus /> New run</Button> : null}
          {live ? <Button size="sm" variant="danger-soft" onClick={() => void stopTrafficRun(jobId)}><Square /> Stop</Button> : null}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-3">
        {failed ? <div className="mb-3 rounded-md bg-danger-soft px-3 py-2 text-xs text-danger">{run?.job.error}</div> : null}
        <div className="grid grid-cols-[repeat(auto-fit,minmax(20rem,1fr))] gap-x-5 gap-y-4">
          <TimeSeriesChart title="All flows" unit="Mb/s" data={total} note="received, and asked when every flow has a rate" />
          {throughput ? <TimeSeriesChart title="Throughput per flow (received)" unit="Mb/s" data={throughput} /> : null}
          {!few && busiest.length ? (
            <section>
              <h3 className="mb-1 text-xs font-medium text-fg">Busiest flows now</h3>
              <ol className="space-y-0.5 text-2xs tabular-nums">
                {busiest.map(([id, bps]) => (
                  <li key={id} className="flex justify-between gap-2 text-fg"><span className="truncate font-mono">{id}</span><span className="text-fg-muted">{formatBps(bps)}</span></li>
                ))}
              </ol>
            </section>
          ) : null}
        </div>

        {t ? (
          <p className="mt-4 text-2xs text-fg-muted tabular-nums">
            {t.flows} flow{t.flows === 1 ? '' : 's'} ({t.processes} processes) · received {formatBps(t.delivered_bps)} on average
            {t.offered_bps ? ` of ${formatBps(t.offered_bps)} asked (${((t.delivered_ratio ?? 0) * 100).toFixed(1)}%)` : ''}
            {t.retransmits ? ` · ${t.retransmits.toLocaleString()} retransmits` : ''}
            {t.lost_percent !== null ? ` · ${t.lost_percent.toFixed(3)}% UDP loss` : ''}
            {t.flows_with_errors ? ` · ${t.flows_with_errors} flow(s) with errors` : ''}
            {t.flows_without_data ? ` · ${t.flows_without_data} without data` : ''}
          </p>
        ) : null}

        {result?.flows?.length ? (
          <section className="mt-4">
            <h3 className="mb-1.5 text-xs font-medium text-fg">
              Summary{result.duration_s ? <span className="font-normal text-fg-subtle"> · {result.duration_s.toFixed(0)}s</span> : null}
              {result.flows_truncated ? <span className="font-normal text-fg-subtle"> · the slowest, fastest and failing {result.flows.length} of {count} flows; every flow is in the export</span> : null}
            </h3>
            <table className="w-full text-left text-2xs tabular-nums">
              <thead className="text-fg-muted">
                <tr className="border-b border-border">
                  <th className="py-1 font-medium">Flow</th><th className="font-medium">Direction</th>
                  <th className="text-right font-medium">Mean Mb/s</th><th className="text-right font-medium">p50</th><th className="text-right font-medium">Min</th><th className="text-right font-medium">Max</th>
                  <th className="text-right font-medium">Data</th><th className="text-right font-medium">Retrans.</th><th className="text-right font-medium">RTT ms</th><th className="text-right font-medium">Jitter ms</th><th className="text-right font-medium">Loss %</th>
                </tr>
              </thead>
              <tbody>
                {result.flows.flatMap((f) =>
                  Object.entries(f.summary).map(([dir, s]) => (
                    <tr key={`${f.id}:${dir}`} className="border-b border-border/60 text-fg">
                      <td className="py-1"><span className="font-mono">{f.id}</span> <span className="text-fg-muted">{nameOf(f.client)} → {nameOf(f.server)} · {f.protocol.toUpperCase()}</span></td>
                      <td className="text-fg-muted">{dir === 'fwd' ? 'client → server' : 'server → client'}</td>
                      <td className="text-right">{mbps(s.bps?.mean)}</td><td className="text-right">{mbps(s.bps?.p50)}</td><td className="text-right">{mbps(s.bps?.min)}</td><td className="text-right">{mbps(s.bps?.max)}</td>
                      <td className="text-right">{formatBytes(s.bytes)}</td>
                      <td className="text-right">{s.retransmits ?? '–'}</td>
                      <td className="text-right">{s.rtt_ms ? s.rtt_ms.mean.toFixed(2) : '–'}</td>
                      <td className="text-right">{s.jitter_ms ? s.jitter_ms.mean.toFixed(3) : '–'}</td>
                      <td className="text-right">{s.lost_percent !== undefined ? s.lost_percent.toFixed(3) : '–'}</td>
                    </tr>
                  )),
                )}
              </tbody>
            </table>
            {result.flows.some((f) => f.errors.length) ? (
              <ul className="mt-2 text-2xs text-danger">
                {result.flows.flatMap((f) => f.errors.map((e) => <li key={f.id + e}>{f.id}: {e}</li>))}
              </ul>
            ) : null}
          </section>
        ) : null}

        {run ? <EnvironmentDetails jobId={jobId} fingerprint={result?.environment_fingerprint} /> : null}
      </div>
    </div>
  );
}
