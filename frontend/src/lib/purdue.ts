// Purdue model levels: the one definition shared by the Purdue sheet, the
// Purdue canvas layout and the inspector. A device's level is its image's
// (`io.ae3gis.purdue-level`), else its catalog type's, else its subnet's
// (switches, routers, attackers, IDSs have none of their own). A subnet's
// level is its own override, else inferred from its devices.
import type { Container, Subnet } from '@/types/topology';
import { effectiveImage, imagePurdueLevel, purdueLevelFor, roleFor } from '@/catalog/catalog';

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

/** A subnet's level when nothing says otherwise (an office LAN). */
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

export function zoneOf(level: number): PurdueZone {
  return purdueLevelInfo(level).zone;
}

/** A device's own level: its image's, else its type's; undefined when neither
 *  has one (it then sits at its subnet's level). */
export function deviceOwnLevel(c: Pick<Container, 'type' | 'image'>): number | undefined {
  const own = imagePurdueLevel(effectiveImage(c)) ?? purdueLevelFor(c.type);
  return own === undefined ? undefined : snapPurdueLevel(own);
}

export type PurdueLevelSource = 'image' | 'type' | 'subnet';

/** A device's level and where it comes from (shown in the inspector). */
export function deviceLevelInfo(c: Pick<Container, 'type' | 'image'>, subnet: Pick<Subnet, 'name' | 'containers' | 'purdueLevel'>): { level: number; source: PurdueLevelSource } {
  const image = imagePurdueLevel(effectiveImage(c));
  if (image !== undefined) return { level: snapPurdueLevel(image), source: 'image' };
  const type = purdueLevelFor(c.type);
  if (type !== undefined) return { level: snapPurdueLevel(type), source: 'type' };
  return { level: subnetLevel(subnet), source: 'subnet' };
}

/** A device's level: its own, else its subnet's. */
export function deviceLevel(c: Pick<Container, 'type' | 'image'>, subnet: Pick<Subnet, 'name' | 'containers' | 'purdueLevel'>): number {
  return deviceOwnLevel(c) ?? subnetLevel(subnet);
}

/** A subnet's level when it has no override: "DMZ" in its name, else the
 *  median own level of its hosts (switches and routers are generic), else L4. */
export function inferSubnetLevel(subnet: Pick<Subnet, 'name' | 'containers'>): number {
  if (/\bdmz\b/i.test(subnet.name)) return 3.5;
  const levels = subnet.containers
    .filter((c) => roleFor(c.type) === 'host')
    .map(deviceOwnLevel)
    .filter((l): l is number => l !== undefined)
    .sort((a, b) => a - b);
  if (levels.length === 0) return DEFAULT_PURDUE_LEVEL;
  const mid = Math.floor(levels.length / 2);
  return snapPurdueLevel(levels.length % 2 ? levels[mid] : (levels[mid - 1] + levels[mid]) / 2);
}

/** A subnet's level: its `purdueLevel` override, else inferred. */
export function subnetLevel(subnet: Pick<Subnet, 'name' | 'containers' | 'purdueLevel'>): number {
  return typeof subnet.purdueLevel === 'number' ? snapPurdueLevel(subnet.purdueLevel) : inferSubnetLevel(subnet);
}
