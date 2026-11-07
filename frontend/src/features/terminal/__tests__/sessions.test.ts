import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Terminal } from '@xterm/xterm';
import type { FitAddon } from '@xterm/addon-fit';
import { useAppStore } from '@/store';
import { acquireSession, disposeAllSessions, getSession, prepareCommand, setSessionDeps } from '../sessions';

class FakeSocket {
  static all: FakeSocket[] = [];
  readyState: number = WebSocket.CONNECTING;
  binaryType = 'blob';
  sent: string[] = [];
  onopen: ((ev: unknown) => void) | null = null;
  onmessage: ((ev: { data: unknown }) => void) | null = null;
  onclose: ((ev: { code: number }) => void) | null = null;
  onerror: ((ev: unknown) => void) | null = null;
  readonly url: string;
  constructor(url: string) { this.url = url; FakeSocket.all.push(this); }
  send(d: string) { this.sent.push(d); }
  close() { this.readyState = WebSocket.CLOSED; }
  // Server side:
  accept() { this.readyState = WebSocket.OPEN; this.onopen?.({}); }
  output(text: string) { this.onmessage?.({ data: new TextEncoder().encode(text).buffer }); }
  drop(code = 1006) { this.readyState = WebSocket.CLOSED; this.onclose?.({ code }); }
}

function fakeTerminal() {
  const onData: ((d: string) => void)[] = [];
  return {
    written: [] as string[],
    modes: { bracketedPasteMode: false },
    options: {} as Record<string, unknown>,
    cols: 100,
    rows: 30,
    loadAddon: () => {},
    open: vi.fn(),
    reset: vi.fn(),
    dispose: vi.fn(),
    write(d: string | Uint8Array) { this.written.push(typeof d === 'string' ? d : new TextDecoder().decode(d)); },
    writeln(d: string) { this.written.push(`${d}\n`); },
    onData(cb: (d: string) => void) { onData.push(cb); return { dispose: () => {} }; },
    onResize() { return { dispose: () => {} }; },
    input(d: string) { onData.forEach((cb) => cb(d)); },
  };
}

let terms: ReturnType<typeof fakeTerminal>[] = [];
const last = () => FakeSocket.all[FakeSocket.all.length - 1];

beforeEach(() => {
  FakeSocket.all = [];
  terms = [];
  setSessionDeps({
    createTerminal: () => { const t = fakeTerminal(); terms.push(t); return t as unknown as Terminal; },
    createFit: () => ({ fit: () => {}, activate: () => {}, dispose: () => {} }) as unknown as FitAddon,
    createSocket: (url) => new FakeSocket(url) as unknown as WebSocket,
  });
  useAppStore.setState({
    backendId: 'topo1',
    deployStatus: 'deployed',
    dockTabs: [{ kind: 'terminal', id: 'term:h1', containerId: 'h1', name: 'h1' }],
  });
});

afterEach(() => {
  vi.useRealTimers();
  disposeAllSessions();
  setSessionDeps(null);
  useAppStore.setState({ backendId: null, deployStatus: 'idle', dockTabs: [] });
});

describe('prepareCommand', () => {
  it('types one line and presses Enter', () => {
    expect(prepareCommand('ls -la', false)).toBe('ls -la\r');
  });
  it('turns newlines into CR and drops trailing ones', () => {
    expect(prepareCommand('cat <<EOF\nhi\r\nEOF\n\n', false)).toBe('cat <<EOF\rhi\rEOF\r');
  });
  it('brackets the body when the program asked for bracketed paste', () => {
    expect(prepareCommand('a\nb', true)).toBe('\x1b[200~a\rb\x1b[201~\r');
  });
});

describe('terminal sessions', () => {
  it('connects once and survives the view detaching and re-attaching', () => {
    const s = acquireSession('term:h1', 'h1');
    expect(FakeSocket.all).toHaveLength(1);
    expect(last().url).toContain('/topologies/ws/topo1/exec/h1');
    expect(last().binaryType).toBe('arraybuffer');
    const a = document.createElement('div');
    const b = document.createElement('div');
    s.attach(a);
    s.detach();
    s.attach(b);
    expect(acquireSession('term:h1', 'h1')).toBe(s);
    expect(FakeSocket.all).toHaveLength(1);
    expect(terms[0].open).toHaveBeenCalledTimes(1);
    expect(b.childElementCount).toBe(1);
    expect(a.childElementCount).toBe(0);
  });

  it('writes PTY bytes to the terminal and types commands into the socket', () => {
    const s = acquireSession('term:h1', 'h1');
    expect(s.runCommand('whoami')).toBe(false); // not open yet
    last().accept();
    last().output('root@h1:~# ');
    expect(terms[0].written.join('')).toContain('root@h1:~# ');
    expect(s.runCommand('ssh root@10.0.5.20')).toBe(true);
    terms[0].modes.bracketedPasteMode = true;
    s.runCommand('ls');
    expect(last().sent.filter((m) => !m.startsWith('{'))).toEqual(['ssh root@10.0.5.20\r', '\x1b[200~ls\x1b[201~\r']);
  });

  it('is ready after a new shell’s first output settles, at once when already running', async () => {
    vi.useFakeTimers();
    const s = acquireSession('term:h1', 'h1');
    let ready: boolean | null = null;
    void s.whenReady().then((ok) => { ready = ok; });
    last().accept();
    last().output('Welcome\r\n');
    await vi.advanceTimersByTimeAsync(200);
    expect(ready).toBeNull();
    last().output('root@h1:~# ');
    await vi.advanceTimersByTimeAsync(300);
    expect(ready).toBe(true);
    await expect(s.whenReady()).resolves.toBe(true);
  });

  it('gives up on a socket that closes, and reopens a closed shell on demand', async () => {
    const s = acquireSession('term:h1', 'h1');
    const pending = s.whenReady();
    last().drop(4004);
    await expect(pending).resolves.toBe(false);
    expect(terms[0].written.join('')).toContain('[connection closed] code=4004');
    void s.whenReady();
    expect(FakeSocket.all).toHaveLength(2);
  });

  it('ends the session when its dock tab closes', () => {
    acquireSession('term:h1', 'h1');
    const ws = last();
    useAppStore.getState().closeTerminal('h1');
    expect(getSession('term:h1')).toBeUndefined();
    expect(ws.readyState).toBe(WebSocket.CLOSED);
    expect(terms[0].dispose).toHaveBeenCalled();
  });

  it('follows the deploy status: closes when the lab goes away, reconnects when it is back', () => {
    acquireSession('term:h1', 'h1');
    const first = last();
    useAppStore.setState({ deployStatus: 'destroying' });
    expect(first.readyState).toBe(WebSocket.CLOSED);
    expect(terms[0].written.join('')).toContain('Topology is not deployed');
    useAppStore.setState({ deployStatus: 'idle' });
    expect(FakeSocket.all).toHaveLength(1);
    useAppStore.setState({ deployStatus: 'deployed' });
    expect(FakeSocket.all).toHaveLength(2);
  });
});
