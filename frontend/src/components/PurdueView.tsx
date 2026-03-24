import { useState, useEffect, useRef } from 'react';
import type { TopologyData, Container, ContainerType } from '../data/sampleTopology';
import './PurdueView.css';

interface PurdueViewProps {
  open: boolean;
  onClose: () => void;
  topology: TopologyData;
}

const PURDUE_LEVELS = [
  { level: 5,   label: 'Level 5', name: 'Enterprise Network',            color: '#4466ff', zone: 'it'  },
  { level: 4,   label: 'Level 4', name: 'Business Planning & Logistics', color: '#4466ff', zone: 'it'  },
  { level: 3.5, label: 'DMZ',     name: 'Demilitarized Zone',            color: '#ff3344', zone: 'dmz' },
  { level: 3,   label: 'Level 3', name: 'Operations Management',         color: '#ffaa00', zone: 'ot'  },
  { level: 2,   label: 'Level 2', name: 'Control Zone (SCADA/HMI)',      color: '#ffaa00', zone: 'ot'  },
  { level: 1,   label: 'Level 1', name: 'Field Control (PLCs/RTUs)',     color: '#00ff9f', zone: 'ot'  },
  { level: 0,   label: 'Level 0', name: 'Physical Process',              color: '#00ff9f', zone: 'ot'  },
] as const;

type PurdueLevel = (typeof PURDUE_LEVELS)[number];

const TYPE_COLORS: Record<ContainerType, string> = {
  'router':      '#ff00ff',
  'firewall':    '#ff3344',
  'switch':      '#ffaa00',
  'web-server':  '#00ff9f',
  'file-server': '#00d4ff',
  'plc':         '#ffaa00',
  'workstation': '#4466ff',
  'hmi':         '#33ccff',
};

const TYPE_LABELS: Record<ContainerType, string> = {
  'router':      'RTR',
  'firewall':    'FW',
  'switch':      'SW',
  'web-server':  'WEB',
  'file-server': 'FS',
  'plc':         'PLC',
  'workstation': 'WS',
  'hmi':         'HMI',
};

type SubnetZone = 'ot' | 'dmz' | 'it';

function classifySubnetZone(containers: Container[]): SubnetZone {
  const types = new Set(containers.map(c => c.type));
  // OT: any subnet hosting a PLC is operational technology
  if (types.has('plc')) return 'ot';
  // DMZ: server-only subnets (historian, jumpbox, etc.) with no end-user workstations
  const hasServers = types.has('web-server') || types.has('file-server');
  const hasWorkstations = types.has('workstation') || types.has('hmi');
  if (hasServers && !hasWorkstations) return 'dmz';
  // IT: everything else (workstation subnets, mixed IT subnets)
  return 'it';
}

function assignPurdueLevel(zone: SubnetZone, containerType: ContainerType): number {
  if (zone === 'ot') {
    if (containerType === 'plc') return 1;
    if (containerType === 'workstation' || containerType === 'hmi') return 2;
    return 3;
  }
  if (zone === 'dmz') return 3.5;
  // IT zone: infrastructure + servers → Level 4, end-user workstations → Level 5
  if (containerType === 'router' || containerType === 'switch' || containerType === 'firewall'
      || containerType === 'web-server' || containerType === 'file-server') return 4;
  return 5;
}

function DeviceIcon({ type }: { type: ContainerType }) {
  const color = TYPE_COLORS[type];
  switch (type) {
    case 'router':
      return (
        <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
          <circle cx="16" cy="16" r="12" stroke={color} strokeWidth="1.5" fill="rgba(255,0,255,0.08)" />
          <path d="M16 8v16M8 16h16" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
          <path d="M16 8l-3 3M16 8l3 3M16 24l-3-3M16 24l3-3M8 16l3-3M8 16l3 3M24 16l-3-3M24 16l-3 3"
            stroke={color} strokeWidth="1" strokeLinecap="round" />
        </svg>
      );
    case 'firewall':
      return (
        <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
          <path d="M16 4L4 10v8c0 6.5 5.1 12.6 12 14 6.9-1.4 12-7.5 12-14v-8L16 4z"
            stroke={color} strokeWidth="1.5" fill="rgba(255,51,68,0.08)" strokeLinejoin="round" />
          <path d="M12 16h8M12 20h8" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );
    case 'switch':
      return (
        <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
          <rect x="4" y="10" width="24" height="12" rx="2" stroke={color} strokeWidth="1.5" fill="rgba(255,170,0,0.08)" />
          <circle cx="10" cy="16" r="2" fill={color} opacity="0.6" />
          <circle cx="16" cy="16" r="2" fill={color} opacity="0.6" />
          <circle cx="22" cy="16" r="2" fill={color} opacity="0.6" />
        </svg>
      );
    case 'web-server':
      return (
        <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
          <rect x="6" y="4" width="20" height="24" rx="2" stroke={color} strokeWidth="1.5" fill="rgba(0,255,159,0.08)" />
          <line x1="10" y1="10" x2="22" y2="10" stroke={color} strokeWidth="1" opacity="0.6" />
          <line x1="10" y1="14" x2="22" y2="14" stroke={color} strokeWidth="1" opacity="0.6" />
          <line x1="10" y1="18" x2="22" y2="18" stroke={color} strokeWidth="1" opacity="0.6" />
          <circle cx="16" cy="24" r="1.5" fill={color} opacity="0.4" />
        </svg>
      );
    case 'file-server':
      return (
        <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
          <rect x="6" y="4" width="20" height="24" rx="2" stroke={color} strokeWidth="1.5" fill="rgba(0,212,255,0.08)" />
          <path d="M10 4h6l2 4H10V4z" stroke={color} strokeWidth="1" fill="rgba(0,212,255,0.15)" />
          <line x1="10" y1="14" x2="22" y2="14" stroke={color} strokeWidth="1" opacity="0.4" />
          <line x1="10" y1="18" x2="22" y2="18" stroke={color} strokeWidth="1" opacity="0.4" />
          <line x1="10" y1="22" x2="22" y2="22" stroke={color} strokeWidth="1" opacity="0.4" />
        </svg>
      );
    case 'plc':
      return (
        <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
          <rect x="5" y="6" width="22" height="20" rx="2" stroke={color} strokeWidth="1.5" fill="rgba(255,170,0,0.08)" />
          <rect x="8" y="9" width="4" height="4" rx="1" fill={color} opacity="0.4" />
          <rect x="14" y="9" width="4" height="4" rx="1" fill={color} opacity="0.6" />
          <rect x="20" y="9" width="4" height="4" rx="1" fill={color} opacity="0.3" />
          <line x1="8" y1="18" x2="24" y2="18" stroke={color} strokeWidth="1" opacity="0.3" />
          <line x1="8" y1="22" x2="24" y2="22" stroke={color} strokeWidth="1" opacity="0.3" />
        </svg>
      );
    case 'workstation':
      return (
        <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
          <rect x="6" y="6" width="20" height="14" rx="2" stroke={color} strokeWidth="1.5" fill="rgba(68,102,255,0.08)" />
          <line x1="12" y1="24" x2="20" y2="24" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
          <line x1="16" y1="20" x2="16" y2="24" stroke={color} strokeWidth="1.5" />
          <line x1="10" y1="12" x2="14" y2="12" stroke={color} strokeWidth="1" opacity="0.5" />
        </svg>
      );
  }
}

interface ContainerEntry {
  container: Container;
  subnetName: string;
  level: number;
}

function DeviceCard({ entry, levelColor }: { entry: ContainerEntry; levelColor: string }) {
  const { container, subnetName } = entry;
  const typeColor = TYPE_COLORS[container.type];
  const typeLabel = TYPE_LABELS[container.type];
  return (
    <div className="purdue-card" style={{ borderColor: `${levelColor}55` }}>
      <DeviceIcon type={container.type} />
      <div className="purdue-card-type" style={{ color: typeColor }}>{typeLabel}</div>
      <div className="purdue-card-name">{container.name}</div>
      <div className="purdue-card-ip">{container.ip}</div>
      <div className="purdue-card-subnet" style={{ borderColor: `${levelColor}44`, color: levelColor }}>
        {subnetName}
      </div>
    </div>
  );
}

function PurdueRow({ levelDef, entries }: { levelDef: PurdueLevel; entries: ContainerEntry[] }) {
  return (
    <div className="purdue-row">
      <div className="purdue-row-level" style={{ color: levelDef.color, borderColor: `${levelDef.color}33` }}>
        {levelDef.label}
      </div>
      <div className="purdue-row-name" style={{ color: levelDef.color }}>
        {levelDef.name}
      </div>
      <div className="purdue-row-cards">
        {entries.length === 0 ? (
          <div className="purdue-empty-band">(empty)</div>
        ) : (
          entries.map(entry => (
            <DeviceCard key={entry.container.id} entry={entry} levelColor={levelDef.color} />
          ))
        )}
      </div>
    </div>
  );
}

export function PurdueView({ open, onClose, topology }: PurdueViewProps) {
  const [selectedSiteId, setSelectedSiteId] = useState<string>('');
  const mouseDownOnOverlay = useRef(false);

  useEffect(() => {
    if (!open) return;
    const handle = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handle);
    return () => document.removeEventListener('keydown', handle);
  }, [open, onClose]);

  // Default to first site when opening
  useEffect(() => {
    if (open && topology.sites.length > 0) {
      setSelectedSiteId(s =>
        s && topology.sites.find(x => x.id === s) ? s : topology.sites[0].id
      );
    }
  }, [open, topology.sites]);

  if (!open) return null;

  const site = topology.sites.find(s => s.id === selectedSiteId);

  // Build level → ContainerEntry[]
  const levelMap = new Map<number, ContainerEntry[]>();
  for (const pl of PURDUE_LEVELS) levelMap.set(pl.level, []);

  if (site) {
    for (const subnet of site.subnets) {
      const zone = classifySubnetZone(subnet.containers);
      for (const container of subnet.containers) {
        const level = assignPurdueLevel(zone, container.type);
        levelMap.get(level)?.push({ container, subnetName: subnet.name, level });
      }
    }
  }

  const itLevels = PURDUE_LEVELS.filter(pl => pl.zone === 'it');
  const dmzLevels = PURDUE_LEVELS.filter(pl => pl.zone === 'dmz');
  const otLevels = PURDUE_LEVELS.filter(pl => pl.zone === 'ot');

  return (
    <div
      className="purdue-overlay"
      onMouseDown={e => { mouseDownOnOverlay.current = e.target === e.currentTarget; }}
      onClick={() => { if (mouseDownOnOverlay.current) onClose(); }}
    >
      <div className="purdue-panel" onClick={e => e.stopPropagation()}>
        <div className="purdue-header">
          <div className="purdue-title">Purdue Model</div>
          <div className="purdue-site-selector">
            <span className="purdue-site-label">Site:</span>
            <select
              className="purdue-select"
              value={selectedSiteId}
              onChange={e => setSelectedSiteId(e.target.value)}
            >
              {topology.sites.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <button className="purdue-close" onClick={onClose}>×</button>
        </div>

        <div className="purdue-body">
          <div className="purdue-zone purdue-zone-it">
            <div className="purdue-zone-label" style={{ color: '#4466ff' }}>IT</div>
            <div className="purdue-zone-rows">
              {itLevels.map(pl => (
                <PurdueRow key={pl.level} levelDef={pl} entries={levelMap.get(pl.level) ?? []} />
              ))}
            </div>
          </div>

          <div className="purdue-zone purdue-zone-dmz">
            <div className="purdue-zone-label" style={{ color: '#ff3344' }}>DMZ</div>
            <div className="purdue-zone-rows">
              {dmzLevels.map(pl => (
                <PurdueRow key={pl.level} levelDef={pl} entries={levelMap.get(pl.level) ?? []} />
              ))}
            </div>
          </div>

          <div className="purdue-zone purdue-zone-ot">
            <div className="purdue-zone-label" style={{ color: '#00ff9f' }}>OT</div>
            <div className="purdue-zone-rows">
              {otLevels.map(pl => (
                <PurdueRow key={pl.level} levelDef={pl} entries={levelMap.get(pl.level) ?? []} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
