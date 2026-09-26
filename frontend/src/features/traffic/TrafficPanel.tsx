import { useAppStore } from '@/store';
import { TrafficForm } from './TrafficForm';
import { TrafficRunView } from './TrafficRunView';

/** A traffic tab in the dock: the new-run form, or one run's live view. */
export function TrafficPanel({ tabId, jobId }: { tabId: string; jobId: string | null }) {
  const seed = useAppStore((s) => {
    const t = s.dockTabs.find((x) => x.id === tabId);
    return t?.kind === 'traffic' ? t.seed : undefined;
  });
  return jobId ? <TrafficRunView jobId={jobId} /> : <TrafficForm tabId={tabId} seed={seed} />;
}
