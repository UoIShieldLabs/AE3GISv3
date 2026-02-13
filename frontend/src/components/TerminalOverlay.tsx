import { useEffect, useRef, useState, useCallback } from 'react';
import type { KeyboardEvent } from 'react';
import type { Container } from '../data/sampleTopology';

interface TerminalOverlayProps {
  container: Container;
  backendId: string | null;
  deployStatus: string;
  topoName: string;
  onClose: () => void;
}

type ConnStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

const STATUS_COLOR: Record<ConnStatus, string> = {
  connecting: '#f0a500',
  connected: '#00ff9f',
  disconnected: '#808090',
  error: '#ff3344',
};

export function TerminalOverlay({
  container,
  backendId,
  deployStatus,
  topoName,
  onClose,
}: TerminalOverlayProps) {
  const [lines, setLines] = useState<string[]>([]);
  const [input, setInput] = useState('');
  const [connStatus, setConnStatus] = useState<ConnStatus>('connecting');
  const [history, setHistory] = useState<string[]>([]);
  const [, setHistoryIdx] = useState(-1);

  const wsRef = useRef<WebSocket | null>(null);
  const outputRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const appendText = useCallback((rawText: string) => {
    // Strip ANSI escape codes emitted by the PTY, then normalise line endings
    const text = rawText
      .replace(/\x1b\[[^a-zA-Z]*[a-zA-Z]/g, '') // CSI sequences  (e.g. colours, cursor)
      .replace(/\x1b[^[]/g, '')                   // other ESC sequences
      .replace(/\r\n/g, '\n')                      // CRLF → LF
      .replace(/\r/g, '\n');                       // bare CR → LF

    setLines((prev) => {
      const parts = text.split('\n');
      if (parts.length === 1) {
        const next = [...prev];
        if (next.length === 0) return [parts[0]];
        next[next.length - 1] += parts[0];
        return next;
      }
      const next = [...prev];
      if (next.length === 0) next.push('');
      next[next.length - 1] += parts[0];
      for (let i = 1; i < parts.length; i++) {
        next.push(parts[i]);
      }
      return next;
    });
  }, []);

  useEffect(() => {
    if (!backendId || deployStatus !== 'deployed') {
      setConnStatus('error');
      setLines(['Topology is not deployed. Deploy it first to open a terminal.']);
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/topologies/ws/${backendId}/exec/${container.id}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    setConnStatus('connecting');
    setLines([]);

    ws.onopen = () => setConnStatus('connecting');

    ws.onmessage = (ev: MessageEvent<string>) => {
      setConnStatus((prev) => (prev === 'connecting' ? 'connected' : prev));
      appendText(ev.data as string);
    };

    ws.onclose = () => {
      setConnStatus('disconnected');
      appendText('\r\n[connection closed]');
    };

    ws.onerror = () => {
      setConnStatus('error');
      appendText('\r\n[websocket error]');
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [backendId, container.id, deployStatus, appendText]);

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [lines]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const sendInput = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(input + '\n');
    // Don't echo locally — the PTY echoes input back through the server
    if (input.trim()) {
      setHistory((prev) => [input, ...prev.slice(0, 99)]);
    }
    setHistoryIdx(-1);
    setInput('');
  }, [input]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        sendInput();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setHistoryIdx((i) => {
          const next = Math.min(i + 1, history.length - 1);
          if (next >= 0) setInput(history[next]);
          return next;
        });
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setHistoryIdx((i) => {
          const next = Math.max(i - 1, -1);
          setInput(next >= 0 ? history[next] : '');
          return next;
        });
      } else if (e.key === 'c' && e.ctrlKey) {
        e.preventDefault();
        const ws = wsRef.current;
        if (ws?.readyState === WebSocket.OPEN) ws.send('\x03');
        setInput('');
      }
    },
    [sendInput, history],
  );

  const isConnected = connStatus === 'connected';
  const dockerName = `clab-${topoName || 'ae3gis-topology'}-${container.id}`;

  return (
    <div className="terminal-overlay" onClick={onClose}>
      <div
        className="terminal-window"
        onClick={(e) => e.stopPropagation()}
        style={{ height: '520px' }}
      >
        <div className="terminal-titlebar">
          <span className="terminal-titlebar-text">
            <span style={{ color: STATUS_COLOR[connStatus], marginRight: '8px' }}>●</span>
            {dockerName} — {container.ip}
          </span>
          <button className="terminal-titlebar-close" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="terminal-body" style={{ padding: 0, display: 'flex', flexDirection: 'column' }}>
          <div ref={outputRef} className="terminal-output">
            {lines.map((line, i) => (
              <div key={i} className="terminal-line">
                {line || '\u00a0'}
              </div>
            ))}
          </div>

          <div className="terminal-input-row">
            <span className="terminal-prompt">{'$ '}</span>
            <input
              ref={inputRef}
              className="terminal-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!isConnected}
              placeholder={
                connStatus === 'connecting'
                  ? 'connecting...'
                  : connStatus !== 'connected'
                  ? 'not connected'
                  : ''
              }
              spellCheck={false}
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="off"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
