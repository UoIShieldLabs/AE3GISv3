// Node-type catalog — the frontend view of the backend's single source of
// truth (GET /api/v1/catalog). Its types are generated from the backend's
// OpenAPI document. Values are populated once at startup by applyCatalog();
// the objects are mutated in place so existing imports keep a stable reference.

import type { components } from '@/api/schema';
import type { ContainerType } from '../types/topology';

export type { ContainerType };

export type Catalog = components['schemas']['Catalog'];
export type NodeTypeSpec = components['schemas']['NodeTypeSpec'];
export type ImageSpec = components['schemas']['ImageSpec'];
export type Stability = ImageSpec['stability'];

// ── Live, catalog-backed lookup maps (filled by applyCatalog) ──────────────
export const typeColors: Record<string, string> = {};
export const typeLabels: Record<string, string> = {};
export const typeDisplayNames: Record<string, string> = {};
export const typeIcons: Record<string, string> = {};
export const typeRoles: Record<string, string> = {};
export const typeWebUiPorts: Record<string, number> = {};
export let typeOptions: { value: string; label: string }[] = [];

const DEFAULT_COLOR = '#9ca3af';
const DEFAULT_LABEL = 'UNK';
const DEFAULT_ICON = 'default';

let _catalog: Catalog | null = null;

export function applyCatalog(catalog: Catalog): void {
  _catalog = catalog;
  // Clear then refill in place to preserve references held by importers.
  for (const k of Object.keys(typeColors)) delete typeColors[k];
  for (const k of Object.keys(typeLabels)) delete typeLabels[k];
  for (const k of Object.keys(typeDisplayNames)) delete typeDisplayNames[k];
  for (const k of Object.keys(typeIcons)) delete typeIcons[k];
  for (const k of Object.keys(typeRoles)) delete typeRoles[k];
  for (const k of Object.keys(typeWebUiPorts)) delete typeWebUiPorts[k];
  const options: { value: string; label: string }[] = [];

  for (const [type, spec] of Object.entries(catalog.types)) {
    typeColors[type] = spec.color || DEFAULT_COLOR;
    typeLabels[type] = spec.label || DEFAULT_LABEL;
    typeDisplayNames[type] = spec.displayName || type;
    typeIcons[type] = spec.icon || DEFAULT_ICON;
    typeRoles[type] = spec.role;
    if (typeof spec.webUiPort === 'number') typeWebUiPorts[type] = spec.webUiPort;
    options.push({ value: type, label: spec.displayName || type });
  }
  typeOptions = options;
}

export function getCatalog(): Catalog | null {
  return _catalog;
}

export function colorFor(type: string): string {
  return typeColors[type] ?? DEFAULT_COLOR;
}

export function labelFor(type: string): string {
  return typeLabels[type] ?? DEFAULT_LABEL;
}

export function iconFor(type: string): string {
  return typeIcons[type] ?? DEFAULT_ICON;
}

export function displayNameFor(type: string): string {
  return typeDisplayNames[type] ?? type;
}

export function defaultImageFor(type: string): string {
  return _catalog?.types[type]?.defaultImage ?? (_catalog?.defaults?.host_image ?? '');
}

/** The image refs a type offers (its variants), default first as listed. */
export function variantsFor(type: string): string[] {
  const spec = _catalog?.types[type];
  if (!spec) return [];
  return spec.images?.length ? spec.images : [spec.defaultImage];
}

/** What the catalog says about an image ref (undefined: a plain registry image). */
export function imageSpecFor(ref: string): ImageSpec | undefined {
  return _catalog?.images?.[ref];
}

/** Friendly name for an image ref (its catalog name, else the ref itself). */
export function imageNameFor(ref: string): string {
  return imageSpecFor(ref)?.displayName ?? ref;
}

/** True when AE3GIS builds this image from a Dockerfile (vs pulling it). */
export function isBuiltImage(ref: string): boolean {
  return imageSpecFor(ref)?.source?.kind === 'build';
}

/** The image a container deploys with: its own, else its type's default. */
export function effectiveImage(container: { type: string; image?: string }): string {
  return container.image?.trim() || defaultImageFor(container.type);
}

/** Layout rank for a type (routers on top, switches, then hosts). */
export function rankFor(type: string): number {
  const role = typeRoles[type];
  if (role === 'router') return 0;
  if (role === 'switch') return 1;
  return 2;
}

export type NodeRole = NodeTypeSpec['role'];

/** Engine role for a type. Falls back to the conventional names when the
 *  catalog has not loaded so gateway detection still works offline. */
export function roleFor(type: string): NodeRole {
  const role = typeRoles[type];
  if (role === 'router' || role === 'switch' || role === 'host') return role;
  if (type === 'router' || type === 'firewall') return 'router';
  if (type === 'switch') return 'switch';
  return 'host';
}

export function purdueLevelFor(type: string): number | undefined {
  return _catalog?.types[type]?.purdueLevel ?? undefined;
}

export function categoryFor(type: string): string {
  return _catalog?.types[type]?.category ?? 'other';
}

const CATEGORY_LABELS: Record<string, string> = { ics: 'ICS', ot: 'OT', it: 'IT', iot: 'IoT', dmz: 'DMZ' };

/** Human label for a catalog category id (declared label first). */
export function categoryLabel(category: string, catalog: Catalog | null = _catalog): string {
  const c = category.trim();
  const declared = catalog?.categories?.find((x) => x.id === c)?.label;
  if (declared) return declared;
  if (!c) return 'Other';
  return CATEGORY_LABELS[c.toLowerCase()] ?? c[0].toUpperCase() + c.slice(1);
}
