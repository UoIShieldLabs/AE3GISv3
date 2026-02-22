import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps, Node } from '@xyflow/react';
import type { ContainerType } from '../../data/sampleTopology';

export type RouterNodeData = {
  label: string;
  ip: string;
  type: ContainerType;
};

export type RouterNodeType = Node<RouterNodeData, 'routerNode'>;

const COLOR_ROUTER   = '#ff00ff';
const COLOR_FIREWALL = '#ff3344';

function color(type: ContainerType): string {
  return type === 'firewall' ? COLOR_FIREWALL : COLOR_ROUTER;
}

function RouterIcon({ type }: { type: ContainerType }) {
  const c = color(type);
  if (type === 'firewall') {
    return (
      <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
        <path d="M16 4L4 10v8c0 6.5 5.1 12.6 12 14 6.9-1.4 12-7.5 12-14v-8L16 4z"
          stroke={c} strokeWidth="1.5" fill="rgba(255,51,68,0.08)" strokeLinejoin="round" />
        <path d="M12 16h8M12 20h8" stroke={c} strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    );
  }
  return (
    <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
      <circle cx="16" cy="16" r="12" stroke={c} strokeWidth="1.5" fill="rgba(255,0,255,0.08)" />
      <path d="M16 8v16M8 16h16" stroke={c} strokeWidth="1.5" strokeLinecap="round" />
      <path d="M16 8l-3 3M16 8l3 3M16 24l-3-3M16 24l3-3M8 16l3-3M8 16l3 3M24 16l-3-3M24 16l-3 3"
        stroke={c} strokeWidth="1" strokeLinecap="round" />
    </svg>
  );
}

export const RouterNode = memo(function RouterNode({ data }: NodeProps<RouterNodeType>) {
  const c = color(data.type);
  const label = data.type === 'firewall' ? 'FW' : 'RTR';

  return (
    <div
      style={{
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '3px',
        padding: '8px 10px',
        background: '#14141e',
        border: `1px solid ${c}44`,
        borderRadius: '6px',
        minWidth: '90px',
        boxShadow: `0 0 10px ${c}11`,
      }}
    >
      {/* Incoming from subnet cloud above */}
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: c, width: 6, height: 6, border: 'none', opacity: 0.6 }}
      />
      {/* WAN links left/right */}
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: c, width: 6, height: 6, border: 'none', opacity: 0.6 }}
      />
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: c, width: 6, height: 6, border: 'none', opacity: 0.6 }}
      />
      {/* WAN links downward */}
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: c, width: 6, height: 6, border: 'none', opacity: 0.6 }}
      />

      <RouterIcon type={data.type} />

      <div style={{
        fontFamily: "'Share Tech Mono', monospace",
        fontSize: '10px',
        color: c,
        letterSpacing: '1px',
        opacity: 0.8,
      }}>
        {label}
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
        {data.label}
      </div>

      <div style={{
        fontFamily: "'Share Tech Mono', monospace",
        fontSize: '9px',
        color: '#505060',
      }}>
        {data.ip}
      </div>
    </div>
  );
});
