import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps, Node } from '@xyflow/react';
import type { ContainerType, Container } from '../../data/sampleTopology';

export type DeviceNodeData = {
  container: Container;
  onSelect: (container: Container) => void;
  onOpenTerminal: (container: Container) => void;
};

export type DeviceNodeType = Node<DeviceNodeData, 'device'>;

const typeColors: Record<ContainerType, string> = {
  'router': '#ff00ff',
  'firewall': '#ff3344',
  'switch': '#ffaa00',
  'web-server': '#00ff9f',
  'file-server': '#00d4ff',
  'plc': '#ffaa00',
  'workstation': '#4466ff',
};

const typeLabels: Record<ContainerType, string> = {
  'router': 'RTR',
  'firewall': 'FW',
  'switch': 'SW',
  'web-server': 'WEB',
  'file-server': 'FS',
  'plc': 'PLC',
  'workstation': 'WS',
};

function DeviceIcon({ type }: { type: ContainerType }) {
  const color = typeColors[type];

  switch (type) {
    case 'router':
      return (
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
          <circle cx="16" cy="16" r="12" stroke={color} strokeWidth="1.5" fill="rgba(255,0,255,0.08)" />
          <path d="M16 8v16M8 16h16" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
          <path d="M16 8l-3 3M16 8l3 3M16 24l-3-3M16 24l3-3M8 16l3-3M8 16l3 3M24 16l-3-3M24 16l-3 3"
            stroke={color} strokeWidth="1" strokeLinecap="round" />
        </svg>
      );

    case 'firewall':
      return (
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
          <path d="M16 4L4 10v8c0 6.5 5.1 12.6 12 14 6.9-1.4 12-7.5 12-14v-8L16 4z"
            stroke={color} strokeWidth="1.5" fill="rgba(255,51,68,0.08)" strokeLinejoin="round" />
          <path d="M12 16h8M12 20h8" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );

    case 'switch':
      return (
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
          <rect x="4" y="10" width="24" height="12" rx="2" stroke={color} strokeWidth="1.5" fill="rgba(255,170,0,0.08)" />
          <circle cx="10" cy="16" r="2" fill={color} opacity="0.6" />
          <circle cx="16" cy="16" r="2" fill={color} opacity="0.6" />
          <circle cx="22" cy="16" r="2" fill={color} opacity="0.6" />
        </svg>
      );

    case 'web-server':
      return (
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
          <rect x="6" y="4" width="20" height="24" rx="2" stroke={color} strokeWidth="1.5" fill="rgba(0,255,159,0.08)" />
          <line x1="10" y1="10" x2="22" y2="10" stroke={color} strokeWidth="1" opacity="0.6" />
          <line x1="10" y1="14" x2="22" y2="14" stroke={color} strokeWidth="1" opacity="0.6" />
          <line x1="10" y1="18" x2="22" y2="18" stroke={color} strokeWidth="1" opacity="0.6" />
          <circle cx="16" cy="24" r="1.5" fill={color} opacity="0.4" />
        </svg>
      );

    case 'file-server':
      return (
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
          <rect x="6" y="4" width="20" height="24" rx="2" stroke={color} strokeWidth="1.5" fill="rgba(0,212,255,0.08)" />
          <path d="M10 4h6l2 4H10V4z" stroke={color} strokeWidth="1" fill="rgba(0,212,255,0.15)" />
          <line x1="10" y1="14" x2="22" y2="14" stroke={color} strokeWidth="1" opacity="0.4" />
          <line x1="10" y1="18" x2="22" y2="18" stroke={color} strokeWidth="1" opacity="0.4" />
          <line x1="10" y1="22" x2="22" y2="22" stroke={color} strokeWidth="1" opacity="0.4" />
        </svg>
      );

    case 'plc':
      return (
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
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
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
          <rect x="6" y="6" width="20" height="14" rx="2" stroke={color} strokeWidth="1.5" fill="rgba(68,102,255,0.08)" />
          <line x1="12" y1="24" x2="20" y2="24" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
          <line x1="16" y1="20" x2="16" y2="24" stroke={color} strokeWidth="1.5" />
          <line x1="10" y1="12" x2="14" y2="12" stroke={color} strokeWidth="1" opacity="0.5" />
        </svg>
      );
  }
}

export const DeviceNode = memo(function DeviceNode({ data }: NodeProps<DeviceNodeType>) {
  const { container, onSelect, onOpenTerminal } = data;
  const color = typeColors[container.type];
  const typeLabel = typeLabels[container.type];

  return (
    <div
      style={{
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '4px',
        padding: '10px 12px',
        background: '#14141e',
        border: `1px solid ${color}33`,
        borderRadius: '6px',
        transition: 'all 0.2s ease',
        minWidth: '90px',
      }}
      onClick={() => onSelect(container)}
      onDoubleClick={(e) => { e.stopPropagation(); onOpenTerminal(container); }}
      onMouseEnter={(e) => {
        const el = e.currentTarget;
        el.style.borderColor = `${color}88`;
        el.style.boxShadow = `0 0 15px ${color}22`;
        el.style.background = '#1a1a28';
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget;
        el.style.borderColor = `${color}33`;
        el.style.boxShadow = 'none';
        el.style.background = '#14141e';
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: color, width: 6, height: 6, border: 'none' }} />

      <DeviceIcon type={container.type} />

      <div style={{
        fontFamily: "'Share Tech Mono', monospace",
        fontSize: '10px',
        color: color,
        letterSpacing: '1px',
        opacity: 0.8,
      }}>
        {typeLabel}
      </div>

      <div style={{
        fontFamily: "'Rajdhani', sans-serif",
        fontSize: '11px',
        fontWeight: 600,
        color: '#d0d0d8',
        textAlign: 'center',
        maxWidth: '100px',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>
        {container.name}
      </div>

      <div style={{
        fontFamily: "'Share Tech Mono', monospace",
        fontSize: '9px',
        color: '#505060',
      }}>
        {container.ip}
      </div>

      {container.status && (
        <div style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          background: container.status === 'running' ? '#00ff9f' : '#ff3344',
          boxShadow: container.status === 'running'
            ? '0 0 6px rgba(0,255,159,0.5)'
            : '0 0 6px rgba(255,51,68,0.5)',
          position: 'absolute',
          top: '6px',
          right: '6px',
        }} />
      )}

      <Handle type="source" position={Position.Bottom} style={{ background: color, width: 6, height: 6, border: 'none' }} />
    </div>
  );
});
