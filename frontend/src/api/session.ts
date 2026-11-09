// The signed-in session's bearer token (classroom mode; see backend auth.py).
//
// Kept per tab in sessionStorage, so an instructor tab and a student tab can
// sit side by side in one browser; "remember me" also keeps it in localStorage
// so a new tab (or a restart) stays signed in. Storage can be unavailable
// (private windows, blocked site data): every access is guarded and the token
// then lives for this page load only.

const KEY = 'ae3gis.session';

let cached: string | null | undefined;

function read(storage: () => Storage): string | null {
  try {
    return storage().getItem(KEY);
  } catch {
    return null;
  }
}

function write(storage: () => Storage, value: string | null): void {
  try {
    if (value === null) storage().removeItem(KEY);
    else storage().setItem(KEY, value);
  } catch {
    /* storage unavailable: the in-memory copy still works */
  }
}

export function getToken(): string | null {
  if (cached === undefined) cached = read(() => sessionStorage) ?? read(() => localStorage);
  return cached;
}

export function setToken(token: string, remember: boolean): void {
  cached = token;
  write(() => sessionStorage, token);
  if (remember) write(() => localStorage, token);
  else if (read(() => localStorage) !== null) write(() => localStorage, null);
}

/** Forget this tab's token; a remembered one goes too if it is the same. */
export function clearToken(): void {
  const current = getToken();
  cached = null;
  write(() => sessionStorage, null);
  if (current !== null && read(() => localStorage) === current) write(() => localStorage, null);
}

// A request came back 401 (the session ended or was revoked). The store
// registers what to do (sign out, show the login page); the client only reports.
let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

export function notifyUnauthorized(): void {
  unauthorizedHandler?.();
}
