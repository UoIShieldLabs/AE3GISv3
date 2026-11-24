import { useEffect } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router';
import { useAppStore } from '@/store';
import { restoreSession } from '@/features/auth/actions';
import { ChoosePasswordScreen } from '@/features/auth/ChoosePasswordScreen';
import { installImageRefresh } from '@/features/images/imagePolling';
import { Spinner } from '@/ui';

/** Every route but /login: finds out who this tab is signed in as, sends a
 *  signed-out tab to the login page (and back after), asks for a new password
 *  after a temporary one, and only then starts the app-wide refreshers that
 *  call the API. With accounts off it passes straight through. */
export function RequireAuth() {
  const status = useAppStore((s) => s.authStatus);
  const mustChangePassword = useAppStore((s) => !!s.user?.must_change_password);
  const location = useLocation();

  useEffect(() => {
    if (status === 'unknown') void restoreSession();
  }, [status]);

  // Image build statuses (palette dots, inspector, Images sheet) stay fresh
  // from one app-wide refresher, once requests can authenticate.
  const ready = status === 'signedIn' && !mustChangePassword;
  useEffect(() => {
    if (ready) installImageRefresh();
  }, [ready]);

  if (status === 'unknown') {
    return (
      <div className="flex h-full items-center justify-center bg-app">
        <Spinner />
      </div>
    );
  }
  if (status === 'signedOut') {
    const next = `${location.pathname}${location.search}`;
    return <Navigate to={next === '/' ? '/login' : `/login?next=${encodeURIComponent(next)}`} replace />;
  }
  // A temporary password: the backend refuses everything until it is replaced.
  if (mustChangePassword) return <ChoosePasswordScreen />;
  return <Outlet />;
}
