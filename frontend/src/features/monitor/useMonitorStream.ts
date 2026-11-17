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

/** Labs up to this many nodes get every node's row (history and live); above
 *  it live sweeps carry the busiest nodes and the pinned ones (the backend's
 *  ``LIVE_NODE_LIMIT``). Every node is recorded either way. */
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
  /** Over the node limit: ``nodes`` holds the busiest and pinned nodes only. */
  partial: boolean;
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
 *  sweeps over the WebSocket, re-rendered once a second. ``pins`` only matter
 *  over the node limit: their history is fetched and the stream carries them. */
export function useMonitorStream(topologyId: string | null, jobId: string, pins: readonly string[] = []): MonitorStream {
  const [state, setState] = useState<MonitorStream>({
    monitor: null, host: [], agg: [], nodes: [], markers: [], latest: null, partial: false, oom: [], missing: [], ended: false, connection: 'connecting',
  });
  const buf = useRef({ host: [] as HostRow[], agg: [] as AggRow[], nodes: [] as NodeRow[], markers: [] as Marker[], latest: null as SweepMessage | null, oom: new Set<string>(), missing: [] as string[], dirty: false });
  const pinsRef = useRef<readonly string[]>(pins);
  /** Set while a partial monitor streams: follow new pins (history + reconnect). */
  const repin = useRef<((pins: readonly string[]) => void) | null>(null);
  const pinsKey = pins.join(',');

  useEffect(() => {
    if (!topologyId) return;
    let closed = false;
    let ended = false;
    let ws: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | null = null;
    let fetched = new Set<string>();
    let partialMode = false;
    const b = buf.current;
    Object.assign(b, { host: [], agg: [], nodes: [], markers: [], latest: null, oom: new Set<string>(), missing: [], dirty: false });

    const flush = () => {
      if (!b.dirty) return;
      b.dirty = false;
      setState((s) => ({ ...s, host: b.host, agg: b.agg, nodes: b.nodes, markers: b.markers.slice(), latest: b.latest, oom: [...b.oom], missing: b.missing }));
    };
    const tick = setInterval(flush, TICK_MS);

    const addSweeps = (sweeps: readonly SweepMessage[]) => {
      if (!sweeps.length) return;
      b.host = mergeRows(b.host, sweeps.map(hostRowFromSweep), byT, HOST_LIMIT);
      b.agg = mergeRows(b.agg, sweeps.map(aggFromSweep), byT, HOST_LIMIT);
      b.nodes = mergeRows(b.nodes, sweeps.flatMap(nodeRowsFromSweep), byTTarget, NODE_LIMIT);
      const last = sweeps[sweeps.length - 1];
      if (!b.latest || last.t >= b.latest.t) {
        b.latest = last;
        b.missing = last.missing;
      }
      for (const s of sweeps) for (const n of s.oom) b.oom.add(n);
      b.dirty = true;
    };

    const addNodeRows = (rows: NodeRow[]) => {
      b.nodes = mergeRows(b.nodes, rows, byTTarget, NODE_LIMIT);
      for (const r of rows) if ((r.oom_kills ?? 0) > 0) b.oom.add(r.target);
      b.dirty = true;
    };

    const connect = () => {
      setState((s) => ({ ...s, connection: 'connecting' }));
      const sock = new WebSocket(api.wsUrl(api.monitorWsPath(topologyId, jobId, partialMode ? pinsRef.current : [])));
      ws = sock;
      sock.onopen = () => setState((s) => ({ ...s, connection: 'open' }));
      sock.onmessage = (ev: MessageEvent<string>) => {
        let msg: Message;
        try { msg = JSON.parse(ev.data) as Message; } catch { return; }
        switch (msg.type) {
          case 'hello':
            setState((s) => ({ ...s, monitor: msg.monitor }));
            addSweeps(msg.backlog);
            flush();
            break;
          case 'sweep':
            addSweeps([msg]);
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
      sock.onclose = () => {
        if (ws !== sock) return; // replaced by a reconnect
        setState((s) => ({ ...s, connection: 'closed' }));
        if (!closed && !ended) retry = setTimeout(connect, 2000);
      };
    };

    /** Recorded rows of pinned nodes not fetched yet (partial monitors only). */
    const fetchPinned = async (every: number) => {
      const fresh = pinsRef.current.filter((n) => !fetched.has(n));
      if (!fresh.length) return;
      fetched = new Set([...fetched, ...fresh]);
      try {
        const rec = await api.monitorSamples(jobId, { nodes: fresh, every });
        if (!closed) addNodeRows((rec.nodes as unknown as NodeRow[]).filter((r) => r.kind === 'node'));
      } catch {
        // The stream still brings them from now on.
      }
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
      const partial = monitor.monitored.length > NODE_ROWS_LIMIT;
      partialMode = partial;
      const elapsed = monitor.job.started_at ? (Date.now() - utcMs(monitor.job.started_at)) / 1000 : 0;
      const duration = (monitor.result as { duration_s?: number } | null)?.duration_s ?? elapsed;
      const every = everyFor(duration, monitor.interval_s);
      try {
        const rec = await api.monitorSamples(jobId, { every, hostOnly: partial });
        if (closed) return;
        b.host = mergeRows(b.host, rec.host as HostRow[], byT, HOST_LIMIT);
        const nodeRows = rec.nodes as unknown as NodeRow[];
        addNodeRows(nodeRows);
        b.agg = mergeRows(b.agg, aggFromNodeRows(nodeRows), byT, HOST_LIMIT);
        b.markers = (rec.markers as unknown as Marker[]).concat(b.markers);
      } catch {
        // No history (yet): the live stream still works.
      }
      if (partial) await fetchPinned(every);
      if (closed) return;
      setState((s) => ({ ...s, monitor, partial }));
      flush();
      if (monitor.live) {
        connect();
        if (partial) {
          repin.current = () => {
            void fetchPinned(every);
            const old = ws;
            ws = null;
            old?.close();
            connect();
          };
        }
      } else {
        ended = true;
        if (partial) repin.current = () => void fetchPinned(every).then(flush);
        setState((s) => ({ ...s, ended: true, connection: 'closed' }));
      }
    })();

    return () => {
      closed = true;
      repin.current = null;
      clearInterval(tick);
      if (retry) clearTimeout(retry);
      const old = ws;
      ws = null;
      old?.close();
    };
  }, [topologyId, jobId]);

  // Pins changed: a partial monitor fetches the new ones' history and asks the
  // stream for them (a small lab already has every node's rows).
  useEffect(() => {
    const before = pinsRef.current.join(',');
    pinsRef.current = pinsKey ? pinsKey.split(',') : [];
    if (before !== pinsKey) repin.current?.(pinsRef.current);
  }, [pinsKey]);

  return state;
}
