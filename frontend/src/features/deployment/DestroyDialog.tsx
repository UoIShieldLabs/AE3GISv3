import type { LucideIcon } from 'lucide-react';
import { Archive, Moon, Trash2 } from 'lucide-react';
import { cn } from '@/lib/cn';
import { useAppStore } from '@/store';
import { useAppShallow } from '@/store/selectors';
import { Dialog } from '@/ui';
import { destroyTopology } from './actions';

type Tone = 'neutral' | 'accent' | 'danger';

const TONES: Record<Tone, { icon: string; card: string }> = {
  neutral: { icon: 'bg-surface-2 text-fg-muted', card: 'hover:border-border-strong' },
  accent: { icon: 'bg-accent-soft text-accent', card: 'hover:border-accent' },
  danger: { icon: 'bg-danger-soft text-danger', card: 'hover:border-danger' },
};

function Option({ icon: Icon, title, hint, tone, onClick, autoFocus }: {
  icon: LucideIcon; title: string; hint: string; tone: Tone; onClick: () => void; autoFocus?: boolean;
}) {
  const t = TONES[tone];
  return (
    <button
      type="button"
      onClick={onClick}
      autoFocus={autoFocus}
      className={cn(
        'flex w-full items-center gap-3 rounded-lg border border-border bg-surface px-3 py-2.5 text-left transition-colors',
        'hover:bg-hover focus-visible:outline-2 focus-visible:outline-ring',
        t.card,
      )}
    >
      <span className={cn('flex size-8 shrink-0 items-center justify-center rounded-md', t.icon)}>
        <Icon className="size-4" />
      </span>
      <span className="min-w-0">
        <span className={cn('block text-sm font-medium', tone === 'danger' ? 'text-danger' : 'text-fg')}>{title}</span>
        <span className="block text-xs text-fg-muted">{hint}</span>
      </span>
    </button>
  );
}

/** How to stop a lab: leave it running, save and stop, or delete it. */
export function DestroyDialog() {
  const { open, hasSave } = useAppShallow((s) => ({ open: s.destroyDialogOpen, hasSave: !!s.savedState }));
  const close = () => useAppStore.getState().setDestroyDialogOpen(false);
  const destroy = (save: boolean) => { close(); void destroyTopology({ save }); };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) close(); }} title="Stop this lab?" size="sm">
      <div className="space-y-2">
        <Option icon={Archive} tone="accent" title="Save & stop" hint={hasSave ? 'Replaces your last save' : 'Resume where you left off'} onClick={() => destroy(true)} autoFocus />
        <Option icon={Moon} tone="neutral" title="Keep running" hint="Leave it up and come back later" onClick={close} />
        <Option icon={Trash2} tone="danger" title="Delete" hint={hasSave ? 'Wipe all changes, including your save' : 'Wipe all changes'} onClick={() => destroy(false)} />
      </div>
      <p className="mt-3 text-[11px] leading-4 text-fg-subtle">Saving keeps files and firewall rules, not running programs.</p>
    </Dialog>
  );
}
