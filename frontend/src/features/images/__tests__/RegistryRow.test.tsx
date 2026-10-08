import { beforeEach, describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import type { Registry } from '@/api/client';
import { applyCatalog } from '@/catalog/catalog';
import { CATALOG } from '@/test/catalogFixture';
import { TooltipProvider } from '@/ui';
import { RegistryRow } from '../RegistriesPanel';
import { registrySummary } from '../imagePolling';

const REG: Registry = {
  id: 'r1',
  namespace: 'lab',
  url: 'https://hub.docker.com/u/lab',
  hub_url: 'https://hub.docker.com/u/lab',
  created_at: '2026-10-07T10:00:00Z',
  synced_at: '2026-10-07T10:01:00Z',
  repositories: 6,
  skipped: 2,
  pending: ['later'],
  pulls_remaining: 10,
  loaded: [
    { ref: 'lab/edge-fw:latest', repo: 'edge-fw', tag: 'latest', type: 'firewall', name: 'Edge FW', platforms: ['linux/amd64'], new_type: false },
  ],
  rejected: [{ repo: 'broken', tag: 'latest', reasons: ['io.ae3gis.type is required: the node type this image is a variant of'] }],
  warnings: ['edge-fw: unknown label io.ae3gis.type.colour (ignored)'],
  active_job: null,
  last_job: null,
};

function renderRow(reg: Registry = REG) {
  render(<TooltipProvider><RegistryRow registry={reg} /></TooltipProvider>);
}

describe('RegistryRow', () => {
  beforeEach(() => applyCatalog(CATALOG));

  it('summarises a sync', () => {
    expect(registrySummary(REG)).toBe('1 image loaded · 1 rejected · 1 pending');
    renderRow();
    expect(screen.getByText('lab')).toBeInTheDocument();
    expect(screen.getByText(/2 of 6 repos not marked/)).toBeInTheDocument();
    expect(screen.getByText(/1 rejected · 1 waiting for Docker Hub's pull limit/)).toBeInTheDocument();
  });

  it('expands to loaded images, rejection reasons, pending repos and warnings', () => {
    renderRow();
    expect(screen.queryByText('Edge FW')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Show details' }));
    expect(screen.getByText('Edge FW')).toBeInTheDocument();
    expect(screen.getByText('variant of Firewall')).toBeInTheDocument();
    expect(screen.getByText('broken:latest')).toBeInTheDocument();
    expect(screen.getByText(/io.ae3gis.type is required/)).toBeInTheDocument();
    expect(screen.getByText(/10 Docker Hub pulls left/)).toBeInTheDocument();
    expect(screen.getByText(/unknown label io.ae3gis.type.colour/)).toBeInTheDocument();
  });

  it('shows the running step while syncing', () => {
    const job = {
      id: 'j', kind: 'sync_registry', status: 'running', created_at: '2026-10-07T10:02:00Z',
      steps: [{ name: 'inspect', status: 'running', message: 'Reading edge-fw (1/2)', jobs: [] }],
    };
    renderRow({ ...REG, active_job: job });
    expect(screen.getByText('Reading edge-fw (1/2)')).toBeInTheDocument();
  });
});
