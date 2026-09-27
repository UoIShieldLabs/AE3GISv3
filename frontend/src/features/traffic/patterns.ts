// Traffic pattern drafts (the form) → request patterns, and a preview of how
// many flows they make (the backend expands them; see domain/traffic/patterns).
import type { NodeSelector, TrafficPattern } from '@/api/client';

export type PatternKind = TrafficPattern['kind'];
/** Which nodes: every host, every node, or a picked list. */
export type NodeSet = 'hosts' | 'all' | 'pick';

export interface PatternDraft {
  kind: PatternKind;
  servers: string[];
  clientSet: NodeSet;
  clients: string[];
  each: 'one' | 'all';
  nodeSet: NodeSet;
  nodes: string[];
  fanout: number;
  protocol: 'tcp' | 'udp';
  direction: 'forward' | 'reverse' | 'bidir';
  bitrate: string;
  parallel: number;
}

const BITRATE = /^\d+(\.\d+)?[KMGkmg]?$/;

export function newPattern(kind: PatternKind): PatternDraft {
  return { kind, servers: [], clientSet: 'hosts', clients: [], each: 'one', nodeSet: 'hosts', nodes: [], fanout: 1, protocol: 'tcp', direction: 'forward', bitrate: '10M', parallel: 1 };
}

function selector(set: NodeSet, picks: string[]): 'all' | string[] | NodeSelector {
  if (set === 'all') return 'all';
  if (set === 'hosts') return { roles: ['host'] };
  return picks;
}

export function toRequestPattern(d: PatternDraft, id = 'p1'): TrafficPattern {
  const common = { id, kind: d.kind, protocol: d.protocol, direction: d.direction, bitrate: d.bitrate.trim(), parallel: d.parallel, each: d.each, fanout: d.fanout, omit_s: 0 };
  return d.kind === 'mesh'
    ? { ...common, nodes: selector(d.nodeSet, d.nodes) }
    : { ...common, clients: selector(d.clientSet, d.clients), servers: d.servers };
}

/** How many flows the draft makes, given the running nodes each set means. */
export function flowCount(d: PatternDraft, resolve: (set: NodeSet, picks: string[]) => string[]): number {
  if (d.kind === 'mesh') {
    const n = resolve(d.nodeSet, d.nodes).length;
    return n < 2 ? 0 : n * Math.min(Math.max(1, d.fanout), n - 1);
  }
  const servers = new Set(resolve('pick', d.servers));
  const clients = resolve(d.clientSet, d.clients).filter((c) => !servers.has(c)).length;
  if (!servers.size) return 0;
  return d.each === 'all' ? clients * servers.size : clients;
}

/** What stops the draft from running, if anything. */
export function patternError(d: PatternDraft, flows: number, maxFlows: number): string | null {
  if (!BITRATE.test(d.bitrate.trim())) return 'Bitrate like 10M, 500K or 1G (0 = as fast as it goes)';
  if (d.parallel < 1 || d.parallel > 16) return 'Parallel streams: 1–16';
  if (d.kind === 'clients_to_servers' && !d.servers.length) return 'Pick at least one server';
  if (d.kind === 'mesh' && (d.fanout < 1 || !Number.isFinite(d.fanout))) return 'Peers per node: at least 1';
  if (flows === 0) return 'These choices make no flows';
  if (flows > maxFlows) return `${flows} flows; the server allows ${maxFlows}`;
  return null;
}
