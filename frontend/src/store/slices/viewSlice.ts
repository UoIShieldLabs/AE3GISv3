import type { SliceCreator, ViewSlice } from '../types';

export const createViewSlice: SliceCreator<ViewSlice> = (set) => ({
  theme: 'system',
  tool: 'select',
  snapToGrid: true,
  showMinimap: true,
  layoutMode: 'tree',
  sidebarTab: 'palette',
  sidebarOpen: true,
  inspectorOpen: true,
  expanded: {},
  selection: { nodeIds: [], edgeIds: [] },
  zoom: 1,
  purdueOpen: false,
  commandPaletteOpen: false,
  imagesOpen: false,
  imagesFocus: null,
  collapsedCategories: [],
  jobDetailsOpen: false,
  captureDialog: null,
  runsOpen: false,

  setZoom: (zoom) => set((s) => { if (Math.abs(s.zoom - zoom) > 0.004) s.zoom = zoom; }, false, 'setZoom'),
  setPurdueOpen: (purdueOpen) => set({ purdueOpen }, false, 'setPurdueOpen'),
  setCommandPaletteOpen: (commandPaletteOpen) => set({ commandPaletteOpen }, false, 'setCommandPaletteOpen'),
  openImages: (imagesFocus = null) => set({ imagesOpen: true, imagesFocus }, false, 'openImages'),
  setImagesOpen: (imagesOpen) => set((s) => { s.imagesOpen = imagesOpen; if (!imagesOpen) s.imagesFocus = null; }, false, 'setImagesOpen'),
  setJobDetailsOpen: (jobDetailsOpen) => set({ jobDetailsOpen }, false, 'setJobDetailsOpen'),
  openCaptureDialog: (captureDialog) => set({ captureDialog }, false, 'openCaptureDialog'),
  closeCaptureDialog: () => set({ captureDialog: null }, false, 'closeCaptureDialog'),
  setRunsOpen: (runsOpen) => set({ runsOpen }, false, 'setRunsOpen'),
  toggleCategory: (id) =>
    set((s) => {
      s.collapsedCategories = s.collapsedCategories.includes(id)
        ? s.collapsedCategories.filter((c) => c !== id)
        : [...s.collapsedCategories, id];
    }, false, 'toggleCategory'),

  setTheme: (theme) => set({ theme }, false, 'setTheme'),
  setTool: (tool) => set({ tool }, false, 'setTool'),
  setSnapToGrid: (snapToGrid) => set({ snapToGrid }, false, 'setSnapToGrid'),
  setShowMinimap: (showMinimap) => set({ showMinimap }, false, 'setShowMinimap'),
  setLayoutMode: (layoutMode) => set({ layoutMode }, false, 'setLayoutMode'),
  setSidebarTab: (sidebarTab) => set({ sidebarTab, sidebarOpen: true }, false, 'setSidebarTab'),
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }, false, 'setSidebarOpen'),
  setInspectorOpen: (inspectorOpen) => set({ inspectorOpen }, false, 'setInspectorOpen'),

  toggleExpanded: (id) =>
    set((s) => {
      if (s.expanded[id]) delete s.expanded[id];
      else s.expanded[id] = true;
    }, false, 'toggleExpanded'),
  setExpanded: (ids, expanded) =>
    set((s) => {
      for (const id of ids) {
        if (expanded) s.expanded[id] = true;
        else delete s.expanded[id];
      }
    }, false, 'setExpanded'),
  collapseAll: () => set({ expanded: {} }, false, 'collapseAll'),

  setSelection: (selection) =>
    set((s) => {
      const same =
        s.selection.nodeIds.length === selection.nodeIds.length &&
        s.selection.edgeIds.length === selection.edgeIds.length &&
        s.selection.nodeIds.every((id, i) => id === selection.nodeIds[i]) &&
        s.selection.edgeIds.every((id, i) => id === selection.edgeIds[i]);
      if (!same) s.selection = selection;
    }, false, 'setSelection'),
  selectNodes: (ids) => set({ selection: { nodeIds: ids, edgeIds: [] } }, false, 'selectNodes'),
  clearSelection: () =>
    set((s) => {
      if (s.selection.nodeIds.length || s.selection.edgeIds.length) s.selection = { nodeIds: [], edgeIds: [] };
    }, false, 'clearSelection'),
});
