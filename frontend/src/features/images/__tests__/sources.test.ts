import { describe, expect, it } from 'vitest';
import type { ImagesReport, ImageStatus, Registry } from '@/api/client';
import { imagesFor, sourceEntries, sourceKeyOf } from '../sources';

const img = (ref: string, extra: Partial<ImageStatus> = {}): ImageStatus => ({
  ref, display_name: ref, description: '', stability: 'stable', kind: 'registry', status: 'ready', reason: '', ...extra,
});

const reg = (namespace: string, refs: string[], extra: Partial<Registry> = {}): Registry => ({
  id: namespace, namespace, url: `https://hub.docker.com/u/${namespace}`, hub_url: `https://hub.docker.com/u/${namespace}`, created_at: '2026-11-08T00:00:00Z',
  repositories: refs.length, skipped: 0,
  loaded: refs.map((ref) => ({ ref, repo: ref.split('/')[1].split(':')[0], tag: 'latest', type: 'workstation', name: ref, new_type: false })),
  ...extra,
});

function report(extra: Partial<ImagesReport> = {}): ImagesReport {
  return {
    host: { platform: 'linux/arm64', can_build: true, detail: '' },
    sources: [
      { name: 'ae3gis-containers', kind: 'git', path: 'data/sources/ae3gis-containers', available: true, can_sync: true, detail: '' },
      { name: 'ae3gis-tools', kind: 'path', path: 'tools', available: true, can_sync: false, detail: '' },
    ],
    registries: [reg('tollan', ['tollan/process-sim:latest', 'tollan/zeek:latest']), reg('acme', ['acme/fw:latest'], { rejected: [{ repo: 'bad', tag: 'latest', reasons: ['x'] }] })],
    images: [
      img('tollan/process-sim:latest'),
      img('tollan/zeek:latest', { status: 'missing' }),
      img('acme/fw:latest'),
      img('ae3gis.local/nftables', { kind: 'build', source: 'ae3gis-containers', status: 'stale' }),
      img('ae3gis.local/zeek', { kind: 'build', source: 'ae3gis-containers', active_job: { id: 'j', kind: 'build_image', status: 'running', created_at: '', steps: [] } }),
      img('ae3gis.local/scadabr', { kind: 'build', source: 'ae3gis-containers', stability: 'hidden', status: 'missing' }),
      img('ae3gis.local/nettools', { kind: 'build', source: 'ae3gis-tools' }),
      img('kathara/base'),
    ],
    ...extra,
  };
}

describe('image sources', () => {
  it('files each image under its registry, build source, or public', () => {
    const r = report();
    expect(sourceKeyOf(img('tollan/zeek:latest'), r)).toBe('registry:tollan');
    expect(sourceKeyOf(img('ae3gis.local/nftables', { kind: 'build', source: 'ae3gis-containers' }), r)).toBe('build:ae3gis-containers');
    expect(sourceKeyOf(img('kathara/base'), r)).toBe('public');
    expect(imagesFor(r, 'registry:tollan').map((i) => i.ref)).toEqual(['tollan/process-sim:latest', 'tollan/zeek:latest']);
    expect(imagesFor(r, 'public').map((i) => i.ref)).toEqual(['kathara/base']);
  });

  it('lists all, then registries, build sources and public, with counts and flags', () => {
    const entries = sourceEntries(report());
    expect(entries.map((e) => [e.key, e.count])).toEqual([
      ['all', 7],
      ['registry:tollan', 2],
      ['registry:acme', 1],
      ['build:ae3gis-containers', 2],
      ['build:ae3gis-tools', 1],
      ['public', 1],
    ]);
    const by = Object.fromEntries(entries.map((e) => [e.key, e]));
    // A pulled image that is missing only waits for a deploy; a stale build needs one.
    expect(by['registry:tollan'].attention).toBe(0);
    expect(by['build:ae3gis-containers'].attention).toBe(1);
    expect(by['build:ae3gis-containers'].busy).toBe(true);
    expect(by['registry:acme'].warning).toBe(true);
    expect(by['registry:tollan'].warning).toBe(false);
  });

  it('lists every image registries first, then builds on this host, then public', () => {
    expect(imagesFor(report(), 'all').map((i) => i.ref)).toEqual([
      'tollan/process-sim:latest', 'tollan/zeek:latest', 'acme/fw:latest',
      'ae3gis.local/nftables', 'ae3gis.local/zeek', 'ae3gis.local/nettools',
      'kathara/base',
    ]);
  });

  it('never lists hidden images, and drops an empty public entry', () => {
    const r = report({ images: report().images.filter((i) => i.ref !== 'kathara/base') });
    expect(imagesFor(r, 'all').some((i) => i.ref === 'ae3gis.local/scadabr')).toBe(false);
    expect(sourceEntries(r).some((e) => e.key === 'public')).toBe(false);
  });

  it('keeps many registries in the order they were added', () => {
    const names = Array.from({ length: 10 }, (_, i) => `ns${i}`);
    const r = report({ registries: names.map((n) => reg(n, [])), images: [] });
    expect(sourceEntries(r).filter((e) => e.group === 'registry').map((e) => e.label)).toEqual(names);
  });
});
