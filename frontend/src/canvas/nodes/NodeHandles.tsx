import { Handle, Position } from '@xyflow/react';
import { HANDLE_IDS } from './nodeStyles';

const POS: Record<(typeof HANDLE_IDS)[number], Position> = {
  top: Position.Top,
  right: Position.Right,
  bottom: Position.Bottom,
  left: Position.Left,
};

/** Connection handles on all four sides. Edges themselves float to the node border. */
export function NodeHandles({ connectable = true }: { connectable?: boolean }) {
  return (
    <>
      {HANDLE_IDS.map((id) => (
        <Handle key={id} id={id} type="source" position={POS[id]} isConnectable={connectable} className="!bg-accent !border-surface" />
      ))}
    </>
  );
}
