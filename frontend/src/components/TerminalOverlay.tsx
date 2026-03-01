import { useEffect, useRef, useCallback, useState } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import type { Container } from '../data/sampleTopology';
import { wsUrl as buildWsUrl, getAuthToken } from '../api/client';

export interface TerminalOverlayProps {
  sessions: Container[];
  activeId: string;
  onActivate: (id: string) => void;
  onClose: (id: string) => void;
  backendId: string | null;
  deployStatus: string;
  topoName: string;
  minimized: boolean;
  onMinimizedChange: (minimized: boolean) => void;
}

// ── Single terminal session (xterm.js + WebSocket PTY) ─────────────

interface TerminalSessionProps {
  container: Container;
  backendId: string | null;
  deployStatus: string;
  topoName: string;
  active: boolean;
}

function TerminalSession({ container, backendId, deployStatus, active }: TerminalSessionProps) {
  const termDivRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Initialise xterm.js once on mount
  useEffect(() => {
    if (!termDivRef.current) return;

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: "'Share Tech Mono', 'Courier New', monospace",
      theme: {
        background: '#0c0c0c',
        foreground: '#d0d0d8',
        cursor: '#00ff9f',
        selectionBackground: 'rgba(0, 255, 159, 0.3)',
      },
      scrollback: 5000,
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(termDivRef.current);
    try { fitAddon.fit(); } catch { /* ignore before layout */ }

    termRef.current = term;
    fitAddonRef.current = fitAddon;

    // Auto-fit whenever the container div changes size (handles tab show/hide)
    const observer = new ResizeObserver(() => {
      try { fitAddon.fit(); } catch { /* ignore */ }
    });
    observer.observe(termDivRef.current);

    return () => {
      observer.disconnect();
      term.dispose();
      termRef.current = null;
      fitAddonRef.current = null;
    };
  }, []);

  // Also fit on explicit active change (belt-and-suspenders for display:none transitions)
  useEffect(() => {
    if (!active) return;
    const t = setTimeout(() => {
      try { fitAddonRef.current?.fit(); } catch { /* ignore */ }
    }, 0);
    return () => clearTimeout(t);
  }, [active]);

  // WebSocket connection — reconnects when backend/container/status changes
  useEffect(() => {
    const term = termRef.current;
    if (!term) return;

    if (!backendId || deployStatus !== 'deployed') {
      term.writeln('\r\n\x1b[33mTopology is not deployed. Deploy it first to open a terminal.\x1b[0m');
      return;
    }

    let closed = false;
    term.reset();

    const encodedId = encodeURIComponent(container.id);
    const precheckUrl = `/api/topologies/${backendId}/exec/${encodedId}/precheck`;
    const wsUrlStr = buildWsUrl(`/api/topologies/ws/${backendId}/exec/${encodedId}`);

    const run = async () => {
      try {
        const headers: Record<string, string> = {};
        const token = getAuthToken();
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch(precheckUrl, { headers });
        if (closed) return;
        if (!res.ok) {
          term.writeln(`\r\n\x1b[31m[error] Precheck failed: HTTP ${res.status}\x1b[0m`);
          return;
        }

        const precheck = await res.json() as { reason?: string; detail?: string };
        if (closed) return;
        if (precheck.reason !== 'ok') {
          term.writeln(`\r\n\x1b[31m[error] ${precheck.reason ?? 'unknown'}\x1b[0m`);
          if (precheck.detail) term.writeln(`\x1b[31m[detail] ${precheck.detail}\x1b[0m`);
          return;
        }

        const ws = new WebSocket(wsUrlStr);
        wsRef.current = ws;

        ws.onopen = () => {
          // Send current terminal dimensions so the PTY is sized correctly
          if (termRef.current) {
            const { cols, rows } = termRef.current;
            ws.send(JSON.stringify({ type: 'resize', cols, rows }));
          }
        };

        ws.onmessage = (ev: MessageEvent<string>) => {
          term.write(ev.data as string);
        };

        ws.onclose = (ev: CloseEvent) => {
          if (!closed) term.writeln(`\r\n\x1b[90m[connection closed] code=${ev.code}\x1b[0m`);
        };

        ws.onerror = () => {
          term.writeln('\r\n\x1b[31m[websocket error]\x1b[0m');
        };

        // Forward all keystrokes immediately — no line buffering
        const onDataDisposable = term.onData((data) => {
          if (ws.readyState === WebSocket.OPEN) ws.send(data);
        });

        // Tell the backend whenever the terminal is resized
        const onResizeDisposable = term.onResize(({ cols, rows }) => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'resize', cols, rows }));
          }
        });

        return () => {
          onDataDisposable.dispose();
          onResizeDisposable.dispose();
          ws.close();
        };
      } catch (err) {
        if (closed) return;
        term.writeln(`\r\n\x1b[31m[error] ${err instanceof Error ? err.message : String(err)}\x1b[0m`);
      }
    };

    let cleanup: (() => void) | undefined;
    void run().then((c) => { if (!closed) cleanup = c; });

    return () => {
      closed = true;
      cleanup?.();
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [backendId, container.id, deployStatus]);

  return (
    <div
      className="terminal-body"
      style={{ display: active ? 'flex' : 'none', padding: '4px', overflow: 'hidden' }}
    >
      <div ref={termDivRef} style={{ flex: 1, minHeight: 0 }} />
    </div>
  );
}

// ── Tab bar + multi-session panel ─────────────────────────────────

export function TerminalOverlay({
  sessions,
  activeId,
  onActivate,
  onClose,
  backendId,
  deployStatus,
  topoName,
  minimized,
  onMinimizedChange,
}: TerminalOverlayProps) {
  const [height, setHeight] = useState(300);
  const dragging = useRef(false);
  const panelRef = useRef<HTMLDivElement>(null);

  const handleTabClick = (id: string) => {
    if (id === activeId && !minimized) {
      onMinimizedChange(true);
    } else {
      onActivate(id);
      onMinimizedChange(false);
    }
  };

  // Drag-to-resize from the top edge
  const onDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
    const startY = e.clientY;
    const startH = height;

    const onMove = (ev: MouseEvent) => {
      if (!dragging.current) return;
      const delta = startY - ev.clientY;
      const newH = Math.max(120, Math.min(window.innerHeight * 0.85, startH + delta));
      setHeight(newH);
    };

    const onUp = () => {
      dragging.current = false;
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.body.style.cursor = 'ns-resize';
    document.body.style.userSelect = 'none';
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [height]);

  return (
    <div
      ref={panelRef}
      className={`terminal-panel${minimized ? ' terminal-panel--minimized' : ''}`}
      style={minimized ? undefined : { height }}
    >
      {/* Drag handle */}
      <div className="terminal-resize-handle" onMouseDown={onDragStart} />
      <div className="terminal-tabbar">
        <div className="terminal-tabs">
          {sessions.map((c) => (
            <div
              key={c.id}
              className={`terminal-tab${c.id === activeId && !minimized ? ' terminal-tab--active' : ''}`}
              onClick={() => handleTabClick(c.id)}
            >
              <span className="terminal-tab-label">{c.name}{c.ip ? ` — ${c.ip}` : ''}</span>
              <button
                className="terminal-tab-close"
                onClick={(e) => { e.stopPropagation(); onClose(c.id); }}
                title="Close"
              >
                ×
              </button>
            </div>
          ))}
        </div>
        <button
          className="terminal-tabbar-minimize"
          onClick={() => onMinimizedChange(!minimized)}
          title={minimized ? 'Restore' : 'Minimize'}
        >
          {minimized ? '▲' : '▼'}
        </button>
      </div>

      {sessions.map((c) => (
        <TerminalSession
          key={c.id}
          container={c}
          backendId={backendId}
          deployStatus={deployStatus}
          topoName={topoName}
          active={c.id === activeId && !minimized}
        />
      ))}
    </div>
  );
}
