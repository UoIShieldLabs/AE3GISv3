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
  const term = {
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
    // The shell's prompt markers (OSC 133), as xterm's parser would hand them over.
    oscHandlers: new Map<number, (data: string) => boolean>(),
    parser: {
      registerOscHandler(id: number, cb: (data: string) => boolean) { handlers().set(id, cb); return { dispose: () => {} }; },
    },
    marker(data: string) { this.oscHandlers.get(133)?.(data); },
  };
  function handlers() { return term.oscHandlers; }
  return term;
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

describe('prompt markers', () => {
  const open = () => {
    const s = acquireSession('term:h1', 'h1');
    last().accept();
    return s;
  };
  const busy = () => !!useAppStore.getState().busyTerminals.h1;

  it('tracks a run from the typed command to the prompt, with its exit code', async () => {
    vi.useFakeTimers();
    const s = open();
    terms[0].marker('D;0'); // the first prompt: the shell prints markers
    await vi.advanceTimersByTimeAsync(200);
    const ends: unknown[] = [];
    expect(s.runTracked('false', (end) => ends.push(end))).toBe('tracked');
    expect(busy()).toBe(true);
    terms[0].marker('C');
    terms[0].marker('D;1');
    expect(ends).toEqual([]); // not before the prompt settles
    await vi.advanceTimersByTimeAsync(200);
    expect(ends).toEqual([{ exit: 1 }]);
    expect(busy()).toBe(false);
    expect(s.isBusy()).toBe(false);
  });

  it('keeps a multi-line command running until its last line is back at the prompt', async () => {
    vi.useFakeTimers();
    const s = open();
    terms[0].marker('D;0');
    await vi.advanceTimersByTimeAsync(200);
    const ends: unknown[] = [];
    s.runTracked('a\nb', (end) => ends.push(end));
    terms[0].marker('C');
    terms[0].marker('D;0');
    await vi.advanceTimersByTimeAsync(50);
    terms[0].marker('C'); // the next line starts right away
    await vi.advanceTimersByTimeAsync(500);
    expect(ends).toEqual([]);
    expect(busy()).toBe(true);
    terms[0].marker('D;0');
    await vi.advanceTimersByTimeAsync(200);
    expect(ends).toEqual([{ exit: 0 }]);
  });

  it('only sends when the shell prints no markers, or something already holds it', async () => {
    vi.useFakeTimers();
    const s = open();
    const onEnd = vi.fn();
    expect(s.runTracked('ls', onEnd)).toBe('sent'); // no marker seen yet
    terms[0].marker('D');
    await vi.advanceTimersByTimeAsync(200);
    expect(s.runTracked('ssh root@10.0.5.20', onEnd)).toBe('tracked');
    expect(s.runTracked('hostname', onEnd)).toBe('sent'); // typed into the ssh
    expect(onEnd).not.toHaveBeenCalled();
    expect(busy()).toBe(true);
  });

  it('takes a run typed right after the prompt came back', () => {
    vi.useFakeTimers();
    const s = open();
    terms[0].marker('D;0');
    const first = vi.fn();
    expect(s.runTracked('one', first)).toBe('tracked');
    terms[0].marker('C');
    terms[0].marker('D;0');
    expect(s.runTracked('two', vi.fn())).toBe('tracked'); // within the settle window
    expect(first).toHaveBeenCalledWith({ exit: 0 });
  });

  it('loses track of a run when the shell closes, and interrupts with Ctrl-C', async () => {
    vi.useFakeTimers();
    const s = open();
    terms[0].marker('D;0');
    await vi.advanceTimersByTimeAsync(200);
    const ends: unknown[] = [];
    s.runTracked('sleep 100', (end) => ends.push(end));
    expect(s.interrupt()).toBe(true);
    expect(last().sent).toContain('\x03');
    last().drop();
    expect(ends).toEqual([null]);
    expect(busy()).toBe(false);
    expect(s.interrupt()).toBe(false);
  });
});

