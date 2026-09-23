import { useMemo } from 'react';
import { useAppStore } from '@/store';
import { buildCatalogTree, type CatalogCategoryNode } from './tree';

/** The catalog grouped by category (reactive to catalog loads). */
export function useCatalogTree(query = ''): CatalogCategoryNode[] {
  const catalog = useAppStore((s) => s.catalog);
  return useMemo(() => buildCatalogTree(catalog, query), [catalog, query]);
}
