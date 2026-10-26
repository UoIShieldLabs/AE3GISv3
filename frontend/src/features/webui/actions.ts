import { useAppStore } from '@/store';
import { webuiTabId } from '@/store/slices/dockSlice';

/** Open a node's web UI as a dock tab (one per node). */
export function openWebUi(nodeId: string, name?: string) {
  useAppStore.getState().openDockTab({ kind: 'webui', id: webuiTabId(nodeId), nodeId, title: `${name ?? nodeId} · web` });
}
