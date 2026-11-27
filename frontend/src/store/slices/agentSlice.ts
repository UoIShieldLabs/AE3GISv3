import type { AgentSlice, SliceCreator } from '../types';

export const createAgentSlice: SliceCreator<AgentSlice> = (set) => ({
  agentOpen: false,
  agentChatId: null,
  agentListing: false,
  agentListScope: 'all',
  agentLock: null,

  setAgentOpen: (open) => set({ agentOpen: open }, false, 'setAgentOpen'),
  toggleAgent: () => set((s) => { s.agentOpen = !s.agentOpen; }, false, 'toggleAgent'),
  openAgentChat: (chatId) => set({ agentChatId: chatId, agentOpen: true, agentListing: false }, false, 'openAgentChat'),
  setAgentListing: (listing) => set({ agentListing: listing }, false, 'setAgentListing'),
  setAgentListScope: (scope) => set({ agentListScope: scope }, false, 'setAgentListScope'),
  openOwnerChats: () => set({ agentOpen: true, agentListing: true, agentListScope: 'owner' }, false, 'openOwnerChats'),
  setAgentLock: (lock) => set({ agentLock: lock }, false, 'setAgentLock'),
});
