import type { InternalNode } from '@xyflow/react';
import type { Position } from '@/types/topology';

interface Box extends Position {
  width: number;
  height: number;
}

function boxOf(node: InternalNode): Box {
  const { x, y } = node.internals.positionAbsolute;
  const width = node.measured?.width ?? node.width ?? 0;
  const height = node.measured?.height ?? node.height ?? 0;
  return { x, y, width, height };
}

function center(b: Box): Position {
  return { x: b.x + b.width / 2, y: b.y + b.height / 2 };
}

/** Point where the ray from `b`'s centre toward `toward` exits `b`'s rectangle. */
function exitPoint(b: Box, toward: Position): Position {
  const c = center(b);
  const dx = toward.x - c.x;
  const dy = toward.y - c.y;
  if (dx === 0 && dy === 0) return c;
  const hw = b.width / 2;
  const hh = b.height / 2;
  const tx = dx !== 0 ? hw / Math.abs(dx) : Infinity;
  const ty = dy !== 0 ? hh / Math.abs(dy) : Infinity;
  const t = Math.min(tx, ty);
  return { x: c.x + dx * t, y: c.y + dy * t };
}

export interface FloatingEdgeParams {
  sx: number;
  sy: number;
  tx: number;
  ty: number;
}

/** Endpoints on the borders of both nodes along the line between their centres. */
export function floatingEdgeParams(source: InternalNode, target: InternalNode): FloatingEdgeParams {
  const sb = boxOf(source);
  const tb = boxOf(target);
  const s = exitPoint(sb, center(tb));
  const t = exitPoint(tb, center(sb));
  return { sx: s.x, sy: s.y, tx: t.x, ty: t.y };
}
