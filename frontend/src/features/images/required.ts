// Which images a topology needs, and which of those still need work (pure).
import type { ImageStatus } from '@/api/client';
import type { Container, TopologyData } from '@/types/topology';

export interface RequiredImages {
  /** Image ref -> names of the devices using it. */
  users: Map<string, string[]>;
  toBuild: ImageStatus[];
  building: ImageStatus[];
  stale: ImageStatus[];
  failed: ImageStatus[];
  unavailable: ImageStatus[];
}

export function requiredImageRefs(topology: TopologyData, resolve: (c: Container) => string): Map<string, string[]> {
  const users = new Map<string, string[]>();
  for (const site of topology.sites) {
    for (const subnet of site.subnets) {
      for (const c of subnet.containers) {
        const ref = resolve(c);
        if (ref) users.set(ref, [...(users.get(ref) ?? []), c.name]);
      }
    }
  }
  return users;
}

export function classifyRequired(users: Map<string, string[]>, statuses: ImageStatus[]): RequiredImages {
  const out: RequiredImages = { users, toBuild: [], building: [], stale: [], failed: [], unavailable: [] };
  for (const img of statuses) {
    if (!users.has(img.ref) || img.kind !== 'build') continue;
    if (img.status === 'missing') out.toBuild.push(img);
    else if (img.status === 'building') out.building.push(img);
    else if (img.status === 'stale') out.stale.push(img);
    else if (img.status === 'failed') out.failed.push(img);
    else if (img.status === 'unavailable') out.unavailable.push(img);
  }
  return out;
}

export function nameList(images: ImageStatus[], max = 3): string {
  const names = images.map((i) => i.display_name);
  return names.length > max ? `${names.slice(0, max).join(', ')} +${names.length - max}` : names.join(', ');
}
