import { describe, expect, it } from 'vitest';
import { THEMES, resolveTheme } from '../themes';

const sheets = import.meta.glob('../../styles/themes/*.css', { query: '?raw', import: 'default', eager: true }) as Record<string, string>;

/** Custom properties declared by the rules whose selector list contains `selector` itself. */
function tokensOf(selector: string): Set<string> {
  const tokens = new Set<string>();
  for (const css of Object.values(sheets)) {
    const plain = css.replace(/\/\*[\s\S]*?\*\//g, '');
    for (const [, selectors, body] of plain.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
      if (!selectors.split(',').some((s) => s.trim() === selector)) continue;
      for (const [, name] of body.matchAll(/(--[\w-]+)\s*:/g)) tokens.add(name);
    }
  }
  return tokens;
}

describe('themes', () => {
  const required = tokensOf("[data-theme='light']");

  it('reads the light theme as the reference token set', () => {
    expect(required.size).toBeGreaterThan(30);
    expect(required).toContain('--bg-app');
    expect(required).toContain('--terminal-bg');
  });

  it.each(THEMES.map((t) => t.id))('%s defines every color token', (id) => {
    const defined = tokensOf(`[data-theme='${id}']`);
    expect([...required].filter((t) => !defined.has(t))).toEqual([]);
  });

  it('has unique ids', () => {
    expect(new Set(THEMES.map((t) => t.id)).size).toBe(THEMES.length);
  });

  it('resolves a preference', () => {
    expect(resolveTheme('system', false).id).toBe('light');
    expect(resolveTheme('system', true).id).toBe('dark');
    expect(resolveTheme('light', true).id).toBe('light');
    expect(resolveTheme('dark', false)).toMatchObject({ id: 'dark', scheme: 'dark' });
  });

  it('follows the OS for an id no longer offered', () => {
    expect(resolveTheme('retired-theme', true).id).toBe('dark');
    expect(resolveTheme('retired-theme', false).id).toBe('light');
  });
});
