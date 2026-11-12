import { describe, expect, it } from 'vitest';
import type { Tutorial, TutorialTraffic } from '@/types/topology';
import { expandTraffic, hasSetup, rowOf, rowProblem, rowSummary, rowWhat, stepsRequest, type SetupNode } from '../model';

const nodes = new Map<string, SetupNode>([
  ['ew', { id: 'ew', name: 'eng-ws', ip: '10.0.5.15' }],
  ['pc', { id: 'pc', name: 'pc', ip: '10.0.5.20' }],
  ['rtu', { id: 'rtu', name: 'rtu', ip: '10.0.3.50' }],
  ['web', { id: 'web', name: 'web', ip: '10.0.4.10' }],
  ['sw', { id: 'sw', name: 'switch' }],
]);

const row = (over: Partial<TutorialTraffic>): TutorialTraffic => ({ id: 'row', kind: 'command', from: [], to: [], ...over });
const tutorial = (setup?: Tutorial['setup']): Tutorial => ({ id: 't1', title: 'Industroyer', cells: [], setup });

describe('lab setup model', () => {
  it('turns the steps into one tagged run that stops at the first failure', () => {
    const t = tutorial({
      steps: [
        { id: 's1', containerId: 'fw', command: 'nft insert rule x' },
        { id: 's2', containerId: '', command: 'echo nowhere' },
        { id: 's3', containerId: 'ids', command: '  ' },
      ],
      traffic: [],
    });
    expect(hasSetup(t)).toBe(true);
    expect(stepsRequest(t)).toEqual({
      steps: [{ containerId: 'fw', script: 'nft insert rule x', args: [], label: '' }],
      label: 'Lab setup: Industroyer',
      tag: 'tutorial-setup:t1',
      stop_on_failure: true,
    });
    expect(stepsRequest(tutorial())).toBeNull();
    expect(hasSetup(tutorial())).toBe(false);
    expect(hasSetup(tutorial({ steps: [], traffic: [] }))).toBe(false);
  });

  it('runs a command on every sender, once per destination when it names {to}', () => {
    const { items, patterns, problems } = expandTraffic({
      steps: [],
      traffic: [
        row({ id: 'a', from: ['ew', 'pc'], to: ['rtu', 'web'], command: 'while sleep 2; do nc -z {to} 2404; done' }),
        row({ id: 'b', from: ['ew', 'gone'], to: ['rtu'], command: 'breaker status' }),
      ],
    }, nodes);
    expect(problems).toEqual({});
    expect(patterns).toEqual([]);
    expect(items).toEqual([
      { id: 'r0.f0.t0', containerId: 'ew', command: 'while sleep 2; do nc -z 10.0.3.50 2404; done' },
      { id: 'r0.f0.t1', containerId: 'ew', command: 'while sleep 2; do nc -z 10.0.4.10 2404; done' },
      { id: 'r0.f1.t0', containerId: 'pc', command: 'while sleep 2; do nc -z 10.0.3.50 2404; done' },
      { id: 'r0.f1.t1', containerId: 'pc', command: 'while sleep 2; do nc -z 10.0.4.10 2404; done' },
      { id: 'r1.f0', containerId: 'ew', command: 'breaker status' }, // no {to}: once per sender; the removed node is skipped
    ]);
    expect(items.map((i) => rowOf(i.id))).toEqual([0, 0, 0, 0, 1]);
  });

  it('makes iperf3 rows patterns: every sender to every destination', () => {
    const { items, patterns } = expandTraffic({
      steps: [],
      traffic: [row({ id: 'a', from: ['ew'], to: ['rtu'], command: 'true' }), row({ id: 'b', kind: 'iperf3', from: ['ew', 'pc'], to: ['web'], protocol: 'udp', bitrate: '500K' })],
    }, nodes);
    expect(items).toHaveLength(1);
    expect(patterns).toEqual([{
      id: 'r1', kind: 'clients_to_servers', clients: ['ew', 'pc'], servers: ['web'], each: 'all',
      protocol: 'udp', bitrate: '500K', direction: 'forward', parallel: 1, fanout: 1, omit_s: 0,
    }]);
    expect(rowOf(patterns[0].id)).toBe(1);
  });

  it('says why a row cannot run, and leaves it out', () => {
    expect(rowProblem(row({ from: [], command: 'true' }), nodes)).toBe('Pick at least one sender');
    expect(rowProblem(row({ from: ['ew'], command: ' ' }), nodes)).toBe('Write the command to run');
    expect(rowProblem(row({ from: ['ew'], command: 'ping {to}' }), nodes)).toMatch(/pick at least one destination/);
    expect(rowProblem(row({ from: ['ew'], to: ['sw'], command: 'ping {to}' }), nodes)).toBe('switch has no IP address');
    expect(rowProblem(row({ kind: 'iperf3', from: ['ew'] }), nodes)).toBe('Pick at least one destination');
    expect(rowProblem(row({ kind: 'iperf3', from: ['ew'], to: ['rtu'], bitrate: 'fast' }), nodes)).toMatch(/Rate like/);
    expect(rowProblem(row({ kind: 'iperf3', from: ['ew'], to: ['ew'] }), nodes)).toMatch(/same node/);
    expect(rowProblem(row({ from: ['ew'], command: 'breaker status' }), nodes)).toBeNull();
    const { items, problems } = expandTraffic({ steps: [], traffic: [row({ id: 'bad', from: [], command: 'x' }), row({ id: 'ok', from: ['ew'], command: 'x' })] }, nodes);
    expect(problems).toEqual({ bad: 'Pick at least one sender' });
    expect(items).toEqual([{ id: 'r1.f0', containerId: 'ew', command: 'x' }]);
  });

  it('a node never sends to itself', () => {
    const { items } = expandTraffic({ steps: [], traffic: [row({ from: ['ew', 'pc'], to: ['ew', 'pc'], command: 'ping {to}' })] }, nodes);
    expect(items.map((i) => `${i.containerId}>${i.command}`)).toEqual(['ew>ping 10.0.5.20', 'pc>ping 10.0.5.15']);
  });

  it('summarises a row in a few words', () => {
    expect(rowSummary(row({ from: ['ew'], to: ['rtu'], command: 'nc {to}' }), nodes)).toBe('eng-ws → rtu');
    expect(rowSummary(row({ from: ['ew'], to: ['rtu'], command: 'breaker status' }), nodes)).toBe('eng-ws');
    expect(rowSummary(row({ kind: 'iperf3', from: ['ew', 'pc', 'web'], to: ['rtu'] }), nodes)).toBe('3 nodes → rtu');
    expect(rowWhat(row({ kind: 'iperf3', protocol: 'udp' }))).toBe('iperf3 · UDP 1M');
    expect(rowWhat(row({ command: ' breaker status ' }))).toBe('breaker status');
  });
});
