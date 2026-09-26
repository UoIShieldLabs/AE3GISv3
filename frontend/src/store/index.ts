import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { temporal } from 'zundo';
import type { AppState } from './types';
import { createTopologySlice } from './slices/topologySlice';
import { createDocumentSlice } from './slices/documentSlice';
import { createViewSlice } from './slices/viewSlice';
import { createDockSlice } from './slices/dockSlice';
import { createActivitySlice } from './slices/activitySlice';
import { createCatalogSlice } from './slices/catalogSlice';
import { createImagesSlice } from './slices/imagesSlice';

export type { AppState } from './types';
export * from './types';

/** Slice of state tracked by undo/redo. */
type Tracked = Pick<AppState, 'topology'>;

export const useAppStore = create<AppState>()(
  devtools(
    persist(
      temporal(
        immer((...a) => ({
          ...createTopologySlice(...a),
          ...createDocumentSlice(...a),
          ...createViewSlice(...a),
          ...createDockSlice(...a),
          ...createActivitySlice(...a),
          ...createCatalogSlice(...a),
          ...createImagesSlice(...a),
        })),
        {
          partialize: (s): Tracked => ({ topology: s.topology }),
          equality: (a, b) => a.topology === b.topology,
          limit: 100,
        },
      ),
      {
        name: 'ae3gis.ui',
        version: 1,
        partialize: (s) => ({
          theme: s.theme,
          snapToGrid: s.snapToGrid,
          showMinimap: s.showMinimap,
          layoutMode: s.layoutMode,
          sidebarTab: s.sidebarTab,
          sidebarOpen: s.sidebarOpen,
          inspectorOpen: s.inspectorOpen,
          collapsedCategories: s.collapsedCategories,
        }),
      },
    ),
    { name: 'ae3gis', enabled: import.meta.env.DEV },
  ),
);

// Loading or creating a topology starts a fresh history: wrap the slice
// actions so the swap itself is never an undo step.
{
  const base = useAppStore.getState();
  const fresh = <A extends unknown[]>(fn: (...args: A) => void) => (...args: A) => {
    const t = useAppStore.temporal.getState();
    t.pause();
    fn(...args);
    t.resume();
    t.clear();
  };
  useAppStore.setState({ loadTopology: fresh(base.loadTopology), newTopology: fresh(base.newTopology) });
}

/** Undo/redo entry points; recompute `dirty` against the last saved snapshot. */
function afterTimeTravel() {
  const s = useAppStore.getState();
  useAppStore.setState({ dirty: s.topology !== s.savedTopology });
}

export function undo(steps = 1) {
  useAppStore.temporal.getState().undo(steps);
  afterTimeTravel();
}

export function redo(steps = 1) {
  useAppStore.temporal.getState().redo(steps);
  afterTimeTravel();
}

/** Drop history (e.g. when a different topology is loaded). */
export function clearHistory() {
  useAppStore.temporal.getState().clear();
}
