// Catalog-keyed node glyphs, drawn in the user's icon style. The catalog's
// per-type `icon` name selects the glyph; the style (registry.ts) its look.
import { useAppStore } from '@/store';
import { colorFor, iconFor } from '../catalog';
// Everything but the component lives in ./registry.
import { glyphFor } from './registry';

/** Render the catalog glyph for a container type in the current icon style.
 *  Color and icon both come from the catalog; unknown types fall back to a
 *  neutral default glyph. */
export function NodeGlyph({ type, size = 32, color }: { type: string; size?: number; color?: string }) {
  const iconStyle = useAppStore((s) => s.iconStyle);
  const glyph = glyphFor(iconStyle, iconFor(type));
  const c = color ?? colorFor(type);
  // `ae-glyph`: the theme hook (a theme may glow it); `color` feeds its currentColor.
  return <span className="ae-glyph inline-flex shrink-0" style={{ color: c }}>{glyph({ color: c, size })}</span>;
}
