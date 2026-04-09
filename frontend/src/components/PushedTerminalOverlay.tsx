import { useEffect, useRef, useCallback, useState } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { wsUrl as buildWsUrl } from '../api/client';

export interface PushedSession {
  sessionId: string;
  topologyId: string;
  containerId: string;
  containerName: string;
  script: string;
  phaseName: string;
}

interface PushedTerminalOverlayProps {
  sessions: PushedSession[];
  activeId: string;
  onActivate: (id: string) => void;
  onClose: (id: string) => void;
  minimized: boolean;
  onMinimizedChange: (minimized: boolean) => void;
}

// ── Single pushed session terminal ───────────────────────────────────

interface PushedTerminalSessionProps {
  session: PushedSession;
  active: boolean;
}

function PushedTerminalSession({ session, active }: PushedTerminalSessionProps) {
  const termDivRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const fitAndSync = useCallback(() => {
    const term = termRef.current;
    const fitAddon = fitAddonRef.current;
    const host = termDivRef.current;
    if (!term || !fitAddon || !host) return;
    if (host.offsetParent === null) return;
    try { fitAddon.fit(); } catch { return; }
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
    }
  }, []);

  // Initialise xterm.js once on mount
  useEffect(() => {
    if (!termDivRef.current) return;
    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: "'DejaVu Sans Mono', 'Liberation Mono', 'Consolas', 'Courier New', monospace",
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
    termRef.current = term;
    fitAddonRef.current = fitAddon;

    const scheduleFit = () => requestAnimationFrame(() => fitAndSync());
    scheduleFit();
    const observer = new ResizeObserver(() => scheduleFit());
    observer.observe(termDivRef.current);
    window.addEventListener('resize', scheduleFit);
    document.fonts?.ready.then(() => scheduleFit()).catch(() => {});

    return () => {
      observer.disconnect();
      window.removeEventListener('resize', scheduleFit);
      term.dispose();
      termRef.current = null;
      fitAddonRef.current = null;
    };
  }, [fitAndSync]);

  // Fit when tab becomes active
  useEffect(() => {
    if (!active) return;
    const t1 = window.setTimeout(() => fitAndSync(), 0);
    const t2 = window.setTimeout(() => fitAndSync(), 50);
    const t3 = window.setTimeout(() => fitAndSync(), 150);
    return () => { window.clearTimeout(t1); window.clearTimeout(t2); window.clearTimeout(t3); };
  }, [active, fitAndSync]);

  // WebSocket connection to the exec session
  useEffect(() => {
    const term = termRef.current;
    if (!term) return;

    let closed = false;
    term.reset();

    const wsUrlStr = buildWsUrl(`/api/topologies/ws/${session.topologyId}/exec-session/${session.sessionId}`);

    const ws = new WebSocket(wsUrlStr);
    wsRef.current = ws;

    ws.onopen = () => fitAndSync();

    ws.onmessage = (ev: MessageEvent<string | ArrayBuffer | Blob>) => {
      let text: string;
      if (typeof ev.data === 'string') {
        if (ev.data === '{"type":"ping"}') return;
        text = ev.data;
      } else if (ev.data instanceof ArrayBuffer) {
        text = new TextDecoder().decode(ev.data);
      } else {
        ev.data.text().then((t) => term.write(t)).catch(() => {});
        return;
      }
      term.write(text);
    };

    ws.onclose = (ev: CloseEvent) => {
      if (!closed) term.writeln(`\r\n\x1b[90m[connection closed] code=${ev.code}\x1b[0m`);
    };

    ws.onerror = () => term.writeln('\r\n\x1b[31m[websocket error]\x1b[0m');

    const onDataDisposable = term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) ws.send(data);
    });

    const onResizeDisposable = term.onResize(({ cols, rows }) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'resize', cols, rows }));
      }
    });

    return () => {
      closed = true;
      onDataDisposable.dispose();
      onResizeDisposable.dispose();
      ws.close();
      wsRef.current = null;
    };
  }, [session.sessionId, session.topologyId, fitAndSync]);

  return (
    <div
      className="terminal-body"
      style={{ display: active ? 'flex' : 'none', padding: '4px', overflow: 'hidden' }}
    >
      <div ref={termDivRef} style={{ flex: 1, minHeight: 0 }} />
    </div>
  );
}

// ── Tab bar + multi-session panel ─────────────────────────────────────

export function PushedTerminalOverlay({
  sessions,
  activeId,
  onActivate,
  onClose,
  minimized,
  onMinimizedChange,
}: PushedTerminalOverlayProps) {
  const [height, setHeight] = useState(300);
  const dragging = useRef(false);

  const handleTabClick = (id: string) => {
    if (id === activeId && !minimized) {
      onMinimizedChange(true);
    } else {
      onActivate(id);
      onMinimizedChange(false);
    }
  };

  const onDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
    const startY = e.clientY;
    const startH = height;
    const onMove = (ev: MouseEvent) => {
      if (!dragging.current) return;
      const delta = startY - ev.clientY;
      setHeight(Math.max(120, Math.min(window.innerHeight * 0.85, startH + delta)));
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

  if (sessions.length === 0) return null;

  return (
    <div
      className={`terminal-panel${minimized ? ' terminal-panel--minimized' : ''}`}
      style={minimized ? undefined : { height, bottom: 0, borderTop: '2px solid var(--neon-purple, #b44dff)' }}
    >
      <div className="terminal-resize-handle" onMouseDown={onDragStart} />
      <div className="terminal-tabbar" style={{ borderColor: 'var(--neon-purple, #b44dff)' }}>
        <div className="terminal-tabs">
          {/* Phase label */}
          {sessions[0] && (
            <div style={{
              padding: '0 10px',
              fontSize: '11px',
              color: 'var(--neon-purple, #b44dff)',
              display: 'flex',
              alignItems: 'center',
              fontFamily: 'var(--font-mono)',
              letterSpacing: '0.5px',
              borderRight: '1px solid rgba(180,77,255,0.3)',
              marginRight: '4px',
            }}>
              {sessions[0].phaseName}
            </div>
          )}
          {sessions.map((s) => (
            <div
              key={s.sessionId}
              className={`terminal-tab${s.sessionId === activeId && !minimized ? ' terminal-tab--active' : ''}`}
              onClick={() => handleTabClick(s.sessionId)}
              style={s.sessionId === activeId && !minimized ? { borderColor: 'var(--neon-purple, #b44dff)' } : undefined}
            >
              <span className="terminal-tab-label">
                {s.containerName}
              </span>
              <button
                className="terminal-tab-close"
                onClick={(e) => { e.stopPropagation(); onClose(s.sessionId); }}
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

      {sessions.map((s) => (
        <PushedTerminalSession
          key={s.sessionId}
          session={s}
          active={s.sessionId === activeId && !minimized}
        />
      ))}
    </div>
  );
}
