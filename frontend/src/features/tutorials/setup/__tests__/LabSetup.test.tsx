import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import * as api from '@/api/client';
import { clearHistory, undo, useAppStore } from '@/store';
import { applyCatalog } from '@/catalog/catalog';
import { TooltipProvider } from '@/ui';
import { CATALOG } from '@/test/catalogFixture';
import type { Tutorial } from '@/types/topology';
import { TutorialNotebook } from '../../TutorialNotebook';

vi.mock('@/api/client', async (original) => ({
  ...(await original<typeof api>()),
  listScenarioRuns: vi.fn(),
  runScenarioSteps: vi.fn(),
  getScenarioRun: vi.fn(),
  startBackgroundRun: vi.fn(),
  getBackgroundRun: vi.fn(),
  startTrafficRun: vi.fn(),
  stopJob: vi.fn(),
}));
vi.mock('@/features/deployment/statusPolling', () => ({ startPolling: vi.fn() }));
vi.mock('@/features/terminal/sessions', () => ({ acquireSession: vi.fn(), getSession: vi.fn() }));

const m = vi.mocked(api);
const S = () => useAppStore.getState();
const DEPLOYED_AT = '2026-11-12T10:00:00';

const job = (id: string, created_at: string) => ({ id, kind: 'scenario', status: 'succeeded', created_at, started_at: created_at, steps: [] }) as unknown as api.Job;
function scenarioRun(over: Partial<api.ScenarioRun> & { stepStatus?: string[] } = {}): api.ScenarioRun {
  const { stepStatus = ['ok', 'ok'], ...rest } = over;
  const steps = stepStatus.map((status, index) => ({ index, container_id: 'x', command: 'c', status, exit_code: status === 'ok' ? 0 : 2, stdout: `out ${index}\n`, stderr: '' }));
  return {
    id: 'run1', topology_id: 'topo1', label: 'Lab setup', tag: `tutorial-setup:${ids.tutorial}`, status: 'succeeded', live: false,
    step_count: 2, node_ids: [], steps: [], ws_path: '',
    result: { steps, stopped_by: stepStatus.every((s) => s === 'ok') ? 'completed' : 'failed_step', failed: stepStatus.filter((s) => s !== 'ok').length },
    job: job('run1', '2026-11-12T10:05:00'),
    ...rest,
  } as api.ScenarioRun;
}

const ids = { tutorial: '', fw: '', ew: '', rtu: '' };

/** A tutorial whose setup has two steps and two traffic rows (a command, an iperf3 row). */
function build(): Tutorial {
  const siteId = S().addSite({ name: 'S' });
  const sn = S().addSubnet({ siteId, name: 'OT', cidr: '10.0.3.0/24', autoInfra: false })!;
  ids.fw = S().addContainer({ subnetId: sn, type: 'router', name: 'fw', ip: '10.0.3.1' })!;
  ids.ew = S().addContainer({ subnetId: sn, type: 'workstation', name: 'eng-ws', ip: '10.0.3.15' })!;
  ids.rtu = S().addContainer({ subnetId: sn, type: 'workstation', name: 'rtu', ip: '10.0.3.50' })!;
  ids.tutorial = S().addTutorial('Industroyer');
  S().addTutorialCell(ids.tutorial, 'command', undefined, { containerId: ids.ew, command: 'breaker status' });
  S().updateTutorialSetup(ids.tutorial, (s) => {
    s.steps.push({ id: 's1', containerId: ids.fw, command: 'nft insert rule permit' }, { id: 's2', containerId: ids.rtu, command: 'service c104 start' });
    s.traffic.push(
      { id: 'r1', kind: 'command', label: 'Polling', from: [ids.ew], to: [ids.rtu], command: 'while sleep 2; do nc -z {to} 2404; done' },
      { id: 'r2', kind: 'iperf3', from: [ids.ew], to: [ids.rtu], protocol: 'udp', bitrate: '500K' },
    );
  });
  S().markClean();
  return S().topology.tutorials!.find((t) => t.id === ids.tutorial)!;
}

const tutorialNow = () => S().topology.tutorials!.find((t) => t.id === ids.tutorial)!;
function renderNotebook() {
  const Live = () => <TutorialNotebook tutorial={useAppStore((s) => s.topology.tutorials!.find((t) => t.id === ids.tutorial)!)} onSave={() => {}} />;
  render(<TooltipProvider><Live /></TooltipProvider>);
}
const deploy = () => act(() => { useAppStore.setState({ deployStatus: 'deployed', backendId: 'topo1', deployedAt: DEPLOYED_AT }); });

beforeEach(() => {
  vi.clearAllMocks();
  applyCatalog(CATALOG);
  useAppStore.setState({ catalog: CATALOG, catalogStatus: 'ready', dockTabs: [], activeDockTabId: null, activity: [] });
  S().newTopology('Test');
  S().resetTutorialSession();
  clearHistory();
  useAppStore.setState({ deployStatus: 'idle', dirty: false, backendId: null, deployedAt: null });
  m.listScenarioRuns.mockResolvedValue([]);
  m.stopJob.mockResolvedValue({} as api.Job);
});

afterEach(() => { useAppStore.setState({ activity: [] }); });

describe('Lab setup', () => {
  it('is not shown for a tutorial without setup', () => {
    build();
    act(() => S().updateTutorialSetup(ids.tutorial, (s) => { s.steps = []; s.traffic = []; }));
    expect(tutorialNow().setup).toBeUndefined();
    renderNotebook();
    expect(screen.queryByRole('region', { name: 'Lab setup' })).toBeNull();
  });

  it('is one collapsed row, blocked until the lab is deployed', () => {
    build();
    renderNotebook();
    expect(screen.getByRole('region', { name: 'Lab setup' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Configure lab/ })).toBeDisabled();
    expect(screen.getByRole('switch', { name: 'Background traffic' })).toBeDisabled();
    expect(screen.queryByText('nft insert rule permit')).toBeNull(); // collapsed
    fireEvent.click(screen.getByRole('button', { name: /Lab setup/ }));
    expect(screen.getByText('nft insert rule permit')).toBeInTheDocument();
    expect(screen.getByText('Polling')).toBeInTheDocument();
    expect(screen.getByText(/iperf3 · UDP 500K/)).toBeInTheDocument();
  });

  it('Configure lab runs the steps, then starts the traffic', async () => {
    build();
    m.runScenarioSteps.mockResolvedValue(scenarioRun({ live: true, status: 'running', result: null }));
    m.getScenarioRun.mockResolvedValue(scenarioRun());
    m.startBackgroundRun.mockResolvedValue({} as api.BackgroundRun);
    m.startTrafficRun.mockResolvedValue({} as api.TrafficRun);
    renderNotebook();
    deploy();
    await waitFor(() => expect(screen.getByText('not run yet')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /Configure lab/ }));
    // The hook polls the run on a real 800 ms timer: allow for a busy machine.
    await waitFor(() => expect(screen.getByText(/^configured/)).toBeInTheDocument(), { timeout: 10000 });
    expect(m.runScenarioSteps).toHaveBeenCalledWith('topo1', {
      steps: [
        { containerId: ids.fw, script: 'nft insert rule permit', args: [], label: '' },
        { containerId: ids.rtu, script: 'service c104 start', args: [], label: '' },
      ],
      label: 'Lab setup: Industroyer',
      tag: `tutorial-setup:${ids.tutorial}`,
      stop_on_failure: true,
    });
    await waitFor(() => expect(m.startBackgroundRun).toHaveBeenCalled(), { timeout: 5000 });
    expect(m.startBackgroundRun).toHaveBeenCalledWith('topo1', {
      items: [{ id: 'r0.f0.t0', containerId: ids.ew, command: 'while sleep 2; do nc -z 10.0.3.50 2404; done' }],
      label: 'Background traffic',
      tag: `tutorial-traffic:${ids.tutorial}`,
    });
    expect(m.startTrafficRun.mock.calls[0][1]).toMatchObject({ duration_s: null, patterns: [{ id: 'r1', clients: [ids.ew], servers: [ids.rtu], protocol: 'udp', bitrate: '500K' }] });
    expect(screen.getByRole('button', { name: /Run again/ })).toBeInTheDocument();
  }, 20000);

  it('a failed step opens the block, shows its output on click and starts no traffic', async () => {
    build();
    m.runScenarioSteps.mockResolvedValue(scenarioRun({ stepStatus: ['failed'] }));
    renderNotebook();
    deploy();
    await waitFor(() => expect(screen.getByText('not run yet')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /Configure lab/ }));
    await waitFor(() => expect(screen.getByText('step 1 failed')).toBeInTheDocument());
    expect(screen.getByText('exit 2')).toBeInTheDocument(); // opened by itself
    expect(m.startBackgroundRun).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: /nft insert rule permit/ }));
    expect(screen.getByText('out 0')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Try again/ })).toBeEnabled();
  });

  it('knows the lab is configured after a reload, but not after a redeploy', async () => {
    build();
    m.listScenarioRuns.mockResolvedValue([scenarioRun({ result: null })]);
    m.getScenarioRun.mockResolvedValue(scenarioRun());
    renderNotebook();
    deploy();
    await waitFor(() => expect(screen.getByText(/^configured/)).toBeInTheDocument());
    // The lab is redeployed: the run belongs to the one before.
    act(() => { useAppStore.setState({ deployedAt: '2026-11-12T11:00:00' }); });
    await waitFor(() => expect(screen.getByText('not run yet')).toBeInTheDocument());
  });

  it('one switch starts and stops all the background traffic', async () => {
    build();
    m.startBackgroundRun.mockResolvedValue({} as api.BackgroundRun);
    m.startTrafficRun.mockResolvedValue({} as api.TrafficRun);
    m.getBackgroundRun.mockResolvedValue({
      id: 'bg1', tag: `tutorial-traffic:${ids.tutorial}`, live: true,
      items: [{ id: 'r0.f0.t0', container_id: ids.ew, command: 'x', status: 'running', output: 'open\n' }],
    } as unknown as api.BackgroundRun);
    renderNotebook();
    deploy();
    const toggle = screen.getByRole('switch', { name: 'Background traffic' });
    await waitFor(() => expect(toggle).toBeEnabled());
    fireEvent.click(toggle);
    await waitFor(() => expect(m.startBackgroundRun).toHaveBeenCalled());
    expect(m.startTrafficRun).toHaveBeenCalled();
    expect(m.runScenarioSteps).not.toHaveBeenCalled(); // the switch is only about traffic
    // /runtime now lists both runs.
    act(() => {
      S().setActivity([
        { job_id: 'bg1', kind: 'background', status: 'running', label: 'Background traffic', node_ids: [ids.ew], connection_ids: [] },
        { job_id: 'tr1', kind: 'traffic', status: 'running', label: 'Background traffic: Industroyer', node_ids: [], connection_ids: [] },
      ] as api.Activity[]);
    });
    await waitFor(() => expect(toggle).toBeChecked());
    fireEvent.click(screen.getByRole('button', { name: /Lab setup/ }));
    await waitFor(() => expect(screen.getByText('running')).toBeInTheDocument());

    fireEvent.click(toggle);
    await waitFor(() => expect(m.stopJob).toHaveBeenCalledTimes(2));
    expect(m.stopJob.mock.calls.map((c) => c[0]).sort()).toEqual(['bg1', 'tr1']);
    act(() => S().setActivity([]));
    await waitFor(() => expect(toggle).not.toBeChecked());
  });

  it('is edited in place, undoable, and a duplicate gets its own ids', () => {
    build();
    act(() => S().setTutorialEditing(ids.tutorial, true));
    renderNotebook();
    // The editor replaces the run view while editing.
    expect(screen.queryByRole('button', { name: /Configure lab/ })).toBeNull();
    expect(screen.getAllByLabelText('Setup step command')).toHaveLength(2);
    fireEvent.click(screen.getByRole('button', { name: /Setup step/ }));
    expect(tutorialNow().setup!.steps).toHaveLength(3);
    expect(tutorialNow().setup!.steps[2].containerId).toBe(ids.rtu); // follows the step before it
    expect(S().dirty).toBe(true);
    act(() => undo());
    expect(tutorialNow().setup!.steps).toHaveLength(2);
    fireEvent.click(screen.getAllByRole('button', { name: 'Delete traffic' })[1]);
    expect(tutorialNow().setup!.traffic.map((r) => r.id)).toEqual(['r1']);

    const copyId = S().duplicateTutorial(ids.tutorial)!;
    const copy = S().topology.tutorials!.find((t) => t.id === copyId)!;
    expect(copy.setup!.steps.map((s) => s.command)).toEqual(['nft insert rule permit', 'service c104 start']);
    expect(copy.setup!.steps.every((s) => !['s1', 's2'].includes(s.id))).toBe(true);
  });
});
