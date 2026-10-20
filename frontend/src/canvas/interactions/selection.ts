// The canvas has one source of truth for what is selected: the store. React
// Flow's select changes are folded into it here, and the projection derives
// every node's and edge's `selected` flag from it. Applying those changes to the
// local nodes/edges as well made two writers that undid each other: a marquee
// selects a node and its links in one gesture, the store caught up one render
// late, and the two flipped the link's selection back and forth until React
// gave up ("Maximum update depth exceeded").
import type { Selection } from '@/store/types';

export interface SelectChange {
  id: string;
  selected: boolean;
}

/** `selection` with React Flow's select changes for nodes or edges applied (order kept). */
export function applySelectChanges(selection: Selection, kind: 'nodeIds' | 'edgeIds', changes: readonly SelectChange[]): Selection {
  const ids = new Set(selection[kind]);
  for (const c of changes) {
    if (c.selected) ids.add(c.id);
    else ids.delete(c.id);
  }
  return { ...selection, [kind]: [...ids] };
}
