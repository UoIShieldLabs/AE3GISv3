import type { ReactElement } from 'react';

export type GlyphProps = { color: string; size: number };
export type Glyph = (p: GlyphProps) => ReactElement;

/** A set of device glyphs, keyed by the catalog's `icon` names. */
export interface IconStyle {
  id: string;
  label: string;
  description: string;
  /** Stroke width the UI's Lucide icons take under this style. */
  uiStrokeWidth: number;
  /** A name this style doesn't draw falls back to Classic. */
  glyphs: Partial<Record<string, Glyph>>;
}
