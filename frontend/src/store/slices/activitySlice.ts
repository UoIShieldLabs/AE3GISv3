import type { ActivitySlice, SliceCreator } from '../types';

/** Captures and traffic runs in progress (from GET /runtime); never saved. */
export const createActivitySlice: SliceCreator<ActivitySlice> = (set) => ({
  activity: [],
  setActivity: (activity) => set({ activity }, false, 'setActivity'),
});
