// Purdue model levels: the one definition shared by the Purdue sheet, the
// Purdue canvas layout and the subnet inspector. Device levels come from the
// catalog (`purdueLevel` per type); a subnet's level is its own override, else
// inferred from its devices.
import type { Container, Subnet } from '@/types/topology';
import { purdueLevelFor, roleFor } from '@/catalog/catalog';

export type PurdueZone = 'IT' | 'DMZ' | 'OT';

export const PURDUE_LEVELS = [
  { level: 5, label: 'Level 5', name: 'Enterprise network', zone: 'IT' },
  { level: 4, label: 'Level 4', name: 'Business planning & logistics', zone: 'IT' },
  { level: 3.5, label: 'DMZ', name: 'Demilitarized zone', zone: 'DMZ' },
  { level: 3, label: 'Level 3', name: 'Operations management', zone: 'OT' },
  { level: 2, label: 'Level 2', name: 'Control (SCADA / HMI)', zone: 'OT' },
  { level: 1, label: 'Level 1', name: 'Field control (PLC / RTU)', zone: 'OT' },
  { level: 0, label: 'Level 0', name: 'Physical process', zone: 'OT' },
] as const satisfies readonly { level: number; label: string; name: string; zone: PurdueZone }[];

/** Level used for a type the catalog gives no level (matches the Purdue sheet). */
export const DEFAULT_PURDUE_LEVEL = 4;

/** Nearest of the model's levels (5, 4, 3.5, 3, 2, 1, 0). */
export function snapPurdueLevel(n: number): number {
  let best: number = PURDUE_LEVELS[0].level;
  for (const { level } of PURDUE_LEVELS) if (Math.abs(level - n) < Math.abs(best - n)) best = level;
  return best;
}

export function purdueLevelInfo(level: number): (typeof PURDUE_LEVELS)[number] {
  const snapped = snapPurdueLevel(level);
  return PURDUE_LEVELS.find((l) => l.level === snapped) ?? PURDUE_LEVELS[1];
}

/** A device's level, from its catalog type. */
export function deviceLevel(c: Pick<Container, 'type'>): number {
  return snapPurdueLevel(purdueLevelFor(c.type) ?? DEFAULT_PURDUE_LEVEL);
}

/** A subnet's level when it has no override: "DMZ" in its name, else the
 *  median level of its hosts (switches and routers are generic), else L4. */
export function inferSubnetLevel(subnet: Pick<Subnet, 'name' | 'containers'>): number {
  if (/\bdmz\b/i.test(subnet.name)) return 3.5;
  const levels = subnet.containers.filter((c) => roleFor(c.type) === 'host').map(deviceLevel).sort((a, b) => a - b);
  if (levels.length === 0) return DEFAULT_PURDUE_LEVEL;
  const mid = Math.floor(levels.length / 2);
  return snapPurdueLevel(levels.length % 2 ? levels[mid] : (levels[mid - 1] + levels[mid]) / 2);
}

/** A subnet's level: its `purdueLevel` override, else inferred. */
export function subnetLevel(subnet: Pick<Subnet, 'name' | 'containers' | 'purdueLevel'>): number {
  return typeof subnet.purdueLevel === 'number' ? snapPurdueLevel(subnet.purdueLevel) : inferSubnetLevel(subnet);
}
