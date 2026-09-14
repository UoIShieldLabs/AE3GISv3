import { useState } from 'react';
import { ChevronDown, Download, Layers3, Library, PanelLeft, PanelRight, Play, Redo2, Save, Search, Square, Undo2 } from 'lucide-react';
import { cn } from '@/lib/cn';
import { MOD } from '@/lib/keyboard';
import { useAppStore, undo, redo, type DeployStatus } from '@/store';
import { useAppShallow, useUndoState } from '@/store/selectors';
import {
  Badge, Button, IconButton, Separator, Tooltip,
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/ui';
import { ThemeToggle } from './ThemeToggle';

export interface TopBarProps {
  onSave: () => void;
  onExport: () => void;
  onDeploy: () => void;
  onDestroy: () => void;
  onLibrary: () => void;
  readOnly?: boolean;
}

const STATUS: Record<DeployStatus, { label: string; tone: 'neutral' | 'success' | 'warning' | 'danger'; dot: boolean | 'pulse' }> = {
  idle: { label: 'Not deployed', tone: 'neutral', dot: true },
  deploying: { label: 'Deploying…', tone: 'warning', dot: 'pulse' },
  deployed: { label: 'Deployed', tone: 'success', dot: 'pulse' },
  destroying: { label: 'Destroying…', tone: 'warning', dot: 'pulse' },
  error: { label: 'Error', tone: 'danger', dot: true },
};

export function TopBar({ onSave, onExport, onDeploy, onDestroy, onLibrary, readOnly }: TopBarProps) {
  const { name, dirty, backendId, deployStatus, busy, lastError, sidebarOpen, inspectorOpen } = useAppShallow((s) => ({
    name: s.topology.name ?? '', dirty: s.dirty, backendId: s.backendId, deployStatus: s.deployStatus, busy: s.busy, lastError: s.lastError,
    sidebarOpen: s.sidebarOpen, inspectorOpen: s.inspectorOpen,
  }));
  const { setSidebarOpen, setInspectorOpen, setPurdueOpen, setCommandPaletteOpen } = useAppStore.getState();
  const setMeta = useAppStore((s) => s.setTopologyMeta);
  const { canUndo, canRedo } = useUndoState();
  const status = STATUS[deployStatus];
  const transitioning = deployStatus === 'deploying' || deployStatus === 'destroying';

  return (
    <div className="flex w-full items-center gap-2">
      <div className="flex items-center gap-1">
        <IconButton label="Topology library" onClick={onLibrary}><Library /></IconButton>
        <span className="hidden select-none text-sm font-semibold tracking-tight sm:inline">AE3GIS</span>
      </div>
      <Separator orientation="vertical" className="mx-1 h-5" />
      <IconButton label={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'} shortcut={`${MOD}B`} size="icon-sm" variant={sidebarOpen ? 'secondary' : 'ghost'} onClick={() => setSidebarOpen(!sidebarOpen)}><PanelLeft /></IconButton>
      <IconButton label={inspectorOpen ? 'Hide inspector' : 'Show inspector'} shortcut={`${MOD}I`} size="icon-sm" variant={inspectorOpen ? 'secondary' : 'ghost'} onClick={() => setInspectorOpen(!inspectorOpen)}><PanelRight /></IconButton>
      <Separator orientation="vertical" className="mx-1 h-5" />

      <div className="flex min-w-0 items-center gap-2">
        <NameEditor value={name} onCommit={(v) => setMeta({ name: v })} readOnly={readOnly} />
        {dirty ? (
          <Tooltip content="Unsaved changes"><span className="size-1.5 shrink-0 rounded-full bg-warning" /></Tooltip>
        ) : null}
      </div>

      <div className="ml-auto flex items-center gap-1">
        <Tooltip content="Search & commands" shortcut={`${MOD}K`}>
          <Button size="sm" variant="outline" className="hidden w-44 justify-start gap-2 text-fg-subtle md:inline-flex" onClick={() => setCommandPaletteOpen(true)}>
            <Search /> Search… <span className="ml-auto font-mono text-2xs">{MOD}K</span>
          </Button>
        </Tooltip>
        <Tooltip content="Purdue model view">
          <Button size="sm" variant="ghost" onClick={() => setPurdueOpen(true)}><Layers3 /> Purdue</Button>
        </Tooltip>
        {!readOnly ? (
          <>
            <IconButton label="Undo" shortcut={`${MOD}Z`} size="icon-sm" disabled={!canUndo} onClick={() => undo()}><Undo2 /></IconButton>
            <IconButton label="Redo" shortcut={`⇧${MOD}Z`} size="icon-sm" disabled={!canRedo} onClick={() => redo()}><Redo2 /></IconButton>
            <Separator orientation="vertical" className="mx-1 h-5" />
            <Tooltip content="Save" shortcut={`${MOD}S`}>
              <Button size="sm" variant={dirty ? 'primary' : 'secondary'} onClick={onSave} disabled={busy || transitioning} loading={busy && !transitioning}>
                <Save /> Save
              </Button>
            </Tooltip>
          </>
        ) : null}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button size="sm" variant="ghost">More <ChevronDown className="-mr-1 opacity-70" /></Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onSelect={onExport}><Download /> Export JSON</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={onLibrary}><Library /> Topology library</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <Separator orientation="vertical" className="mx-1 h-5" />

        <Tooltip content={lastError ?? status.label}>
          <Badge tone={status.tone} dot={status.dot} className="h-6 px-2">{status.label}</Badge>
        </Tooltip>
        {deployStatus === 'deployed' || deployStatus === 'destroying' ? (
          <Button size="sm" variant="danger-soft" onClick={onDestroy} disabled={busy || transitioning} loading={deployStatus === 'destroying'}>
            <Square /> Destroy
          </Button>
        ) : (
          <Tooltip content={!backendId ? 'Save the topology before deploying' : deployStatus === 'error' ? 'Retry deployment' : 'Deploy with Kathara'}>
            <Button size="sm" variant="primary" onClick={onDeploy} disabled={busy || transitioning || !backendId || readOnly} loading={deployStatus === 'deploying'} className={cn(deployStatus !== 'deploying' && 'bg-success hover:bg-success/90')}>
              <Play /> Deploy
            </Button>
          </Tooltip>
        )}
        <Separator orientation="vertical" className="mx-1 h-5" />
        <ThemeToggle />
      </div>
    </div>
  );
}

function NameEditor({ value, onCommit, readOnly }: { value: string; onCommit: (v: string) => void; readOnly?: boolean }) {
  const [draft, setDraft] = useState(value);
  const [prev, setPrev] = useState(value);
  if (prev !== value) {
    setPrev(value);
    setDraft(value);
  }
  const commit = () => {
    const v = draft.trim();
    if (v && v !== value) onCommit(v);
    else setDraft(value);
  };
  return (
    <input
      value={draft}
      readOnly={readOnly}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
        if (e.key === 'Escape') { setDraft(value); (e.target as HTMLInputElement).blur(); }
      }}
      placeholder="Untitled topology"
      aria-label="Topology name"
      className={cn(
        'h-7 min-w-24 max-w-72 truncate rounded-md border border-transparent bg-transparent px-1.5 text-[13px] font-medium text-fg outline-none',
        'hover:border-border focus:border-accent focus:bg-surface focus:ring-2 focus:ring-accent/25',
        'placeholder:font-normal placeholder:text-fg-subtle',
      )}
      style={{ width: `${Math.max(10, Math.min(40, draft.length + 2))}ch` }}
    />
  );
}
