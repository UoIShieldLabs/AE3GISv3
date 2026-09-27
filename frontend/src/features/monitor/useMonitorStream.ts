import { useEffect, useRef, useState } from 'react';
import * as api from '@/api/client';
import {
  aggFromNodeRows,
  aggFromSweep,
  everyFor,
  hostRowFromSweep,
  mergeRows,
  nodeRowsFromSweep,
  type AggRow,
  type HostRow,
  type Marker,
  type NodeRow,
  type SweepMessage,
} from './model';

/** Per-node rows are kept (and fetched) only for selections up to this size. */
export const NODE_ROWS_LIMIT = 50;
const HOST_LIMIT = 7200;
const NODE_LIMIT = 60_000;
const TICK_MS = 1000;

export interface MonitorStream {
  monitor: api.Monitor | null;
  host: HostRow[];
  agg: AggRow[];
  nodes: NodeRow[];
  markers: Marker[];
  latest: SweepMessage | null;
  /** Nodes that reported an OOM kill, and nodes that disappeared, so far. */
  oom: string[];
  missing: string[];
  ended: boolean;
  connection: 'connecting' | 'open' | 'closed';
}

type Message =
  | { type: 'hello'; monitor: api.Monitor; backlog: SweepMessage[] }
  | SweepMessage
  | ({ type: 'marker' } & Marker)
  | { type: 'end'; result: Record<string, unknown> | null };

const byT = (r: { t: number }) => String(r.t);
/** The API's timestamps are UTC, sometimes without a zone suffix. */
const utcMs = (iso: string) => Date.parse(/(Z|[+-]\d\d:\d\d)$/.test(iso) ? iso : `${iso}Z`);
const byTTarget = (r: NodeRow) => `${r.t}:${r.target}`;

/** A monitor's recorded history (downsampled for long ones), then its live
 *  sweeps over the WebSocket, re-rendered once a second. */
export function useMonitorStream(topologyId: string | null, jobId: string): MonitorStream {
  const [state, setState] = useState<MonitorStream>({
    monitor: null, host: [], agg: [], nodes: [], markers: [], latest: null, oom: [], missing: [], ended: false, connection: 'connecting',
  });
  const buf = useRef({ host: [] as HostRow[], agg: [] as AggRow[], nodes: [] as NodeRow[], markers: [] as Marker[], latest: null as SweepMessage | null, oom: new Set<string>(), missing: [] as string[], dirty: false });

  useEffect(() => {
    if (!topologyId) return;
    let closed = false;
    let ended = false;
    let ws: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | null = null;
    const b = buf.current;
    Object.assign(b, { host: [], agg: [], nodes: [], markers: [], latest: null, oom: new Set<string>(), missing: [], dirty: false });

    const flush = () => {
      if (!b.dirty) return;
      b.dirty = false;
      setState((s) => ({ ...s, host: b.host, agg: b.agg, nodes: b.nodes, markers: b.markers.slice(), latest: b.latest, oom: [...b.oom], missing: b.missing }));
    };
    const tick = setInterval(flush, TICK_MS);

    const addSweeps = (sweeps: readonly SweepMessage[], keepNodes: boolean) => {
      if (!sweeps.length) return;
      b.host = mergeRows(b.host, sweeps.map(hostRowFromSweep), byT, HOST_LIMIT);
      b.agg = mergeRows(b.agg, sweeps.map(aggFromSweep), byT, HOST_LIMIT);
      if (keepNodes) b.nodes = mergeRows(b.nodes, sweeps.flatMap(nodeRowsFromSweep), byTTarget, NODE_LIMIT);
      const last = sweeps[sweeps.length - 1];
      if (!b.latest || last.t >= b.latest.t) {
        b.latest = last;
        b.missing = last.missing;
      }
      for (const s of sweeps) for (const n of s.oom) b.oom.add(n);
      b.dirty = true;
    };

    const connect = (keepNodes: boolean) => {
      setState((s) => ({ ...s, connection: 'connecting' }));
      ws = new WebSocket(api.wsUrl(api.monitorWsPath(topologyId, jobId)));
      ws.onopen = () => setState((s) => ({ ...s, connection: 'open' }));
      ws.onmessage = (ev: MessageEvent<string>) => {
        let msg: Message;
        try { msg = JSON.parse(ev.data) as Message; } catch { return; }
        switch (msg.type) {
          case 'hello':
            setState((s) => ({ ...s, monitor: msg.monitor }));
            addSweeps(msg.backlog, keepNodes);
            flush();
            break;
          case 'sweep':
            addSweeps([msg], keepNodes);
            break;
          case 'marker':
            b.markers.push({ t: msg.t, step: msg.step, source: msg.source, text: msg.text });
            b.dirty = true;
            break;
          case 'end':
            ended = true;
            flush();
            void api.getMonitor(jobId).then((monitor) => setState((s) => ({ ...s, monitor, ended: true })), () => setState((s) => ({ ...s, ended: true })));
            break;
        }
      };
      ws.onclose = () => {
        setState((s) => ({ ...s, connection: 'closed' }));
        if (!closed && !ended) retry = setTimeout(() => connect(keepNodes), 2000);
      };
    };

    // History first (what the WebSocket's backlog no longer holds), then live.
    void (async () => {
      let monitor: api.Monitor;
      try {
        monitor = await api.getMonitor(jobId);
      } catch {
        if (!closed) setState((s) => ({ ...s, connection: 'closed', ended: true }));
        return;
      }
      if (closed) return;
      const keepNodes = monitor.monitored.length <= NODE_ROWS_LIMIT;
      const elapsed = monitor.job.started_at ? (Date.now() - utcMs(monitor.job.started_at)) / 1000 : 0;
      const duration = (monitor.result as { duration_s?: number } | null)?.duration_s ?? elapsed;
      try {
        const rec = await api.monitorSamples(jobId, { every: everyFor(duration, monitor.interval_s), hostOnly: !keepNodes });
        if (closed) return;
        b.host = mergeRows(b.host, rec.host as HostRow[], byT, HOST_LIMIT);
        const nodeRows = rec.nodes as unknown as NodeRow[];
        b.nodes = mergeRows(b.nodes, nodeRows, byTTarget, NODE_LIMIT);
        b.agg = mergeRows(b.agg, aggFromNodeRows(nodeRows), byT, HOST_LIMIT);
        b.markers = (rec.markers as unknown as Marker[]).concat(b.markers);
        for (const r of nodeRows) if ((r.oom_kills ?? 0) > 0) b.oom.add(r.target);
        b.dirty = true;
      } catch {
        // No history (yet): the live stream still works.
      }
      setState((s) => ({ ...s, monitor }));
      flush();
      if (monitor.live) connect(keepNodes);
      else {
        ended = true;
        setState((s) => ({ ...s, ended: true, connection: 'closed' }));
      }
    })();

    return () => {
      closed = true;
      clearInterval(tick);
      if (retry) clearTimeout(retry);
      ws?.close();
    };
  }, [topologyId, jobId]);

  return state;
}
