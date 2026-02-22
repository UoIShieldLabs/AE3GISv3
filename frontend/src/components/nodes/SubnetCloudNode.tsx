import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps, Node } from '@xyflow/react';

export type SubnetCloudNodeData = {
  label: string;
  cidr: string;
  containerCount: number;
  onDrillDown: (subnetId: string) => void;
};

export type SubnetCloudNodeType = Node<SubnetCloudNodeData, 'subnetCloud'>;

const containerStyle: React.CSSProperties = {
  cursor: 'pointer',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  gap: '6px',
  padding: '20px 30px',
  background: 'rgba(0, 212, 255, 0.04)',
  border: '1px solid rgba(0, 212, 255, 0.25)',
  borderRadius: '60px',
  transition: 'all 0.3s ease',
  position: 'relative',
  minWidth: '160px',
};

const cloudIconStyle: React.CSSProperties = {
  marginBottom: '4px',
};

const labelStyle: React.CSSProperties = {
  fontFamily: "'Orbitron', sans-serif",
  fontSize: '12px',
  fontWeight: 700,
  color: '#00d4ff',
  textAlign: 'center',
  letterSpacing: '1px',
  textShadow: '0 0 10px rgba(0, 212, 255, 0.4)',
};

const cidrStyle: React.CSSProperties = {
  fontFamily: "'Share Tech Mono', monospace",
  fontSize: '11px',
  color: '#808090',
};

const countStyle: React.CSSProperties = {
  fontFamily: "'Share Tech Mono', monospace",
  fontSize: '10px',
  color: '#505060',
};

function CloudIcon() {
  return (
    <svg width="36" height="24" viewBox="0 0 36 24" fill="none" style={cloudIconStyle}>
      <path
        d="M28 12a6 6 0 0 0-5.6-4A8 8 0 0 0 7 12a5 5 0 0 0 0 10h21a4 4 0 0 0 0-8z"
        stroke="#00d4ff"
        strokeWidth="1.5"
        fill="rgba(0, 212, 255, 0.05)"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export const SubnetCloudNode = memo(function SubnetCloudNode({ data, id }: NodeProps<SubnetCloudNodeType>) {
  return (
    <div
      style={containerStyle}
      onClick={() => data.onDrillDown(id)}
      title="Click to drill down"
      onMouseEnter={(e) => {
        const el = e.currentTarget;
        el.style.background = 'rgba(0, 212, 255, 0.08)';
        el.style.borderColor = 'rgba(0, 212, 255, 0.5)';
        el.style.boxShadow = '0 0 20px rgba(0, 212, 255, 0.15)';
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget;
        el.style.background = 'rgba(0, 212, 255, 0.04)';
        el.style.borderColor = 'rgba(0, 212, 255, 0.25)';
        el.style.boxShadow = 'none';
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#00d4ff', width: 6, height: 6, border: 'none', opacity: 0.5 }} />
      <CloudIcon />
      <div style={labelStyle}>{data.label}</div>
      <div style={cidrStyle}>{data.cidr}</div>
      <div style={countStyle}>{data.containerCount} containers</div>
      <Handle type="source" position={Position.Bottom} style={{ background: '#00d4ff', width: 6, height: 6, border: 'none', opacity: 0.5 }} />
    </div>
  );
});
