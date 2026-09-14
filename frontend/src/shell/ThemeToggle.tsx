import { Monitor, Moon, Sun } from 'lucide-react';
import { useAppStore, type Theme } from '@/store';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuTrigger, IconButton,
} from '@/ui';
import { useResolvedTheme } from '@/app/theme';

export function ThemeToggle() {
  const theme = useAppStore((s) => s.theme);
  const setTheme = useAppStore((s) => s.setTheme);
  const resolved = useResolvedTheme();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <IconButton label="Theme" size="icon-sm">{resolved === 'dark' ? <Moon /> : <Sun />}</IconButton>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuRadioGroup value={theme} onValueChange={(v) => setTheme(v as Theme)}>
          <DropdownMenuRadioItem value="light"><Sun /> Light</DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="dark"><Moon /> Dark</DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="system"><Monitor /> System</DropdownMenuRadioItem>
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
