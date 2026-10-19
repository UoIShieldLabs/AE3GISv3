import { afterEach, describe, expect, it, vi } from 'vitest';
import { useAppStore } from '@/store';
import { applyCatalog, colorFor, displayNameFor, type Catalog } from '@/catalog/catalog';
import { CATALOG } from '@/test/catalogFixture';

const st = () => useAppStore.getState();

const SYNCED: Catalog = {
  ...CATALOG,
  types: {
    ...CATALOG.types,
    bastion: {
      displayName: 'Bastion Host', role: 'host', category: 'hub:lab', defaultImage: 'lab/bastion:latest',
      images: ['lab/bastion:latest'], color: '#240177', label: 'BS', icon: 'server', description: '', origin: 'lab',
    },
  },
};

function serve(body: unknown, status = 200) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
}

describe('catalog slice', () => {
  afterEach(() => vi.restoreAllMocks());

  it('refreshCatalog replaces a loaded catalog and its lookups', async () => {
    applyCatalog(CATALOG);
    useAppStore.setState({ catalog: CATALOG, catalogStatus: 'ready' });
    expect(displayNameFor('bastion')).toBe('bastion');

    const fetch = serve(SYNCED);
    await st().loadCatalog();
    expect(fetch).not.toHaveBeenCalled(); // loading is once

    await st().refreshCatalog();
    expect(fetch).toHaveBeenCalledOnce();
    expect(st().catalog).toEqual(SYNCED);
    expect(displayNameFor('bastion')).toBe('Bastion Host');
    expect(colorFor('bastion')).toBe('#240177');
  });

  it('a failed refresh keeps the catalog', async () => {
    applyCatalog(CATALOG);
    useAppStore.setState({ catalog: CATALOG, catalogStatus: 'ready' });
    serve({ detail: 'down', code: 'error' }, 500);
    await st().refreshCatalog();
    expect(st().catalog).toBe(CATALOG);
    expect(st().catalogStatus).toBe('ready');
  });
});
