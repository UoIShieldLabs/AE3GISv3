import { describe, it, expect } from 'vitest';
import { computeTreeLayout, computeCircleLayout, computeGridLayout } from '../algorithms';
import { nextFreePosition, boundsOf } from '../placement';

const box = (id: string) => ({ id, width: 100, height: 50 });

describe('layout algorithms', () => {
  it('tree layout centres a parent over its children and keeps input order', () => {
    const pos = computeTreeLayout([box('r'), box('a'), box('b')], [{ source: 'r', target: 'a' }, { source: 'r', target: 'b' }]);
    const r = pos.get('r')!, a = pos.get('a')!, b = pos.get('b')!;
    expect(a.y).toBeGreaterThan(r.y);
    expect(a.x).toBeLessThan(b.x);
    expect(r.x + 50).toBeCloseTo((a.x + b.x + 100) / 2, 5);
  });

  it('tree layout tolerates cycles', () => {
    const pos = computeTreeLayout([box('a'), box('b')], [{ source: 'a', target: 'b' }, { source: 'b', target: 'a' }]);
    expect(pos.size).toBe(2);
  });

  it('circle layout places all nodes without overlap of positions', () => {
    const nodes = ['a', 'b', 'c', 'd', 'e'].map(box);
    const pos = computeCircleLayout(nodes);
    expect(new Set([...pos.values()].map((p) => `${p.x.toFixed(0)},${p.y.toFixed(0)}`)).size).toBe(5);
  });

  it('grid layout is row-major', () => {
    const pos = computeGridLayout(['a', 'b', 'c', 'd'].map(box));
    expect(pos.get('a')!.y).toBe(pos.get('b')!.y);
    expect(pos.get('c')!.y).toBeGreaterThan(pos.get('a')!.y);
  });
});

describe('placement', () => {
  it('nextFreePosition avoids occupied rects', () => {
    const size = { width: 100, height: 50 };
    const first = nextFreePosition([], size);
    const occupied = [{ ...first, ...size }];
    const second = nextFreePosition(occupied, size);
    expect(second).not.toEqual(first);
    expect(second.x >= first.x + size.width || second.y >= first.y + size.height).toBe(true);
  });

  it('boundsOf spans all rects', () => {
    const b = boundsOf([{ x: 0, y: 0, width: 10, height: 10 }, { x: 40, y: 20, width: 10, height: 5 }])!;
    expect(b).toEqual({ x: 0, y: 0, width: 50, height: 25 });
  });
});
