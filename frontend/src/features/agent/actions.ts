// The agent sidebar's actions: plain functions over the stores, like
// features/deployment/actions.ts, so the panel, the top bar and ⌘K share them.
import * as api from '@/api/client';
import { useAppStore } from '@/store';
import { toast } from '@/ui';
import { saveTopology } from '@/features/deployment/actions';
import { useAgentStore } from './agentStore';
import { followRun, resync, unfollow } from './stream';

/** The server's name for a chat from its first message (services/agent/store.py). */
function titleFrom(text: string): string {
  const line = text.split(/\s+/).filter(Boolean).join(' ');
  return line.length > 60 ? `${line.slice(0, 60)}…` : line || 'New chat';
}

/** What the user is looking at, sent with each message. */
export function buildContext(pathname = window.location.pathname): api.AgentContext {
  const st = useAppStore.getState();
  const m = /^\/t\/([^/]+)(?:\/site\/([^/]+)(?:\/subnet\/([^/]+))?)?/.exec(pathname);
  if (!m || m[1] === 'draft' || !st.backendId || st.backendId !== m[1]) {
    return { page: pathname === '/' ? 'library' : 'editor (unsaved draft)', selection: [] };
  }
  const scope: Record<string, string> = {};
  if (m[2]) scope.site_id = m[2];
  if (m[3]) scope.subnet_id = m[3];
  return {
    topology_id: st.backendId,
    topology_name: st.backendName ?? st.topology.name ?? null,
    scope,
    selection: st.selection.nodeIds.slice(0, 50),
  };
}

export async function loadAgentStatus(): Promise<api.AgentStatus | null> {
  try {
    const status = await api.getAgentStatus();
    useAgentStore.getState().setStatus(status);
    return status;
  } catch {
    useAgentStore.getState().setStatus(null);
    return null;
  }
}

export async function loadChats(owner?: string): Promise<void> {
  try {
    const chats = await api.listAgentChats(owner ? { owner } : {});
    if (!owner) useAgentStore.getState().setChats(chats);
    // Runs still going (e.g. after a reload): follow them again.
    for (const c of chats) if (c.active_job_id && !owner) void resync(c.id);
  } catch (err) {
    toast.error('Could not load chats', { description: api.errorMessage(err) });
  }
}

/** Show a chat in the panel (also someone else's, read-only: a student's, for staff). */
export async function openChat(chatId: string): Promise<void> {
  useAppStore.getState().openAgentChat(chatId);
  try {
    const detail = await api.getAgentChat(chatId);
    useAgentStore.getState().setDetail(detail);
    if (detail.active_job_id) followRun(chatId, detail.active_job_id);
  } catch (err) {
    toast.error('Could not open the chat', { description: api.errorMessage(err) });
    useAppStore.getState().openAgentChat(null);
  }
}

/** Start a new chat (made on the server with the first message). */
export function newChat() {
  useAppStore.getState().openAgentChat(null);
}

/** Send a message: saves the editor's changes first (the agent reads the saved
 *  topology), makes the chat if needed, and follows the run. */
export async function sendMessage(chatId: string | null, text: string): Promise<string | null> {
  const st = useAppStore.getState();
  if (st.backendId && st.dirty) {
    const saved = await saveTopology();
    if (!saved) return null;
  }
  const store = useAgentStore.getState();
  let id = chatId;
  try {
    if (!id) {
      const chat = await api.createAgentChat({ topology_id: useAppStore.getState().backendId });
      store.upsertChat(chat);
      store.setDetail({ ...chat, messages: [], pending_approvals: [], can_send: true });
      useAppStore.getState().openAgentChat(chat.id);
      id = chat.id;
    }
    const chatIdNow = id;
    store.patchChat(chatIdNow, () => ({ sending: text, error: null }));
    const res = await api.sendAgentMessage(chatIdNow, text, buildContext());
    const s = useAgentStore.getState();
    s.addMessage(chatIdNow, res.message);
    const current = s.byId[chatIdNow]?.chat;
    if (current) {
      // The server names a new chat after its first message; show that at once.
      const title = current.title === 'New chat' ? titleFrom(text) : current.title;
      const chat = { ...current, title, active_job_id: res.job_id, updated_at: new Date().toISOString() };
      s.patchChat(chatIdNow, () => ({ sending: null, chat }));
      s.upsertChat(chat);
    }
    followRun(chatIdNow, res.job_id);
    const now = useAppStore.getState();
    if (now.backendId && !now.agentLock) now.setAgentLock({ topologyId: now.backendId, chatId: chatIdNow, jobId: res.job_id });
    return chatIdNow;
  } catch (err) {
    if (id) useAgentStore.getState().patchChat(id, () => ({ sending: null, error: api.errorMessage(err) }));
    else toast.error('Could not start a chat', { description: api.errorMessage(err) });
    return id;
  }
}

export async function stopRun(chatId: string): Promise<void> {
  const lock = useAppStore.getState().agentLock;
  const jobId =
    useAgentStore.getState().byId[chatId]?.run?.jobId ??
    (lock?.chatId === chatId ? lock.jobId : null) ??
    useAgentStore.getState().chats?.find((c) => c.id === chatId)?.active_job_id;
  if (!jobId) return;
  try {
    await api.stopJob(jobId);
  } catch (err) {
    toast.error('Could not stop the agent', { description: api.errorMessage(err) });
  }
}

export async function decide(chatId: string, callId: string, approve: boolean): Promise<void> {
  const store = useAgentStore.getState();
  store.patchChat(chatId, (c) => ({
    approvals: { ...c.approvals, [callId]: { ...c.approvals[callId], status: approve ? 'approved' : 'denied' } },
  }));
  try {
    await api.decideAgentApproval(chatId, callId, approve);
  } catch (err) {
    toast.error('That approval is no longer pending', { description: api.errorMessage(err) });
    void resync(chatId);
  }
}

export async function setAutoApprove(chatId: string, value: boolean): Promise<void> {
  try {
    useAgentStore.getState().upsertChat(await api.updateAgentChat(chatId, { auto_approve: value }));
  } catch (err) {
    toast.error('Could not change the setting', { description: api.errorMessage(err) });
  }
}

export async function renameChat(chatId: string, title: string): Promise<void> {
  const t = title.trim();
  if (!t) return;
  try {
    useAgentStore.getState().upsertChat(await api.updateAgentChat(chatId, { title: t }));
  } catch (err) {
    toast.error('Could not rename the chat', { description: api.errorMessage(err) });
  }
}

export async function deleteChat(chatId: string): Promise<void> {
  try {
    await api.deleteAgentChat(chatId);
    unfollow(chatId);
    useAgentStore.getState().removeChat(chatId);
    const st = useAppStore.getState();
    if (st.agentChatId === chatId) st.openAgentChat(null);
    if (st.agentLock?.chatId === chatId) st.setAgentLock(null);
  } catch (err) {
    toast.error('Could not delete the chat', { description: api.errorMessage(err) });
  }
}
