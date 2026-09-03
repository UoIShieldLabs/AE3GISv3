import { useEffect, useState } from 'react';
import { fetchCatalog } from '../api/client';
import { applyCatalog, getCatalog } from './catalog';

/** Fetch the node-type catalog once and report when the app can render.
 *  Fails open: if the catalog can't be fetched, the app still renders (nodes
 *  fall back to neutral colours/labels) rather than blocking on a spinner. */
export function useCatalogReady(): boolean {
  const [ready, setReady] = useState(() => getCatalog() !== null);
  useEffect(() => {
    if (getCatalog()) return;
    let cancelled = false;
    fetchCatalog()
      .then((c) => { if (!cancelled) { applyCatalog(c); setReady(true); } })
      .catch(() => { if (!cancelled) setReady(true); });
    return () => { cancelled = true; };
  }, []);
  return ready;
}
