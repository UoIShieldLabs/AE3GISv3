export function deploymentName(topologyId: string, topologyName?: string | null): string {
  const base = (topologyName || 'ae3gis-topology').trim() || 'ae3gis-topology';
  return `${base}-${topologyId.slice(0, 8)}`;
}

