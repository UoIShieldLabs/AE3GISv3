import { useEffect, useRef } from 'react';
import '@xterm/xterm/css/xterm.css';
import { useResolvedTheme } from '@/app/theme';
import { acquireSession, getSession } from './sessions';

/** The view of a container's terminal session (see `sessions.ts`). Unmounting
 *  only detaches it: the shell lives until its dock tab is closed. */
export function TerminalSession({ tabId, containerId, active }: { tabId: string; containerId: string; active: boolean }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const theme = useResolvedTheme().id;

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const session = acquireSession(tabId, containerId);
    session.attach(host);
    const schedule = () => requestAnimationFrame(() => session.fit());
    schedule();
    const ro = new ResizeObserver(schedule);
    ro.observe(host);
    window.addEventListener('resize', schedule);
    document.fonts?.ready.then(schedule).catch(() => {});
    return () => {
      ro.disconnect();
      window.removeEventListener('resize', schedule);
      session.detach();
    };
  }, [tabId, containerId]);

  useEffect(() => { getSession(tabId)?.applyLook(); }, [theme, tabId]);

  useEffect(() => {
    if (!active) return;
    const ids = [0, 60, 180].map((ms) => window.setTimeout(() => getSession(tabId)?.fit(), ms));
    return () => ids.forEach(clearTimeout);
  }, [active, tabId]);

  return (
    <div className={active ? 'flex h-full min-h-0 flex-1 p-1' : 'hidden'}>
      <div ref={hostRef} className="min-h-0 flex-1" />
    </div>
  );
}
