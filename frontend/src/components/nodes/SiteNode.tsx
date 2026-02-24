import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps, Node } from '@xyflow/react';

export type SiteNodeData = {
  label: string;
  location: string;
  subnetCount: number;
  containerCount: number;
  onDrillDown: (siteId: string) => void;
};

export type SiteNodeType = Node<SiteNodeData, 'site'>;

const containerStyle: React.CSSProperties = {
  cursor: 'pointer',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  gap: '8px',
  padding: '12px',
  transition: 'all 0.3s ease',
};

const dotStyle: React.CSSProperties = {
  width: '24px',
  height: '24px',
  borderRadius: '50%',
  background: 'radial-gradient(circle at 40% 40%, #00ff9f, #008855)',
  boxShadow: '0 0 15px rgba(0, 255, 159, 0.5), 0 0 30px rgba(0, 255, 159, 0.2)',
  border: '2px solid rgba(0, 255, 159, 0.6)',
  animation: 'pulse-dot 3s ease-in-out infinite',
};

const ringStyle: React.CSSProperties = {
  position: 'absolute',
  width: '40px',
  height: '40px',
  borderRadius: '50%',
  border: '1px solid rgba(0, 255, 159, 0.2)',
  top: '4px',
  left: '50%',
  transform: 'translateX(-50%)',
};

const labelStyle: React.CSSProperties = {
  fontFamily: "'Orbitron', sans-serif",
  fontSize: '16px',
  fontWeight: 700,
  color: '#d0d0d8',
  textAlign: 'center',
  letterSpacing: '1px',
  textShadow: '0 0 8px rgba(0, 255, 159, 0.3)',
  whiteSpace: 'nowrap',
};

const sublabelStyle: React.CSSProperties = {
  fontFamily: "'Share Tech Mono', monospace",
  fontSize: '15px',
  color: '#808090',
  textAlign: 'center',
};

const statsStyle: React.CSSProperties = {
  fontFamily: "'Share Tech Mono', monospace",
  fontSize: '12px',
  color: '#505060',
  display: 'flex',
  gap: '8px',
};

export const SiteNode = memo(function SiteNode({ data, id }: NodeProps<SiteNodeType>) {
  return (
    <div
      style={containerStyle}
      onClick={() => data.onDrillDown(id)}
      title="Click to drill down"
    >
      <Handle type="target" position={Position.Top} style={{ background: '#00ff9f', width: 6, height: 6, border: 'none', opacity: 0.5 }} />
      <div style={{ position: 'relative', display: 'flex', justifyContent: 'center' }}>
        <div style={dotStyle} />
        <div style={ringStyle} />
      </div>
      <div style={labelStyle}>{data.label}</div>
      <div style={sublabelStyle}>{data.location}</div>
      <div style={statsStyle}>
        <span>{data.subnetCount} subnets</span>
        <span>{data.containerCount} nodes</span>
      </div>
      <Handle type="source" position={Position.Bottom} style={{ background: '#00ff9f', width: 6, height: 6, border: 'none', opacity: 0.5 }} />
    </div>
  );
});
