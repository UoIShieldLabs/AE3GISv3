// Terminal sessions live here, not in the component that shows them. A dock
// remount (minimize, restore, leaving the editor) only detaches the view, so
// the shell — and whatever was started in it, e.g. an ssh — keeps running.
// A session ends when its dock tab closes; it reconnects (a fresh shell) when
// the topology or its deploy status changes, as the terminal always has.
import { Terminal, type ITheme } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { execWsPath, wsUrl } from '@/api/client';
import { useAppStore } from '@/store';

/** A new shell counts as ready once its first output has gone quiet for this long… */
const READY_QUIET_MS = 300;
/** …or this long after the socket opened, whichever comes first. */
const READY_MAX_MS = 5000;
/** A prompt counts as "the command is over" once no next command starts within
 *  this long (the lines of a multi-line command start one right after another). */
const IDLE_SETTLE_MS = 150;
/** The prompt markers our shells print (OSC 133): `C` = a command started,
 *  `D[;exit]` = the prompt is back. See `engine/terminal.py`. */
const OSC_SHELL = 133;

/** How a command typed by `runTracked` ended: its exit code (null when the shell
 *  doesn't report one), or null when the session lost track of it (it closed). */
export type RunEnd = { exit: number | null } | null;

/** xterm draws its own cells, so it takes the theme's --terminal-* tokens as values. */
function terminalLook(): { theme: ITheme; fontFamily: string; fontSize: number } {
  const css = getComputedStyle(document.documentElement);
  const v = (name: string) => css.getPropertyValue(name).trim();
  return {
    theme: {
      background: v('--terminal-bg'),
      foreground: v('--terminal-fg'),
      cursor: v('--terminal-cursor'),
      selectionBackground: v('--terminal-selection'),
    },
    fontFamily: v('--terminal-font'),
    fontSize: parseFloat(v('--terminal-font-size')) || 13,
  };
}

/** Text to type so the shell runs `text` as one command, the way xterm pastes:
 *  newlines become CR, the body is bracketed when the foreground program asked
 *  for bracketed paste (a remote shell may, ours don't), then Enter. */
export function prepareCommand(text: string, bracketed: boolean): string {
  const body = text.replace(/\r?\n/g, '\r').replace(/\r+$/, '');
  return (bracketed ? `\x1b[200~${body}\x1b[201~` : body) + '\r';
}

/** What a session is built from; swapped for fakes in tests. */
export interface SessionDeps {
  createTerminal: (look: ReturnType<typeof terminalLook>) => Terminal;
  createFit: () => FitAddon;
  createSocket: (url: string) => WebSocket;
}

const defaultDeps: SessionDeps = {
  createTerminal: (look) => new Terminal({ cursorBlink: true, ...look, scrollback: 5000 }),
  createFit: () => new FitAddon(),
  createSocket: (url) => new WebSocket(url),
};

let deps = defaultDeps;

/** Test seam: replace xterm / WebSocket (null restores the real ones). */
export function setSessionDeps(next: Partial<SessionDeps> | null): void {
  deps = next ? { ...defaultDeps, ...next } : defaultDeps;
}

export class TerminalSessionHandle {
  readonly tabId: string;
  readonly containerId: string;
  readonly term: Terminal;
  private readonly fitAddon: FitAddon;
  /** Persistent host for xterm: moved between views, opened once. */
  private readonly wrapper: HTMLDivElement;
  private opened = false;
  private ws: WebSocket | null = null;
  /** The store state (`deployedKey`) last synced to; undefined before the first sync. */
  private syncedKey: string | null | undefined = undefined;
  private ready = false;
  private quietTimer: ReturnType<typeof setTimeout> | null = null;
  private maxTimer: ReturnType<typeof setTimeout> | null = null;
  private waiters = new Set<(ok: boolean) => void>();
  private lookToken = 0;
  private disposed = false;
  /** The shell prints prompt markers (seen at least one). */
  private integrated = false;
  /** A command holds the shell (between a start and the prompt coming back). */
  private busy = false;
  private lastExit: number | null = null;
  private idleTimer: ReturnType<typeof setTimeout> | null = null;
  /** The tracked run waiting for the prompt, if any. */
  private onRunEnd: ((end: RunEnd) => void) | null = null;

  constructor(tabId: string, containerId: string) {
    this.tabId = tabId;
    this.containerId = containerId;
    this.term = deps.createTerminal(terminalLook());
    this.fitAddon = deps.createFit();
    this.term.loadAddon(this.fitAddon);
    this.wrapper = document.createElement('div');
    this.wrapper.style.height = '100%';
    this.wrapper.style.width = '100%';
    this.term.onData((d) => { if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(d); });
    this.term.onResize(() => this.sendResize());
    // Consumed here, so the markers are never drawn.
    this.term.parser?.registerOscHandler(OSC_SHELL, (data) => { this.onMarker(data); return true; });
    this.sync();
  }

  /** Show the terminal inside `host` (the dock body). */
  attach(host: HTMLElement): void {
    if (this.disposed) return;
    host.appendChild(this.wrapper);
    if (!this.opened) {
      this.term.open(this.wrapper);
      this.opened = true;
    }
    this.fit();
  }

  /** Take the terminal off screen; the shell keeps running. */
  detach(): void {
    this.wrapper.remove();
  }

  /** Fit to the visible host and tell the PTY. False when hidden or not shown yet. */
  fit(): boolean {
    if (!this.opened || this.wrapper.offsetParent === null) return false;
    try { this.fitAddon.fit(); } catch { return false; }
    this.sendResize();
    return true;
  }

  /** Re-read the theme's terminal tokens (a font change loads the font, then re-fits). */
  applyLook(): void {
    const look = terminalLook();
    this.term.options.theme = look.theme;
    if (this.term.options.fontFamily === look.fontFamily && this.term.options.fontSize === look.fontSize) return;
    const token = ++this.lookToken;
    const apply = () => {
      if (token !== this.lookToken || this.disposed) return;
      this.term.options.fontFamily = look.fontFamily;
      this.term.options.fontSize = look.fontSize;
      this.fit();
    };
    if (document.fonts) document.fonts.load(`${look.fontSize}px ${look.fontFamily}`).then(apply, apply);
    else apply();
  }

  /** Type `text` into the shell and press Enter, as if the user had. False when not connected. */
  runCommand(text: string): boolean {
    if (this.ws?.readyState !== WebSocket.OPEN) return false;
    this.term.input(prepareCommand(text, this.term.modes.bracketedPasteMode), true);
    return true;
  }

  /** `runCommand`, and tell `onEnd` when the prompt is back. 'tracked' when the
   *  shell will report it; 'sent' when it can't (no prompt markers, or the
   *  command went to whatever already holds the shell, e.g. an open ssh);
   *  'offline' when not connected. `onEnd` is only called for 'tracked'. */
  runTracked(text: string, onEnd: (end: RunEnd) => void): 'tracked' | 'sent' | 'offline' {
    // The prompt is already back from the last command: don't wait out the settle.
    if (this.idleTimer) this.settleIdle();
    const tracked = this.integrated && !this.busy;
    if (!this.runCommand(text)) return 'offline';
    if (!tracked) return 'sent';
    this.clearIdleTimer();
    this.onRunEnd = onEnd;
    this.setBusy(true);
    return 'tracked';
  }

  /** Press Ctrl-C in the shell. False when not connected. */
  interrupt(): boolean {
    if (this.ws?.readyState !== WebSocket.OPEN) return false;
    this.ws.send('\x03');
    return true;
  }

  /** A command holds the shell right now (as far as the prompt markers tell). */
  isBusy(): boolean {
    return this.busy;
  }

  /** Resolves true once the shell can take input: immediately for a running
   *  session, after its first output settles for a new one. A closed session
   *  (e.g. after `exit`) is reopened first. False when there is no shell to reach. */
  whenReady(): Promise<boolean> {
    if (this.disposed || !this.deployedKey()) return Promise.resolve(false);
    const state = this.ws?.readyState;
    if (state !== WebSocket.OPEN && state !== WebSocket.CONNECTING) this.connect(false);
    if (this.ready) return Promise.resolve(true);
    return new Promise((resolve) => this.waiters.add(resolve));
  }

  /** Follow the store: (re)connect when the topology or its deploy status changed. */
  sync(): void {
    const key = this.deployedKey();
    if (key === this.syncedKey) return;
    this.syncedKey = key;
    this.close();
    this.term.reset();
    if (!key) {
      this.term.writeln('\x1b[33mTopology is not deployed. Deploy it to open a shell.\x1b[0m');
      return;
    }
    this.connect(true);
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.close();
    this.wrapper.remove();
    this.term.dispose();
  }

  private onMarker(data: string): void {
    const [kind, code] = data.split(';');
    if (kind === 'C') {
      this.integrated = true;
      this.clearIdleTimer();
      this.setBusy(true);
    } else if (kind === 'D') {
      this.integrated = true;
      const exit = code === undefined || code === '' ? null : Number(code);
      this.lastExit = exit !== null && Number.isFinite(exit) ? exit : null;
      this.clearIdleTimer();
      this.idleTimer = setTimeout(() => this.settleIdle(), IDLE_SETTLE_MS);
    }
  }

  private settleIdle(): void {
    this.clearIdleTimer();
    this.setBusy(false);
    this.endRun({ exit: this.lastExit });
  }

  private setBusy(busy: boolean): void {
    if (this.busy === busy) return;
    this.busy = busy;
    useAppStore.getState().setTerminalBusy(this.containerId, busy);
  }

  private endRun(end: RunEnd): void {
    const cb = this.onRunEnd;
    this.onRunEnd = null;
    cb?.(end);
  }

  private clearIdleTimer(): void {
    if (this.idleTimer) clearTimeout(this.idleTimer);
    this.idleTimer = null;
  }

  private deployedKey(): string | null {
    const { backendId, deployStatus } = useAppStore.getState();
    return backendId && deployStatus === 'deployed' ? `${backendId}|deployed` : null;
  }

  private connect(fresh: boolean): void {
    const backendId = useAppStore.getState().backendId;
    if (!this.deployedKey() || !backendId) return;
    this.close();
    if (!fresh) this.term.write('\r\n');
    const ws = deps.createSocket(wsUrl(execWsPath(backendId, this.containerId)));
    ws.binaryType = 'arraybuffer';
    this.ws = ws;
    ws.onopen = () => {
      if (!this.fit()) this.sendResize();
      this.maxTimer = setTimeout(() => this.markReady(), READY_MAX_MS);
    };
    ws.onmessage = (ev: MessageEvent<string | ArrayBuffer>) => {
      if (typeof ev.data === 'string') {
        // Status lines from the bridge ("Connecting to …", errors), not the shell.
        if (ev.data !== '{"type":"ping"}') this.term.write(ev.data);
        return;
      }
      // Raw PTY bytes: xterm decodes UTF-8 across chunk boundaries.
      this.term.write(new Uint8Array(ev.data));
      if (!this.ready) {
        if (this.quietTimer) clearTimeout(this.quietTimer);
        this.quietTimer = setTimeout(() => this.markReady(), READY_QUIET_MS);
      }
    };
    ws.onclose = (ev) => {
      if (this.ws !== ws) return;
      this.ws = null;
      this.clearTimers();
      this.ready = false;
      this.shellGone();
      this.term.writeln(`\r\n\x1b[90m[connection closed] code=${ev.code}\x1b[0m`);
      this.settle(false);
    };
    ws.onerror = () => { if (this.ws === ws) this.term.writeln('\r\n\x1b[31m[websocket error]\x1b[0m'); };
  }

  private close(): void {
    const ws = this.ws;
    this.ws = null;
    this.clearTimers();
    this.ready = false;
    this.shellGone();
    if (ws) {
      ws.onopen = ws.onmessage = ws.onclose = ws.onerror = null;
      ws.close();
    }
    this.settle(false);
  }

  /** The shell ended: nothing runs in it any more, and a tracked run is lost. */
  private shellGone(): void {
    this.clearIdleTimer();
    this.integrated = false;
    this.lastExit = null;
    this.setBusy(false);
    this.endRun(null);
  }

  private markReady(): void {
    this.clearTimers();
    if (this.ws?.readyState !== WebSocket.OPEN) return;
    this.ready = true;
    this.settle(true);
  }

  private settle(ok: boolean): void {
    const waiters = [...this.waiters];
    this.waiters.clear();
    for (const w of waiters) w(ok);
  }

  private clearTimers(): void {
    if (this.quietTimer) clearTimeout(this.quietTimer);
    if (this.maxTimer) clearTimeout(this.maxTimer);
    this.quietTimer = this.maxTimer = null;
  }

  private sendResize(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'resize', cols: this.term.cols, rows: this.term.rows }));
    }
  }
}

const sessions = new Map<string, TerminalSessionHandle>();
let installed = false;

/** Follow the store once: closed dock tabs end their session; a topology or
 *  deploy-status change reconnects every session. */
function install(): void {
  if (installed) return;
  installed = true;
  useAppStore.subscribe((s, prev) => {
    if (s.dockTabs !== prev.dockTabs) {
      const open = new Set(s.dockTabs.map((t) => t.id));
      for (const id of [...sessions.keys()]) if (!open.has(id)) disposeSession(id);
    }
    if (s.backendId !== prev.backendId || s.deployStatus !== prev.deployStatus) {
      for (const session of sessions.values()) session.sync();
    }
  });
}

/** The session for a terminal dock tab, created (and connected) on first use. */
export function acquireSession(tabId: string, containerId: string): TerminalSessionHandle {
  install();
  let session = sessions.get(tabId);
  if (!session) {
    session = new TerminalSessionHandle(tabId, containerId);
    sessions.set(tabId, session);
  }
  return session;
}

export function getSession(tabId: string): TerminalSessionHandle | undefined {
  return sessions.get(tabId);
}

export function disposeSession(tabId: string): void {
  sessions.get(tabId)?.dispose();
  sessions.delete(tabId);
}

/** Tests: end every session. */
export function disposeAllSessions(): void {
  for (const id of [...sessions.keys()]) disposeSession(id);
}
