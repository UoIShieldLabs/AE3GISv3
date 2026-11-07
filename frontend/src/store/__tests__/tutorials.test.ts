import { beforeEach, describe, expect, it } from 'vitest';
import { clearHistory, redo, undo, useAppStore } from '../index';
import type { TopologyData, TutorialCommandCell } from '@/types/topology';
import { isTutorialUnsaved, nextCell, progressOf } from '@/features/tutorials/model';

const S = () => useAppStore.getState();
const tutorials = () => (S().topology as TopologyData).tutorials ?? [];

function hostIn(): string {
  const siteId = S().addSite({ name: 'S1' });
  const subnetId = S().addSubnet({ siteId, name: 'LAN', cidr: '10.0.1.0/24' })!;
  return S().addContainer({ subnetId, type: 'workstation', name: 'attacker' })!;
}

beforeEach(() => {
  S().newTopology('Test');
  S().resetTutorialSession();
  clearHistory();
});

describe('tutorial authoring (topology slice)', () => {
  it('adds tutorials and cells, dirty and undoable', () => {
    const id = S().addTutorial();
    expect(tutorials()[0]).toMatchObject({ id, title: 'Tutorial 1', cells: [] });
    expect(S().dirty).toBe(true);
    const note = S().addTutorialCell(id, 'markdown', undefined, { source: '# Recon', command: 'ignored' })!;
    const cmd = S().addTutorialCell(id, 'command', undefined, { containerId: 'h1', command: 'nmap -sn 10.0.5.0/24' })!;
    const first = S().addTutorialCell(id, 'command', 0)!;
    expect(tutorials()[0].cells.map((c) => c.id)).toEqual([first, note, cmd]);
    expect(tutorials()[0].cells[1]).toEqual({ id: note, kind: 'markdown', source: '# Recon' });
    expect(tutorials()[0].cells[0]).toMatchObject({ kind: 'command', containerId: '', command: '' });
    undo();
    expect(tutorials()[0].cells.map((c) => c.id)).toEqual([note, cmd]);
    redo();
    expect(tutorials()[0].cells).toHaveLength(3);
  });

  it('updates only the fields a cell kind has', () => {
    const id = S().addTutorial('SSH lab');
    const note = S().addTutorialCell(id, 'markdown')!;
    const cmd = S().addTutorialCell(id, 'command')!;
    S().updateTutorialCell(id, note, { source: 'hello', command: 'nope' });
    S().updateTutorialCell(id, cmd, { containerId: 'h2', command: 'ls', source: 'nope' });
    expect(tutorials()[0].cells).toEqual([
      { id: note, kind: 'markdown', source: 'hello' },
      { id: cmd, kind: 'command', containerId: 'h2', command: 'ls' },
    ]);
  });

  it('moves, removes, renames, duplicates and deletes', () => {
    const id = S().addTutorial('A');
    const a = S().addTutorialCell(id, 'markdown')!;
    const b = S().addTutorialCell(id, 'command')!;
    S().moveTutorialCell(id, 0, 1);
    expect(tutorials()[0].cells.map((c) => c.id)).toEqual([b, a]);
    S().moveTutorialCell(id, 0, 5); // out of range: ignored
    S().removeTutorialCell(id, a);
    expect(tutorials()[0].cells.map((c) => c.id)).toEqual([b]);
    S().updateTutorial(id, { title: 'Renamed' });
    const other = S().addTutorial('B');
    const copy = S().duplicateTutorial(id)!;
    expect(tutorials().map((t) => t.title)).toEqual(['Renamed', 'Renamed (copy)', 'B']);
    expect(tutorials()[1].id).toBe(copy);
    expect(tutorials()[1].cells[0].id).not.toBe(b);
    S().removeTutorial(other);
    expect(tutorials().map((t) => t.id)).toEqual([id, copy]);
  });

  it('keeps cells whose node was deleted, and unknown fields round-trip', () => {
    const node = hostIn();
    const id = S().addTutorial();
    S().addTutorialCell(id, 'command', undefined, { containerId: node, command: 'id' });
    S().deleteNodes([node]);
    expect((tutorials()[0].cells[0] as TutorialCommandCell).containerId).toBe(node);

    S().loadTopology({
      sites: [], siteConnections: [],
      tutorials: [{ id: 't1', title: 'Old', extra: 1, cells: [{ id: 'c1', kind: 'command', containerId: 'x', command: 'ls', wait: 'prompt' }] }],
    });
    S().updateTutorialCell('t1', 'c1', { command: 'ls -la' });
    expect(tutorials()[0]).toMatchObject({ extra: 1, cells: [{ wait: 'prompt', command: 'ls -la' }] });
  });
});

describe('tutorial UI (tutorial slice)', () => {
  it('opens tabs, closes to the neighbour, then to the list', () => {
    S().openTutorial('t1');
    S().openTutorial('t2', { edit: true });
    S().openTutorial('t1');
    expect(S().openTutorialIds).toEqual(['t1', 't2']);
    expect(S().activeTutorialId).toBe('t1');
    expect(S().tutorialsOpen).toBe(true);
    expect(S().editingTutorials).toEqual({ t2: true });
    S().closeTutorial('t1');
    expect(S().activeTutorialId).toBe('t2');
    S().closeTutorial('t2');
    expect(S().activeTutorialId).toBeNull();
    expect(S().editingTutorials).toEqual({});
  });

  it('tracks runs per tutorial and resets them', () => {
    S().markCellRun('t1', 'c1', 10);
    S().markCellRun('t1', 'c2', 20);
    expect(S().tutorialProgress).toEqual({ t1: { c1: 10, c2: 20 } });
    S().resetTutorialProgress('t1');
    expect(S().tutorialProgress).toEqual({});
    S().openTutorial('t1');
    S().markCellRun('t1', 'c1');
    S().resetTutorialSession();
    expect(S()).toMatchObject({ openTutorialIds: [], activeTutorialId: null, tutorialProgress: {} });
  });

  it('runs are not part of the design: no dirty, no undo step', () => {
    S().markCellRun('t1', 'c1');
    expect(S().dirty).toBe(false);
    expect(useAppStore.temporal.getState().pastStates).toHaveLength(0);
  });
});

describe('tutorial model', () => {
  it('counts progress and finds the next step after the latest run', () => {
    const id = S().addTutorial();
    S().addTutorialCell(id, 'markdown');
    const c1 = S().addTutorialCell(id, 'command')!;
    const c2 = S().addTutorialCell(id, 'command')!;
    const c3 = S().addTutorialCell(id, 'command')!;
    const t = tutorials()[0];
    expect(progressOf(t, undefined)).toEqual({ run: 0, total: 3 });
    expect(nextCell(t, undefined)?.id).toBe(c1);
    expect(nextCell(t, { [c2]: 5 })?.id).toBe(c3);
    // Re-running an earlier step moves "next" back after it.
    expect(nextCell(t, { [c1]: 9, [c2]: 5 })?.id).toBe(c2);
    expect(nextCell(t, { [c3]: 1 })).toBeNull();
    expect(progressOf(t, { [c1]: 1, [c3]: 2, gone: 3 })).toEqual({ run: 2, total: 3 });
  });

  it('tells which tutorials changed since the last save', () => {
    const a = S().addTutorial('A');
    const b = S().addTutorial('B');
    S().markClean();
    expect(isTutorialUnsaved(a, S().topology, S().savedTopology)).toBe(false);
    S().addTutorialCell(a, 'markdown');
    expect(isTutorialUnsaved(a, S().topology, S().savedTopology)).toBe(true);
    expect(isTutorialUnsaved(b, S().topology, S().savedTopology)).toBe(false);
    undo();
    expect(isTutorialUnsaved(a, S().topology, S().savedTopology)).toBe(false);
    const c = S().addTutorial('C');
    expect(isTutorialUnsaved(c, S().topology, S().savedTopology)).toBe(true);
    expect(isTutorialUnsaved(c, S().topology, null)).toBe(true);
  });
});
