import { useEffect } from 'react';
import * as api from '@/api/client';
import { useAppStore } from '@/store';

const DEBOUNCE_MS = 700;

/** Ask the backend to validate the current design whenever it changes (debounced). */
export function useServerValidation() {
  const topology = useAppStore((s) => s.topology);
  useEffect(() => {
    let cancelled = false;
    const t = window.setTimeout(() => {
      void api.validateTopology(topology).then((r) => {
        if (!cancelled) useAppStore.getState().setDiagnostics(r.diagnostics);
      }).catch(() => { /* backend unreachable: keep the last known diagnostics */ });
    }, DEBOUNCE_MS);
    return () => { cancelled = true; window.clearTimeout(t); };
  }, [topology]);
}
