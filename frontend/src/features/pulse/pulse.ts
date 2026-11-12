// One live-view connection app-wide (like statusPolling): while it is on, the
// backend's collector reports which links carry traffic and what runs in each
// node of the deployed lab. The store only changes when that picture does, so
// the canvas re-projects on events, not once a second.
import { pulseWsPath, wsUrl } from '@/api/client';
import { useAppStore, type NodeProcess, type TrafficDir } from '@/store';

const RETRY_MS = 3000;
/** The collector could not run (no tools image, no Docker): try again, but rarely. */
const UNAVAILABLE_RETRY_MS = 30000;

type Message =
  | { type: 'hello' }
  | { type: 'pulse'; links: Record<string, TrafficDir>; nodes: Record<string, NodeProcess[]> }
  | { type: 'unavailable'; reason?: string };

let current: string | null = null;
let ws: WebSocket | null = null;
let timer: ReturnType<typeof setTimeout> | null = null;
let lastKey = '';

/** Test seam: how the socket is made (null restores the real one). */
let createSocket = (url: string): WebSocket => new WebSocket(url);
export function setPulseSocket(factory: ((url: string) => WebSocket) | null): void {
  createSocket = factory ?? ((url) => new WebSocket(url));
}

function clear(): void {
  lastKey = '';
  const st = useAppStore.getState();
  if (Object.keys(st.linkTraffic).length || Object.keys(st.nodeProcesses).length) st.setPulse({}, {});
}

function connect(topologyId: string): void {
  if (current !== topologyId) return;
  const st = useAppStore.getState();
  if (st.pulseState !== 'unavailable') st.setPulseState('connecting');
  const socket = createSocket(wsUrl(pulseWsPath(topologyId)));
  ws = socket;
  let retry = RETRY_MS;
  socket.onmessage = (ev: MessageEvent<string>) => {
    if (ws !== socket) return;
    let msg: Message;
    try { msg = JSON.parse(ev.data) as Message; } catch { return; }
    if (msg.type === 'pulse') {
      const s = useAppStore.getState();
      if (s.pulseState !== 'live') s.setPulseState('live');
      // The server sends a picture only when it changed; compare anyway, so a
      // reconnect that replays the same one costs nothing.
      const key = JSON.stringify([msg.links, msg.nodes]);
      if (key !== lastKey) {
        lastKey = key;
        s.setPulse(msg.links ?? {}, msg.nodes ?? {});
      }
    } else if (msg.type === 'unavailable') {
      retry = UNAVAILABLE_RETRY_MS;
      useAppStore.getState().setPulseState('unavailable');
      clear();
    }
  };
  socket.onclose = () => {
    if (ws !== socket) return;
    ws = null;
    if (current !== topologyId) return;
    if (retry === RETRY_MS) {
      useAppStore.getState().setPulseState('connecting');
      clear();
    }
    timer = setTimeout(() => connect(topologyId), retry);
  };
}

/** Watch a deployed topology's lab. Safe to call repeatedly. */
export function startPulse(topologyId: string): void {
  if (current === topologyId) return;
  stopPulse();
  current = topologyId;
  connect(topologyId);
}

export function stopPulse(): void {
  current = null;
  if (timer !== null) clearTimeout(timer);
  timer = null;
  const socket = ws;
  ws = null;
  if (socket) {
    socket.onmessage = socket.onclose = null;
    socket.close();
  }
  clear();
  const st = useAppStore.getState();
  if (st.pulseState !== 'off') st.setPulseState('off');
}
