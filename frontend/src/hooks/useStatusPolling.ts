import { useCallback, useEffect, useRef } from 'react';
import type { Dispatch } from 'react';
import * as api from '../api/client';
import type { TopologyAction } from '../store/topologyReducer';

/** Poll deployment status every 5s and push it into the reducer.
 *  Container ids come straight from the engine now (no clab name prefix). */
export function useStatusPolling(dispatch: Dispatch<TopologyAction>) {
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const stop = useCallback(() => {
    if (timer.current !== null) { clearInterval(timer.current); timer.current = null; }
  }, []);

  const start = useCallback((topologyId: string) => {
    stop();
    const poll = async () => {
      try {
        const { containers } = await api.getTopologyStatus(topologyId);
        const statuses: Record<string, 'running' | 'stopped' | 'paused'> = {};
        for (const c of containers) {
          const s = c.state?.toLowerCase();
          statuses[c.id] = s === 'running' ? 'running' : s === 'paused' ? 'paused' : 'stopped';
        }
        dispatch({ type: 'UPDATE_CONTAINER_STATUSES', payload: { statuses } });
      } catch { /* transient */ }
    };
    void poll();
    timer.current = setInterval(() => { void poll(); }, 5000);
  }, [dispatch, stop]);

  useEffect(() => () => stop(), [stop]);
  return { start, stop };
}
