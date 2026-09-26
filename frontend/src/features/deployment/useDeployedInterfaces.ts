import { useEffect, useState } from 'react';
import * as api from '@/api/client';
import { useAppShallow } from '@/store/selectors';

// One fetch per deploy: interfaces only change when the lab is redeployed.
const cache = new Map<string, Promise<api.DeployedInterfaces>>();

/** The deployed lab's interfaces by node and its links (what captures can
 *  target), or null while not deployed / loading. */
export function useDeployedInterfaces(): api.DeployedInterfaces | null {
  const { backendId, deployStatus } = useAppShallow((s) => ({ backendId: s.backendId, deployStatus: s.deployStatus }));
  const [data, setData] = useState<{ key: string; value: api.DeployedInterfaces } | null>(null);
  const key = backendId && deployStatus === 'deployed' ? backendId : null;

  useEffect(() => {
    if (!backendId) return;
    if (!key) {
      cache.delete(backendId);
      return;
    }
    let live = true;
    let pending = cache.get(key);
    if (!pending) {
      pending = api.getInterfaces(key);
      cache.set(key, pending);
      pending.catch(() => cache.delete(key));
    }
    pending.then((value) => { if (live) setData({ key, value }); }).catch(() => {});
    return () => { live = false; };
  }, [backendId, key]);

  return key && data?.key === key ? data.value : null;
}
