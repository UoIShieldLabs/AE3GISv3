import { memo, useRef } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps, Node } from '@xyflow/react';
import type { Container } from '../../data/sampleTopology';

export type HmiNodeData = {
  container: Container;
  onSelect: (container: Container) => void;
  onOpenTerminal: (container: Container) => void;
};

export type HmiNodeType = Node<HmiNodeData, 'hmi'>;

const HMI_COLOR = '#33ccff';

function HmiIcon() {
  const color = HMI_COLOR;
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
      <rect x="6" y="6" width="20" height="14" rx="2" stroke={color} strokeWidth="1.5" fill="rgba(51,204,255,0.08)" />
      <path d="M8 14h16" stroke={color} strokeWidth="1" opacity="0.7" />
      <path d="M8 10h16" stroke={color} strokeWidth="1" opacity="0.7" />
      <rect x="12" y="18" width="8" height="2" fill={color} opacity="0.8" />
      <circle cx="16" cy="26" r="1.5" fill={color} opacity="0.8" />
    </svg>
  );
}

export const HmiNode = memo(function HmiNode({ data }: NodeProps<HmiNodeType>) {
  const { container, onSelect, onOpenTerminal } = data;
  const lastClickRef = useRef(0);

  const handleClick = () => {
    const now = Date.now();
    if (now - lastClickRef.current < 350) {
      onOpenTerminal(container);
      lastClickRef.current = 0;
    } else {
      lastClickRef.current = now;
      onSelect(container);
    }
  };

  return (
    <div
      style={{
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '5px',
        padding: '14px 18px',
        background: '#14141e',
        border: `1px solid ${HMI_COLOR}33`,
        borderRadius: '6px',
        transition: 'all 0.2s ease',
        minWidth: '115px',
      }}
      onClick={handleClick}
      onMouseEnter={(e) => {
        const el = e.currentTarget;
        el.style.borderColor = `${HMI_COLOR}88`;
        el.style.boxShadow = `0 0 15px ${HMI_COLOR}22`;
        el.style.background = '#1a1a28';
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget;
        el.style.borderColor = `${HMI_COLOR}33`;
        el.style.boxShadow = 'none';
        el.style.background = '#14141e';
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: HMI_COLOR, width: 6, height: 6, border: 'none' }} />

      <HmiIcon />

      <div style={{
        fontFamily: "'Share Tech Mono', monospace",
        fontSize: '14px',
        color: HMI_COLOR,
        letterSpacing: '1px',
        opacity: 0.8,
      }}>
        HMI
      </div>

      <div style={{
        fontFamily: "'Rajdhani', sans-serif",
        fontSize: '16px',
        fontWeight: 600,
        color: '#d0d0d8',
        textAlign: 'center',
        maxWidth: '120px',
        wordBreak: 'break-word',
      }}>
        {container.name}
      </div>

      <div style={{
        fontFamily: "'Share Tech Mono', monospace",
        fontSize: '14px',
        color: '#505060',
      }}>
        {container.ip}
      </div>

      {container.status && (
        <div style={{
          width: '9px',
          height: '9px',
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

      <Handle type="source" position={Position.Bottom} style={{ background: HMI_COLOR, width: 6, height: 6, border: 'none' }} />
    </div>
  );
});