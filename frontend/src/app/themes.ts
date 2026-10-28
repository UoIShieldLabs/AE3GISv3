// The themes the app offers. Looks live in CSS (src/styles/themes/<id>.css,
// one block of tokens under [data-theme='<id>']); this registry only names
// them, so adding a theme is that file plus one entry here.

export interface ThemeDef {
  id: string;
  label: string;
  /** Light or dark family: drives `color-scheme`, React Flow and toasts. */
  scheme: 'light' | 'dark';
  description?: string;
}

export const THEMES = [
  { id: 'light', label: 'Light', scheme: 'light' },
  { id: 'dark', label: 'Dark', scheme: 'dark' },
] as const satisfies readonly ThemeDef[];

export type ThemeId = (typeof THEMES)[number]['id'];
/** What the user picked: a theme, or follow the OS (light/dark). */
export type ThemePref = 'system' | ThemeId;

export const DEFAULT_THEME_PREF: ThemePref = 'system';

const BY_ID: Record<string, ThemeDef> = Object.fromEntries(THEMES.map((t) => [t.id, t]));

/** The theme in effect for a preference; an id no longer offered (a stale
 *  saved preference) follows the OS like 'system'. */
export function resolveTheme(pref: string, systemDark: boolean): ThemeDef {
  return BY_ID[pref] ?? BY_ID[systemDark ? 'dark' : 'light'];
}
