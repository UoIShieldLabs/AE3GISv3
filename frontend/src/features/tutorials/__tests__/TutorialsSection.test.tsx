import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { clearHistory, useAppStore } from '@/store';
import { applyCatalog } from '@/catalog/catalog';
import { TooltipProvider } from '@/ui';
import { CATALOG } from '@/test/catalogFixture';
import { TutorialsSection } from '../TutorialsSection';

// The terminal is a seam: assert what would be typed into it. `shell` says what
// the fake shell reports back, and holds the last tracked run so a test can end it.
type RunEnd = { exit: number | null } | null;
const typed: { tabId: string; text: string }[] = [];
const shell: { tracking: boolean; end: ((end: RunEnd) => void) | null; interrupts: string[] } = { tracking: false, end: null, interrupts: [] };
vi.mock('@/features/terminal/sessions', () => ({
  acquireSession: (tabId: string) => ({
    whenReady: async () => true,
    runTracked: (text: string, onEnd: (end: RunEnd) => void) => {
      typed.push({ tabId, text });
      if (!shell.tracking) return 'sent';
      shell.end = onEnd;
      return 'tracked';
    },
  }),
  getSession: (tabId: string) => ({ interrupt: () => { shell.interrupts.push(tabId); return true; } }),
}));

// The panel turns the live lab view on; no backend to connect to here.
vi.mock('@/features/pulse/useLabPulse', () => ({ useLabPulse: () => {} }));

const S = () => useAppStore.getState();

/** A topology with an attacker host and a tutorial: a note, two steps on it, one on a deleted node. */
function setup() {
  const siteId = S().addSite({ name: 'S' });
  const sn = S().addSubnet({ siteId, name: 'IT', cidr: '10.0.5.0/24', autoInfra: false })!;
  const attacker = S().addContainer({ subnetId: sn, type: 'workstation', name: 'attacker', ip: '10.0.5.10' })!;
  const gone = S().addContainer({ subnetId: sn, type: 'workstation', name: 'gone' })!;
  const id = S().addTutorial('SSH pivot');
  S().addTutorialCell(id, 'markdown', undefined, { source: '## Find the historian\n\n<script>window.pwned = 1</script>' });
  const c1 = S().addTutorialCell(id, 'command', undefined, { containerId: attacker, command: 'nmap -sn 10.0.5.0/24' })!;
  const c2 = S().addTutorialCell(id, 'command', undefined, { containerId: attacker, command: 'ssh root@10.0.5.20' })!;
  S().addTutorialCell(id, 'command', undefined, { containerId: gone, command: 'id' });
  S().deleteNodes([gone]);
  S().markClean();
  return { id, attacker, c1, c2 };
}

function renderSection(onSave = vi.fn()) {
  render(<TooltipProvider><TutorialsSection onSave={onSave} /></TooltipProvider>);
  return onSave;
}

const deploy = () => act(() => { useAppStore.setState({ deployStatus: 'deployed', backendId: 'topo1' }); });

beforeEach(() => {
  typed.length = 0;
  Object.assign(shell, { tracking: false, end: null, interrupts: [] });
  applyCatalog(CATALOG);
  useAppStore.setState({ catalog: CATALOG, catalogStatus: 'ready', dockTabs: [], activeDockTabId: null });
  S().newTopology('Test');
  S().resetTutorialSession();
  clearHistory();
  useAppStore.setState({ deployStatus: 'idle', dirty: false, backendId: null });
});

describe('TutorialsSection', () => {
  it('lists none, then creates one in edit mode (no render loop)', () => {
    renderSection();
    expect(screen.getByText('No tutorials yet')).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole('button', { name: /New tutorial/ }).at(-1)!);
    expect(screen.getByDisplayValue('Tutorial 1')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Done/ })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /Command/ }).length).toBeGreaterThan(0);
  });

  it('opens a tutorial from the list and renders its notes without raw HTML', () => {
    setup();
    renderSection();
    fireEvent.click(screen.getByRole('button', { name: /SSH pivot/ }));
    expect(screen.getByRole('heading', { name: 'Find the historian' })).toBeInTheDocument();
    expect(document.querySelector('script')).toBeNull();
    expect(screen.getByRole('tab', { name: 'SSH pivot' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText('0 of 3 steps run')).toBeInTheDocument();
    expect(screen.getByText(/Node removed/)).toBeInTheDocument();
  });

  it('gates running on a deployed lab', () => {
    const { id } = setup();
    S().openTutorial(id);
    renderSection();
    expect(screen.getByText('Deploy the topology to run steps.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Next step/ })).toBeDisabled();
    for (const b of screen.getAllByRole('button', { name: /^Run on/ })) expect(b).toBeDisabled();
  });

  it('types steps into the node’s terminal: Next, then a chosen cell', async () => {
    const { id, attacker, c2 } = setup();
    S().openTutorial(id);
    renderSection();
    deploy();
    fireEvent.click(screen.getByRole('button', { name: /Next step/ }));
    await waitFor(() => expect(screen.getByText('1 of 3 steps run')).toBeInTheDocument());
    expect(typed).toEqual([{ tabId: `term:${attacker}`, text: 'nmap -sn 10.0.5.0/24' }]);
    expect(S().dockTabs.map((t) => t.id)).toEqual([`term:${attacker}`]);
    expect(S().tutorialProgress[id][c2]).toBeUndefined();

    fireEvent.click(screen.getAllByRole('button', { name: 'Run on attacker' })[1]);
    await waitFor(() => expect(screen.getByText('2 of 3 steps run')).toBeInTheDocument());
    expect(typed[1].text).toBe('ssh root@10.0.5.20');
    // The step on the deleted node can't run, so "next" stops there.
    expect(screen.getByRole('button', { name: /^Run on node/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Next step/ })).toBeDisabled();
    expect(S().dirty).toBe(false); // running is not an edit
  });

  it('marks unsaved tutorials and saves through the editor', () => {
    const { id } = setup();
    S().openTutorial(id);
    const onSave = renderSection();
    expect(screen.queryByText('Unsaved changes')).toBeNull();
    act(() => { S().updateTutorial(id, { title: 'SSH pivot v2' }); });
    expect(screen.getByText('Unsaved changes')).toBeInTheDocument();
    expect(screen.getByLabelText('unsaved changes')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(onSave).toHaveBeenCalled();
  });

  it('edits cells in edit mode', () => {
    const { id } = setup();
    S().openTutorial(id, { edit: true });
    renderSection();
    const command = screen.getByDisplayValue('ssh root@10.0.5.20');
    fireEvent.change(command, { target: { value: 'ssh -o StrictHostKeyChecking=no root@10.0.5.20' } });
    fireEvent.blur(command);
    const cells = S().topology.tutorials![0].cells;
    expect(cells[2]).toMatchObject({ command: 'ssh -o StrictHostKeyChecking=no root@10.0.5.20' });
    fireEvent.click(screen.getAllByRole('button', { name: 'Delete note' })[0]);
    expect(S().topology.tutorials![0].cells).toHaveLength(3);
    fireEvent.click(screen.getByRole('button', { name: /Done/ }));
    expect(screen.queryByRole('textbox', { name: 'Command' })).toBeNull();
  });

  it('closes a tab back to the list', () => {
    const { id } = setup();
    S().openTutorial(id);
    renderSection();
    fireEvent.click(screen.getByRole('button', { name: 'Close SSH pivot' }));
    expect(S().openTutorialIds).toEqual([]);
    expect(screen.getByText('In this topology')).toBeInTheDocument();
  });
});

describe('TutorialsSection for a student', () => {
  beforeEach(() => { useAppStore.setState({ user: { id: 's1', username: 'alice', role: 'student' } }); });
  afterEach(() => { useAppStore.setState({ user: null }); });

  it('steps through a tutorial without any authoring controls', () => {
    const { id } = setup();
    deploy();
    renderSection();
    expect(screen.queryByRole('button', { name: /New/ })).toBeNull();
    act(() => { S().openTutorial(id, { edit: true }); }); // even an edit request stays read-only
    expect(screen.queryByRole('button', { name: /^Edit$/ })).toBeNull();
    expect(screen.queryByRole('button', { name: /Done/ })).toBeNull();
    expect(screen.queryByDisplayValue('SSH pivot')).toBeNull();
    expect(screen.getByRole('button', { name: /Next step/ })).toBeEnabled();
  });
});

describe('command cell status', () => {
  it('shows a tracked run as running with Stop, then how it ended', async () => {
    const { id, attacker, c1 } = setup();
    S().openTutorial(id);
    renderSection();
    deploy();
    shell.tracking = true;
    fireEvent.click(screen.getAllByRole('button', { name: 'Run on attacker' })[0]);
    await waitFor(() => expect(screen.getByText('running')).toBeInTheDocument());
    expect(S().cellStatus[id][c1]).toEqual({ state: 'running' });

    fireEvent.click(screen.getByRole('button', { name: 'Stop on attacker' }));
    await waitFor(() => expect(shell.interrupts).toEqual([`term:${attacker}`]));

    act(() => shell.end!({ exit: 130 }));
    expect(screen.getByText('stopped')).toBeInTheDocument(); // Ctrl-C after Stop is not a failure
    expect(screen.queryByText('exit 130')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Stop on attacker' })).toBeNull();
    expect(screen.getAllByRole('button', { name: 'Run on attacker' })).toHaveLength(2);
  });

  it('says "sent" when the shell cannot report the run, and forgets status on reset', async () => {
    const { id, c1 } = setup();
    S().openTutorial(id);
    renderSection();
    deploy();
    fireEvent.click(screen.getAllByRole('button', { name: 'Run on attacker' })[0]);
    await waitFor(() => expect(screen.getByText(/^sent /)).toBeInTheDocument());
    expect(S().cellStatus[id][c1]).toEqual({ state: 'sent' });
    act(() => S().resetTutorialProgress(id));
    expect(S().cellStatus[id]).toBeUndefined();
    expect(screen.queryByText(/^sent /)).toBeNull();
  });

  it('gives each node one colour, shared by its cells', () => {
    const { id } = setup();
    S().openTutorial(id);
    renderSection();
    const cells = [...document.querySelectorAll<HTMLElement>('[data-cell-id]')].filter((el) => el.style.boxShadow);
    expect(cells).toHaveLength(2); // both steps on the attacker; the removed node's step has none
    expect(new Set(cells.map((el) => el.style.boxShadow))).toEqual(new Set(['inset 3px 0 0 var(--chart-1)']));
  });
});

