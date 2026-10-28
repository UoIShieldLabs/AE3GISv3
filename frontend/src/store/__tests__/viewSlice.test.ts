import { beforeEach, describe, expect, it } from 'vitest';
import { useAppStore } from '@/store';

const st = () => useAppStore.getState();
const persisted = () => JSON.parse(localStorage.getItem('ae3gis.ui') ?? '{}').state ?? {};

describe('view slice: appearance', () => {
  beforeEach(() => useAppStore.setState({ theme: 'system', iconStyle: 'classic' }));

  it('defaults to the OS theme and Classic icons', () => {
    expect(useAppStore.getInitialState()).toMatchObject({ theme: 'system', iconStyle: 'classic' });
  });

  it('sets the theme and icon style independently, and persists both', () => {
    st().setTheme('neon');
    st().setIconStyle('netmap');
    expect(st()).toMatchObject({ theme: 'neon', iconStyle: 'netmap' });
    expect(persisted()).toMatchObject({ theme: 'neon', iconStyle: 'netmap' });
    st().setTheme('light');
    expect(st().iconStyle).toBe('netmap');
  });
});
