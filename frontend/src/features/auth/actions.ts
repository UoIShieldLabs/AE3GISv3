// Sign-in flows (classroom mode). Plain functions over the store, like the
// deployment actions. With accounts off the backend answers /auth/me with the
// instructor and nobody ever sees the login page.
import * as api from '@/api/client';
import { clearToken, getToken, setToken, setUnauthorizedHandler } from '@/api/session';
import { useAppStore } from '@/store';
import { toast } from '@/ui';
import { disposeAllSessions } from '@/features/terminal/sessions';
import { stopPolling } from '@/features/deployment/statusPolling';

let restoring: Promise<void> | null = null;

/** Find out whether accounts are on and who this tab is signed in as. */
export function restoreSession(): Promise<void> {
  restoring ??= (async () => {
    const set = useAppStore.getState().setAuth;
    let health: api.Health | null = null;
    try {
      health = await api.getHealth();
    } catch {
      // Backend unreachable: let the app load as before; a 401 later still
      // brings the login page up.
      set({ authRequired: null, user: null, authStatus: 'signedIn' });
      return;
    }
    set({ authRequired: health.auth_required, signupOpen: health.signup_open ?? false });
    if (health.auth_required && !getToken()) {
      set({ user: null, authStatus: 'signedOut' });
      return;
    }
    try {
      const me = await api.getMe();
      set({ user: me.user, authStatus: 'signedIn' });
    } catch {
      clearToken();
      set({ user: null, authStatus: 'signedOut' });
    }
  })().finally(() => {
    restoring = null;
  });
  return restoring;
}

function signedIn(session: api.SignIn, remember: boolean): void {
  setToken(session.token, remember);
  useAppStore.getState().setAuth({ user: session.user, authStatus: 'signedIn' });
}

export async function signIn(username: string, password: string, remember: boolean): Promise<void> {
  signedIn(await api.login(username, password), remember);
}

export async function signUp(username: string, password: string, joinCode: string, remember: boolean): Promise<void> {
  signedIn(await api.signup(username, password, joinCode), remember);
}

/** Forget everything tied to the session: terminals, polling, the open topology. */
function teardown(): void {
  disposeAllSessions();
  stopPolling();
  const s = useAppStore.getState();
  s.clearBackend();
  s.newTopology();
  clearToken();
  s.setAuth({ user: null, authStatus: 'signedOut' });
}

export async function signOut(): Promise<void> {
  try {
    await api.logout();
  } catch {
    /* the session ends locally either way */
  }
  teardown();
}

/** A request came back 401: the session ended (expired, password reset,
 *  removed). Once per sign-in; the login page takes it from there. */
function onUnauthorized(): void {
  const s = useAppStore.getState();
  if (!s.authRequired || s.authStatus !== 'signedIn') return;
  teardown();
  toast.info('Signed out', { description: 'Your session ended; sign in again.' });
}

setUnauthorizedHandler(onUnauthorized);
