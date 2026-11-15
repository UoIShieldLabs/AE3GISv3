// A tutorial's lab setup, made runnable (pure): its steps as one scenario run,
// its background traffic rows as background-run items and iperf3 patterns.
import type { BackgroundRunRequest, ScenarioRunRequest, TrafficPattern } from '@/api/client';
import type { Tutorial, TutorialSetup, TutorialTraffic } from '@/types/topology';

/** What the setup knows about a node: enough to address and name it. */
export interface SetupNode { id: string; name: string; ip?: string }

/** Marks the runs a tutorial's setup starts, so they can be found again. */
export const setupTag = (tutorialId: string) => `tutorial-setup:${tutorialId}`;
export const trafficTag = (tutorialId: string) => `tutorial-traffic:${tutorialId}`;
/** Label of the iperf3 traffic run a tutorial starts (traffic runs carry no tag). */
export const TRAFFIC_LABEL = 'Background traffic';
/** In a command row, replaced by each destination's IP address. */
export const TO = '{to}';
export const DEFAULT_BITRATE = '1M';
const BITRATE = /^\d+(\.\d+)?[KMGkmg]?$/;

export function hasSetup(tutorial: Tutorial): boolean {
  return !!(tutorial.setup?.steps?.length || tutorial.setup?.traffic?.length);
}

/** The steps as a run request; null when there is none to run. */
export function stepsRequest(tutorial: Tutorial): ScenarioRunRequest | null {
  const steps = (tutorial.setup?.steps ?? []).filter((s) => s.containerId && s.command.trim());
  if (!steps.length) return null;
  return {
    steps: steps.map((s) => ({ containerId: s.containerId, script: s.command, args: [], label: '' })),
    label: `Lab setup: ${tutorial.title}`.slice(0, 80),
    tag: setupTag(tutorial.id),
    stop_on_failure: true,
  };
}

/** A background-run item id: row, sender and destination by position (ids must stay short). */
export const itemId = (row: number, from: number, to?: number) => `r${row}.f${from}${to === undefined ? '' : `.t${to}`}`;
/** The row (index) an item or pattern id belongs to. */
export function rowOf(id: string): number {
  const m = /^r(\d+)/.exec(id);
  return m ? Number(m[1]) : -1;
}

export interface ExpandedTraffic {
  /** Commands to keep running: one per sender, or per sender and destination when the command names `{to}`. */
  items: BackgroundRunRequest['items'];
  /** iperf3 rows: every sender to every destination. */
  patterns: TrafficPattern[];
  /** Per row (by id): why it cannot start, if it cannot. */
  problems: Record<string, string>;
}

/** Why a traffic row cannot run as written, or null. */
export function rowProblem(row: TutorialTraffic, nodes: ReadonlyMap<string, SetupNode>): string | null {
  const from = (row.from ?? []).filter((id) => nodes.has(id));
  const to = (row.to ?? []).filter((id) => nodes.has(id));
  if (!from.length) return 'Pick at least one sender';
  if (row.kind === 'iperf3') {
    if (!to.length) return 'Pick at least one destination';
    if (!BITRATE.test((row.bitrate ?? DEFAULT_BITRATE).trim())) return 'Rate like 1M, 500K or 1G';
    if (to.every((t) => from.includes(t)) && from.length === 1) return 'The sender and the destination are the same node';
    return null;
  }
  const command = (row.command ?? '').trim();
  if (!command) return 'Write the command to run';
  if (command.includes(TO)) {
    if (!to.length) return `The command names ${TO}: pick at least one destination`;
    const noIp = to.find((t) => !nodes.get(t)?.ip);
    if (noIp) return `${nodes.get(noIp)?.name ?? noIp} has no IP address`;
  }
  return null;
}

/** Turn the traffic rows into what the backend runs; rows with a problem are left out. */
export function expandTraffic(setup: TutorialSetup | undefined, nodes: ReadonlyMap<string, SetupNode>): ExpandedTraffic {
  const out: ExpandedTraffic = { items: [], patterns: [], problems: {} };
  (setup?.traffic ?? []).forEach((row, r) => {
    const problem = rowProblem(row, nodes);
    if (problem) { out.problems[row.id] = problem; return; }
    const from = row.from.filter((id) => nodes.has(id));
    const to = (row.to ?? []).filter((id) => nodes.has(id));
    if (row.kind === 'iperf3') {
      out.patterns.push({
        id: `r${r}`, kind: 'clients_to_servers', clients: from, servers: to, each: 'all',
        protocol: row.protocol ?? 'tcp', bitrate: (row.bitrate ?? DEFAULT_BITRATE).trim(),
        direction: 'forward', parallel: 1, fanout: 1, omit_s: 0,
      });
      return;
    }
    const command = (row.command ?? '').trim();
    from.forEach((f, i) => {
      if (!command.includes(TO)) { out.items.push({ id: itemId(r, i), containerId: f, command }); return; }
      to.forEach((t, j) => {
        if (t === f) return; // a node does not send to itself
        out.items.push({ id: itemId(r, i, j), containerId: f, command: command.split(TO).join(nodes.get(t)!.ip!) });
      });
    });
  });
  return out;
}

/** "eng-ws → rtu", "3 nodes → web, db", "eng-ws" (a command that names no destination). */
export function rowSummary(row: TutorialTraffic, nodes: ReadonlyMap<string, SetupNode>): string {
  const names = (ids: string[] | undefined) => {
    const known = (ids ?? []).map((id) => nodes.get(id)?.name).filter((n): n is string => !!n);
    return known.length > 2 ? `${known.length} nodes` : known.join(', ');
  };
  const from = names(row.from) || 'nobody';
  const to = names(row.to);
  const aimed = row.kind === 'iperf3' || (row.command ?? '').includes(TO);
  return aimed && to ? `${from} → ${to}` : from;
}

/** What the row sends, in a few words. */
export function rowWhat(row: TutorialTraffic): string {
  if (row.kind === 'iperf3') return `iperf3 · ${(row.protocol ?? 'tcp').toUpperCase()} ${(row.bitrate ?? DEFAULT_BITRATE).trim()}`;
  return (row.command ?? '').trim() || 'no command yet';
}
