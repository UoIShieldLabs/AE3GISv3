import { describe, expect, it } from 'vitest';
import type { ImageStatus } from '@/api/client';
import type { TopologyData } from '@/types/topology';
import { classifyRequired, nameList, requiredImageRefs } from '../required';

const img = (ref: string, status: ImageStatus['status'], kind: ImageStatus['kind'] = 'build'): ImageStatus => ({
  ref, display_name: ref.split('/').pop()!, description: '', stability: 'stable', kind, status, reason: '',
});

const topology = {
  name: 't',
  sites: [{
    id: 's', name: 'S', location: '', subnets: [{
      id: 'n', name: 'N', cidr: '10.0.0.0/24', gateway: '10.0.0.1', connections: [],
      containers: [
        { id: 'a', name: 'fw', type: 'firewall', ip: '10.0.0.1', image: 'ae3gis.local/nftables' },
        { id: 'b', name: 'web', type: 'web-server', ip: '10.0.0.2', image: 'ae3gis.local/nginx' },
        { id: 'c', name: 'web2', type: 'web-server', ip: '10.0.0.3', image: 'ae3gis.local/nginx' },
        { id: 'd', name: 'r', type: 'router', ip: '10.0.0.4' },
      ],
    }],
    subnetConnections: [],
  }],
  siteConnections: [],
} as unknown as TopologyData;

describe('required images', () => {
  it('maps each image to the devices that use it (defaults resolved)', () => {
    const users = requiredImageRefs(topology, (c) => c.image ?? 'kathara/frr');
    expect([...users.entries()]).toEqual([
      ['ae3gis.local/nftables', ['fw']],
      ['ae3gis.local/nginx', ['web', 'web2']],
      ['kathara/frr', ['r']],
    ]);
  });

  it('classifies only build images this topology uses', () => {
    const users = requiredImageRefs(topology, (c) => c.image ?? 'kathara/frr');
    const req = classifyRequired(users, [
      img('ae3gis.local/nftables', 'missing'),
      img('ae3gis.local/nginx', 'stale'),
      img('kathara/frr', 'missing', 'registry'),
      img('ae3gis.local/zeek', 'failed'), // not used here
    ]);
    expect(req.toBuild.map((i) => i.ref)).toEqual(['ae3gis.local/nftables']);
    expect(req.stale.map((i) => i.ref)).toEqual(['ae3gis.local/nginx']);
    expect(req.failed).toEqual([]);
  });

  it('abbreviates long name lists', () => {
    expect(nameList(['a/1', 'a/2', 'a/3', 'a/4'].map((r) => img(r, 'missing')))).toBe('1, 2, 3 +1');
  });
});
