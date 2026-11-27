import type { AgentSlice, SliceCreator } from '../types';

export const createAgentSlice: SliceCreator<AgentSlice> = (set) => ({
  agentOpen: false,
  agentChatId: null,
  agentLock: null,

  setAgentOpen: (open) => set({ agentOpen: open }, false, 'setAgentOpen'),
  toggleAgent: () => set((s) => { s.agentOpen = !s.agentOpen; }, false, 'toggleAgent'),
  openAgentChat: (chatId) => set({ agentChatId: chatId, agentOpen: true }, false, 'openAgentChat'),
  setAgentLock: (lock) => set({ agentLock: lock }, false, 'setAgentLock'),
});
