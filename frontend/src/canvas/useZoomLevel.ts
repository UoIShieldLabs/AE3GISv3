import { useStore } from '@xyflow/react';

export type ZoomLevel = 'full' | 'compact' | 'minimal';

/** Semantic zoom buckets so nodes can drop detail when zoomed out. */
export function useZoomLevel(): ZoomLevel {
  return useStore((s) => {
    const z = s.transform[2];
    if (z < 0.4) return 'minimal';
    if (z < 0.7) return 'compact';
    return 'full';
  });
}
