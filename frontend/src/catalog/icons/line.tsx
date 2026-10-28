// Line: the Lucide icons the rest of the UI uses, so devices match the chrome.
// They take the style's UI stroke width from the LucideProvider.
import {
  Box, BrickWallFire, ChartSpline, Cpu, EthernetPort, Gauge, Monitor, Router, ScanEye, Server, Skull,
  type LucideIcon,
} from 'lucide-react';
import type { Glyph, IconStyle } from './types';

const lucide = (Icon: LucideIcon): Glyph => ({ color, size }) => <Icon color={color} size={size} />;

export const line = {
  id: 'line',
  label: 'Line',
  description: 'Lucide line icons, like the rest of the UI',
  uiStrokeWidth: 1.75,
  glyphs: {
    router: lucide(Router),
    switch: lucide(EthernetPort),
    firewall: lucide(BrickWallFire),
    server: lucide(Server),
    plc: lucide(Cpu),
    workstation: lucide(Monitor),
    hmi: lucide(Gauge),
    ids: lucide(ScanEye),
    siem: lucide(ChartSpline),
    attacker: lucide(Skull),
    default: lucide(Box),
  },
} as const satisfies IconStyle;
