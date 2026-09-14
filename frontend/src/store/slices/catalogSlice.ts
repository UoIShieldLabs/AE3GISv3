import { fetchCatalog } from '@/api/client';
import { applyCatalog } from '@/catalog/catalog';
import type { CatalogSlice, SliceCreator } from '../types';

export const createCatalogSlice: SliceCreator<CatalogSlice> = (set, get) => ({
  catalog: null,
  catalogStatus: 'idle',

  loadCatalog: async () => {
    if (get().catalogStatus === 'loading' || get().catalogStatus === 'ready') return;
    set({ catalogStatus: 'loading' }, false, 'loadCatalog/start');
    try {
      const catalog = await fetchCatalog();
      applyCatalog(catalog);
      set({ catalog, catalogStatus: 'ready' }, false, 'loadCatalog/ready');
    } catch {
      // Fail open: the editor still works with neutral colours/labels.
      set({ catalogStatus: 'error' }, false, 'loadCatalog/error');
    }
  },
});
