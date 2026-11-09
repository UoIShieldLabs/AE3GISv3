import { ExternalLink, RotateCw } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import * as api from '@/api/client';
import { useAppStore } from '@/store';
import { IconButton, Spinner } from '@/ui';

/** A node's own web UI in the dock, relayed through the backend. Reload and
 *  "open in a new tab" help when presenting (fullscreen the dock = projector).
 *  In classroom mode the relay's pages (and their assets and forms) cannot
 *  send a header, so this tab's sign-in is handed over as a cookie first. */
export function WebUiPanel({ nodeId }: { nodeId: string }) {
  const backendId = useAppStore((s) => s.backendId);
  const authRequired = useAppStore((s) => !!s.authRequired);
  const ref = useRef<HTMLIFrameElement>(null);
  const [nonce, setNonce] = useState(0);
  // The reload (nonce) the cookie was last set for.
  const [cookieFor, setCookieFor] = useState<number | null>(null);

  useEffect(() => {
    if (!authRequired) return;
    let alive = true;
    // A failure still loads the frame: the relay then explains (401).
    void api.issueWebUiCookie().catch(() => undefined).finally(() => { if (alive) setCookieFor(nonce); });
    return () => { alive = false; };
  }, [authRequired, nonce]);

  if (!backendId) return <div className="p-3 text-xs text-fg-subtle">Save the topology first.</div>;
  const src = api.webUiUrl(backendId, nodeId);
  const ready = !authRequired || cookieFor === nonce;
  return (
    <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col">
      <div className="flex items-center gap-1 border-b border-border px-2 py-1 text-2xs text-fg-muted">
        <span className="min-w-0 flex-1 truncate font-mono">{nodeId} · web UI</span>
        <IconButton label="Reload" size="icon-xs" onClick={() => setNonce((n) => n + 1)}><RotateCw /></IconButton>
        <IconButton label="Open in a new tab" size="icon-xs" disabled={!ready} onClick={() => window.open(src, '_blank', 'noopener')}><ExternalLink /></IconButton>
      </div>
      {ready ? (
        <iframe
          ref={ref}
          key={nonce}
          src={src}
          title={`${nodeId} web UI`}
          className="min-h-0 flex-1 bg-white"
          sandbox="allow-scripts allow-forms allow-same-origin"
        />
      ) : (
        <div className="flex flex-1 items-center justify-center"><Spinner /></div>
      )}
    </div>
  );
}
