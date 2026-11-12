// Tutorial actions: plain functions over the store, callable from the panel,
// the top bar and ⌘K. Running a command types it into the node's normal
// terminal (its dock tab), so later steps run inside whatever earlier ones
// started — an ssh, a python REPL, a root shell.
import { useAppStore } from '@/store';
import { terminalTabId } from '@/store/slices/dockSlice';
import { locate } from '@/lib/topology';
import type { TopologyData } from '@/types/topology';
import { toast } from '@/ui';
import { nextCell } from './model';

/** Show the Tutorials section of the right column. */
export function openTutorialsPanel(): void {
  useAppStore.getState().setTutorialsOpen(true);
}

/** Add a tutorial and open it, ready to write. */
export function createTutorial(): string {
  const st = useAppStore.getState();
  const id = st.addTutorial();
  st.openTutorial(id, { edit: true });
  return id;
}

/** Why a command can't run right now, or null when it can. */
export function runBlocker(): string | null {
  const { deployStatus, backendId } = useAppStore.getState();
  return deployStatus === 'deployed' && backendId ? null : 'Deploy the topology to run steps';
}

/** Type a command cell into its node's terminal and press Enter. Resolves
 *  true once sent (it does not wait for the command to finish). */
export async function runTutorialCell(tutorialId: string, cellId: string): Promise<boolean> {
  const st = useAppStore.getState();
  const cell = (st.topology as TopologyData).tutorials?.find((t) => t.id === tutorialId)?.cells.find((c) => c.id === cellId);
  if (cell?.kind !== 'command' || !cell.command.trim()) return false;
  const blocked = runBlocker();
  if (blocked) {
    toast.error(blocked);
    return false;
  }
  const hit = locate(st.topology, cell.containerId);
  if (hit?.kind !== 'container') {
    toast.error('This step’s node no longer exists', { description: 'Edit the tutorial to pick another node.' });
    return false;
  }
  const node = hit.container;
  st.openTerminal(node);
  // xterm loads with the first terminal, not with the editor.
  const { acquireSession } = await import('@/features/terminal/sessions');
  const session = acquireSession(terminalTabId(node.id), node.id);
  const sent = (await session.whenReady())
    ? session.runTracked(cell.command, (end) => {
        // Back at the prompt (or the shell closed, and with it our view of the run).
        const key = `${tutorialId}:${cellId}`;
        const stopped = stopping.delete(key);
        useAppStore.getState().setCellStatus(tutorialId, cellId, end ? { state: 'done', exit: end.exit, ...(stopped ? { stopped } : {}) } : { state: 'sent' });
      })
    : 'offline';
  if (sent === 'offline') {
    toast.error(`Couldn't reach ${node.name}'s shell`, { description: 'Check the terminal tab for details.' });
    return false;
  }
  const after = useAppStore.getState();
  after.markCellRun(tutorialId, cellId);
  after.setCellStatus(tutorialId, cellId, { state: sent === 'tracked' ? 'running' : 'sent' });
  return true;
}

/** Cells whose Stop was pressed and whose run hasn't ended yet. */
const stopping = new Set<string>();

/** Press Ctrl-C in the terminal a running cell was typed into. */
export async function stopTutorialCell(tutorialId: string, cellId: string): Promise<boolean> {
  const st = useAppStore.getState();
  const cell = (st.topology as TopologyData).tutorials?.find((t) => t.id === tutorialId)?.cells.find((c) => c.id === cellId);
  if (cell?.kind !== 'command') return false;
  const { getSession } = await import('@/features/terminal/sessions');
  const sent = getSession(terminalTabId(cell.containerId))?.interrupt() ?? false;
  if (sent) stopping.add(`${tutorialId}:${cellId}`);
  return sent;
}

/** Run the step after the one run last (the first, if none has). */
export async function runNextStep(tutorialId: string): Promise<boolean> {
  const st = useAppStore.getState();
  const tutorial = (st.topology as TopologyData).tutorials?.find((t) => t.id === tutorialId);
  const next = tutorial ? nextCell(tutorial, st.tutorialProgress[tutorialId]) : null;
  return next ? runTutorialCell(tutorialId, next.id) : false;
}
