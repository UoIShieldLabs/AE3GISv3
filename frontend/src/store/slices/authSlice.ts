import type { AuthSlice, SliceCreator } from '../types';

/** Who is signed in. The flows (restore, sign in/up/out) are plain functions in
 *  features/auth/actions.ts; this only holds what they found. */
export const createAuthSlice: SliceCreator<AuthSlice> = (set) => ({
  authRequired: null,
  signupOpen: false,
  user: null,
  authStatus: 'unknown',

  setAuth: (patch) => set(patch, false, 'setAuth'),
});
