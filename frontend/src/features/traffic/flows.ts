// Flow editing helpers (pure).
import type { Iperf3Flow } from '@/api/client';
import type { SavedFlow } from '@/types/topology';

export const MAX_FLOWS = 8;
const BITRATE = /^\d+(\.\d+)?[KMGkmg]?$/;

export function nextFlowId(flows: readonly SavedFlow[]): string {
  const used = new Set(flows.map((f) => f.id));
  let i = 1;
  while (used.has(`f${i}`)) i += 1;
  return `f${i}`;
}

export function newFlow(flows: readonly SavedFlow[], client = '', server = ''): SavedFlow {
  return { id: nextFlowId(flows), client, server, protocol: 'tcp', direction: 'forward', bitrate: '', parallel: 1 };
}

/** Problems per flow id (empty when every flow can run). */
export function flowErrors(flows: readonly SavedFlow[]): Record<string, string> {
  const out: Record<string, string> = {};
  const ids = new Set<string>();
  for (const f of flows) {
    if (ids.has(f.id)) out[f.id] = 'Duplicate id';
    ids.add(f.id);
    if (!f.client || !f.server) out[f.id] = 'Pick a client and a server';
    else if (f.client === f.server) out[f.id] = 'Client and server must differ';
    else if (f.bitrate && !BITRATE.test(f.bitrate)) out[f.id] = 'Bitrate like 50M, 500K or 1G';
    else if (f.parallel !== undefined && (f.parallel < 1 || f.parallel > 16)) out[f.id] = 'Parallel streams: 1–16';
  }
  return out;
}

export function toRequestFlow(f: SavedFlow): Iperf3Flow {
  return {
    generator: 'iperf3',
    id: f.id,
    client: f.client,
    server: f.server,
    server_address: null,
    protocol: f.protocol,
    direction: f.direction,
    bitrate: f.bitrate ? f.bitrate : null,
    parallel: f.parallel ?? 1,
    length: f.length ?? null,
    omit_s: 0,
  };
}
