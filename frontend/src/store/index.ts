import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { temporal } from 'zundo';
import type { AppState } from './types';
import { createTopologySlice } from './slices/topologySlice';
import { createDocumentSlice } from './slices/documentSlice';
import { createViewSlice } from './slices/viewSlice';
import { createDockSlice } from './slices/dockSlice';
import { createTutorialSlice } from './slices/tutorialSlice';
import { createActivitySlice } from './slices/activitySlice';
import { createPulseSlice } from './slices/pulseSlice';
import { createCatalogSlice } from './slices/catalogSlice';
import { createImagesSlice } from './slices/imagesSlice';
import { createAuthSlice } from './slices/authSlice';
import { createAgentSlice } from './slices/agentSlice';

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
          ...createTutorialSlice(...a),
          ...createPulseSlice(...a),
          ...createActivitySlice(...a),
          ...createCatalogSlice(...a),
          ...createImagesSlice(...a),
          ...createAuthSlice(...a),
          ...createAgentSlice(...a),
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
          iconStyle: s.iconStyle,
          snapToGrid: s.snapToGrid,
          showMinimap: s.showMinimap,
          layoutMode: s.layoutMode,
          sidebarTab: s.sidebarTab,
          sidebarOpen: s.sidebarOpen,
          inspectorOpen: s.inspectorOpen,
          collapsedCategories: s.collapsedCategories,
          libraryLayout: s.libraryLayout,
          librarySort: s.librarySort,
          agentOpen: s.agentOpen,
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

// ── The agent's editor lock ──────────────────────────────────────────
// While an agent run works in the open topology the editor is read-only: every
// topology mutation (and undo/redo) goes through this one guard, so no gesture,
// menu or shortcut can slip an edit in between the agent's. The agent's own
// browser actions (e.g. arrange) run inside `asAgent`.

/** The editor actions that change the topology (everything but load/new/markClean
 *  and the agent's own `applyRemoteTopology`). */
const TOPOLOGY_MUTATIONS = [
  'setTopologyMeta', 'addSite', 'updateSite', 'addSubnet', 'updateSubnet', 'addContainer', 'updateContainer',
  'addInterface', 'updateInterfaceIp', 'removeInterface', 'addConnection', 'updateConnection', 'deleteNodes',
  'deleteConnections', 'deleteItems', 'duplicateNodes', 'moveNodes', 'applyLayout', 'setTrafficFlows',
  'addScenario', 'updateScenario', 'removeScenario', 'addPhase', 'updatePhase', 'removePhase', 'addStep',
  'updateStep', 'removeStep', 'moveStep', 'addTutorial', 'updateTutorial', 'removeTutorial', 'duplicateTutorial',
  'updateTutorialSetup', 'addTutorialCell', 'updateTutorialCell', 'removeTutorialCell', 'moveTutorialCell',
] as const satisfies readonly (keyof AppState)[];

let agentDepth = 0;
let onLockedEdit: (() => void) | null = null;

/** The open topology is being edited by an agent run (the editor is read-only). */
export function editorLocked(s: AppState = useAppStore.getState()): boolean {
  return !!s.agentLock && s.agentLock.topologyId === s.backendId;
}

/** Run `fn` as the agent: past the editor lock. */
export function asAgent<T>(fn: () => T): T {
  agentDepth += 1;
  try {
    return fn();
  } finally {
    agentDepth -= 1;
  }
}

/** What to do when a locked edit is refused (the agent feature shows a toast). */
export function setLockedEditHandler(fn: (() => void) | null) {
  onLockedEdit = fn;
}

function refusedWhileLocked(): boolean {
  if (agentDepth > 0 || !editorLocked()) return false;
  onLockedEdit?.();
  return true;
}

{
  const base = useAppStore.getState();
  const guarded: Partial<AppState> = {};
  for (const name of TOPOLOGY_MUTATIONS) {
    const fn = base[name] as (...args: unknown[]) => unknown;
    (guarded as Record<string, unknown>)[name] = (...args: unknown[]) => (refusedWhileLocked() ? null : fn(...args));
  }
  useAppStore.setState(guarded);
}

/** Undo/redo entry points; recompute `dirty` against the last saved snapshot. */
function afterTimeTravel() {
  const s = useAppStore.getState();
  useAppStore.setState({ dirty: s.topology !== s.savedTopology });
}

export function undo(steps = 1) {
  if (refusedWhileLocked()) return;
  useAppStore.temporal.getState().undo(steps);
  afterTimeTravel();
}

export function redo(steps = 1) {
  if (refusedWhileLocked()) return;
  useAppStore.temporal.getState().redo(steps);
  afterTimeTravel();
}

/** Drop history (e.g. when a different topology is loaded). */
export function clearHistory() {
  useAppStore.temporal.getState().clear();
}
