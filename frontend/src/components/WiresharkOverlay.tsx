import { useCallback, useRef, useState } from 'react';
import type { Container } from '../data/sampleTopology';
import { getAuthToken, downloadPcap } from '../api/client';

export interface WiresharkOverlayProps {
  sessions: Container[];
  activeId: string;
  onActivate: (id: string) => void;
  onClose: (id: string) => void;
  backendId: string | null;
  minimized: boolean;
  onMinimizedChange: (minimized: boolean) => void;
}

// ── Single Wireshark session (iframe to noVNC) ─────────────────

interface WiresharkSessionProps {
  container: Container;
  backendId: string | null;
  active: boolean;
}

function WiresharkSession({ container, backendId, active }: WiresharkSessionProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  if (!backendId) {
    return (
      <div style={{ display: active ? 'flex' : 'none', alignItems: 'center', justifyContent: 'center', flex: 1, color: 'var(--neon-orange)' }}>
        Topology is not deployed.
      </div>
    );
  }

  const token = getAuthToken();
  const encodedId = encodeURIComponent(container.id);
  const src = `/api/topologies/${backendId}/capture/${encodedId}/view/?token=${token}`;

  return (
    <div
      style={{
        display: active ? 'flex' : 'none',
        flexDirection: 'column',
        flex: 1,
        minHeight: 0,
        position: 'relative',
      }}
    >
      {loading && !error && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex',
          alignItems: 'center', justifyContent: 'center',
          background: '#0c0c0c', color: 'var(--neon-cyan)', zIndex: 1,
          fontSize: '14px',
        }}>
          Starting Wireshark...
        </div>
      )}
      {error && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex',
          alignItems: 'center', justifyContent: 'center',
          background: '#0c0c0c', color: 'var(--neon-red)', zIndex: 1,
          fontSize: '14px',
        }}>
          {error}
        </div>
      )}
      <iframe
        src={src}
        style={{
          flex: 1, border: 'none', width: '100%', minHeight: 0,
          background: '#0c0c0c',
        }}
        onLoad={() => setLoading(false)}
        onError={() => { setLoading(false); setError('Failed to load Wireshark'); }}
        allow="clipboard-write"
      />
    </div>
  );
}

// ── Download pcap button ─────────────────────────────────────────

function DownloadPcapButton({ backendId, activeSession }: { backendId: string | null; activeSession: Container | null }) {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDownload = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!backendId || !activeSession || downloading) return;
    setDownloading(true);
    setError(null);
    try {
      await downloadPcap(backendId, activeSession.id);
    } catch (err: any) {
      setError(err?.message || 'Download failed');
      setTimeout(() => setError(null), 3000);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <button
      onClick={handleDownload}
      disabled={downloading || !backendId || !activeSession}
      title={error || (downloading ? 'Downloading...' : 'Download the current capture file')}
      style={{
        background: error ? 'rgba(255,68,68,0.15)' : downloading ? 'rgba(0,229,255,0.1)' : 'rgba(180,77,255,0.12)',
        border: '1px solid',
        borderColor: error ? 'var(--neon-red, #ff4444)' : downloading ? 'var(--neon-cyan, #00e5ff)' : 'var(--neon-purple, #b44dff)',
        borderRadius: 4,
        color: error ? 'var(--neon-red, #ff4444)' : downloading ? 'var(--neon-cyan, #00e5ff)' : 'var(--neon-purple, #b44dff)',
        cursor: downloading ? 'wait' : 'pointer',
        fontSize: 11, fontWeight: 600, padding: '3px 10px', lineHeight: 1,
        fontFamily: 'inherit', letterSpacing: '0.5px',
      }}
      onMouseEnter={(e) => { if (!downloading && !error) { e.currentTarget.style.background = 'rgba(180,77,255,0.25)'; e.currentTarget.style.color = '#fff'; } }}
      onMouseLeave={(e) => { if (!downloading && !error) { e.currentTarget.style.background = 'rgba(180,77,255,0.12)'; e.currentTarget.style.color = 'var(--neon-purple, #b44dff)'; } }}
    >
      {downloading ? 'Saving...' : error ? 'Error' : 'Save PCAP'}
    </button>
  );
}

// ── Floating popup window ────────────────────────────────────────

const DEFAULT_WIDTH = 900;
const DEFAULT_HEIGHT = 600;
const MIN_WIDTH = 400;
const MIN_HEIGHT = 300;
const TITLEBAR_HEIGHT = 36;

export function WiresharkOverlay({
  sessions,
  activeId,
  onActivate,
  onClose,
  backendId,
  minimized,
  onMinimizedChange,
}: WiresharkOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState(() => ({
    x: Math.max(40, Math.round((window.innerWidth - DEFAULT_WIDTH) / 2)),
    y: Math.max(40, Math.round((window.innerHeight - DEFAULT_HEIGHT) / 2)),
  }));
  const [size, setSize] = useState({ w: DEFAULT_WIDTH, h: DEFAULT_HEIGHT });
  const dragState = useRef<{ startX: number; startY: number; origX: number; origY: number } | null>(null);
  const resizeState = useRef<{ startX: number; startY: number; origW: number; origH: number } | null>(null);

  // ── Drag (title bar) ──────────────────────────────────
  const onDragStart = useCallback((e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('button')) return;
    e.preventDefault();
    dragState.current = { startX: e.clientX, startY: e.clientY, origX: pos.x, origY: pos.y };

    const onMove = (ev: MouseEvent) => {
      if (!dragState.current) return;
      const dx = ev.clientX - dragState.current.startX;
      const dy = ev.clientY - dragState.current.startY;
      setPos({
        x: Math.max(0, Math.min(window.innerWidth - 100, dragState.current.origX + dx)),
        y: Math.max(0, Math.min(window.innerHeight - TITLEBAR_HEIGHT, dragState.current.origY + dy)),
      });
    };
    const onUp = () => {
      dragState.current = null;
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    document.body.style.cursor = 'grabbing';
    document.body.style.userSelect = 'none';
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [pos.x, pos.y]);

  // ── Resize (bottom-right corner) ──────────────────────
  const onResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    resizeState.current = { startX: e.clientX, startY: e.clientY, origW: size.w, origH: size.h };

    const onMove = (ev: MouseEvent) => {
      if (!resizeState.current) return;
      const dx = ev.clientX - resizeState.current.startX;
      const dy = ev.clientY - resizeState.current.startY;
      setSize({
        w: Math.max(MIN_WIDTH, resizeState.current.origW + dx),
        h: Math.max(MIN_HEIGHT, resizeState.current.origH + dy),
      });
    };
    const onUp = () => {
      resizeState.current = null;
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    document.body.style.cursor = 'nwse-resize';
    document.body.style.userSelect = 'none';
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [size.w, size.h]);

  // If minimized, just show a small bar in the corner
  if (minimized) {
    return (
      <div
        style={{
          position: 'fixed',
          bottom: 8,
          right: 8,
          zIndex: 9000,
          background: '#1a1a2e',
          border: '1px solid var(--neon-purple, #b44dff)',
          borderRadius: 6,
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          padding: '4px 8px',
          cursor: 'pointer',
          boxShadow: '0 2px 12px rgba(180,77,255,0.3)',
        }}
        onClick={() => onMinimizedChange(false)}
        title="Restore Wireshark"
      >
        <span style={{ color: 'var(--neon-purple, #b44dff)', fontSize: 12, fontWeight: 600 }}>
          Wireshark ({sessions.length})
        </span>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      style={{
        position: 'fixed',
        left: pos.x,
        top: pos.y,
        width: size.w,
        height: size.h,
        zIndex: 9000,
        display: 'flex',
        flexDirection: 'column',
        background: '#0c0c0c',
        border: '1px solid var(--neon-purple, #b44dff)',
        borderRadius: 8,
        boxShadow: '0 4px 24px rgba(180,77,255,0.35), 0 0 1px rgba(180,77,255,0.6)',
        overflow: 'hidden',
      }}
    >
      {/* Title bar — draggable */}
      <div
        onMouseDown={onDragStart}
        style={{
          height: TITLEBAR_HEIGHT,
          minHeight: TITLEBAR_HEIGHT,
          background: '#1a1a2e',
          borderBottom: '1px solid var(--neon-purple, #b44dff)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 6px',
          cursor: 'grab',
          gap: 2,
          userSelect: 'none',
        }}
      >
        {/* Tabs */}
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden', gap: 2 }}>
          {sessions.map((c) => (
            <div
              key={c.id}
              onClick={() => onActivate(c.id)}
              style={{
                padding: '4px 10px',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                borderRadius: '4px 4px 0 0',
                background: c.id === activeId ? 'rgba(180,77,255,0.15)' : 'transparent',
                color: c.id === activeId ? 'var(--neon-purple, #b44dff)' : '#888',
                borderBottom: c.id === activeId ? '2px solid var(--neon-purple, #b44dff)' : '2px solid transparent',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                whiteSpace: 'nowrap',
              }}
            >
              <span>{c.name}</span>
              <button
                onClick={(e) => { e.stopPropagation(); onClose(c.id); }}
                title="Stop Capture"
                style={{
                  background: 'none', border: 'none', color: '#888',
                  cursor: 'pointer', fontSize: 14, lineHeight: 1, padding: 0,
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--neon-red, #ff4444)')}
                onMouseLeave={(e) => (e.currentTarget.style.color = '#888')}
              >
                x
              </button>
            </div>
          ))}
        </div>

        {/* Window controls */}
        <DownloadPcapButton
          backendId={backendId}
          activeSession={sessions.find((c) => c.id === activeId) ?? null}
        />
        <button
          onClick={() => onMinimizedChange(true)}
          title="Minimize"
          style={{
            background: 'none', border: 'none', color: '#888',
            cursor: 'pointer', fontSize: 16, padding: '0 4px', lineHeight: 1,
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = '#fff')}
          onMouseLeave={(e) => (e.currentTarget.style.color = '#888')}
        >
          _
        </button>
      </div>

      {/* Content area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        {sessions.map((c) => (
          <WiresharkSession
            key={c.id}
            container={c}
            backendId={backendId}
            active={c.id === activeId}
          />
        ))}
      </div>

      {/* Resize handle (bottom-right corner) */}
      <div
        onMouseDown={onResizeStart}
        style={{
          position: 'absolute',
          bottom: 0,
          right: 0,
          width: 16,
          height: 16,
          cursor: 'nwse-resize',
          background: 'linear-gradient(135deg, transparent 50%, rgba(180,77,255,0.4) 50%)',
          borderRadius: '0 0 8px 0',
        }}
      />
    </div>
  );
}