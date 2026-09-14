import type { EdgeTypes } from '@xyflow/react';
import { TopologyEdge } from './TopologyEdge';

export const edgeTypes = { topology: TopologyEdge } satisfies EdgeTypes;
export { ConnectionLine } from './ConnectionLine';
