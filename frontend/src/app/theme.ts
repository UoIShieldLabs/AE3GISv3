import { useEffect, useSyncExternalStore } from 'react';
import { useAppStore } from '@/store';

const mql = typeof window !== 'undefined' && window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

function subscribe(cb: () => void) {
  mql?.addEventListener('change', cb);
  return () => mql?.removeEventListener('change', cb);
}

function useSystemDark(): boolean {
  return useSyncExternalStore(subscribe, () => !!mql?.matches, () => false);
}

/** The theme actually in effect ('system' resolved against the OS). */
export function useResolvedTheme(): 'light' | 'dark' {
  const theme = useAppStore((s) => s.theme);
  const systemDark = useSystemDark();
  return theme === 'system' ? (systemDark ? 'dark' : 'light') : theme;
}

/** Keep <html data-theme> in sync with the store (index.html applies it pre-paint). */
export function useApplyTheme() {
  const resolved = useResolvedTheme();
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', resolved);
  }, [resolved]);
  return resolved;
}
