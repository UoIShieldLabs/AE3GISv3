// Catalog-keyed node glyphs. The catalog's per-type `icon` name selects one of
// these SVGs; a new node type reuses an existing icon by naming it in
// node_types.json (or falls back to `default`) — no code change needed here
// unless a genuinely new glyph is wanted.
import { colorFor, iconFor } from './catalog';

type GlyphProps = { color: string; size: number };

const GLYPHS: Record<string, (p: GlyphProps) => React.ReactElement> = {
  router: ({ color, size }) => (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <circle cx="16" cy="16" r="12" stroke={color} strokeWidth="1.5" fill="rgba(255,0,255,0.08)" />
      <path d="M16 8v16M8 16h16" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
      <path d="M16 8l-3 3M16 8l3 3M16 24l-3-3M16 24l3-3M8 16l3-3M8 16l3 3M24 16l-3-3M24 16l-3 3"
        stroke={color} strokeWidth="1" strokeLinecap="round" />
    </svg>
  ),
  firewall: ({ color, size }) => (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <path d="M16 4L4 10v8c0 6.5 5.1 12.6 12 14 6.9-1.4 12-7.5 12-14v-8L16 4z"
        stroke={color} strokeWidth="1.5" fill="rgba(255,51,68,0.08)" strokeLinejoin="round" />
      <path d="M12 16h8M12 20h8" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  ),
  switch: ({ color, size }) => (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <rect x="4" y="10" width="24" height="12" rx="2" stroke={color} strokeWidth="1.5" fill="rgba(255,170,0,0.08)" />
      <circle cx="10" cy="16" r="2" fill={color} opacity="0.6" />
      <circle cx="16" cy="16" r="2" fill={color} opacity="0.6" />
      <circle cx="22" cy="16" r="2" fill={color} opacity="0.6" />
    </svg>
  ),
  server: ({ color, size }) => (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <rect x="6" y="4" width="20" height="24" rx="2" stroke={color} strokeWidth="1.5" fill="rgba(0,255,159,0.08)" />
      <line x1="10" y1="10" x2="22" y2="10" stroke={color} strokeWidth="1" opacity="0.6" />
      <line x1="10" y1="14" x2="22" y2="14" stroke={color} strokeWidth="1" opacity="0.6" />
      <line x1="10" y1="18" x2="22" y2="18" stroke={color} strokeWidth="1" opacity="0.6" />
      <circle cx="16" cy="24" r="1.5" fill={color} opacity="0.4" />
    </svg>
  ),
  plc: ({ color, size }) => (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <rect x="5" y="6" width="22" height="20" rx="2" stroke={color} strokeWidth="1.5" fill="rgba(255,170,0,0.08)" />
      <rect x="8" y="9" width="4" height="4" rx="1" fill={color} opacity="0.4" />
      <rect x="14" y="9" width="4" height="4" rx="1" fill={color} opacity="0.6" />
      <rect x="20" y="9" width="4" height="4" rx="1" fill={color} opacity="0.3" />
      <line x1="8" y1="18" x2="24" y2="18" stroke={color} strokeWidth="1" opacity="0.3" />
      <line x1="8" y1="22" x2="24" y2="22" stroke={color} strokeWidth="1" opacity="0.3" />
    </svg>
  ),
  workstation: ({ color, size }) => (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <rect x="6" y="6" width="20" height="14" rx="2" stroke={color} strokeWidth="1.5" fill="rgba(68,102,255,0.08)" />
      <line x1="12" y1="24" x2="20" y2="24" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
      <line x1="16" y1="20" x2="16" y2="24" stroke={color} strokeWidth="1.5" />
      <line x1="10" y1="12" x2="14" y2="12" stroke={color} strokeWidth="1" opacity="0.5" />
    </svg>
  ),
  hmi: ({ color, size }) => (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <rect x="6" y="6" width="20" height="14" rx="2" stroke={color} strokeWidth="1.5" fill="rgba(51,204,255,0.08)" />
      <path d="M8 14h16" stroke={color} strokeWidth="1" opacity="0.7" />
      <path d="M8 10h16" stroke={color} strokeWidth="1" opacity="0.7" />
      <rect x="12" y="18" width="8" height="2" fill={color} opacity="0.8" />
      <circle cx="16" cy="26" r="1.5" fill={color} opacity="0.8" />
    </svg>
  ),
  ids: ({ color, size }) => (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <path d="M16 4L5 9v7c0 6 4.7 11.6 11 13 6.3-1.4 11-7 11-13V9L16 4z"
        stroke={color} strokeWidth="1.5" fill="rgba(255,136,0,0.08)" strokeLinejoin="round" />
      <path d="M9.5 16.5c1.8-3 4-4.5 6.5-4.5s4.7 1.5 6.5 4.5c-1.8 3-4 4.5-6.5 4.5s-4.7-1.5-6.5-4.5z"
        stroke={color} strokeWidth="1.2" strokeLinejoin="round" />
      <circle cx="16" cy="16.5" r="1.8" fill={color} />
    </svg>
  ),
  siem: ({ color, size }) => (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <rect x="5" y="6" width="22" height="16" rx="2" stroke={color} strokeWidth="1.5" fill="rgba(176,77,255,0.08)" />
      <path d="M8 18l4-4 3 2 4-5 3 3" stroke={color} strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
      <line x1="12" y1="26" x2="20" y2="26" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
      <line x1="16" y1="22" x2="16" y2="26" stroke={color} strokeWidth="1.5" />
    </svg>
  ),
  attacker: ({ color, size }) => (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <rect x="6" y="6" width="20" height="14" rx="2" stroke={color} strokeWidth="1.5" fill="rgba(255,34,102,0.08)" />
      <path d="M10 11l3 2-3 2" stroke={color} strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
      <line x1="15" y1="15.5" x2="20" y2="15.5" stroke={color} strokeWidth="1.3" strokeLinecap="round" />
      <line x1="12" y1="24" x2="20" y2="24" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
      <line x1="16" y1="20" x2="16" y2="24" stroke={color} strokeWidth="1.5" />
    </svg>
  ),
  default: ({ color, size }) => (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <rect x="7" y="9" width="18" height="14" rx="2" stroke={color} strokeWidth="1.5" fill="rgba(156,163,175,0.10)" />
      <circle cx="16" cy="16" r="3" stroke={color} strokeWidth="1.5" />
    </svg>
  ),
};

/** Render the catalog glyph for a container type. Color and icon both come from
 *  the catalog; unknown types fall back to a neutral default glyph. */
export function NodeGlyph({ type, size = 32, color }: { type: string; size?: number; color?: string }) {
  const glyph = GLYPHS[iconFor(type)] ?? GLYPHS.default;
  return glyph({ color: color ?? colorFor(type), size });
}
