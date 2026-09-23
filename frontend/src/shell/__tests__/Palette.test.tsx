import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { useAppStore } from '@/store';
import { applyCatalog } from '@/catalog/catalog';
import { AddEntityContext, type AddEntityApi } from '@/features/topology/AddEntityContext';
import { TooltipProvider } from '@/ui';
import { CATALOG } from '@/test/catalogFixture';
import { Palette } from '../Palette';

function renderPalette(api: Partial<AddEntityApi> = {}) {
  const value: AddEntityApi = { requestAdd: vi.fn(), requestBulkDevices: vi.fn(), requestBulkConnections: vi.fn(), ...api };
  render(
    <TooltipProvider>
      <AddEntityContext.Provider value={value}>
        <Palette scope={{ level: 'subnet', siteId: 's', subnetId: 'n' }} />
      </AddEntityContext.Provider>
    </TooltipProvider>,
  );
  return value;
}

beforeEach(() => {
  applyCatalog(CATALOG);
  useAppStore.setState({ catalog: CATALOG, catalogStatus: 'ready', collapsedCategories: [], images: null });
});

describe('Palette', () => {
  it('groups types under their categories', () => {
    renderPalette();
    expect(screen.getByText('Network')).toBeInTheDocument();
    expect(screen.getByText('Security')).toBeInTheDocument();
    expect(screen.getByText('Firewall')).toBeInTheDocument();
  });

  it('offers a variant expander only on types with several variants', () => {
    renderPalette();
    expect(screen.getByRole('button', { name: 'Show Firewall variants' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Show Router variants' })).toBeNull();
  });

  it('adds a specific variant with its image, the default without one', () => {
    const api = renderPalette();
    fireEvent.click(screen.getByRole('button', { name: 'Show Firewall variants' }));
    fireEvent.click(screen.getByText('nftables'));
    expect(api.requestAdd).toHaveBeenLastCalledWith({ kind: 'device', type: 'firewall', image: 'ae3gis.local/nftables' }, { subnetId: 'n' });
    fireEvent.click(screen.getByText('FRRouting'));
    expect(api.requestAdd).toHaveBeenLastCalledWith({ kind: 'device', type: 'firewall' }, { subnetId: 'n' });
  });

  it('collapses a category', () => {
    renderPalette();
    fireEvent.click(screen.getByRole('button', { name: /Security/ }));
    expect(screen.queryByText('Firewall')).toBeNull();
    expect(useAppStore.getState().collapsedCategories).toEqual(['security']);
  });

  it('search reaches variants directly', () => {
    renderPalette();
    fireEvent.change(screen.getByPlaceholderText('Search devices and images…'), { target: { value: 'iptables' } });
    expect(screen.getByText('iptables')).toBeInTheDocument();
    expect(screen.queryByText('Router')).toBeNull();
  });
});
