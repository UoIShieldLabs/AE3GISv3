import type { SliceCreator, TerminalSlice } from '../types';

export const createTerminalSlice: SliceCreator<TerminalSlice> = (set) => ({
  terminals: [],
  activeTerminalId: null,
  terminalMinimized: false,

  openTerminal: (c) =>
    set((s) => {
      if (!s.terminals.some((t) => t.id === c.id)) s.terminals.push({ id: c.id, name: c.name, ip: c.ip });
      s.activeTerminalId = c.id;
      s.terminalMinimized = false;
    }, false, 'openTerminal'),

  closeTerminal: (id) =>
    set((s) => {
      s.terminals = s.terminals.filter((t) => t.id !== id);
      if (s.activeTerminalId === id) s.activeTerminalId = s.terminals.length ? s.terminals[s.terminals.length - 1].id : null;
    }, false, 'closeTerminal'),

  setActiveTerminal: (id) => set({ activeTerminalId: id, terminalMinimized: false }, false, 'setActiveTerminal'),
  setTerminalMinimized: (terminalMinimized) => set({ terminalMinimized }, false, 'setTerminalMinimized'),
});
