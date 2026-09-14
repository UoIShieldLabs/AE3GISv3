import { findSite, locate, type Scope } from '@/lib/topology';
import { useAppStore } from '@/store';

/** Subnet a click-to-add should target: the scope's own subnet, the selected one, or a site's only subnet. */
export function targetSubnetFor(scope: Scope, selectionIds: string[]): string | undefined {
  if (scope.level === 'subnet') return scope.subnetId;
  const t = useAppStore.getState().topology;
  if (selectionIds.length === 1) {
    const hit = locate(t, selectionIds[0]);
    if (hit?.kind === 'subnet') return hit.subnet.id;
    if (hit?.kind === 'container') return hit.subnet.id;
  }
  if (scope.level === 'site') {
    const site = findSite(t, scope.siteId);
    if (site?.subnets.length === 1) return site.subnets[0].id;
  }
  return undefined;
}

export function targetSiteFor(scope: Scope, selectionIds: string[]): string | undefined {
  if (scope.level !== 'root') return scope.siteId;
  const t = useAppStore.getState().topology;
  if (selectionIds.length === 1) {
    const hit = locate(t, selectionIds[0]);
    if (hit) return hit.site.id;
  }
  if (t.sites.length === 1) return t.sites[0].id;
  return undefined;
}
