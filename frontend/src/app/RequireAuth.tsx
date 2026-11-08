import { useEffect } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router';
import { useAppStore } from '@/store';
import { restoreSession } from '@/features/auth/actions';
import { installImageRefresh } from '@/features/images/imagePolling';
import { Spinner } from '@/ui';

/** Every route but /login: finds out who this tab is signed in as, sends a
 *  signed-out tab to the login page (and back after), and only then starts the
 *  app-wide refreshers that call the API. With accounts off it passes straight
 *  through. */
export function RequireAuth() {
  const status = useAppStore((s) => s.authStatus);
  const location = useLocation();

  useEffect(() => {
    if (status === 'unknown') void restoreSession();
  }, [status]);

  // Image build statuses (palette dots, inspector, Images sheet) stay fresh
  // from one app-wide refresher, once requests can authenticate.
  useEffect(() => {
    if (status === 'signedIn') installImageRefresh();
  }, [status]);

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
  return <Outlet />;
}
