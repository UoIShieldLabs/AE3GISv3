import { describe, expect, it } from 'vitest';
import { useAppStore } from '../index';

const S = () => useAppStore.getState();

describe('auth slice', () => {
  it('starts unknown and records what the flows found', () => {
    expect(S().authStatus).toBe('unknown');
    S().setAuth({ authRequired: true, signupOpen: true, user: { id: 'u', username: 'alice', role: 'student' }, authStatus: 'signedIn' });
    expect(S()).toMatchObject({ authRequired: true, signupOpen: true, authStatus: 'signedIn' });
    expect(S().user?.username).toBe('alice');
  });
});

describe('record meta (document slice)', () => {
  it('holds the account fields of the loaded record and clears with it', () => {
    S().setRecordMeta({ owner: { id: 'u', username: 'alice' }, published: true, sourceId: 'src', updateAvailable: true });
    expect(S()).toMatchObject({ published: true, sourceId: 'src', updateAvailable: true });
    expect(S().owner?.username).toBe('alice');
    S().clearBackend();
    expect(S()).toMatchObject({ owner: null, published: false, sourceId: null, updateAvailable: false });
  });
});
