// The device icon styles the app offers, independent of the color theme.
// Adding one is a glyph file plus an entry here.
import { classic, CLASSIC_GLYPHS } from './classic';
import { line } from './line';
import { netmap } from './netmap';
import type { Glyph, IconStyle } from './types';

export const ICON_STYLES = [classic, netmap, line] as const satisfies readonly IconStyle[];

export type IconStyleId = (typeof ICON_STYLES)[number]['id'];

export const DEFAULT_ICON_STYLE: IconStyleId = 'classic';

const BY_ID: Record<string, IconStyle> = Object.fromEntries(ICON_STYLES.map((s) => [s.id, s]));

/** The style for an id; one no longer offered (a stale saved choice) is Classic. */
export function iconStyleFor(id: string): IconStyle {
  return BY_ID[id] ?? classic;
}

/** A style's glyph for a catalog icon name, falling back to Classic's. */
export function glyphFor(styleId: string, icon: string): Glyph {
  return iconStyleFor(styleId).glyphs[icon] ?? CLASSIC_GLYPHS[icon] ?? CLASSIC_GLYPHS.default;
}
