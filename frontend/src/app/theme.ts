import { useLayoutEffect, useSyncExternalStore } from 'react';
import { useAppStore } from '@/store';
import { resolveTheme, type ThemeDef } from './themes';

const mql = typeof window !== 'undefined' && window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

function subscribe(cb: () => void) {
  mql?.addEventListener('change', cb);
  return () => mql?.removeEventListener('change', cb);
}

function useSystemDark(): boolean {
  return useSyncExternalStore(subscribe, () => !!mql?.matches, () => false);
}

/** The theme actually in effect ('system' resolved against the OS). */
export function useResolvedTheme(): ThemeDef {
  const theme = useAppStore((s) => s.theme);
  const systemDark = useSystemDark();
  return resolveTheme(theme, systemDark);
}

/** Keep <html data-theme data-scheme> in sync with the store (index.html sets
 *  data-theme pre-paint). */
export function useApplyTheme() {
  const resolved = useResolvedTheme();
  useLayoutEffect(() => {
    const root = document.documentElement;
    root.setAttribute('data-theme', resolved.id);
    root.setAttribute('data-scheme', resolved.scheme);
  }, [resolved]);
  return resolved;
}
