import { createContext, type Dispatch } from 'react';
import type { TopologyAction } from './topologyReducer';

export const TopologyDispatchContext = createContext<Dispatch<TopologyAction>>(() => {});
