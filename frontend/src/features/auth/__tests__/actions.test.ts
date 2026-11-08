import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '@/api/client';
import { getToken, notifyUnauthorized, setToken } from '@/api/session';
import { useAppStore } from '@/store';
import { restoreSession, signIn, signOut } from '../actions';

vi.mock('@/features/terminal/sessions', () => ({ disposeAllSessions: vi.fn() }));
vi.mock('@/features/deployment/statusPolling', () => ({ stopPolling: vi.fn() }));

const health = (auth_required: boolean, signup_open = false) =>
  ({ status: 'ok', version: 't', engine: 'fake', engine_ok: true, engine_detail: '', auth_required, signup_open, topologies: 0 }) as api.Health;
const student = { id: 's1', username: 'alice', role: 'student' as const };

const S = () => useAppStore.getState();

beforeEach(() => {
  vi.restoreAllMocks();
  sessionStorage.clear();
  localStorage.clear();
  setToken('', false);
  sessionStorage.clear();
  useAppStore.setState({ authRequired: null, signupOpen: false, user: null, authStatus: 'unknown' });
});

describe('restoreSession', () => {
  it('with accounts off, the tab is the instructor without signing in', async () => {
    vi.spyOn(api, 'getHealth').mockResolvedValue(health(false));
    vi.spyOn(api, 'getMe').mockResolvedValue({ user: { id: null, username: 'instructor', role: 'instructor' }, auth_required: false });
    await restoreSession();
    expect(S().authStatus).toBe('signedIn');
    expect(S().user?.role).toBe('instructor');
    expect(S().authRequired).toBe(false);
  });

  it('with accounts on and no token, the tab is signed out (and learns about sign-up)', async () => {
    vi.spyOn(api, 'getHealth').mockResolvedValue(health(true, true));
    const me = vi.spyOn(api, 'getMe');
    await restoreSession();
    expect(S().authStatus).toBe('signedOut');
    expect(S().signupOpen).toBe(true);
    expect(me).not.toHaveBeenCalled();
  });

  it('forgets a token the backend no longer accepts', async () => {
    setToken('stale', false);
    vi.spyOn(api, 'getHealth').mockResolvedValue(health(true));
    vi.spyOn(api, 'getMe').mockRejectedValue(new api.ApiError(401, 'Sign in required', 'unauthorized'));
    await restoreSession();
    expect(S().authStatus).toBe('signedOut');
    expect(getToken()).toBeNull();
  });
});

describe('signing in and out', () => {
  it('keeps the token and the user, then drops both', async () => {
    useAppStore.setState({ authRequired: true });
    vi.spyOn(api, 'login').mockResolvedValue({ token: 'tok', expires_at: '2030-01-01T00:00:00Z', user: student });
    await signIn('alice', 'pw', false);
    expect(getToken()).toBe('tok');
    expect(S().user).toEqual(student);
    expect(S().authStatus).toBe('signedIn');
    vi.spyOn(api, 'logout').mockResolvedValue(undefined);
    await signOut();
    expect(getToken()).toBeNull();
    expect(S().authStatus).toBe('signedOut');
  });

  it('a 401 elsewhere signs the tab out (once signed in, accounts on)', () => {
    useAppStore.setState({ authRequired: true, authStatus: 'signedIn', user: student });
    setToken('tok', false);
    notifyUnauthorized();
    expect(S().authStatus).toBe('signedOut');
    expect(S().user).toBeNull();
    expect(getToken()).toBeNull();
  });
});
