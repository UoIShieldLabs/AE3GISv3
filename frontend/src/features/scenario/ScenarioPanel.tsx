import { ScenarioForm } from './ScenarioForm';
import { ScenarioRunView } from './ScenarioRunView';

/** A scenario tab in the dock: the authoring panel, or one run's live view. */
export function ScenarioPanel({ jobId }: { tabId: string; jobId: string | null }) {
  return jobId ? <ScenarioRunView jobId={jobId} /> : <ScenarioForm />;
}
