import type { PulseSlice, SliceCreator } from '../types';

/** The live lab view (links carrying traffic, what runs in each node), fed by
 *  `features/pulse/pulse.ts` while the Tutorials panel is open; never saved. */
export const createPulseSlice: SliceCreator<PulseSlice> = (set) => ({
  pulseState: 'off',
  linkTraffic: {},
  nodeProcesses: {},
  setPulseState: (pulseState) => set({ pulseState }, false, 'setPulseState'),
  setPulse: (linkTraffic, nodeProcesses) => set({ linkTraffic, nodeProcesses }, false, 'setPulse'),
});
