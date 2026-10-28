import { beforeEach, describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { useAppStore } from '@/store';
import { applyCatalog } from '@/catalog/catalog';
import { CATALOG } from '@/test/catalogFixture';
import { NodeGlyph } from '../icons';
import { CLASSIC_GLYPHS } from '../icons/classic';
import { ICON_STYLES, glyphFor, iconStyleFor } from '../icons/registry';

const ICON_NAMES = Object.keys(CLASSIC_GLYPHS);

beforeEach(() => {
  applyCatalog(CATALOG);
  useAppStore.setState({ iconStyle: 'classic' });
});

describe('icon styles', () => {
  it('has unique ids', () => {
    expect(new Set(ICON_STYLES.map((s) => s.id)).size).toBe(ICON_STYLES.length);
  });

  it.each(ICON_STYLES.map((s) => s.id))('%s draws an svg for every icon name', (id) => {
    for (const icon of ICON_NAMES) {
      const { container, unmount } = render(glyphFor(id, icon)({ color: '#f00', size: 20 }));
      const svg = container.querySelector('svg');
      expect(svg, `${id}/${icon}`).not.toBeNull();
      expect(svg).toHaveAttribute('width', '20');
      unmount();
    }
  });

  it('falls back to Classic for an unknown style or icon', () => {
    expect(iconStyleFor('retired-style').id).toBe('classic');
    expect(glyphFor('netmap', 'no-such-icon')).toBe(CLASSIC_GLYPHS.default);
    expect(glyphFor('retired-style', 'router')).toBe(CLASSIC_GLYPHS.router);
  });
});

describe('NodeGlyph', () => {
  const routerSvg = (ui: React.ReactElement) => render(ui).container.querySelector('svg')!;

  it('draws in the store icon style', () => {
    expect(routerSvg(<NodeGlyph type="router" />).querySelector('circle[r="12"]')).not.toBeNull();
    useAppStore.setState({ iconStyle: 'line' });
    expect(routerSvg(<NodeGlyph type="router" />)).toHaveClass('lucide-router');
    useAppStore.setState({ iconStyle: 'netmap' });
    expect(routerSvg(<NodeGlyph type="router" />).querySelector('path[d="M16 4l12 12-12 12L4 16z"]')).not.toBeNull();
  });

  it('falls back to Classic for a stale stored style', () => {
    useAppStore.setState({ iconStyle: 'retired-style' as never });
    expect(routerSvg(<NodeGlyph type="router" />).querySelector('circle[r="12"]')).not.toBeNull();
  });

  it('wraps the glyph in the theme hook, colored by the catalog', () => {
    const { container } = render(<NodeGlyph type="firewall" size={14} />);
    const hook = container.firstElementChild as HTMLElement;
    expect(hook).toHaveClass('ae-glyph');
    expect(hook.style.color).toBe('rgb(255, 0, 0)');
  });
});
