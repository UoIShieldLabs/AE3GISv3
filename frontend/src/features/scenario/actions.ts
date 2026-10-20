// Scenario-runner actions shared by the dock panel, the palette and the top bar.
import * as api from '@/api/client';
import { useAppStore } from '@/store';
import { scenarioTabId } from '@/store/slices/dockSlice';
import { startPolling } from '@/features/deployment/statusPolling';
import { toast } from '@/ui';

/** Open the authoring panel (phases → steps, with Run buttons). */
export function openScenarioPanel() {
  useAppStore.getState().openDockTab({
    kind: 'scenario', id: scenarioTabId(null), jobId: null, title: 'Scenarios', seed: { nonce: Date.now() },
  });
}

/** Open a run's live view (a separate tab, so the authoring panel stays open). */
export function openScenarioRun(jobId: string, title = 'Scenario run') {
  useAppStore.getState().openDockTab({ kind: 'scenario', id: scenarioTabId(jobId), jobId, title });
}

function onStartError(err: unknown) {
  const running = err instanceof api.ApiError && err.code === 'scenario_active' ? String(err.data.job_id ?? '') : '';
  toast.error('Could not start the scenario', {
    description: api.errorMessage(err),
    action: running ? { label: 'Show it', onClick: () => openScenarioRun(running) } : undefined,
  });
}

/** Run a single ad-hoc step (a command on a node). */
export async function startScenarioStep(step: api.ScenarioStepRequest): Promise<api.ScenarioRun | null> {
  const id = useAppStore.getState().backendId;
  if (!id) return null;
  try {
    const run = await api.runScenarioStep(id, step);
    openScenarioRun(run.id, run.label || 'Scenario step');
    startPolling(id);
    return run;
  } catch (err) {
    onStartError(err);
    return null;
  }
}

/** Run every step of a stored phase, in order. */
export async function startScenarioPhase(phaseId: string, label = ''): Promise<api.ScenarioRun | null> {
  const id = useAppStore.getState().backendId;
  if (!id) return null;
  try {
    const run = await api.runScenarioPhase(id, phaseId, label);
    openScenarioRun(run.id, run.label || 'Scenario phase');
    startPolling(id);
    return run;
  } catch (err) {
    onStartError(err);
    return null;
  }
}

export async function stopScenarioRun(jobId: string): Promise<void> {
  try {
    await api.stopJob(jobId);
    const id = useAppStore.getState().backendId;
    if (id) startPolling(id);
  } catch (err) {
    toast.error('Could not stop the scenario', { description: api.errorMessage(err) });
  }
}

export function exportScenarioRun(jobId: string) {
  api.downloadUrl(api.scenarioExportUrl(jobId), `scenario-${jobId.slice(0, 8)}.zip`).catch((err: unknown) =>
    toast.error('Export failed', { description: api.errorMessage(err) }),
  );
}
