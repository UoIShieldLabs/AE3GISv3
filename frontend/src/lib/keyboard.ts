/** True when a key event originates from a text-editing element or an open overlay. */
export function isEditableTarget(e: KeyboardEvent): boolean {
  const el = e.target as HTMLElement | null;
  if (!el) return false;
  const tag = el.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
  if (el.isContentEditable) return true;
  if (el.closest('[role="dialog"], [role="menu"], [cmdk-root]')) return true;
  return false;
}

export const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform);

/** Platform-aware modifier label for tooltips. */
export const MOD = isMac ? '⌘' : 'Ctrl';

export function hasMod(e: KeyboardEvent | React.KeyboardEvent): boolean {
  return isMac ? e.metaKey : e.ctrlKey;
}
