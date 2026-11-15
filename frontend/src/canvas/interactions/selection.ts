// The canvas has one source of truth for what is selected: the store. React
// Flow's select changes are folded into it here, and the projection derives
// every node's and edge's `selected` flag from it. Applying those changes to the
// local nodes/edges as well made two writers that undid each other: a marquee
// selects a node and its links in one gesture, the store caught up one render
// late, and the two flipped the link's selection back and forth until React
// gave up ("Maximum update depth exceeded").
//
// The store can also hold ids the canvas doesn't show: the subnet you
// double-clicked to open, a device whose group was collapsed, a node picked
// from the Issues list. React Flow only deselects what it draws, so a click
// on a device kept those alongside it ("2 selected", no device inspector).
// A select change always comes from a gesture on the canvas, so its result
// keeps only what the canvas shows.
import type { Selection } from '@/store/types';

export interface SelectChange {
  id: string;
  selected: boolean;
}

/** What the canvas draws right now (React Flow's node and edge lookups fit). */
export interface OnCanvas {
  nodes: { has(id: string): boolean };
  edges: { has(id: string): boolean };
}

/**
 * `selection` with React Flow's select changes for nodes or edges applied
 * (order kept). With `onCanvas`, ids the canvas doesn't draw are dropped.
 */
export function applySelectChanges(selection: Selection, kind: 'nodeIds' | 'edgeIds', changes: readonly SelectChange[], onCanvas?: OnCanvas): Selection {
  const ids = new Set(selection[kind]);
  for (const c of changes) {
    if (c.selected) ids.add(c.id);
    else ids.delete(c.id);
  }
  const next = { ...selection, [kind]: [...ids] };
  if (!onCanvas) return next;
  return {
    nodeIds: next.nodeIds.filter((id) => onCanvas.nodes.has(id)),
    edgeIds: next.edgeIds.filter((id) => onCanvas.edges.has(id)),
  };
}
