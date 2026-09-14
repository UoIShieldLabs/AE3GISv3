import { useCallback, useEffect, useRef } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { execWsPath, wsUrl } from '@/api/client';
import { useAppShallow } from '@/store/selectors';
import { useResolvedTheme } from '@/app/theme';

const THEMES = {
  dark: { background: '#0b0d11', foreground: '#e6e8ec', cursor: '#5b8def', selectionBackground: 'rgba(91,141,239,0.35)' },
  light: { background: '#ffffff', foreground: '#171a21', cursor: '#2f6df6', selectionBackground: 'rgba(47,109,246,0.25)' },
};

/** One xterm.js instance bound to the exec WebSocket of a container. Stays mounted while its tab exists. */
export function TerminalSession({ containerId, active }: { containerId: string; active: boolean }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const theme = useResolvedTheme();
  const { backendId, deployStatus } = useAppShallow((s) => ({ backendId: s.backendId, deployStatus: s.deployStatus }));

  const fitAndSync = useCallback(() => {
    const term = termRef.current;
    const fit = fitRef.current;
    const host = hostRef.current;
    if (!term || !fit || !host || host.offsetParent === null) return;
    try { fit.fit(); } catch { return; }
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
  }, []);

  useEffect(() => {
    if (!hostRef.current) return;
    const term = new Terminal({
      cursorBlink: true,
      fontSize: 13,
      fontFamily: "'JetBrains Mono Variable', ui-monospace, Menlo, Consolas, monospace",
      theme: THEMES[theme],
      scrollback: 5000,
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(hostRef.current);
    termRef.current = term;
    fitRef.current = fit;
    const schedule = () => requestAnimationFrame(fitAndSync);
    schedule();
    const ro = new ResizeObserver(schedule);
    ro.observe(hostRef.current);
    window.addEventListener('resize', schedule);
    document.fonts?.ready.then(schedule).catch(() => {});
    return () => {
      ro.disconnect();
      window.removeEventListener('resize', schedule);
      term.dispose();
      termRef.current = null;
      fitRef.current = null;
    };
    // theme handled below without recreating the terminal
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fitAndSync]);

  useEffect(() => {
    const term = termRef.current;
    if (term) term.options.theme = THEMES[theme];
  }, [theme]);

  useEffect(() => {
    if (!active) return;
    const ids = [0, 60, 180].map((ms) => window.setTimeout(fitAndSync, ms));
    return () => ids.forEach(clearTimeout);
  }, [active, fitAndSync]);

  useEffect(() => {
    const term = termRef.current;
    if (!term) return;
    if (!backendId || deployStatus !== 'deployed') {
      term.reset();
      term.writeln('\x1b[33mTopology is not deployed. Deploy it to open a shell.\x1b[0m');
      return;
    }
    term.reset();
    let closed = false;
    const ws = new WebSocket(wsUrl(execWsPath(backendId, containerId)));
    wsRef.current = ws;
    ws.onopen = () => fitAndSync();
    ws.onmessage = (ev: MessageEvent<string | ArrayBuffer | Blob>) => {
      if (typeof ev.data === 'string') {
        if (ev.data === '{"type":"ping"}') return;
        term.write(ev.data);
      } else if (ev.data instanceof ArrayBuffer) {
        term.write(new TextDecoder().decode(ev.data));
      } else {
        ev.data.text().then((t) => term.write(t)).catch(() => {});
      }
    };
    ws.onclose = (ev) => { if (!closed) term.writeln(`\r\n\x1b[90m[connection closed] code=${ev.code}\x1b[0m`); };
    ws.onerror = () => term.writeln('\r\n\x1b[31m[websocket error]\x1b[0m');
    const onData = term.onData((d) => { if (ws.readyState === WebSocket.OPEN) ws.send(d); });
    const onResize = term.onResize(({ cols, rows }) => { if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'resize', cols, rows })); });
    return () => {
      closed = true;
      onData.dispose();
      onResize.dispose();
      ws.close();
      wsRef.current = null;
    };
  }, [backendId, containerId, deployStatus, fitAndSync]);

  return (
    <div className={active ? 'flex h-full min-h-0 flex-1 p-1' : 'hidden'}>
      <div ref={hostRef} className="min-h-0 flex-1" />
    </div>
  );
}
