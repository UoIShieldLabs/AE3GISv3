import { memo, useRef } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps, Node } from '@xyflow/react';
import type { Container } from '../../types/topology';
import { typeLabels, colorFor } from '../../catalog/catalog'
import { NodeGlyph } from '../../catalog/icons';

export type DeviceNodeData = {
  container: Container;
  onSelect: (container: Container) => void;
  onOpenTerminal: (container: Container) => void;
};

export type DeviceNodeType = Node<DeviceNodeData, 'device'>;

export const DeviceNode = memo(function DeviceNode({ data }: NodeProps<DeviceNodeType>) {
  const { container, onSelect, onOpenTerminal } = data;
  const color = colorFor(container.type);
  const typeLabel = typeLabels[container.type];
  const lastClickRef = useRef(0);

  const handleClick = () => {
    const now = Date.now();
    if (now - lastClickRef.current < 350) {
      // Double-click detected
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
        border: `1px solid ${color}33`,
        borderRadius: '6px',
        transition: 'all 0.2s ease',
        minWidth: '115px',
      }}
      onClick={handleClick}
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

      <NodeGlyph type={container.type} />

      <div style={{
        fontFamily: "'Share Tech Mono', monospace",
        fontSize: '14px',
        color: color,
        letterSpacing: '1px',
        opacity: 0.8,
      }}>
        {typeLabel}
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

      <Handle type="source" position={Position.Bottom} style={{ background: color, width: 6, height: 6, border: 'none' }} />
    </div>
  );
});
