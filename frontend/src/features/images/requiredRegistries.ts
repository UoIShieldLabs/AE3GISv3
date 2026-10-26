// Which Docker Hub registries a topology's images need but aren't added yet.
// A scenario is portable as plain topology JSON (images are in each container's
// `image`); on import we infer the namespaces so the instructor can add them in
// one click instead of knowing to add `tollan` by hand.
import type { TopologyData } from '@/types/topology';

export interface MissingRegistry {
  namespace: string;
  url: string;
}

/** The Docker Hub namespace of an image ref, or null when it isn't one:
 *  an official library image (no `/`), an image built here (`ae3gis.local/…`),
 *  or one from a custom registry host (`host.tld/…`, `host:port/…`). */
export function dockerHubNamespace(ref: string): string | null {
  if (!ref || ref.startsWith('ae3gis.local/')) return null;
  const path = ref.split('@')[0].split('/');
  if (path.length < 2) return null; // official (library) image
  const first = path[0];
  if (first.includes('.') || first.includes(':')) return null; // a registry host, not Docker Hub
  return first;
}

export function requiredRegistries(topology: TopologyData, installed: readonly string[]): MissingRegistry[] {
  const have = new Set(installed);
  const seen = new Set<string>();
  const out: MissingRegistry[] = [];
  for (const site of topology.sites ?? [])
    for (const subnet of site.subnets ?? [])
      for (const c of subnet.containers ?? []) {
        const ns = typeof c.image === 'string' ? dockerHubNamespace(c.image) : null;
        if (!ns || have.has(ns) || seen.has(ns)) continue;
        seen.add(ns);
        out.push({ namespace: ns, url: `https://hub.docker.com/u/${ns}` });
      }
  return out;
}
