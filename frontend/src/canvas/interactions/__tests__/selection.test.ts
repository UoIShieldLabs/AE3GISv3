import { describe, expect, it } from 'vitest';
import { applySelectChanges } from '../selection';

describe('applySelectChanges', () => {
  it('folds a marquee gesture (node + its link) into one selection', () => {
    const afterNodes = applySelectChanges({ nodeIds: [], edgeIds: [] }, 'nodeIds', [{ id: 'hA', selected: true }]);
    const afterEdges = applySelectChanges(afterNodes, 'edgeIds', [{ id: 'c2', selected: true }]);
    expect(afterEdges).toEqual({ nodeIds: ['hA'], edgeIds: ['c2'] });
  });

  it('adds and removes ids, keeping the order of what stays selected', () => {
    const next = applySelectChanges({ nodeIds: ['a', 'b', 'c'], edgeIds: ['e'] }, 'nodeIds', [
      { id: 'b', selected: false },
      { id: 'd', selected: true },
    ]);
    expect(next).toEqual({ nodeIds: ['a', 'c', 'd'], edgeIds: ['e'] });
  });

  it('is idempotent, so a repeated change settles instead of flip-flopping', () => {
    const once = applySelectChanges({ nodeIds: ['hA'], edgeIds: [] }, 'edgeIds', [{ id: 'c2', selected: true }]);
    expect(applySelectChanges(once, 'edgeIds', [{ id: 'c2', selected: true }])).toEqual(once);
  });
});
