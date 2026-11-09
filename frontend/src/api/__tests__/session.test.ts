import { beforeEach, describe, expect, it, vi } from 'vitest';

// The module caches the token; load a fresh copy per test.
async function load() {
  vi.resetModules();
  return import('../session');
}

beforeEach(() => {
  sessionStorage.clear();
  localStorage.clear();
});

describe('session token', () => {
  it('lives in this tab unless remembered', async () => {
    const s = await load();
    expect(s.getToken()).toBeNull();
    s.setToken('tab-token', false);
    expect(s.getToken()).toBe('tab-token');
    expect(sessionStorage.getItem('ae3gis.session')).toBe('tab-token');
    expect(localStorage.getItem('ae3gis.session')).toBeNull();
  });

  it('a remembered token survives a new tab (fresh module, empty sessionStorage)', async () => {
    (await load()).setToken('kept', true);
    sessionStorage.clear();
    expect((await load()).getToken()).toBe('kept');
  });

  it("signing out in one tab does not forget another account's remembered token", async () => {
    localStorage.setItem('ae3gis.session', 'instructor-token');
    const s = await load();
    s.setToken('student-token', false);
    expect(localStorage.getItem('ae3gis.session')).toBeNull(); // not remembered: dropped
    localStorage.setItem('ae3gis.session', 'instructor-token');
    s.clearToken();
    expect(s.getToken()).toBeNull();
    expect(localStorage.getItem('ae3gis.session')).toBe('instructor-token');
  });

  it('reports a 401 to whoever registered', async () => {
    const s = await load();
    const handler = vi.fn();
    s.notifyUnauthorized(); // nobody registered: no-op
    s.setUnauthorizedHandler(handler);
    s.notifyUnauthorized();
    expect(handler).toHaveBeenCalledTimes(1);
  });
});
