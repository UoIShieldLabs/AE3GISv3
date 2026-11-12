// One colour per node a tutorial uses, shared by its cells in the notebook and
// its card on the canvas. Taken from the theme's chart palette, in order of
// first use, so a tutorial keeps its colours as long as its steps keep their order.
import type { Tutorial } from '@/types/topology';

const PALETTE_SIZE = 6; // --chart-1 … --chart-6, defined by every theme

/** The nodes a tutorial names, in order of first use. */
export function tutorialNodeIds(tutorial: Tutorial): string[] {
  const ids: string[] = [];
  const add = (id: string | undefined) => { if (id && !ids.includes(id)) ids.push(id); };
  for (const step of tutorial.setup?.steps ?? []) add(step.containerId);
  for (const row of tutorial.setup?.traffic ?? []) {
    for (const id of row.from ?? []) add(id);
    for (const id of row.to ?? []) add(id);
  }
  for (const cell of tutorial.cells ?? []) if (cell.kind === 'command') add(cell.containerId);
  return ids;
}

/** Node id → its colour in this tutorial (a CSS value). Cycles past six nodes. */
export function nodeColors(tutorial: Tutorial | null | undefined): Map<string, string> {
  const colors = new Map<string, string>();
  if (!tutorial) return colors;
  tutorialNodeIds(tutorial).forEach((id, i) => colors.set(id, `var(--chart-${(i % PALETTE_SIZE) + 1})`));
  return colors;
}
