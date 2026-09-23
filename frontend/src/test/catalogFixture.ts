import type { Catalog } from '@/catalog/catalog';

/** A small catalog in the backend's v2 shape, for tests. */
export const CATALOG: Catalog = {
  version: 2,
  description: '',
  defaults: { host_image: 'kathara/base' },
  categories: [
    { id: 'network', label: 'Network' },
    { id: 'security', label: 'Security' },
  ],
  sources: { repo: { kind: 'git', url: 'https://example.com/r.git', ref: 'main' } },
  images: {
    'kathara/frr': { displayName: 'FRRouting', description: '', stability: 'stable' },
    'ae3gis.local/nftables': {
      displayName: 'nftables', description: 'default-drop ruleset', stability: 'experimental',
      source: { kind: 'build', repo: 'repo', context: 'nftables', dockerfile: 'dockerfile', args: {} },
    },
    'ae3gis.local/iptables': {
      displayName: 'iptables', description: '', stability: 'stable',
      source: { kind: 'build', repo: 'repo', context: 'iptables', dockerfile: 'dockerfile', args: {} },
    },
    'ae3gis.local/secret': {
      displayName: 'Secret', description: '', stability: 'hidden',
      source: { kind: 'build', repo: 'repo', context: 'secret', dockerfile: 'dockerfile', args: {} },
    },
  },
  types: {
    // Declared before its category's first type on purpose: order follows `categories`.
    firewall: {
      displayName: 'Firewall', role: 'router', category: 'security', defaultImage: 'kathara/frr',
      images: ['ae3gis.local/nftables', 'kathara/frr', 'ae3gis.local/iptables', 'ae3gis.local/secret'],
      color: '#f00', label: 'FW', icon: 'firewall', description: '',
    },
    router: {
      displayName: 'Router', role: 'router', category: 'network', defaultImage: 'kathara/frr',
      images: ['kathara/frr'], color: '#f0f', label: 'RTR', icon: 'router', description: '',
    },
    gizmo: {
      displayName: 'Gizmo', role: 'host', category: 'misc', defaultImage: 'kathara/base',
      color: '#999', label: 'GZ', icon: 'default', description: '',
    },
  },
};
