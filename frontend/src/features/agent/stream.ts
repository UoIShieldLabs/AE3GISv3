// A run's live stream (one WebSocket per chat with a run in progress), kept
// outside React like the terminal sessions: closing the panel or leaving the
// editor keeps following it. Events update the agent store; `ui` events go to
// the browser (the owner's only); the end of a run releases the editor lock and
// re-syncs the chat and the open topology.
import * as api from '@/api/client';
import { useAppStore } from '@/store';
import { refreshFromServer } from '@/features/deployment/actions';
import { useAgentStore, type LiveRun } from './agentStore';
import { handleUiAction, type UiAction } from './uiActions';

interface Follow {
  jobId: string;
  ws: WebSocket;
  ended: boolean;
}

const follows = new Map<string, Follow>();
const OUTPUT_CAP = 20_000;

function patchRun(chatId: string, jobId: string, fn: (run: LiveRun) => Partial<LiveRun>) {
  useAgentStore.getState().patchChat(chatId, (c) => {
    const base: LiveRun = c.run?.jobId === jobId ? c.run : { jobId, phase: 'starting', text: '', thinking: '', pendingTool: null };
    return { run: { ...base, ...fn(base) } };
  });
}

/** Follow a chat's run (a no-op if already following that run). */
export function followRun(chatId: string, jobId: string) {
  const cur = follows.get(chatId);
  if (cur && cur.jobId === jobId && !cur.ended) return;
  cur?.ws.close();
  // A new run: the last one's live tool calls and approvals are history now.
  // (A pending approval stays: it may be this run's, loaded with the chat.)
  useAgentStore.getState().patchChat(chatId, (c) =>
    c.run?.jobId === jobId
      ? {}
      : { tools: {}, approvals: Object.fromEntries(Object.entries(c.approvals).filter(([, a]) => a.status === 'pending')) },
  );
  patchRun(chatId, jobId, () => ({}));
  const ws = new WebSocket(api.wsUrl(api.agentWsPath(chatId, jobId)));
  const follow: Follow = { jobId, ws, ended: false };
  follows.set(chatId, follow);
  ws.onmessage = (ev) => {
    try {
      handle(chatId, follow, JSON.parse(ev.data as string) as Record<string, unknown>);
    } catch {
      // A malformed frame: ignore it.
    }
  };
  ws.onclose = () => {
    if (follows.get(chatId) === follow) follows.delete(chatId);
    // Dropped mid-run (network, backend reload): pick it up again if it's still going.
    if (!follow.ended) window.setTimeout(() => void resync(chatId), 1500);
  };
}

/** Stop following (the chat was deleted). */
export function unfollow(chatId: string) {
  const cur = follows.get(chatId);
  if (cur) {
    cur.ended = true;
    cur.ws.close();
    follows.delete(chatId);
  }
}

/** Reload a chat from the server and follow its run, if one is going. */
export async function resync(chatId: string) {
  try {
    const detail = await api.getAgentChat(chatId);
    useAgentStore.getState().setDetail(detail);
    if (detail.active_job_id) {
      followRun(chatId, detail.active_job_id);
      // Our own run (e.g. after a reload): lock the topology it was sent from.
      const st = useAppStore.getState();
      if (detail.can_send && !st.agentLock) {
        const lastUser = [...detail.messages].reverse().find((m) => m.role === 'user');
        const ctx = (lastUser?.content.context ?? null) as { topology_id?: string } | null;
        const topologyId = ctx?.topology_id ?? detail.topology_id;
        if (topologyId) st.setAgentLock({ topologyId, chatId, jobId: detail.active_job_id });
      }
    } else {
      endRun(chatId, null);
    }
  } catch {
    // Gone (deleted, or signed out): nothing to follow.
  }
}

function endRun(chatId: string, jobId: string | null) {
  const store = useAgentStore.getState();
  store.patchChat(chatId, (c) => (jobId === null || c.run?.jobId === jobId ? { run: null } : {}));
  const st = useAppStore.getState();
  const lock = st.agentLock;
  if (lock && lock.chatId === chatId && (jobId === null || lock.jobId === jobId)) {
    st.setAgentLock(null);
    if (st.backendId) void refreshFromServer(st.backendId, { notifyIfDirty: false });
  }
}

function handle(chatId: string, follow: Follow, msg: Record<string, unknown>) {
  const store = useAgentStore.getState();
  const jobId = follow.jobId;
  const callId = typeof msg.call_id === 'string' ? msg.call_id : '';
  switch (msg.type) {
    case 'turn':
      patchRun(chatId, jobId, () => ({ phase: 'thinking', text: '', thinking: '', pendingTool: null }));
      return;
    case 'text_delta':
      patchRun(chatId, jobId, (r) => ({ text: r.text + String(msg.text ?? '') }));
      return;
    case 'thinking_delta':
      patchRun(chatId, jobId, (r) => ({ thinking: r.thinking + String(msg.text ?? '') }));
      return;
    case 'tool_pending':
      patchRun(chatId, jobId, () => ({ pendingTool: String(msg.name ?? '') }));
      return;
    case 'message': {
      const message = msg.message as api.AgentMessage;
      store.addMessage(chatId, message);
      if (message.role === 'assistant') patchRun(chatId, jobId, () => ({ text: '', thinking: '', pendingTool: null }));
      if (message.role === 'user') store.patchChat(chatId, () => ({ sending: null }));
      return;
    }
    case 'tool_start':
      store.patchChat(chatId, (c) => ({
        tools: { ...c.tools, [callId]: { callId, name: String(msg.name ?? ''), input: msg.input, status: 'running', output: c.tools[callId]?.output ?? '' } },
      }));
      patchRun(chatId, jobId, () => ({ phase: 'working', pendingTool: null }));
      return;
    case 'tool_output':
      store.patchChat(chatId, (c) => {
        const t = c.tools[callId];
        if (!t || t.output.length > OUTPUT_CAP) return {};
        return { tools: { ...c.tools, [callId]: { ...t, output: t.output + String(msg.text ?? '') } } };
      });
      return;
    case 'tool_end':
      store.patchChat(chatId, (c) => {
        const t = c.tools[callId] ?? { callId, name: String(msg.name ?? ''), input: null, output: '', status: 'running' as const };
        return { tools: { ...c.tools, [callId]: { ...t, status: msg.is_error ? 'error' : 'done', text: String(msg.text ?? '') } } };
      });
      return;
    case 'approval':
      store.patchChat(chatId, (c) => ({
        approvals: {
          ...c.approvals,
          [callId]: {
            callId,
            name: String(msg.name ?? c.approvals[callId]?.name ?? ''),
            input: msg.input ?? c.approvals[callId]?.input,
            status: (msg.status as 'pending') ?? 'pending',
          },
        },
      }));
      return;
    case 'ui': {
      // Only the chat's owner's browser follows the agent around.
      if (!useAgentStore.getState().byId[chatId]?.canSend) return;
      handleUiAction(msg.action as UiAction, { jobId, chatId });
      return;
    }
    case 'end':
      follow.ended = true;
      endRun(chatId, jobId);
      follow.ws.close();
      void api.getAgentChat(chatId).then((d) => useAgentStore.getState().setDetail(d)).catch(() => undefined);
      return;
  }
}
