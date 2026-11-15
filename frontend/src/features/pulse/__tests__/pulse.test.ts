import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAppStore } from '@/store';
import { setPulseSocket, startPulse, stopPulse } from '../pulse';

class FakeSocket {
  static all: FakeSocket[] = [];
  onmessage: ((ev: { data: string }) => void) | null = null;
  onclose: ((ev: unknown) => void) | null = null;
  closed = false;
  readonly url: string;
  constructor(url: string) { this.url = url; FakeSocket.all.push(this); }
  close() { this.closed = true; }
  say(msg: unknown) { this.onmessage?.({ data: JSON.stringify(msg) }); }
  drop() { this.onclose?.({}); }
}

const S = () => useAppStore.getState();
const last = () => FakeSocket.all[FakeSocket.all.length - 1];

beforeEach(() => {
  FakeSocket.all = [];
  setPulseSocket((url) => new FakeSocket(url) as unknown as WebSocket);
});

afterEach(() => {
  vi.useRealTimers();
  stopPulse();
  setPulseSocket(null);
});

describe('live lab view connection', () => {
  it('keeps the store on the latest picture, and only writes when it changed', () => {
    startPulse('topo1');
    expect(last().url).toContain('/topologies/ws/topo1/pulse');
    expect(S().pulseState).toBe('connecting');
    last().say({ type: 'hello' });
    last().say({ type: 'pulse', links: { c1: 'fwd' }, nodes: { h1: [{ name: 'zeek', args: 'zeek -i eth0' }] } });
    expect(S().pulseState).toBe('live');
    expect(S().linkTraffic).toEqual({ c1: 'fwd' });
    const { linkTraffic, nodeProcesses } = S();
    last().say({ type: 'pulse', links: { c1: 'fwd' }, nodes: { h1: [{ name: 'zeek', args: 'zeek -i eth0' }] } });
    expect(S().linkTraffic).toBe(linkTraffic);
    expect(S().nodeProcesses).toBe(nodeProcesses);
    startPulse('topo1'); // already watching: no second socket
    expect(FakeSocket.all).toHaveLength(1);
  });

  it('reconnects after a drop and clears what it showed', () => {
    vi.useFakeTimers();
    startPulse('topo1');
    last().say({ type: 'pulse', links: { c1: 'both' }, nodes: {} });
    last().drop();
    expect(S().linkTraffic).toEqual({});
    expect(S().pulseState).toBe('connecting');
    vi.advanceTimersByTime(3000);
    expect(FakeSocket.all).toHaveLength(2);
  });

  it('says so when the collector cannot run, and retries rarely', () => {
    vi.useFakeTimers();
    startPulse('topo1');
    last().say({ type: 'unavailable', reason: 'no cgroup tree' });
    last().drop();
    expect(S().pulseState).toBe('unavailable');
    vi.advanceTimersByTime(5000);
    expect(FakeSocket.all).toHaveLength(1);
    vi.advanceTimersByTime(30000);
    expect(FakeSocket.all).toHaveLength(2);
    expect(S().pulseState).toBe('unavailable'); // until a picture arrives
  });

  it('stops: closes the socket, forgets the picture, and does not come back', () => {
    vi.useFakeTimers();
    startPulse('topo1');
    last().say({ type: 'pulse', links: { c1: 'rev' }, nodes: { h1: [{ name: 'a', args: 'a' }] } });
    const socket = last();
    stopPulse();
    expect(socket.closed).toBe(true);
    expect(S().pulseState).toBe('off');
    expect(S().linkTraffic).toEqual({});
    expect(S().nodeProcesses).toEqual({});
    vi.advanceTimersByTime(60000);
    expect(FakeSocket.all).toHaveLength(1);
  });
});
