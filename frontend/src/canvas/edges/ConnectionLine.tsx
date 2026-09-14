import { getStraightPath, type ConnectionLineComponentProps } from '@xyflow/react';

/** The line drawn while dragging a new connection. */
export function ConnectionLine({ fromX, fromY, toX, toY }: ConnectionLineComponentProps) {
  const [path] = getStraightPath({ sourceX: fromX, sourceY: fromY, targetX: toX, targetY: toY });
  return (
    <g>
      <path d={path} fill="none" className="stroke-accent" strokeWidth={1.75} strokeDasharray="6 4" />
      <circle cx={toX} cy={toY} r={4} className="fill-surface stroke-accent" strokeWidth={1.5} />
    </g>
  );
}
