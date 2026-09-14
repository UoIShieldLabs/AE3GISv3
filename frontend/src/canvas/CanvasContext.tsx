import { createContext, useContext } from 'react';
import type { Container } from '@/types/topology';

/** Actions node/edge components can trigger; provided by the editor around the canvas. */
export interface CanvasActions {
  /** Navigate into a site or subnet. */
  drillInto: (id: string) => void;
  openTerminal: (container: Container) => void;
  toggleExpand: (id: string) => void;
  duplicate: (ids: string[]) => void;
  remove: (ids: string[]) => void;
  /** Select an entity and reveal it in the inspector. */
  inspect: (id: string) => void;
  canOpenTerminal: boolean;
  readOnly: boolean;
}

export const CanvasActionsContext = createContext<CanvasActions | null>(null);

export function useCanvasActions(): CanvasActions {
  const ctx = useContext(CanvasActionsContext);
  if (!ctx) throw new Error('useCanvasActions must be used inside TopologyCanvas');
  return ctx;
}
