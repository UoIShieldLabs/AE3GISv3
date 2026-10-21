import { describe, expect, it } from 'vitest';
import type { TopologyData } from '@/types/topology';
import { dockerHubNamespace, requiredRegistries } from '../requiredRegistries';

describe('dockerHubNamespace', () => {
  it('takes the namespace of a Docker Hub ref', () => {
    expect(dockerHubNamespace('tollan/c104-server:latest')).toBe('tollan');
  });
  it('ignores official, built-here and custom-host refs', () => {
    expect(dockerHubNamespace('httpd:alpine')).toBeNull();
    expect(dockerHubNamespace('ae3gis.local/nettools')).toBeNull();
    expect(dockerHubNamespace('ghcr.io/org/img:1')).toBeNull();
    expect(dockerHubNamespace('registry:5000/org/img')).toBeNull();
  });
});

function topo(images: (string | undefined)[]): TopologyData {
  return {
    sites: [{
      id: 's', name: 'S', location: '', position: { x: 0, y: 0 }, subnetConnections: [],
      subnets: [{
        id: 'n', name: 'N', cidr: '10.0.1.0/24', connections: [],
        containers: images.map((image, i) => ({ id: `c${i}`, name: `c${i}`, type: 'workstation', ip: `10.0.1.${i + 5}`, ...(image ? { image } : {}) })),
      }],
    }],
    siteConnections: [],
  } as TopologyData;
}

describe('requiredRegistries', () => {
  it('lists Docker Hub namespaces not yet installed, deduped', () => {
    const t = topo(['tollan/c104-server:latest', 'tollan/zeek:latest', 'ae3gis.local/nettools', 'httpd:alpine', undefined]);
    expect(requiredRegistries(t, [])).toEqual([{ namespace: 'tollan', url: 'https://hub.docker.com/u/tollan' }]);
  });
  it('drops namespaces already added', () => {
    expect(requiredRegistries(topo(['tollan/c104-server:latest']), ['tollan'])).toEqual([]);
  });
});
