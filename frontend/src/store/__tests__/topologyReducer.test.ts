import { describe, it, expect } from 'vitest';
import { produce } from 'immer';
import { topologyReducer, type TopologyState } from '../topologyReducer';
import type { TopologyAction } from '../topologyReducer';
import { generateId } from '../../utils/idGenerator';

function initial(): TopologyState {
  return {
    topology: { sites: [], siteConnections: [] },
    backendId: null,
    backendName: null,
    deployStatus: 'idle',
    dirty: false,
  };
}

function reduce(state: TopologyState, action: TopologyAction): TopologyState {
  return produce(state, (draft) => { topologyReducer(draft, action); });
}

describe('topologyReducer', () => {
  it('ADD_SITE adds a site and marks dirty', () => {
    const site = { id: 's1', name: 'S1', location: '', position: { x: 0, y: 0 }, subnets: [], subnetConnections: [] };
    const next = reduce(initial(), { type: 'ADD_SITE', payload: site });
    expect(next.topology.sites).toHaveLength(1);
    expect(next.dirty).toBe(true);
  });

  it('ADD_SUBNET auto-creates a router + switch wired together', () => {
    let st = reduce(initial(), { type: 'ADD_SITE', payload: { id: 's1', name: 'S1', location: '', position: { x: 0, y: 0 }, subnets: [], subnetConnections: [] } });
    st = reduce(st, { type: 'ADD_SUBNET', payload: { siteId: 's1', subnet: { id: 'sub1', name: 'Net', cidr: '10.0.1.0/24', containers: [], connections: [] } } });
    const subnet = st.topology.sites[0].subnets[0];
    const types = subnet.containers.map((c) => c.type).sort();
    expect(types).toEqual(['router', 'switch']);
    expect(subnet.gateway).toBe('10.0.1.1'); // first available IP -> router
    expect(subnet.connections).toHaveLength(1);
  });

  it('ADD_INTER_SUBNET_CONNECTION links two subnets via their routers', () => {
    let st = reduce(initial(), { type: 'ADD_SITE', payload: { id: 's1', name: 'S1', location: '', position: { x: 0, y: 0 }, subnets: [], subnetConnections: [] } });
    st = reduce(st, { type: 'ADD_SUBNET', payload: { siteId: 's1', subnet: { id: 'a', name: 'A', cidr: '10.0.1.0/24', containers: [], connections: [] } } });
    st = reduce(st, { type: 'ADD_SUBNET', payload: { siteId: 's1', subnet: { id: 'b', name: 'B', cidr: '10.0.2.0/24', containers: [], connections: [] } } });
    st = reduce(st, { type: 'ADD_INTER_SUBNET_CONNECTION', payload: { siteId: 's1', connection: { from: 'a', to: 'b' } } });
    const conns = st.topology.sites[0].subnetConnections;
    expect(conns).toHaveLength(1);
    expect(conns[0].fromContainer).toBeTruthy();
    expect(conns[0].toContainer).toBeTruthy();
  });

  it('UPDATE_CONTAINER_STATUSES does NOT set dirty', () => {
    const site = { id: 's1', name: 'S1', location: '', position: { x: 0, y: 0 },
      subnets: [{ id: 'x', name: 'X', cidr: '10.0.1.0/24', containers: [{ id: 'c1', name: 'c', type: 'workstation', ip: '10.0.1.5' }], connections: [] }],
      subnetConnections: [] };
    let st = reduce(initial(), { type: 'ADD_SITE', payload: site });
    st = { ...st, dirty: false };
    st = reduce(st, { type: 'UPDATE_CONTAINER_STATUSES', payload: { statuses: { c1: 'running' } } });
    expect(st.topology.sites[0].subnets[0].containers[0].status).toBe('running');
    expect(st.dirty).toBe(false);
  });

  it('generateId produces unique ids', () => {
    expect(generateId()).not.toBe(generateId());
  });
});
