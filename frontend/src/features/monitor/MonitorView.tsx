import { useMemo, useState } from 'react';
import { AlertTriangle, ChevronDown, ChevronRight, Download, Gauge, Pin, PinOff, Plus, Square, X } from 'lucide-react';
import { useAppShallow } from '@/store/selectors';
import { locate } from '@/lib/topology';
import { Badge, Button, IconButton, MultiSelect, Select } from '@/ui';
import { TimeSeriesChart } from '@/ui/charts/TimeSeriesChart';
import { formatBps, formatBytes } from '@/features/capture/packetBuffer';
import { EnvironmentDetails } from '@/features/traffic/EnvironmentDetails';
import { NODE_ROWS_LIMIT, useMonitorStream } from './useMonitorStream';
import {
  cpuByGroupChart,
  dockerRss,
  groupRows,
  hostCpuChart,
  latestByNode,
  memoryChart,
  perNodeChart,
  pressureChart,
  selectionCpuChart,
  selectionNetChart,
  type HostRow,
  type NodeRow,
} from './model';
import { GROUP_BY, grouping, type GroupBy } from './grouping';
import { nodesOf } from './selection';
import { exportMonitor, openMonitorPanel, stopMonitor } from './actions';

const STOPPED_BY: Record<string, string> = {
  completed: 'Completed',
  user: 'Stopped',
  destroy: 'Stopped: the topology was destroyed',
  shutdown: 'Stopped: the server shut down',
  'limit:time': 'Stopped at the time limit',
};

/** Lines per device chart (one per --chart-N colour). */
const SHOWN = 6;
const MACHINE_OPEN_KEY = 'ae3gis.monitor.machineOpen';

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

function readMachineOpen(): boolean {
  try { return localStorage.getItem(MACHINE_OPEN_KEY) === '1'; } catch { return false; }
}
function writeMachineOpen(open: boolean) {
  try { localStorage.setItem(MACHINE_OPEN_KEY, open ? '1' : '0'); } catch { /* per-viewer convenience only */ }
}

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

/** A monitor in the dock: every device of the lab (pinned, busiest or grouped)
 *  over time, then the machine running it. ``seed`` pins devices (a device's
 *  "Monitor…" while this monitor runs). */
export function MonitorView({ jobId, seed }: { jobId: string; seed?: { nodes?: string[]; nonce: number } }) {
  const { backendId, topology, selection } = useAppShallow((s) => ({ backendId: s.backendId, topology: s.topology, selection: s.selection }));
  const [pins, setPins] = useState<string[]>(() => seed?.nodes ?? []);
  const [groupBy, setGroupBy] = useState<GroupBy>('none');
  const [machineOpen, setMachineOpen] = useState(readMachineOpen);
  const { monitor, host, agg, nodes, markers, latest, partial, oom, missing, ended } = useMonitorStream(backendId, jobId, pins);
  const live = !!monitor?.live && !ended;
  const failed = monitor?.status === 'failed';
  const result = monitor?.result as MonitorResult | null | undefined;

  // "Monitor…" on a device while this runs: pin it, once per request (adjusting state while rendering).
  const [appliedSeed, setAppliedSeed] = useState<number | undefined>(seed?.nonce);
  if (seed?.nodes?.length && seed.nonce !== appliedSeed) {
    setAppliedSeed(seed.nonce);
    setPins((p) => [...new Set([...p, ...seed.nodes!])]);
    setGroupBy('none');
  }

  const devices = useMemo(() => nodesOf(topology), [topology]);
  const deviceIds = useMemo(() => new Set(devices.map((d) => d.id)), [devices]);
  const nameOf = (id: string) => {
    const hit = locate(topology, id);
    return hit?.kind === 'container' ? hit.container.name : id;
  };
  const order = useMemo(() => monitor?.monitored ?? [], [monitor]);
  const count = monitor?.monitored.length ?? 0;
  const grouped = groupBy !== 'none' && !partial;
  const pinned = new Set(pins);
  /** New pins mean "show me these": back to one line per device. */
  const changePins = (next: string[]) => {
    if (next.some((id) => !pinned.has(id))) setGroupBy('none');
    setPins(next);
  };
  const togglePin = (id: string) => changePins(pinned.has(id) ? pins.filter((x) => x !== id) : [...pins, id]);
  const selectedUnpinned = selection.nodeIds.filter((id) => deviceIds.has(id) && !pinned.has(id));

  const deviceCharts = useMemo(() => {
    const metric = (key: 'cpu_pct' | 'mem_used' | 'rx_bps' | 'tx_bps') => {
      if (grouped) {
        const g = grouping(topology, groupBy as Exclude<GroupBy, 'none'>);
        return perNodeChart(groupRows(nodes, g.groupOf), key, g.labelOf, g.order, SHOWN);
      }
      return perNodeChart(nodes, key, nameOf, order, SHOWN, pins.length ? pins : undefined);
    };
    return { cpu: metric('cpu_pct'), mem: metric('mem_used'), rx: metric('rx_bps'), tx: metric('tx_bps') };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, order, topology, grouped, groupBy, pins]);

  const machineCharts = useMemo(
    () => ({
      cpu: hostCpuChart(host),
      groups: cpuByGroupChart(host),
      mem: memoryChart(host),
      psi: pressureChart(host),
      labCpu: selectionCpuChart(agg),
      labNet: selectionNetChart(agg),
    }),
    [host, agg],
  );

  const table = useMemo(() => latestByNode(nodes.filter((r): r is NodeRow => r.kind === 'node')), [nodes]);
  const tools = latest?.tools ?? [];
  const lastT = host.length ? host[host.length - 1].t : null;
  const hidden = deviceCharts.cpu.hidden;
  const showing = grouped
    ? `one line per ${groupBy === 'subnet' ? 'subnet' : 'device type'}${hidden ? ` · busiest ${SHOWN} of ${hidden + SHOWN}` : ''}`
    : pins.length
      ? `${Math.min(pins.length, SHOWN)} pinned${pins.length > SHOWN ? ` · the first ${SHOWN} of ${pins.length}` : ''}`
      : `the busiest ${Math.min(SHOWN, count)} of ${count}`;
  // A partial sweep carries only the busiest devices: "of N" would count those, not the lab.
  const note = !grouped && !pins.length && hidden ? (partial ? `busiest ${SHOWN}` : `busiest ${SHOWN} of ${hidden + SHOWN}`) : undefined;
  const deviceOptions = devices.map((d) => ({ value: d.id, label: d.name, description: d.ip, keywords: [d.type] }));

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex h-9 shrink-0 items-center gap-3 border-b border-border bg-surface px-3 text-xs">
        <Gauge className="size-3.5 text-fg-muted" aria-hidden />
        <span className="font-medium text-fg">{monitor?.label || 'Monitor'}</span>
        {live ? <Badge tone="success" dot="pulse">Recording</Badge> : failed ? <Badge tone="danger">Failed</Badge> : monitor ? <Badge>{STOPPED_BY[result?.stopped_by ?? ''] ?? 'Done'}</Badge> : null}
        {monitor ? <span className="text-fg-muted tabular-nums">{count} device{count === 1 ? '' : 's'} · every {monitor.interval_s}s{lastT !== null ? ` · ${lastT.toFixed(0)}s` : ''}</span> : null}
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

        {/* ── Devices ── */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <h3 className="mr-1 font-medium text-fg">Devices</h3>
          <MultiSelect size="sm" className="w-52" value={pins} onValueChange={changePins} options={deviceOptions} placeholder="Pin devices…" searchPlaceholder="Find a device…" aria-label="Pinned devices" />
          {selectedUnpinned.length ? (
            <Button size="sm" variant="ghost" onClick={() => changePins([...pins, ...selectedUnpinned])} title="Pin the devices selected on the canvas">
              <Pin /> Pin selected ({selectedUnpinned.length})
            </Button>
          ) : null}
          {pins.length ? <Button size="sm" variant="ghost" onClick={() => setPins([])}><X /> Clear pins</Button> : null}
          <span title={partial ? `Grouping needs every device's data, sent for labs up to ${NODE_ROWS_LIMIT} devices` : undefined}>
            <Select size="sm" className="w-36" value={partial ? 'none' : groupBy} onValueChange={setGroupBy} options={GROUP_BY} disabled={partial} />
          </span>
          <span className="text-fg-subtle">Showing {showing}{grouped && pins.length ? ' · pins show under Each device' : ''}</span>
        </div>
        <div className="mt-2 grid grid-cols-[repeat(auto-fit,minmax(20rem,1fr))] gap-x-5 gap-y-4">
          <TimeSeriesChart title="CPU" unit="%" data={deviceCharts.cpu} note={note ? `${note} · 100% = one core` : '100% = one core'} />
          <TimeSeriesChart title="Memory" unit="MB" data={deviceCharts.mem} note={note} />
          <TimeSeriesChart title="Receive" unit="Mb/s" data={deviceCharts.rx} note={note} />
          <TimeSeriesChart title="Send" unit="Mb/s" data={deviceCharts.tx} note={note} />
        </div>

        {table.length ? (
          <section className="mt-5">
            <h3 className="mb-1.5 text-xs font-medium text-fg">
              Now{partial ? <span className="font-normal text-fg-subtle"> · the busiest and pinned devices of {count}</span> : null}
            </h3>
            <table className="w-full text-left text-2xs tabular-nums">
              <thead className="text-fg-muted">
                <tr className="border-b border-border">
                  <th className="w-7" aria-label="Pinned" />
                  <th className="py-1 font-medium">Device</th><th className="text-right font-medium">CPU %</th><th className="text-right font-medium">Memory</th><th className="text-right font-medium">Processes</th>
                  <th className="text-right font-medium">Receive</th><th className="text-right font-medium">Send</th><th className="text-right font-medium">Drops</th>
                </tr>
              </thead>
              <tbody>
                {table.map((r) => (
                  <tr key={r.target} className="border-b border-border/60 text-fg">
                    <td>
                      <IconButton size="icon-xs" label={pinned.has(r.target) ? `Unpin ${nameOf(r.target)}` : `Pin ${nameOf(r.target)}`} onClick={() => togglePin(r.target)} className={pinned.has(r.target) ? 'text-accent' : 'text-fg-subtle'}>
                        {pinned.has(r.target) ? <PinOff /> : <Pin />}
                      </IconButton>
                    </td>
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
        ) : null}

        {/* ── The machine ── */}
        <section className="mt-5 border-t border-border pt-3">
          <button
            type="button"
            className="flex w-full items-center gap-1.5 text-left text-xs font-medium text-fg"
            aria-expanded={machineOpen}
            onClick={() => { setMachineOpen((o) => { writeMachineOpen(!o); return !o; }); }}
          >
            {machineOpen ? <ChevronDown className="size-3.5" aria-hidden /> : <ChevronRight className="size-3.5" aria-hidden />}
            Machine &amp; overhead
            <span className="font-normal text-fg-subtle">· the host running the lab, Docker and AE3GIS's own tools</span>
          </button>
          {!machineOpen ? <div className="mt-1 pl-5"><HostLine row={host[host.length - 1]} /></div> : null}
          {machineOpen ? (
            <>
              <div className="mt-2"><HostLine row={host[host.length - 1]} /></div>
              <div className="mt-2 grid grid-cols-[repeat(auto-fit,minmax(20rem,1fr))] gap-x-5 gap-y-4">
                <TimeSeriesChart title="Host CPU" unit="%" data={machineCharts.cpu} />
                <TimeSeriesChart title="CPU by group" unit="cores" data={machineCharts.groups} />
                <TimeSeriesChart title="Memory" unit="GB" data={machineCharts.mem} note="host used vs. what containers and Docker account for" />
                <TimeSeriesChart title="Pressure (stalled time)" unit="%" data={machineCharts.psi} />
                <TimeSeriesChart title="Lab devices CPU" unit="%" data={machineCharts.labCpu} note="across every device · 100% = one core" />
                <TimeSeriesChart title="Lab network" unit="Mb/s" data={machineCharts.labNet} note="all devices together" />
              </div>
              {tools.length ? (
                <p className="mt-3 text-2xs text-fg-subtle">
                  AE3GIS tools now: {tools.map((t) => `${t.purpose || t.target} ${t.cpu_pct?.toFixed(1) ?? '–'}% CPU, ${formatBytes(t.mem_used)}`).join(' · ')}. Tool load is counted apart from the devices.
                </p>
              ) : null}
            </>
          ) : null}
        </section>

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
