import { ExternalLink, RotateCw } from 'lucide-react';
import { useRef, useState } from 'react';
import * as api from '@/api/client';
import { useAppStore } from '@/store';
import { IconButton } from '@/ui';

/** A node's own web UI in the dock, relayed through the backend. Reload and
 *  "open in a new tab" help when presenting (fullscreen the dock = projector). */
export function WebUiPanel({ nodeId }: { nodeId: string }) {
  const backendId = useAppStore((s) => s.backendId);
  const ref = useRef<HTMLIFrameElement>(null);
  const [nonce, setNonce] = useState(0);
  if (!backendId) return <div className="p-3 text-xs text-fg-subtle">Save the topology first.</div>;
  const src = api.webUiUrl(backendId, nodeId);
  return (
    <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col">
      <div className="flex items-center gap-1 border-b border-border px-2 py-1 text-2xs text-fg-muted">
        <span className="min-w-0 flex-1 truncate font-mono">{nodeId} · web UI</span>
        <IconButton label="Reload" size="icon-xs" onClick={() => setNonce((n) => n + 1)}><RotateCw /></IconButton>
        <IconButton label="Open in a new tab" size="icon-xs" onClick={() => window.open(src, '_blank', 'noopener')}><ExternalLink /></IconButton>
      </div>
      <iframe
        ref={ref}
        key={nonce}
        src={src}
        title={`${nodeId} web UI`}
        className="min-h-0 flex-1 bg-white"
        sandbox="allow-scripts allow-forms allow-same-origin"
      />
    </div>
  );
}
