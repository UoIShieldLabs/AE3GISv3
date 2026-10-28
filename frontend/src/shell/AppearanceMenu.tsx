import { Palette } from 'lucide-react';
import { useAppStore } from '@/store';
import { THEMES, type ThemePref } from '@/app/themes';
import { ICON_STYLES, glyphFor, type IconStyleId } from '@/catalog/icons/registry';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuLabel, DropdownMenuRadioGroup, DropdownMenuRadioItem,
  DropdownMenuSeparator, DropdownMenuTrigger, IconButton,
} from '@/ui';

const PREVIEW_ICONS = ['router', 'switch', 'server', 'workstation'];

/** A chip painted by the theme itself: `data-theme` scopes its tokens. */
export function ThemeSwatch({ id }: { id: string }) {
  return (
    <span data-theme={id} className="flex size-4 shrink-0 items-center justify-center rounded-sm border border-border-strong bg-app">
      <span className="size-1.5 rounded-full bg-accent" />
    </span>
  );
}

function SystemSwatch() {
  return (
    <span className="flex size-4 shrink-0 overflow-hidden rounded-sm border border-border-strong">
      <span data-theme="light" className="w-1/2 bg-app" />
      <span data-theme="dark" className="w-1/2 bg-app" />
    </span>
  );
}

/** Theme and device icon style, picked independently (top bar, library, gallery). */
export function AppearanceMenu() {
  const theme = useAppStore((s) => s.theme);
  const iconStyle = useAppStore((s) => s.iconStyle);
  const { setTheme, setIconStyle } = useAppStore.getState();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <IconButton label="Appearance" size="icon-sm"><Palette /></IconButton>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-56">
        <DropdownMenuLabel>Theme</DropdownMenuLabel>
        <DropdownMenuRadioGroup value={theme} onValueChange={(v) => setTheme(v as ThemePref)}>
          <DropdownMenuRadioItem value="system"><SystemSwatch /> System</DropdownMenuRadioItem>
          {THEMES.map((t) => (
            <DropdownMenuRadioItem key={t.id} value={t.id}>
              <ThemeSwatch id={t.id} /> {t.label}
              {'description' in t ? <span className="ml-auto pl-4 text-2xs text-fg-subtle">{t.description}</span> : null}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
        <DropdownMenuSeparator />
        <DropdownMenuLabel>Icons</DropdownMenuLabel>
        <DropdownMenuRadioGroup value={iconStyle} onValueChange={(v) => setIconStyle(v as IconStyleId)}>
          {ICON_STYLES.map((s) => (
            <DropdownMenuRadioItem key={s.id} value={s.id}>
              {s.label}
              <span className="ml-auto flex gap-1 pl-4" aria-hidden>
                {PREVIEW_ICONS.map((icon) => <span key={icon}>{glyphFor(s.id, icon)({ color: 'currentColor', size: 14 })}</span>)}
              </span>
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
