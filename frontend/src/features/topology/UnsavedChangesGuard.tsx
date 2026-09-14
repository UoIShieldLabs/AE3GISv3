import { useEffect } from 'react';
import { useBlocker } from 'react-router';
import { useAppStore } from '@/store';
import { Button, Dialog } from '@/ui';

/** Confirms before leaving a topology with unsaved edits (in-app and on tab close). */
export function UnsavedChangesGuard({ onSave }: { onSave: () => Promise<boolean> }) {
  const dirty = useAppStore((s) => s.dirty);

  const blocker = useBlocker(({ currentLocation, nextLocation }) => {
    if (!dirty) return false;
    const cur = currentLocation.pathname.split('/')[2];
    const next = nextLocation.pathname.split('/')[2];
    return cur !== next; // scope navigation within the same topology is fine
  });

  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => { e.preventDefault(); };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);

  const open = blocker.state === 'blocked';
  return (
    <Dialog
      open={open}
      onOpenChange={(o) => { if (!o && blocker.state === 'blocked') blocker.reset(); }}
      title="Unsaved changes"
      description="Save your work before leaving this topology?"
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={() => blocker.state === 'blocked' && blocker.reset()}>Cancel</Button>
          <Button variant="danger-soft" onClick={() => blocker.state === 'blocked' && blocker.proceed()}>Discard</Button>
          <Button variant="primary" onClick={async () => { if (await onSave() && blocker.state === 'blocked') blocker.proceed(); }}>Save and leave</Button>
        </>
      }
    >
      <p className="text-xs text-fg-muted">Discarding loses every change since the last save.</p>
    </Dialog>
  );
}
