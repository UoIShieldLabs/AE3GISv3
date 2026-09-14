import { useEffect, useState } from 'react';
import * as api from '@/api/client';
import { useAppShallow } from '@/store/selectors';

export interface PlanNode {
  id: string;
  name: string;
  machine_name: string;
  role: string;
  image: string;
  interfaces: { name: string; collision_domain: string; ip: string | null; prefix_len: string | null }[];
  startup: string[];
}

const cache = new Map<string, Promise<api.PlanOut>>();

/** The backend's computed lab plan for the *saved* topology (cached per version). */
export function usePlan(): { plan: api.PlanOut | null; loading: boolean; stale: boolean } {
  const { backendId, version, dirty } = useAppShallow((s) => ({ backendId: s.backendId, version: s.version, dirty: s.dirty }));
  const [plan, setPlan] = useState<api.PlanOut | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!backendId) { setPlan(null); return; }
    const key = `${backendId}@${version}`;
    let p = cache.get(key);
    if (!p) { p = api.getPlan(backendId); cache.set(key, p); }
    let cancelled = false;
    setLoading(true);
    p.then((r) => { if (!cancelled) setPlan(r); }).catch(() => { cache.delete(key); if (!cancelled) setPlan(null); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [backendId, version]);

  return { plan, loading, stale: dirty };
}

export function planNodeFor(plan: api.PlanOut | null, nodeId: string): PlanNode | undefined {
  const nodes = (plan?.plan as { nodes?: PlanNode[] } | undefined)?.nodes ?? [];
  return nodes.find((n) => n.id === nodeId);
}
