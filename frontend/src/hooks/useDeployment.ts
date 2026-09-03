import { useCallback, useState } from 'react';
import type { Dispatch } from 'react';
import * as api from '../api/client';
import type { TopologyAction } from '../store/topologyReducer';
import type { TopologyData } from '../types/topology';

interface DeploymentState {
  topology: TopologyData;
  backendId: string | null;
  backendName: string | null;
  dirty: boolean;
}

interface StatusPolling {
  start: (topologyId: string) => void;
  stop: () => void;
}

/** Save / load / deploy / destroy / new / export orchestration. */
export function useDeployment(
  dispatch: Dispatch<TopologyAction>,
  state: DeploymentState,
  polling: StatusPolling,
  onResetView: () => void,
) {
  const { topology, backendId, backendName, dirty } = state;
  const [busy, setBusy] = useState(false);

  const handleSave = useCallback(async (name?: string) => {
    setBusy(true);
    try {
      if (backendId) {
        await api.updateTopology(backendId, backendName ?? undefined, topology);
        dispatch({ type: 'MARK_CLEAN' });
      } else {
        const record = await api.createTopology(name || 'Untitled Topology', topology);
        dispatch({ type: 'SET_BACKEND_INFO', payload: { id: record.id, name: record.name, status: record.status } });
        dispatch({ type: 'MARK_CLEAN' });
      }
    } finally {
      setBusy(false);
    }
  }, [backendId, backendName, topology, dispatch]);

  const handleLoad = useCallback(async (id: string) => {
    setBusy(true);
    try {
      const record = await api.getTopology(id);
      dispatch({ type: 'LOAD_TOPOLOGY', payload: record.data });
      dispatch({ type: 'SET_BACKEND_INFO', payload: { id: record.id, name: record.name, status: record.status } });
      onResetView();
      polling.stop();
      dispatch({ type: 'CLEAR_CONTAINER_STATUSES' });
      if (record.status === 'deployed') polling.start(record.id);
    } finally {
      setBusy(false);
    }
  }, [dispatch, polling, onResetView]);

  const handleDeploy = useCallback(async () => {
    if (!backendId) return;
    setBusy(true);
    try {
      if (dirty) {
        await api.updateTopology(backendId, backendName ?? undefined, topology);
        dispatch({ type: 'MARK_CLEAN' });
      }
      dispatch({ type: 'SET_DEPLOY_STATUS', payload: 'deploying' });
      await api.deployTopology(backendId);
      dispatch({ type: 'SET_DEPLOY_STATUS', payload: 'deployed' });
      polling.start(backendId);
    } catch {
      dispatch({ type: 'SET_DEPLOY_STATUS', payload: 'error' });
    } finally {
      setBusy(false);
    }
  }, [backendId, backendName, dirty, topology, dispatch, polling]);

  const handleDestroy = useCallback(async () => {
    if (!backendId) return;
    setBusy(true);
    try {
      dispatch({ type: 'SET_DEPLOY_STATUS', payload: 'destroying' });
      await api.destroyTopology(backendId);
      dispatch({ type: 'SET_DEPLOY_STATUS', payload: 'idle' });
      dispatch({ type: 'CLEAR_CONTAINER_STATUSES' });
      polling.stop();
    } catch {
      dispatch({ type: 'SET_DEPLOY_STATUS', payload: 'error' });
    } finally {
      setBusy(false);
    }
  }, [backendId, dispatch, polling]);

  const handleNew = useCallback(() => {
    dispatch({ type: 'LOAD_TOPOLOGY', payload: { sites: [], siteConnections: [] } });
    dispatch({ type: 'CLEAR_BACKEND' });
    onResetView();
    polling.stop();
  }, [dispatch, polling, onResetView]);

  const handleExport = useCallback(() => {
    const payload = {
      name: backendName || topology.name || 'Exported Topology',
      description: 'Exported topology from AE3GIS.',
      topology,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${topology.name || 'topology'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [backendName, topology]);

  return { busy, handleSave, handleLoad, handleDeploy, handleDestroy, handleNew, handleExport };
}
