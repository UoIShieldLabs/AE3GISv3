import { Archive, Square, TimerReset } from 'lucide-react';
import { useAppStore } from '@/store';
import { useAppShallow } from '@/store/selectors';
import { Button, Dialog } from '@/ui';
import { destroyTopology } from './actions';

/** How to stop a lab: keep it running, save its nodes and destroy, or destroy. */
export function DestroyDialog() {
  const { open, savedState } = useAppShallow((s) => ({ open: s.destroyDialogOpen, savedState: s.savedState }));
  const close = () => useAppStore.getState().setDestroyDialogOpen(false);
  const destroy = (save: boolean) => { close(); void destroyTopology({ save }); };

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => { if (!o) close(); }}
      title="Destroy the lab?"
      description="Destroying removes every container, along with the changes made inside them."
      size="md"
      footer={
        <>
          <Button variant="ghost" onClick={close}><TimerReset /> Keep running</Button>
          <Button variant="danger-soft" onClick={() => destroy(false)}><Square /> Destroy without saving</Button>
          <Button variant="primary" onClick={() => destroy(true)} autoFocus><Archive /> Save &amp; destroy</Button>
        </>
      }
    >
      <div className="space-y-3 text-xs text-fg-muted">
        <p>
          <span className="font-medium text-fg">Keep running</span> to come back later: the lab stays up while you are away
          (it keeps using the host's memory and CPU).
        </p>
        <p>
          <span className="font-medium text-fg">Save &amp; destroy</span> keeps each node's files (edited configs, created files,
          installed packages) and firewall rules, and the next deploy picks up from there. Running programs and open shells
          are not saved; addresses and routes are set again from the design.
        </p>
        <p>
          <span className="font-medium text-fg">Destroy without saving</span> discards this session's changes.
          {savedState ? ' The earlier saved state is kept.' : ''}
        </p>
      </div>
    </Dialog>
  );
}
