import type { Position } from '@/types/topology';
import { GRID, PLACEMENT_GAP } from '../constants';

export interface Rect extends Position {
  width: number;
  height: number;
}

export function snapPosition(p: Position, grid = GRID): Position {
  return { x: Math.round(p.x / grid) * grid, y: Math.round(p.y / grid) * grid };
}

function overlaps(a: Rect, b: Rect, gap: number): boolean {
  return a.x < b.x + b.width + gap && a.x + a.width + gap > b.x && a.y < b.y + b.height + gap && a.y + a.height + gap > b.y;
}

/**
 * First free slot for a box of `size`, scanning rows from `origin` (or from the
 * top-left of the occupied region). Keeps new nodes near existing ones without
 * stacking them.
 */
export function nextFreePosition(occupied: Rect[], size: { width: number; height: number }, origin?: Position): Position {
  if (occupied.length === 0) return snapPosition(origin ?? { x: 0, y: 0 });
  const minX = Math.min(...occupied.map((r) => r.x));
  const minY = Math.min(...occupied.map((r) => r.y));
  const maxX = Math.max(...occupied.map((r) => r.x + r.width));
  const start = origin ?? { x: minX, y: minY };
  const stepX = size.width + PLACEMENT_GAP;
  const stepY = size.height + PLACEMENT_GAP;
  const cols = Math.max(1, Math.ceil((maxX - minX + stepX) / stepX) + 1);
  for (let row = 0; row < 200; row++) {
    for (let col = 0; col < cols; col++) {
      const candidate: Rect = { x: start.x + col * stepX, y: start.y + row * stepY, ...size };
      if (!occupied.some((r) => overlaps(candidate, r, PLACEMENT_GAP / 2))) return snapPosition(candidate);
    }
  }
  return snapPosition({ x: maxX + PLACEMENT_GAP, y: minY });
}

/** Bounding box of a set of rects (undefined when empty). */
export function boundsOf(rects: Rect[]): Rect | undefined {
  if (rects.length === 0) return undefined;
  const minX = Math.min(...rects.map((r) => r.x));
  const minY = Math.min(...rects.map((r) => r.y));
  const maxX = Math.max(...rects.map((r) => r.x + r.width));
  const maxY = Math.max(...rects.map((r) => r.y + r.height));
  return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
}
