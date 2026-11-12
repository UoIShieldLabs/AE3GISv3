import { useEffect } from 'react';
import { useAppShallow } from '@/store/selectors';
import { startPulse, stopPulse } from './pulse';

/** Keep the live lab view on while the calling component is mounted and the
 *  loaded topology is deployed. */
export function useLabPulse(): void {
  const { backendId, deployed } = useAppShallow((s) => ({ backendId: s.backendId, deployed: s.deployStatus === 'deployed' }));
  useEffect(() => {
    if (!backendId || !deployed) return;
    startPulse(backendId);
    return stopPulse;
  }, [backendId, deployed]);
}
