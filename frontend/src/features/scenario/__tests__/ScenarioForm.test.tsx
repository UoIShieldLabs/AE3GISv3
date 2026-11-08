import { beforeEach, describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { useAppStore, clearHistory } from '@/store';
import { applyCatalog } from '@/catalog/catalog';
import { TooltipProvider } from '@/ui';
import { CATALOG } from '@/test/catalogFixture';
import { ScenarioForm } from '../ScenarioForm';

const S = () => useAppStore.getState();

function renderForm(readOnly = false) {
  render(
    <TooltipProvider>
      <ScenarioForm readOnly={readOnly} />
    </TooltipProvider>,
  );
}

/** A deployed, saved topology with one phase of one step. */
function deployedPhase() {
  const siteId = S().addSite({ name: 'S' });
  const sn = S().addSubnet({ siteId, name: 'A', cidr: '10.0.1.0/24', autoInfra: false })!;
  const host = S().addContainer({ subnetId: sn, type: 'workstation', ip: '10.0.1.5' })!;
  const phaseId = S().addPhase(S().addScenario('Demo'), 'Bring up')!;
  S().addStep(phaseId, { containerId: host, script: 'ip -o addr' });
  useAppStore.setState({ deployStatus: 'deployed', dirty: false, backendId: 't1' });
}

beforeEach(() => {
  applyCatalog(CATALOG);
  useAppStore.setState({ catalog: CATALOG, catalogStatus: 'ready' });
  S().newTopology('Test');
  clearHistory();
  useAppStore.setState({ deployStatus: 'idle', dirty: false, backendId: null });
});

describe('ScenarioForm', () => {
  it('renders the empty state for a topology without scenarios (no render loop)', () => {
    renderForm();
    expect(screen.getByText('No scenarios yet')).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole('button', { name: /New scenario/ })[0]);
    expect(screen.getByDisplayValue('Scenario 1')).toBeInTheDocument();
    expect(screen.getByText('No phases yet.')).toBeInTheDocument();
  });

  it('enables Run phase on a deployed, saved lab', () => {
    deployedPhase();
    renderForm();
    expect(screen.getByRole('button', { name: /Run phase/ })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Run step' })).toBeEnabled();
  });

  it('gates running on unsaved edits, since the backend runs what was deployed', () => {
    deployedPhase();
    useAppStore.setState({ dirty: true });
    renderForm();
    const runPhase = screen.getByRole('button', { name: /Run phase/ });
    expect(runPhase).toBeDisabled();
    expect(runPhase).toHaveAttribute('title', 'Save your changes first');
    expect(screen.getByRole('button', { name: 'Run step' })).toBeDisabled();
  });

  it('read-only (a student): steps as text, no authoring, still runnable', () => {
    deployedPhase();
    renderForm(true);
    expect(screen.getByText('ip -o addr')).toBeInTheDocument();
    expect(screen.queryByRole('textbox')).toBeNull();
    expect(screen.queryByRole('button', { name: /New scenario/ })).toBeNull();
    expect(screen.queryByRole('button', { name: /Add step/ })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Remove step' })).toBeNull();
    expect(screen.getByRole('button', { name: /Run phase/ })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Run step' })).toBeEnabled();
  });

  it('read-only with no scenarios says so instead of offering to add one', () => {
    renderForm(true);
    expect(screen.getByText(/has not added a scenario/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /New scenario/ })).toBeNull();
  });
});
