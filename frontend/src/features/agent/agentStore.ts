// The agent sidebar's data: the chat list, each opened chat's messages, and the
// live state of a run (streamed text, tool calls, approvals). Its own small store,
// apart from the app store: it changes with every streamed token, and none of it
// is persisted or undoable. The frame (open, which chat, the editor lock) is the
// app store's `agent` slice.
import { create } from 'zustand';
import type * as api from '@/api/client';

export type ToolStatus = 'running' | 'done' | 'error';

/** A tool call as the run reports it, before (and beside) its saved result. */
export interface LiveTool {
  callId: string;
  name: string;
  input: unknown;
  status: ToolStatus;
  /** Live command output (run_in_node). */
  output: string;
  /** The result text the model got (clipped). */
  text?: string;
}

export interface LiveApproval {
  callId: string;
  name: string;
  input: unknown;
  status: 'pending' | 'approved' | 'denied' | 'expired' | 'stopped';
}

export interface LiveRun {
  jobId: string;
  /** thinking: waiting on the model; working: running a tool. */
  phase: 'starting' | 'thinking' | 'working';
  /** Text of the reply being written (until its message is saved). */
  text: string;
  thinking: string;
  /** A tool the model is writing a call for. */
  pendingTool: string | null;
}

export interface ChatState {
  chat: api.AgentChat;
  messages: api.AgentMessage[];
  canSend: boolean;
  run: LiveRun | null;
  tools: Record<string, LiveTool>;
  approvals: Record<string, LiveApproval>;
  /** A message being sent (shown at once, before the server echoes it). */
  sending: string | null;
  error: string | null;
}

interface AgentStore {
  status: api.AgentStatus | null;
  chats: api.AgentChat[] | null;
  byId: Record<string, ChatState>;
  setStatus: (status: api.AgentStatus | null) => void;
  setChats: (chats: api.AgentChat[]) => void;
  upsertChat: (chat: api.AgentChat) => void;
  removeChat: (chatId: string) => void;
  setDetail: (detail: api.AgentChatDetail) => void;
  patchChat: (chatId: string, fn: (c: ChatState) => Partial<ChatState>) => void;
  addMessage: (chatId: string, message: api.AgentMessage) => void;
}

export const useAgentStore = create<AgentStore>()((set) => ({
  status: null,
  chats: null,
  byId: {},
  setStatus: (status) => set({ status }),
  setChats: (chats) => set({ chats }),
  upsertChat: (chat) =>
    set((s) => {
      const chats = s.chats ? [chat, ...s.chats.filter((c) => c.id !== chat.id)] : [chat];
      const cur = s.byId[chat.id];
      return { chats, byId: cur ? { ...s.byId, [chat.id]: { ...cur, chat } } : s.byId };
    }),
  removeChat: (chatId) =>
    set((s) => {
      const byId = { ...s.byId };
      delete byId[chatId];
      return { chats: s.chats?.filter((c) => c.id !== chatId) ?? null, byId };
    }),
  setDetail: (detail) =>
    set((s) => {
      const cur = s.byId[detail.id];
      const { messages, pending_approvals, can_send, ...chat } = detail;
      const approvals: Record<string, LiveApproval> = { ...(cur?.approvals ?? {}) };
      for (const p of pending_approvals ?? []) {
        approvals[p.call_id] = { callId: p.call_id, name: p.name, input: p.input, status: 'pending' };
      }
      const next: ChatState = {
        chat,
        messages,
        canSend: can_send,
        run: cur?.run && chat.active_job_id === cur.run.jobId ? cur.run : null,
        tools: cur?.tools ?? {},
        approvals,
        sending: null,
        error: null,
      };
      // Keep the chat list's entry in step (title, running state).
      const chats = s.chats?.map((c) => (c.id === chat.id ? chat : c)) ?? s.chats;
      return { byId: { ...s.byId, [detail.id]: next }, chats };
    }),
  patchChat: (chatId, fn) =>
    set((s) => {
      const cur = s.byId[chatId];
      if (!cur) return {};
      return { byId: { ...s.byId, [chatId]: { ...cur, ...fn(cur) } } };
    }),
  addMessage: (chatId, message) =>
    set((s) => {
      const cur = s.byId[chatId];
      if (!cur || cur.messages.some((m) => m.seq === message.seq)) return {};
      const messages = [...cur.messages, message].sort((a, b) => a.seq - b.seq);
      return { byId: { ...s.byId, [chatId]: { ...cur, messages } } };
    }),
}));

type Result = { text: string; is_error: boolean };

/** The saved results of each assistant turn's tool calls, by the turn's seq: a
 *  tool row answers the assistant turn just before it (ids alone may repeat
 *  across turns with some model servers). */
export function resultsByTurn(messages: api.AgentMessage[]): Map<number, Map<string, Result>> {
  const out = new Map<number, Map<string, Result>>();
  let turn: number | null = null;
  for (const m of messages) {
    if (m.role === 'assistant') turn = m.seq;
    if (m.role !== 'tool' || turn === null) continue;
    const results = (m.content.results as { tool_call_id: string; text?: string; is_error?: boolean }[] | undefined) ?? [];
    const map = out.get(turn) ?? new Map<string, Result>();
    for (const r of results) map.set(r.tool_call_id, { text: r.text ?? '', is_error: !!r.is_error });
    out.set(turn, map);
  }
  return out;
}
