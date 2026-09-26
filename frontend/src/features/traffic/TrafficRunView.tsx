import { useMemo } from 'react';
import { Activity, Download, Plus, Square } from 'lucide-react';
import { useAppStore } from '@/store';
import { locate } from '@/lib/topology';
import { Badge, Button } from '@/ui';
import { TimeSeriesChart } from '@/ui/charts/TimeSeriesChart';
import { formatBps, formatBytes } from '@/features/capture/packetBuffer';
import { useTrafficStream } from './useTrafficStream';
import { latestRates, metricOf, nodeSeries, throughputSeries } from './series';
import { exportTrafficRun, openTrafficPanel, stopTrafficRun } from './actions';
import { EnvironmentDetails } from './EnvironmentDetails';

const STOPPED_BY: Record<string, string> = {
  completed: 'Completed',
  user: 'Stopped',
  destroy: 'Stopped: the topology was destroyed',
  shutdown: 'Stopped: the server shut down',
  'limit:time': 'Stopped at the time limit',
};

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

const mbps = (bps?: number) => (bps === undefined ? '–' : (bps / 1e6).toFixed(1));

/** A traffic run in the dock: live throughput and node load, then its summary. */
export function TrafficRunView({ jobId }: { jobId: string }) {
  const backendId = useAppStore((s) => s.backendId);
  const topology = useAppStore((s) => s.topology);
  const { run, flows, nodes, sidecars, elapsed, ended } = useTrafficStream(backendId, jobId);
  const live = !!run?.live && !ended;
  const failed = run?.status === 'failed';
  const flowIds = useMemo(() => (run?.flows ?? []).map((f) => String(f.id)), [run]);

  const nameOf = (id: string) => {
    const hit = locate(topology, id);
    return hit?.kind === 'container' ? hit.container.name : id;
  };
  const labelOf = (target: string) => {
    const sc = sidecars[target];
    return sc ? `${sc.role === 'client' ? 'iperf client' : 'iperf server'} ${sc.flow_id} (${nameOf(sc.node_id)})` : nameOf(target);
  };
  const order = useMemo(() => [...(run?.monitored ?? []), ...Object.keys(sidecars)], [run, sidecars]);

  const throughput = useMemo(() => throughputSeries(flows, flowIds), [flows, flowIds]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const cpu = useMemo(() => nodeSeries(nodes, 'cpu', labelOf, order), [nodes, order, topology]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const mem = useMemo(() => nodeSeries(nodes, 'mem', labelOf, order), [nodes, order, topology]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const rx = useMemo(() => nodeSeries(nodes, 'rx', labelOf, order), [nodes, order, topology]);
  const rates = latestRates(flows);

  const peaks = useMemo(() => {
    const out = new Map<string, { cpu: number; mem: number; rx: number; tx: number }>();
    for (const s of nodes) {
      const p = out.get(s.target) ?? { cpu: 0, mem: 0, rx: 0, tx: 0 };
      p.cpu = Math.max(p.cpu, metricOf(s, 'cpu') ?? 0);
      p.mem = Math.max(p.mem, metricOf(s, 'mem') ?? 0);
      p.rx = Math.max(p.rx, metricOf(s, 'rx') ?? 0);
      p.tx = Math.max(p.tx, metricOf(s, 'tx') ?? 0);
      out.set(s.target, p);
    }
    return [...out.entries()].sort((a, b) => b[1].cpu - a[1].cpu);
  }, [nodes]);

  const result = run?.result as { flows?: FlowResult[]; stopped_by?: string; environment_fingerprint?: string; duration_s?: number } | null | undefined;
  const note = (hidden: number) => (hidden ? `busiest 6 of ${hidden + 6}` : undefined);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex h-9 shrink-0 items-center gap-3 border-b border-border bg-surface px-3 text-xs">
        <Activity className="size-3.5 text-fg-muted" aria-hidden />
        <span className="font-medium text-fg">{run?.label || 'Traffic run'}</span>
        {live ? <Badge tone="success" dot="pulse">Running</Badge> : failed ? <Badge tone="danger">Failed</Badge> : run ? <Badge>{STOPPED_BY[result?.stopped_by ?? ''] ?? 'Done'}</Badge> : null}
        {live && elapsed !== null ? <span className="tabular-nums text-fg-muted">{elapsed.toFixed(0)}s{run?.duration_s ? ` / ${run.duration_s}s` : ''}</span> : null}
        <div className="flex min-w-0 items-center gap-2 overflow-hidden">
          {flowIds.map((id) => (
            <span key={id} className="shrink-0 tabular-nums text-fg-muted">
              <span className="font-mono text-fg-subtle">{id}</span> {formatBps(rates[id]?.fwd ?? rates[id]?.rev)}
            </span>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          {!live && run ? <Button size="sm" variant="ghost" onClick={() => exportTrafficRun(jobId)}><Download /> Export</Button> : null}
          {!live && run ? <Button size="sm" variant="ghost" onClick={() => openTrafficPanel()}><Plus /> New run</Button> : null}
          {live ? <Button size="sm" variant="danger-soft" onClick={() => void stopTrafficRun(jobId)}><Square /> Stop</Button> : null}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-3">
        {failed ? <div className="mb-3 rounded-md bg-danger-soft px-3 py-2 text-xs text-danger">{run?.job.error}</div> : null}
        <div className="grid grid-cols-[repeat(auto-fit,minmax(20rem,1fr))] gap-x-5 gap-y-4">
          <TimeSeriesChart title="Throughput (received)" unit="Mb/s" data={throughput} />
          <TimeSeriesChart title="CPU" unit="%" data={cpu} note={note(cpu.hidden)} />
          <TimeSeriesChart title="Memory" unit="MB" data={mem} note={note(mem.hidden)} />
          <TimeSeriesChart title="Interface receive" unit="Mb/s" data={rx} note={note(rx.hidden)} />
        </div>

        {result?.flows?.length ? (
          <section className="mt-5">
            <h3 className="mb-1.5 text-xs font-medium text-fg">Summary{result.duration_s ? <span className="font-normal text-fg-subtle"> · {result.duration_s.toFixed(0)}s</span> : null}</h3>
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

        {peaks.length ? (
          <section className="mt-5">
            <h3 className="mb-1.5 text-xs font-medium text-fg">Peak load</h3>
            <table className="w-full text-left text-2xs tabular-nums">
              <thead className="text-fg-muted">
                <tr className="border-b border-border">
                  <th className="py-1 font-medium">Node / sidecar</th><th className="text-right font-medium">CPU %</th><th className="text-right font-medium">Memory MB</th><th className="text-right font-medium">Receive Mb/s</th><th className="text-right font-medium">Send Mb/s</th>
                </tr>
              </thead>
              <tbody>
                {peaks.map(([target, p]) => (
                  <tr key={target} className="border-b border-border/60 text-fg">
                    <td className="py-1">{labelOf(target)}</td>
                    <td className="text-right">{p.cpu.toFixed(1)}</td><td className="text-right">{p.mem.toFixed(1)}</td><td className="text-right">{p.rx.toFixed(1)}</td><td className="text-right">{p.tx.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-1 text-2xs text-fg-subtle">
              CPU counts the container's own processes. Kernel packet forwarding on routers and firewalls is not charged to them, so compare throughput and drops for those.
            </p>
          </section>
        ) : null}

        {run ? <EnvironmentDetails jobId={jobId} fingerprint={result?.environment_fingerprint} /> : null}
      </div>
    </div>
  );
}
