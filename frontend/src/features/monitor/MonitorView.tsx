import { useMemo } from 'react';
import { AlertTriangle, Download, Gauge, Plus, Square } from 'lucide-react';
import { useAppStore } from '@/store';
import { locate } from '@/lib/topology';
import { Badge, Button } from '@/ui';
import { TimeSeriesChart } from '@/ui/charts/TimeSeriesChart';
import { formatBps, formatBytes } from '@/features/capture/packetBuffer';
import { EnvironmentDetails } from '@/features/traffic/EnvironmentDetails';
import { useMonitorStream } from './useMonitorStream';
import {
  cpuByGroupChart,
  dockerRss,
  hostCpuChart,
  latestByNode,
  memoryChart,
  perNodeChart,
  pressureChart,
  selectionCpuChart,
  selectionNetChart,
  type HostRow,
} from './model';
import { exportMonitor, openMonitorPanel, stopMonitor } from './actions';

const STOPPED_BY: Record<string, string> = {
  completed: 'Completed',
  user: 'Stopped',
  destroy: 'Stopped: the topology was destroyed',
  shutdown: 'Stopped: the server shut down',
  'limit:time': 'Stopped at the time limit',
};

interface Summary { mean: number | null; p95: number | null; max: number | null }
interface MonitorResult {
  stopped_by?: string;
  duration_s?: number;
  sweeps?: number;
  environment_fingerprint?: string;
  host?: Record<string, Summary>;
}

const num = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) ? v : null);
const pct = (v: unknown) => (num(v) === null ? '–' : `${num(v)!.toFixed(num(v)! < 10 ? 1 : 0)}%`);

function HostLine({ row }: { row: HostRow | undefined }) {
  if (!row) return null;
  const parts: string[] = [];
  parts.push(`Host CPU ${pct(row.vm_cpu_pct)}`);
  if (num(row.mem_used) !== null) parts.push(`memory ${formatBytes(num(row.mem_used))} of ${formatBytes(num(row.mem_total))} (${pct(row.mem_used_pct)})`);
  const shims = num(row.containerd_shim_count);
  const vde = num(row.vde_switch_count);
  const docker = dockerRss(row);
  if (docker !== null) {
    parts.push(
      `Docker ${formatBytes(docker)}` +
        (shims !== null ? ` (${shims} shim${shims === 1 ? '' : 's'}` : '') +
        (vde !== null ? `, ${vde} VDE switch${vde === 1 ? '' : 'es'}` : '') +
        (shims !== null ? ')' : ''),
    );
  }
  if (num(row.sweep_ms) !== null) parts.push(`sweep ${num(row.sweep_ms)!.toFixed(0)} ms`);
  return <div className="truncate text-2xs text-fg-muted tabular-nums">{parts.join(' · ')}</div>;
}

/** A monitor in the dock: the host, Docker and the chosen nodes over time. */
export function MonitorView({ jobId }: { jobId: string }) {
  const backendId = useAppStore((s) => s.backendId);
  const topology = useAppStore((s) => s.topology);
  const { monitor, host, agg, nodes, markers, latest, oom, missing, ended } = useMonitorStream(backendId, jobId);
  const live = !!monitor?.live && !ended;
  const failed = monitor?.status === 'failed';
  const result = monitor?.result as MonitorResult | null | undefined;

  const nameOf = (id: string) => {
    const hit = locate(topology, id);
    return hit?.kind === 'container' ? hit.container.name : id;
  };
  const order = useMemo(() => monitor?.monitored ?? [], [monitor]);
  const perNode = nodes.length > 0;

  const charts = useMemo(
    () => ({
      cpu: hostCpuChart(host),
      groups: cpuByGroupChart(host),
      mem: memoryChart(host),
      psi: pressureChart(host),
      selCpu: selectionCpuChart(agg),
      selNet: selectionNetChart(agg),
    }),
    [host, agg],
  );
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const nodeCharts = useMemo(() => (perNode ? { cpu: perNodeChart(nodes, 'cpu_pct', nameOf, order), mem: perNodeChart(nodes, 'mem_used', nameOf, order), rx: perNodeChart(nodes, 'rx_bps', nameOf, order) } : null), [nodes, order, topology]);
  const table = useMemo(() => latestByNode(nodes.filter((r) => r.kind === 'node')), [nodes]);
  const tools = latest?.tools ?? [];
  const note = (hidden: number) => (hidden ? `busiest 6 of ${hidden + 6}` : undefined);
  const count = monitor?.monitored.length ?? 0;
  const lastT = host.length ? host[host.length - 1].t : null;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex h-9 shrink-0 items-center gap-3 border-b border-border bg-surface px-3 text-xs">
        <Gauge className="size-3.5 text-fg-muted" aria-hidden />
        <span className="font-medium text-fg">{monitor?.label || 'Monitor'}</span>
        {live ? <Badge tone="success" dot="pulse">Recording</Badge> : failed ? <Badge tone="danger">Failed</Badge> : monitor ? <Badge>{STOPPED_BY[result?.stopped_by ?? ''] ?? 'Done'}</Badge> : null}
        {monitor ? <span className="text-fg-muted tabular-nums">{count} node{count === 1 ? '' : 's'} · every {monitor.interval_s}s{lastT !== null ? ` · ${lastT.toFixed(0)}s` : ''}</span> : null}
        <div className="ml-auto flex items-center gap-1.5">
          {monitor ? <Button size="sm" variant="ghost" onClick={() => exportMonitor(jobId)}><Download /> Export</Button> : null}
          {!live && monitor ? <Button size="sm" variant="ghost" onClick={() => openMonitorPanel()}><Plus /> New monitor</Button> : null}
          {live ? <Button size="sm" variant="danger-soft" onClick={() => void stopMonitor(jobId)}><Square /> Stop</Button> : null}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-3">
        {failed ? <div className="mb-3 rounded-md bg-danger-soft px-3 py-2 text-xs text-danger">{monitor?.job.error}</div> : null}
        {oom.length || missing.length ? (
          <div className="mb-3 flex items-start gap-2 rounded-md bg-warning-soft px-3 py-2 text-xs text-warning">
            <AlertTriangle className="mt-0.5 size-3.5 shrink-0" aria-hidden />
            <div>
              {oom.length ? <div>Out of memory (a process was killed): {oom.map(nameOf).join(', ')}</div> : null}
              {missing.length ? <div>No longer running: {missing.map(nameOf).join(', ')}</div> : null}
            </div>
          </div>
        ) : null}
        <HostLine row={host[host.length - 1]} />

        <h3 className="mb-1 mt-3 text-xs font-medium text-fg">Host</h3>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(20rem,1fr))] gap-x-5 gap-y-4">
          <TimeSeriesChart title="Host CPU" unit="%" data={charts.cpu} />
          <TimeSeriesChart title="CPU by group" unit="cores" data={charts.groups} />
          <TimeSeriesChart title="Memory" unit="GB" data={charts.mem} note="host used vs. what containers and Docker account for" />
          <TimeSeriesChart title="Pressure (stalled time)" unit="%" data={charts.psi} />
        </div>

        <h3 className="mb-1 mt-5 text-xs font-medium text-fg">
          Monitored nodes <span className="font-normal text-fg-subtle">· {count}</span>
        </h3>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(20rem,1fr))] gap-x-5 gap-y-4">
          <TimeSeriesChart title="CPU per node" unit="%" data={charts.selCpu} note="100% = one core" />
          <TimeSeriesChart title="Network (all monitored nodes)" unit="Mb/s" data={charts.selNet} />
          {nodeCharts ? (
            <>
              <TimeSeriesChart title="CPU" unit="%" data={nodeCharts.cpu} note={note(nodeCharts.cpu.hidden)} />
              <TimeSeriesChart title="Memory" unit="MB" data={nodeCharts.mem} note={note(nodeCharts.mem.hidden)} />
              <TimeSeriesChart title="Receive" unit="Mb/s" data={nodeCharts.rx} note={note(nodeCharts.rx.hidden)} />
            </>
          ) : null}
        </div>

        {table.length ? (
          <section className="mt-5">
            <h3 className="mb-1.5 text-xs font-medium text-fg">Latest</h3>
            <table className="w-full text-left text-2xs tabular-nums">
              <thead className="text-fg-muted">
                <tr className="border-b border-border">
                  <th className="py-1 font-medium">Node</th><th className="text-right font-medium">CPU %</th><th className="text-right font-medium">Memory</th><th className="text-right font-medium">Processes</th>
                  <th className="text-right font-medium">Receive</th><th className="text-right font-medium">Send</th><th className="text-right font-medium">Drops</th>
                </tr>
              </thead>
              <tbody>
                {table.map((r) => (
                  <tr key={r.target} className="border-b border-border/60 text-fg">
                    <td className="py-1">{nameOf(r.target)}</td>
                    <td className="text-right">{r.cpu_pct?.toFixed(1) ?? '–'}</td>
                    <td className="text-right">{formatBytes(r.mem_used)}</td>
                    <td className="text-right">{r.pids ?? '–'}</td>
                    <td className="text-right">{formatBps(r.rx_bps)}</td>
                    <td className="text-right">{formatBps(r.tx_bps)}</td>
                    <td className="text-right">{r.drops ?? '–'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ) : latest ? (
          <section className="mt-5 grid grid-cols-[repeat(auto-fit,minmax(14rem,1fr))] gap-4 text-2xs">
            {(['cpu_pct', 'mem_used', 'net_bps'] as const).map((k) => (
              <div key={k}>
                <h3 className="mb-1 text-xs font-medium text-fg">Top by {k === 'cpu_pct' ? 'CPU' : k === 'mem_used' ? 'memory' : 'network'}</h3>
                <ol className="space-y-0.5 tabular-nums">
                  {latest.selection.top[k].map(([node, v]) => (
                    <li key={node} className="flex justify-between gap-2 text-fg">
                      <span className="truncate">{nameOf(node)}</span>
                      <span className="text-fg-muted">{k === 'cpu_pct' ? `${v.toFixed(1)}%` : k === 'mem_used' ? formatBytes(v) : formatBps(v)}</span>
                    </li>
                  ))}
                </ol>
              </div>
            ))}
          </section>
        ) : null}

        {tools.length ? (
          <p className="mt-3 text-2xs text-fg-subtle">
            AE3GIS tools now: {tools.map((t) => `${t.purpose || t.target} ${t.cpu_pct?.toFixed(1) ?? '–'}% CPU, ${formatBytes(t.mem_used)}`).join(' · ')}. Tool load is counted apart from the nodes.
          </p>
        ) : null}

        {markers.length ? (
          <section className="mt-5">
            <h3 className="mb-1.5 text-xs font-medium text-fg">Events</h3>
            <ul className="space-y-0.5 text-2xs text-fg-muted">
              {markers.map((m, i) => (
                <li key={`${m.t}:${i}`} className="tabular-nums"><span className="text-fg-subtle">{m.t.toFixed(0)}s</span> · {m.source}: {m.text}</li>
              ))}
            </ul>
          </section>
        ) : null}

        {result?.host && !live ? (
          <section className="mt-5">
            <h3 className="mb-1.5 text-xs font-medium text-fg">Summary{result.duration_s ? <span className="font-normal text-fg-subtle"> · {result.duration_s.toFixed(0)}s, {result.sweeps} sweeps</span> : null}</h3>
            <table className="w-full max-w-xl text-left text-2xs tabular-nums">
              <thead className="text-fg-muted">
                <tr className="border-b border-border"><th className="py-1 font-medium">Host</th><th className="text-right font-medium">Mean</th><th className="text-right font-medium">p95</th><th className="text-right font-medium">Max</th></tr>
              </thead>
              <tbody>
                {([
                  ['CPU %', 'vm_cpu_pct', (v: number) => v.toFixed(1)],
                  ['Memory', 'mem_used', (v: number) => formatBytes(v)],
                  ['Memory pressure (some) %', 'psi_mem_some', (v: number) => v.toFixed(2)],
                  ['CPU pressure (some) %', 'psi_cpu_some', (v: number) => v.toFixed(2)],
                  ['Collector sweep ms', 'sweep_ms', (v: number) => v.toFixed(1)],
                ] as const).map(([label, key, fmt]) => {
                  const s = result.host?.[key];
                  return (
                    <tr key={key} className="border-b border-border/60 text-fg">
                      <td className="py-1">{label}</td>
                      <td className="text-right">{s?.mean !== null && s?.mean !== undefined ? fmt(s.mean) : '–'}</td>
                      <td className="text-right">{s?.p95 !== null && s?.p95 !== undefined ? fmt(s.p95) : '–'}</td>
                      <td className="text-right">{s?.max !== null && s?.max !== undefined ? fmt(s.max) : '–'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        ) : null}

        {monitor ? <EnvironmentDetails jobId={jobId} fingerprint={result?.environment_fingerprint} file="monitor.json" /> : null}
      </div>
    </div>
  );
}
