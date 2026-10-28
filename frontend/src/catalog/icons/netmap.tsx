// Netmap: plain geometric markers, like the nodes on Hacknet's network map.
// One shape per kind of device, thin strokes, no fill.
import type { Glyph, GlyphProps, IconStyle } from './types';

const W = 1.5;

function mark(paint: (color: string) => React.ReactNode): Glyph {
  return ({ color, size }: GlyphProps) => (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" stroke={color} strokeWidth={W} strokeLinejoin="round" strokeLinecap="round">
      {paint(color)}
    </svg>
  );
}

const HEXAGON = 'M16 4l11 6v12l-11 6-11-6V10z';

export const netmap = {
  id: 'netmap',
  label: 'Netmap',
  description: 'Hacknet-style network map markers',
  uiStrokeWidth: 1.5,
  glyphs: {
    router: mark((c) => (
      <>
        <path d="M16 4l12 12-12 12L4 16z" />
        <circle cx="16" cy="16" r="2.5" fill={c} stroke="none" />
      </>
    )),
    switch: mark(() => (
      <>
        <rect x="5" y="9" width="22" height="14" />
        <path d="M10 19v-3M14 19v-3M18 19v-3M22 19v-3" />
      </>
    )),
    firewall: mark(() => (
      <>
        <path d={HEXAGON} />
        <path d="M11 16h10" />
      </>
    )),
    server: mark(() => (
      <>
        <rect x="9" y="4" width="14" height="24" />
        <path d="M13 10h6M13 15h6" />
      </>
    )),
    plc: mark(() => (
      <>
        <rect x="6" y="6" width="20" height="20" />
        <rect x="12" y="12" width="8" height="8" />
      </>
    )),
    workstation: mark((c) => (
      <>
        <circle cx="16" cy="16" r="10" />
        <circle cx="16" cy="16" r="2.5" fill={c} stroke="none" />
      </>
    )),
    hmi: mark(() => (
      <>
        <rect x="5" y="7" width="22" height="15" />
        <path d="M11 26h10M9 14.5h14" />
      </>
    )),
    ids: mark((c) => (
      <>
        <path d="M16 5l12 21H4z" />
        <circle cx="16" cy="19" r="2.5" fill={c} stroke="none" />
      </>
    )),
    siem: mark((c) => (
      <>
        <path d={HEXAGON} />
        <circle cx="16" cy="16" r="5" />
        <circle cx="16" cy="16" r="1.5" fill={c} stroke="none" />
      </>
    )),
    attacker: mark(() => (
      <>
        <circle cx="16" cy="16" r="11" />
        <path d="M11.5 11.5l9 9M20.5 11.5l-9 9" />
      </>
    )),
    default: mark(() => <rect x="8" y="8" width="16" height="16" />),
  },
} as const satisfies IconStyle;
