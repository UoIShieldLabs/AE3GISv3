// Pure helpers over a tutorial and its per-session progress.
import type { TopologyData, Tutorial, TutorialCommandCell } from '@/types/topology';

export type TutorialRuns = Record<string, number>;

export function commandCells(tutorial: Tutorial): TutorialCommandCell[] {
  return (tutorial.cells ?? []).filter((c): c is TutorialCommandCell => c.kind === 'command');
}

/** Commands run vs commands in the tutorial (cells deleted since don't count). */
export function progressOf(tutorial: Tutorial, runs: TutorialRuns | undefined): { run: number; total: number } {
  const cells = commandCells(tutorial);
  return { run: runs ? cells.filter((c) => runs[c.id] !== undefined).length : 0, total: cells.length };
}

/** The step "Next" runs: the command after the one run most recently, or the
 *  first command when none has run. Null once the last one has run. */
export function nextCell(tutorial: Tutorial, runs: TutorialRuns | undefined): TutorialCommandCell | null {
  const cells = commandCells(tutorial);
  let latest = -1;
  let latestAt = -Infinity;
  cells.forEach((c, i) => {
    const at = runs?.[c.id];
    if (at !== undefined && at >= latestAt) { latest = i; latestAt = at; }
  });
  return cells[latest + 1] ?? null;
}

/** Whether a tutorial differs from the last save. Edits copy only what they
 *  touch (immer), so an unchanged tutorial is the very object that was saved. */
export function isTutorialUnsaved(tutorialId: string, topology: TopologyData, saved: TopologyData | null): boolean {
  const current = topology.tutorials?.find((t) => t.id === tutorialId);
  if (!saved) return !!current;
  return current !== saved.tutorials?.find((t) => t.id === tutorialId);
}
