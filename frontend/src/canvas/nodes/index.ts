import type { NodeTypes } from '@xyflow/react';
import { SiteNode } from './SiteNode';
import { SubnetNode } from './SubnetNode';
import { DeviceNode } from './DeviceNode';
import { GroupNode } from './GroupNode';

export const nodeTypes = {
  site: SiteNode,
  subnet: SubnetNode,
  device: DeviceNode,
  group: GroupNode,
} satisfies NodeTypes;
