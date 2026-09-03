// Node-type catalog — the frontend view of the backend's single source of
// truth (GET /api/catalog). Replaces the old Docker-Hub-scraped, codegenerated
// ContainerAspects.tsx. Values are populated once at startup by applyCatalog();
// the objects are mutated in place so existing imports keep a stable reference.

import type { ContainerType } from '../types/topology';

export type { ContainerType };

export interface NodeTypeSpec {
  displayName: string;
  role: 'router' | 'switch' | 'host';
  category: string;
  defaultImage: string;
  images: string[];
  color: string;
  label: string;
  icon: string;
  webUiPort?: number;
  purdueLevel?: number;
}

export interface Catalog {
  version: number;
  defaults: Record<string, string>;
  types: Record<string, NodeTypeSpec>;
}

// ── Live, catalog-backed lookup maps (filled by applyCatalog) ──────────────
export const typeColors: Record<string, string> = {};
export const typeLabels: Record<string, string> = {};
export const typeDisplayNames: Record<string, string> = {};
export const typeIcons: Record<string, string> = {};
export const typeRoles: Record<string, string> = {};
export const typeWebUiPorts: Record<string, number> = {};
export let typeOptions: { value: string; label: string }[] = [];
// category -> type -> available full image refs
export const menuHierarchy: Record<string, Record<string, string[]>> = {};

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
  for (const k of Object.keys(menuHierarchy)) delete menuHierarchy[k];
  const options: { value: string; label: string }[] = [];

  for (const [type, spec] of Object.entries(catalog.types)) {
    typeColors[type] = spec.color || DEFAULT_COLOR;
    typeLabels[type] = spec.label || DEFAULT_LABEL;
    typeDisplayNames[type] = spec.displayName || type;
    typeIcons[type] = spec.icon || DEFAULT_ICON;
    typeRoles[type] = spec.role;
    if (typeof spec.webUiPort === 'number') typeWebUiPorts[type] = spec.webUiPort;
    options.push({ value: type, label: spec.displayName || type });
    const cat = spec.category || 'other';
    (menuHierarchy[cat] ??= {})[type] = spec.images && spec.images.length ? spec.images : [spec.defaultImage];
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
