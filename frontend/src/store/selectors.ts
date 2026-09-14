import { useStore } from 'zustand';
import { useShallow } from 'zustand/react/shallow';
import { useAppStore } from './index';
import type { AppState } from './types';
import { locate, locateConnection, type Located, type LocatedConnection } from '@/lib/topology';

export const useTopology = () => useAppStore((s) => s.topology);
export const useDirty = () => useAppStore((s) => s.dirty);
export const useSelection = () => useAppStore((s) => s.selection);
export const useDeployStatus = () => useAppStore((s) => s.deployStatus);
export const useContainerStatus = () => useAppStore((s) => s.containerStatus);
export const useExpanded = () => useAppStore((s) => s.expanded);

export function useEntity(id: string | null | undefined): Located | null {
  return useAppStore(useShallow((s) => (id ? locate(s.topology, id) : null)));
}

export function useConnection(id: string | null | undefined): LocatedConnection | null {
  return useAppStore(useShallow((s) => (id ? locateConnection(s.topology, id) : null)));
}

/** Multiple store fields at once without re-rendering on unrelated changes. */
export function useAppShallow<T>(selector: (s: AppState) => T): T {
  return useAppStore(useShallow(selector));
}

export function useUndoState(): { canUndo: boolean; canRedo: boolean } {
  return useStore(
    useAppStore.temporal,
    useShallow((s) => ({ canUndo: s.pastStates.length > 0, canRedo: s.futureStates.length > 0 })),
  );
}
