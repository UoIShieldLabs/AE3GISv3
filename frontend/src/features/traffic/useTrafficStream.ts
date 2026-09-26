import { useEffect, useRef, useState } from 'react';
import * as api from '@/api/client';

type SidecarRoles = api.TrafficRun['sidecars'];

export interface TrafficStream {
  run: api.TrafficRun | null;
  flows: api.FlowSample[];
  nodes: api.NodeSample[];
  sidecars: SidecarRoles;
  elapsed: number | null;
  ended: boolean;
  connection: 'connecting' | 'open' | 'closed';
}

type Message =
  | { type: 'hello'; run: api.TrafficRun; backlog: { flows: api.FlowSample[]; nodes: api.NodeSample[] } }
  | { type: 'flow'; samples: api.FlowSample[] }
  | { type: 'nodes'; samples: api.NodeSample[] }
  | { type: 'sidecars'; items: SidecarRoles }
  | { type: 'status'; elapsed: number }
  | { type: 'end'; result: Record<string, unknown> | null };

const TICK_MS = 1000;
const flowKey = (s: api.FlowSample) => `${s.flow_id}:${s.direction}:${s.side}:${s.t}`;
const nodeKey = (s: api.NodeSample) => `${s.target}:${s.t}`;

function merge<T>(into: T[], seen: Set<string>, items: readonly T[], key: (x: T) => string): boolean {
  let added = false;
  for (const it of items) {
    const k = key(it);
    if (seen.has(k)) continue;
    seen.add(k);
    into.push(it);
    added = true;
  }
  return added;
}

/** A traffic run's samples, live over its WebSocket (backlog first, then
 *  updates), re-rendered once a second. Works for finished runs too. */
export function useTrafficStream(topologyId: string | null, jobId: string): TrafficStream {
  const [state, setState] = useState<TrafficStream>({ run: null, flows: [], nodes: [], sidecars: {}, elapsed: null, ended: false, connection: 'connecting' });
  const buf = useRef({ flows: [] as api.FlowSample[], nodes: [] as api.NodeSample[], fseen: new Set<string>(), nseen: new Set<string>(), dirty: false });

  useEffect(() => {
    if (!topologyId) return;
    let closed = false;
    let ended = false;
    let ws: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | null = null;
    const b = buf.current;
    b.flows = [];
    b.nodes = [];
    b.fseen = new Set();
    b.nseen = new Set();

    const flush = () => {
      if (!b.dirty) return;
      b.dirty = false;
      setState((s) => ({ ...s, flows: b.flows.slice(), nodes: b.nodes.slice() }));
    };
    const tick = setInterval(flush, TICK_MS);

    const connect = () => {
      setState((s) => ({ ...s, connection: 'connecting' }));
      ws = new WebSocket(api.wsUrl(api.trafficWsPath(topologyId, jobId)));
      ws.onopen = () => setState((s) => ({ ...s, connection: 'open' }));
      ws.onmessage = (ev: MessageEvent<string>) => {
        let msg: Message;
        try { msg = JSON.parse(ev.data) as Message; } catch { return; }
        switch (msg.type) {
          case 'hello':
            b.dirty = merge(b.flows, b.fseen, msg.backlog.flows, flowKey) || b.dirty;
            b.dirty = merge(b.nodes, b.nseen, msg.backlog.nodes, nodeKey) || b.dirty;
            setState((s) => ({ ...s, run: msg.run, sidecars: msg.run.sidecars ?? {} }));
            flush();
            break;
          case 'flow':
            b.dirty = merge(b.flows, b.fseen, msg.samples, flowKey) || b.dirty;
            break;
          case 'nodes':
            b.dirty = merge(b.nodes, b.nseen, msg.samples, nodeKey) || b.dirty;
            break;
          case 'sidecars':
            setState((s) => ({ ...s, sidecars: msg.items }));
            break;
          case 'status':
            setState((s) => ({ ...s, elapsed: msg.elapsed }));
            break;
          case 'end':
            ended = true;
            flush();
            void api.getTrafficRun(jobId).then((run) => setState((s) => ({ ...s, run, ended: true })), () => setState((s) => ({ ...s, ended: true })));
            break;
        }
      };
      ws.onclose = () => {
        setState((s) => ({ ...s, connection: 'closed' }));
        if (!closed && !ended) retry = setTimeout(connect, 2000);
      };
    };
    connect();
    return () => {
      closed = true;
      clearInterval(tick);
      if (retry) clearTimeout(retry);
      ws?.close();
    };
  }, [topologyId, jobId]);

  return state;
}
