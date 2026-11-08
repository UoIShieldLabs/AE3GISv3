// Where node images come from, as the Images sheet's left-hand list: every
// image, then each Docker Hub registry the user added, then each source AE3GIS
// builds from on this host, then the built-in catalog's public images. Pure:
// derived from the GET /images report only.
import type { ImagesReport, ImageStatus } from '@/api/client';
import { needsAttention } from './status';

export type SourceKey = 'all' | 'public' | 'add-registry' | `registry:${string}` | `build:${string}`;

export interface SourceEntry {
  key: SourceKey;
  group: 'all' | 'registry' | 'build' | 'public';
  label: string;
  /** Images listed under it. */
  count: number;
  /** Images that need a build (missing, out of date, failed). */
  attention: number;
  /** A registry with rejected or pending repos, or a failed last sync. */
  warning: boolean;
  /** Syncing, or building one of its images. */
  busy: boolean;
}

/** Images the sheet lists (hidden ones never show). */
export function listedImages(report: ImagesReport): ImageStatus[] {
  return report.images.filter((i) => i.stability !== 'hidden');
}

/** Image ref → the registry namespace it was loaded from. */
function registryByRef(report: ImagesReport): Map<string, string> {
  const map = new Map<string, string>();
  for (const reg of report.registries ?? []) for (const img of reg.loaded ?? []) map.set(img.ref, reg.namespace);
  return map;
}

/** The source an image is listed under. */
export function sourceKeyOf(img: Pick<ImageStatus, 'kind' | 'source' | 'ref'>, report: ImagesReport): SourceKey {
  if (img.kind === 'build') return `build:${img.source ?? ''}`;
  const ns = registryByRef(report).get(img.ref);
  return ns ? `registry:${ns}` : 'public';
}

/** The images listed under a source. 'all' lists every image in the order of
 *  the source list: registries first, then builds on this host, then public. */
export function imagesFor(report: ImagesReport, key: SourceKey): ImageStatus[] {
  const images = listedImages(report);
  const byRef = registryByRef(report);
  const under = (k: SourceKey) => images.filter((img) => {
    if (img.kind === 'build') return k === `build:${img.source ?? ''}`;
    const ns = byRef.get(img.ref);
    return ns ? k === `registry:${ns}` : k === 'public';
  });
  if (key !== 'all') return under(key);
  const order: SourceKey[] = [
    ...(report.registries ?? []).map((r) => `registry:${r.namespace}` as const),
    ...report.sources.map((s) => `build:${s.name}` as const),
    'public',
  ];
  const ordered = order.flatMap(under);
  const placed = new Set(ordered.map((i) => i.ref));
  return [...ordered, ...images.filter((i) => !placed.has(i.ref))];
}

/** The left-hand list, in order: all, registries, build sources, public. */
export function sourceEntries(report: ImagesReport): SourceEntry[] {
  const entry = (key: SourceKey, group: SourceEntry['group'], label: string, extra: Partial<SourceEntry> = {}): SourceEntry => {
    const images = imagesFor(report, key);
    return {
      key, group, label,
      count: images.length,
      attention: images.filter(needsAttention).length,
      warning: false,
      busy: images.some((i) => !!i.active_job),
      ...extra,
    };
  };
  const out: SourceEntry[] = [entry('all', 'all', 'All images')];
  for (const reg of report.registries ?? []) {
    out.push(entry(`registry:${reg.namespace}`, 'registry', reg.namespace, {
      warning: !!(reg.rejected?.length || reg.pending?.length || reg.last_job?.status === 'failed'),
      busy: !!reg.active_job,
    }));
  }
  for (const src of report.sources) {
    const e = entry(`build:${src.name}`, 'build', src.name);
    out.push({ ...e, busy: e.busy || !!src.active_job });
  }
  const pub = entry('public', 'public', 'Public images');
  if (pub.count) out.push(pub);
  return out;
}
