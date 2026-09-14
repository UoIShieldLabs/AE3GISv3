import { createContext, useContext } from 'react';
import type { Position } from '@/types/topology';
import type { Scope } from '@/lib/topology';
import type { PaletteItem } from '@/canvas/interactions/dnd';

/** Where a new entity should land. Ids narrow the container; `at` is a stored-space position. */
export interface AddTarget {
  siteId?: string;
  subnetId?: string;
  at?: Position;
}

export interface AddEntityApi {
  /** Open the right dialog (or add immediately for devices dropped from the palette). */
  requestAdd: (item: PaletteItem, target: AddTarget, opts?: { immediate?: boolean }) => void;
  requestBulkDevices: (subnetId: string) => void;
  requestBulkConnections: (scope: Scope) => void;
}

export const AddEntityContext = createContext<AddEntityApi | null>(null);

export function useAddEntity(): AddEntityApi {
  const ctx = useContext(AddEntityContext);
  if (!ctx) throw new Error('useAddEntity must be used inside AddEntityProvider');
  return ctx;
}
