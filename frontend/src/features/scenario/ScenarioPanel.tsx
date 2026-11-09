import { useCan } from '@/lib/permissions';
import { ScenarioForm } from './ScenarioForm';
import { ScenarioRunView } from './ScenarioRunView';

/** A scenario tab in the dock: the authoring panel (run-only for students),
 *  or one run's live view. */
export function ScenarioPanel({ jobId }: { tabId: string; jobId: string | null }) {
  const author = useCan('authorScenarios');
  return jobId ? <ScenarioRunView jobId={jobId} /> : <ScenarioForm readOnly={!author} />;
}
