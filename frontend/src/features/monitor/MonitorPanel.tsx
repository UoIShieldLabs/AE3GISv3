import { useAppStore } from '@/store';
import { MonitorForm } from './MonitorForm';
import { MonitorView } from './MonitorView';

/** A monitor tab in the dock: the new-monitor form, or one monitor's live view. */
export function MonitorPanel({ tabId, jobId }: { tabId: string; jobId: string | null }) {
  const seed = useAppStore((s) => {
    const t = s.dockTabs.find((x) => x.id === tabId);
    return t?.kind === 'monitor' ? t.seed : undefined;
  });
  return jobId ? <MonitorView jobId={jobId} /> : <MonitorForm tabId={tabId} seed={seed} />;
}
