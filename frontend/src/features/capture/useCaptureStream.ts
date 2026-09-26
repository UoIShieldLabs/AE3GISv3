import { useEffect, useRef, useState } from 'react';
import * as api from '@/api/client';
import { appendPackets } from './packetBuffer';

export interface CaptureStatus {
  packets: number;
  bytes: number;
  file_bytes: number;
  pps: number;
  bps: number;
  undecoded: number;
}

export interface CaptureStream {
  capture: api.Capture | null;
  status: CaptureStatus | null;
  rows: api.PacketSummary[];
  /** Messages the browser was too slow to take (the pcap has them all). */
  dropped: number;
  ended: boolean;
  connection: 'connecting' | 'open' | 'closed';
}

type Message =
  | { type: 'hello'; capture: api.Capture; recent: api.PacketSummary[] }
  | { type: 'packets'; items: api.PacketSummary[]; undecoded: number; dropped?: number }
  | ({ type: 'status' } & CaptureStatus)
  | { type: 'end'; result: Record<string, unknown> | null };

const TICK_MS = 250;

/** Live packet summaries of a capture over its WebSocket. Rows are buffered in
 *  a ref and rendered at most 4×/s, so a busy link never floods React. */
export function useCaptureStream(topologyId: string | null, jobId: string): CaptureStream {
  const [state, setState] = useState<CaptureStream>({ capture: null, status: null, rows: [], dropped: 0, ended: false, connection: 'connecting' });
  const rowsRef = useRef<api.PacketSummary[]>([]);
  const dirty = useRef(false);

  useEffect(() => {
    if (!topologyId) return;
    let closed = false;
    let ended = false;
    let ws: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | null = null;
    rowsRef.current = [];

    const tick = setInterval(() => {
      if (!dirty.current) return;
      dirty.current = false;
      setState((s) => ({ ...s, rows: rowsRef.current }));
    }, TICK_MS);

    const connect = () => {
      setState((s) => ({ ...s, connection: 'connecting' }));
      ws = new WebSocket(api.wsUrl(api.captureWsPath(topologyId, jobId)));
      ws.onopen = () => setState((s) => ({ ...s, connection: 'open' }));
      ws.onmessage = (ev: MessageEvent<string>) => {
        let msg: Message;
        try { msg = JSON.parse(ev.data) as Message; } catch { return; }
        if (msg.type === 'hello') {
          rowsRef.current = appendPackets(rowsRef.current, msg.recent);
          dirty.current = true;
          setState((s) => ({ ...s, capture: msg.capture }));
        } else if (msg.type === 'packets') {
          rowsRef.current = appendPackets(rowsRef.current, msg.items);
          dirty.current = true;
          if (msg.dropped) setState((s) => (s.dropped === msg.dropped ? s : { ...s, dropped: msg.dropped ?? 0 }));
        } else if (msg.type === 'status') {
          const status: CaptureStatus = { packets: msg.packets, bytes: msg.bytes, file_bytes: msg.file_bytes, pps: msg.pps, bps: msg.bps, undecoded: msg.undecoded };
          setState((s) => ({ ...s, status }));
        } else if (msg.type === 'end') {
          ended = true;
          // The final record (status, stats, stopped_by) comes from the API.
          void api.getCapture(jobId).then((capture) => setState((s) => ({ ...s, capture, ended: true, rows: rowsRef.current })), () => setState((s) => ({ ...s, ended: true })));
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
