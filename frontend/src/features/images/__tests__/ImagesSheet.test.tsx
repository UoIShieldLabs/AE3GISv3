import { beforeEach, describe, expect, it } from 'vitest';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import type { ImagesReport, ImageStatus, Registry } from '@/api/client';
import { useAppStore } from '@/store';
import { TooltipProvider } from '@/ui';
import { ImagesSheet } from '../ImagesSheet';

const img = (ref: string, extra: Partial<ImageStatus> = {}): ImageStatus => ({
  ref, display_name: ref, description: '', stability: 'stable', kind: 'registry', status: 'ready', reason: '', ...extra,
});

const reg = (namespace: string, refs: string[]): Registry => ({
  id: namespace, namespace, url: `https://hub.docker.com/u/${namespace}`, hub_url: `https://hub.docker.com/u/${namespace}`,
  created_at: '2026-11-08T00:00:00Z', synced_at: '2026-11-08T00:01:00Z', repositories: refs.length, skipped: 0,
  loaded: refs.map((ref) => ({ ref, repo: ref, tag: 'latest', type: 'workstation', name: ref, new_type: false })),
});

const REPORT: ImagesReport = {
  host: { platform: 'linux/arm64', can_build: true, detail: '' },
  sources: [{ name: 'ae3gis-tools', kind: 'path', path: 'tools', available: true, can_sync: false, detail: '' }],
  registries: [reg('tollan', ['tollan/process-sim:latest'])],
  images: [
    img('kathara/base', { display_name: 'Plain Linux' }),
    img('ae3gis.local/nettools', { display_name: 'Network tools', kind: 'build', source: 'ae3gis-tools', reason: 'Up to date with its source' }),
    img('tollan/process-sim:latest', { display_name: 'Process sim' }),
  ],
};

const nav = () => screen.getByRole('navigation', { name: 'Image sources' });
const current = () => within(nav()).getAllByRole('button').find((b) => b.getAttribute('aria-current') === 'true')?.textContent;
const rows = () => screen.getAllByRole('row').slice(1).map((r) => within(r).getAllByRole('cell')[0].textContent);

function renderSheet() {
  render(<TooltipProvider><ImagesSheet /></TooltipProvider>);
}

beforeEach(() => useAppStore.setState({ images: REPORT, imagesError: null, imagesOpen: true, imagesFocus: null }));

describe('ImagesSheet', () => {
  it('opens on every image, registries first', () => {
    renderSheet();
    expect(current()).toMatch(/^All images/);
    const names = ['Process sim', 'Network tools', 'Plain Linux'];
    expect(rows().map((t, i) => t?.startsWith(names[i]))).toEqual([true, true, true]);
  });

  it("shows a registry's own header and images when picked", () => {
    renderSheet();
    fireEvent.click(within(nav()).getByRole('button', { name: /tollan/ }));
    expect(current()).toMatch(/^tollan/);
    expect(screen.getByRole('button', { name: /Sync/ })).toBeInTheDocument();
    expect(rows()).toHaveLength(1);
  });

  it('opens on the source and details of an image it is asked to show', () => {
    useAppStore.setState({ imagesFocus: 'ae3gis.local/nettools' });
    renderSheet();
    expect(current()).toMatch(/^ae3gis-tools/);
    expect(screen.getByText('Up to date with its source')).toBeInTheDocument();
  });

  it('jumps to a newly requested image even after a source was picked', () => {
    renderSheet();
    fireEvent.click(within(nav()).getByRole('button', { name: /tollan/ }));
    act(() => useAppStore.getState().openImages('ae3gis.local/nettools'));
    expect(current()).toMatch(/^ae3gis-tools/);
  });

  it('falls back to every image when the picked registry is removed', () => {
    renderSheet();
    fireEvent.click(within(nav()).getByRole('button', { name: /tollan/ }));
    act(() => useAppStore.setState({ images: { ...REPORT, registries: [], images: REPORT.images.filter((i) => !i.ref.startsWith('tollan/')) } }));
    expect(current()).toMatch(/^All images/);
  });
});
