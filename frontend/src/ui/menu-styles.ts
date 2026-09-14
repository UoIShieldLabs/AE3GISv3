// Shared class lists for dropdown / context menus so both feel identical.
export const menuContentClass =
  'z-[60] min-w-[176px] overflow-hidden rounded-lg border border-border bg-elevated p-1 text-fg shadow-lg animate-pop';

export const menuItemClass =
  'relative flex cursor-default select-none items-center gap-2 rounded-md px-2 py-1.5 text-[13px] outline-none ' +
  'data-[highlighted]:bg-hover data-[disabled]:pointer-events-none data-[disabled]:opacity-50 ' +
  'data-[variant=danger]:text-danger data-[variant=danger]:data-[highlighted]:bg-danger-soft ' +
  '[&_svg]:size-3.5 [&_svg]:shrink-0 [&_svg]:text-fg-muted data-[variant=danger]:[&_svg]:text-danger';

export const menuLabelClass = 'px-2 py-1 text-2xs font-medium uppercase tracking-wide text-fg-subtle';
export const menuSeparatorClass = '-mx-1 my-1 h-px bg-border';
export const menuShortcutClass = 'ml-auto pl-4 font-mono text-2xs text-fg-subtle';
export const menuIndentClass = 'pl-7';
