import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { Combobox } from '../Combobox';
import { Dialog } from '../Dialog';
import { LAYER } from '../layers';

const value = (layer: string) => Number(layer.replace(/\D/g, ''));

describe('layering', () => {
  it('puts anything openable from inside a modal above it', () => {
    expect(value(LAYER.overlay)).toBeLessThan(value(LAYER.modal));
    expect(value(LAYER.modal)).toBeLessThan(value(LAYER.palette));
    expect(value(LAYER.palette)).toBeLessThan(value(LAYER.floating));
    expect(value(LAYER.floating)).toBeLessThan(value(LAYER.tooltip));
  });

  it('leaves no hardcoded z-index in the primitives', () => {
    const sources = import.meta.glob('../*.{ts,tsx}', { query: '?raw', import: 'default', eager: true }) as Record<string, string>;
    const offenders = Object.entries(sources)
      .filter(([path]) => !path.endsWith('/layers.ts'))
      .filter(([, source]) => /\bz-\[/.test(source))
      .map(([path]) => path);
    expect(offenders).toEqual([]);
  });

  // The bug this guards: a Combobox list inside a Dialog rendered at z-60 while
  // the dialog sat at z-81, so its options were invisible and unclickable.
  it('renders a combobox list above the dialog it opens in', () => {
    render(
      <Dialog open onOpenChange={() => {}} title="Add device">
        <Combobox
          value="a"
          onValueChange={() => {}}
          options={[{ value: 'a', label: 'FRRouting' }, { value: 'b', label: 'FireHOL' }]}
        />
      </Dialog>,
    );
    fireEvent.click(screen.getByRole('combobox'));
    const option = screen.getByText('FireHOL');
    const list = option.closest(`.${CSS.escape(LAYER.floating)}`);
    const dialog = screen.getByRole('dialog', { name: 'Add device' });
    expect(list).not.toBeNull();
    expect(dialog.className).toContain(LAYER.modal);
    expect(value(LAYER.floating)).toBeGreaterThan(value(LAYER.modal));
  });
});
