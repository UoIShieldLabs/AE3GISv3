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

  it('drops what the canvas does not draw: a click on a device after drilling into its subnet selects the device alone', () => {
    // The subnet was selected (then double-clicked to open); inside it, React
    // Flow only knows the devices, so its click selects the device and has
    // nothing to deselect.
    const onCanvas = { nodes: new Set(['fw', 'sw', 'pc']), edges: new Set(['c1']) };
    const next = applySelectChanges({ nodeIds: ['subnet-a'], edgeIds: ['c-site'] }, 'nodeIds', [{ id: 'sw', selected: true }], onCanvas);
    expect(next).toEqual({ nodeIds: ['sw'], edgeIds: [] });
  });

  it('keeps everything on the canvas when adding to a selection', () => {
    const onCanvas = { nodes: new Set(['a', 'b', 'c']), edges: new Set(['e']) };
    const next = applySelectChanges({ nodeIds: ['a', 'hidden'], edgeIds: ['e'] }, 'edgeIds', [{ id: 'e', selected: true }], onCanvas);
    expect(next).toEqual({ nodeIds: ['a'], edgeIds: ['e'] });
  });

  it('is idempotent, so a repeated change settles instead of flip-flopping', () => {
    const once = applySelectChanges({ nodeIds: ['hA'], edgeIds: [] }, 'edgeIds', [{ id: 'c2', selected: true }]);
    expect(applySelectChanges(once, 'edgeIds', [{ id: 'c2', selected: true }])).toEqual(once);
  });
});
