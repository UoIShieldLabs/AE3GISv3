// How a monitor's device charts are grouped: one line per device, or one per
// subnet / device type (the devices' rows summed). Pure.
import { labelFor } from '@/catalog/catalog';
import type { TopologyData } from '@/types/topology';
import { nodesOf } from './selection';

export type GroupBy = 'none' | 'subnet' | 'type';

export const GROUP_BY: { value: GroupBy; label: string }[] = [
  { value: 'none', label: 'Each device' },
  { value: 'subnet', label: 'By subnet' },
  { value: 'type', label: 'By device type' },
];

export interface Grouping {
  /** A node id → its group key (null: not in the topology any more). */
  groupOf: (nodeId: string) => string | null;
  labelOf: (key: string) => string;
  /** Group keys in the topology's order, so a group keeps its colour. */
  order: string[];
}

/** Groups for ``by`` (not 'none'). A multi-homed device counts in its home subnet. */
export function grouping(topology: TopologyData, by: Exclude<GroupBy, 'none'>): Grouping {
  const nodes = nodesOf(topology);
  if (by === 'subnet') {
    const home = new Map(nodes.map((n) => [n.id, n.subnetIds[0] ?? null]));
    const names = new Map(topology.sites.flatMap((site) => site.subnets.map((sn) => [sn.id, sn.name] as const)));
    return {
      groupOf: (id) => home.get(id) ?? null,
      labelOf: (key) => names.get(key) ?? key,
      order: [...names.keys()],
    };
  }
  const type = new Map(nodes.map((n) => [n.id, n.type]));
  return {
    groupOf: (id) => type.get(id) ?? null,
    labelOf: (key) => labelFor(key),
    order: [...new Set(nodes.map((n) => n.type))],
  };
}
