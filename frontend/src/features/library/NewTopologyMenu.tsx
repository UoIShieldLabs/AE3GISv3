import { useRef } from 'react';
import { ChevronDown, FilePlus2, LayoutTemplate, Plus, Upload } from 'lucide-react';
import type { PresetSummary } from '@/api/client';
import {
  Button, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuSub,
  DropdownMenuSubContent, DropdownMenuSubTrigger, DropdownMenuTrigger,
} from '@/ui';
import { cn } from '@/lib/cn';

/** "New topology" (blank), and ▾: blank, from a preset, import JSON. */
export function NewTopologyMenu({ presets, busy, onBlank, onPreset, onImport, onBrowsePresets, className }: {
  presets: PresetSummary[];
  /** A preset or an import is loading. */
  busy?: boolean;
  onBlank: () => void;
  onPreset: (id: string) => void;
  onImport: (file: File) => void;
  onBrowsePresets: () => void;
  className?: string;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  return (
    <div className={cn('flex min-w-0 shrink-0', className)}>
      <Button variant="primary" size="sm" className="min-w-0 flex-1 rounded-r-none" onClick={onBlank} loading={busy}>
        <Plus /> New topology
      </Button>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="primary" size="sm" className="rounded-l-none border-l border-accent-fg/25 px-1.5" aria-label="More ways to start" disabled={busy}>
            <ChevronDown />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuItem onSelect={onBlank}><FilePlus2 /> Blank topology</DropdownMenuItem>
          <DropdownMenuSub>
            <DropdownMenuSubTrigger disabled={presets.length === 0}><LayoutTemplate /> From preset</DropdownMenuSubTrigger>
            <DropdownMenuSubContent className="max-w-80">
              {presets.map((p) => (
                <DropdownMenuItem key={p.id} onSelect={() => onPreset(p.id)}>
                  <span className="truncate">{p.name}</span>
                </DropdownMenuItem>
              ))}
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={onBrowsePresets}>Browse presets…</DropdownMenuItem>
            </DropdownMenuSubContent>
          </DropdownMenuSub>
          <DropdownMenuItem onSelect={() => fileRef.current?.click()}><Upload /> Import JSON…</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <input
        ref={fileRef}
        type="file"
        accept="application/json,.json"
        className="hidden"
        data-testid="import-json"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onImport(f); e.target.value = ''; }}
      />
    </div>
  );
}
