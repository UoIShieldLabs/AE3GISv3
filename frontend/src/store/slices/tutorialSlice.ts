import type { SliceCreator, TutorialSlice } from '../types';

/** Tutorials UI: open tabs and per-session run progress (the tutorials themselves live in the topology). */
export const createTutorialSlice: SliceCreator<TutorialSlice> = (set) => ({
  tutorialsOpen: false,
  openTutorialIds: [],
  activeTutorialId: null,
  editingTutorials: {},
  tutorialProgress: {},
  cellStatus: {},
  busyTerminals: {},

  setTutorialsOpen: (tutorialsOpen) => set({ tutorialsOpen }, false, 'setTutorialsOpen'),

  openTutorial: (tutorialId, options) =>
    set((s) => {
      if (!s.openTutorialIds.includes(tutorialId)) s.openTutorialIds.push(tutorialId);
      s.activeTutorialId = tutorialId;
      s.tutorialsOpen = true;
      if (options?.edit) s.editingTutorials[tutorialId] = true;
    }, false, 'openTutorial'),

  closeTutorial: (tutorialId) =>
    set((s) => {
      const at = s.openTutorialIds.indexOf(tutorialId);
      if (at === -1) return;
      s.openTutorialIds.splice(at, 1);
      delete s.editingTutorials[tutorialId];
      // Closing the shown tab shows its neighbour (the one before, else after), or the list.
      if (s.activeTutorialId === tutorialId) s.activeTutorialId = s.openTutorialIds[Math.max(0, at - 1)] ?? null;
    }, false, 'closeTutorial'),

  setActiveTutorial: (activeTutorialId) => set({ activeTutorialId }, false, 'setActiveTutorial'),

  setTutorialEditing: (tutorialId, editing) =>
    set((s) => {
      if (editing) s.editingTutorials[tutorialId] = true;
      else delete s.editingTutorials[tutorialId];
    }, false, 'setTutorialEditing'),

  markCellRun: (tutorialId, cellId, at = Date.now()) =>
    set((s) => {
      (s.tutorialProgress[tutorialId] ??= {})[cellId] = at;
    }, false, 'markCellRun'),

  setCellStatus: (tutorialId, cellId, status) =>
    set((s) => {
      (s.cellStatus[tutorialId] ??= {})[cellId] = status;
    }, false, 'setCellStatus'),

  setTerminalBusy: (containerId, busy) =>
    set((s) => {
      if (busy) s.busyTerminals[containerId] = true;
      else delete s.busyTerminals[containerId];
    }, false, 'setTerminalBusy'),

  resetTutorialProgress: (tutorialId) =>
    set((s) => {
      delete s.tutorialProgress[tutorialId];
      delete s.cellStatus[tutorialId];
    }, false, 'resetTutorialProgress'),

  // `busyTerminals` follows the terminal sessions, which outlive this reset.
  resetTutorialSession: () =>
    set({ openTutorialIds: [], activeTutorialId: null, editingTutorials: {}, tutorialProgress: {}, cellStatus: {} }, false, 'resetTutorialSession'),
});
