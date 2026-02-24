import { BaseEdge, getSmoothStepPath, type EdgeProps } from '@xyflow/react';

export function NeonEdge(props: EdgeProps) {
  const [edgePath] = getSmoothStepPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    targetX: props.targetX,
    targetY: props.targetY,
    sourcePosition: props.sourcePosition,
    targetPosition: props.targetPosition,
    borderRadius: 12,
  });

  const color = props.data?.color as string || '#00ff9f';

  return (
    <>
      {/* Glow layer */}
      <BaseEdge
        id={props.id + '-glow'}
        path={edgePath}
        style={{
          stroke: color,
          strokeWidth: 6,
          opacity: 0.15,
          filter: 'blur(3px)',
        }}
      />
      {/* Main edge */}
      <BaseEdge
        id={props.id}
        path={edgePath}
        style={{
          stroke: color,
          strokeWidth: 1.5,
          opacity: 0.7,
        }}
      />
      {/* Edge label */}
      {props.label && (
        <text>
          <textPath
            href={`#${props.id}`}
            startOffset="50%"
            textAnchor="middle"
            style={{
              fontSize: '12px',
              fill: '#808090',
              fontFamily: "'Share Tech Mono', monospace",
            }}
          >
            {props.label}
          </textPath>
        </text>
      )}
    </>
  );
}

export function NeonEdgeDirect(props: EdgeProps) {
  const path = `M ${props.sourceX} ${props.sourceY} L ${props.targetX} ${props.targetY}`;
  const color = props.data?.color as string || '#00ff9f';

  return (
    <>
      <BaseEdge
        id={props.id + '-glow'}
        path={path}
        style={{
          stroke: color,
          strokeWidth: 6,
          opacity: 0.15,
          filter: 'blur(3px)',
        }}
      />
      <BaseEdge
        id={props.id}
        path={path}
        style={{
          stroke: color,
          strokeWidth: 1.5,
          opacity: 0.7,
        }}
      />
      {props.label && (
        <text>
          <textPath
            href={`#${props.id}`}
            startOffset="50%"
            textAnchor="middle"
            style={{
              fontSize: '12px',
              fill: '#808090',
              fontFamily: "'Share Tech Mono', monospace",
            }}
          >
            {props.label}
          </textPath>
        </text>
      )}
    </>
  );
}

export function NeonEdgeStraight(props: EdgeProps) {
  const path = `M ${props.sourceX} ${props.sourceY} L ${props.targetX} ${props.targetY}`;
  const color = props.data?.color as string || '#00ff9f';

  return (
    <>
      <BaseEdge
        id={props.id + '-glow'}
        path={path}
        style={{
          stroke: color,
          strokeWidth: 6,
          opacity: 0.12,
          filter: 'blur(4px)',
        }}
      />
      <BaseEdge
        id={props.id}
        path={path}
        style={{
          stroke: color,
          strokeWidth: 1.5,
          opacity: 0.5,
          strokeDasharray: '8 4',
        }}
      />
    </>
  );
}
